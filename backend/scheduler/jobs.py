import asyncio
import json
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from models.database import AsyncSessionLocal, Account, Instance, BillingCache, Log, Settings
from core.aliyun import AliyunClient
import httpx

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def add_log(level: str, category: str, message: str):
    async with AsyncSessionLocal() as db:
        log = Log(level=level, category=category, message=message)
        db.add(log)
        await db.commit()


async def get_setting(key: str, default=None):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Settings).where(Settings.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else default


async def send_tg_notify(message: str):
    bot_token = await get_setting("tg_bot_token")
    chat_id = await get_setting("tg_chat_id")
    if not bot_token or not chat_id:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            )
    except Exception as e:
        await add_log("warning", "notify", f"TG通知发送失败: {e}")


# ==================== 流量巡检 ====================
async def traffic_check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        try:
            client = AliyunClient(
                account.access_key_id,
                account.access_key_secret,
                account.region_id,
                account.site_type,
            )
            traffic_gb = await client.get_cdt_traffic()
            limit = account.traffic_limit_gb or 200.0
            percent = round(traffic_gb / limit * 100, 2)

            # 更新实例记录
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.account_id == account.id)
                    .values(
                        traffic_used_gb=traffic_gb,
                        traffic_percent=percent,
                        last_synced=datetime.utcnow(),
                    )
                )
                await db.commit()

            await add_log("info", "traffic", f"[{account.name}] 流量: {traffic_gb}GB / {percent}%")

            # 熔断
            if percent >= account.threshold_percent:
                if account.instance_id:
                    await client.stop_instance(account.instance_id, account.shutdown_mode)
                    msg = (
                        f"🚨 <b>流量熔断触发</b>\n"
                        f"账户: {account.name}\n"
                        f"已用: {traffic_gb}GB ({percent}%)\n"
                        f"阈值: {account.threshold_percent}%\n"
                        f"动作: 自动停机 ({account.shutdown_mode})"
                    )
                    await send_tg_notify(msg)
                    await add_log("warning", "traffic", f"[{account.name}] 熔断触发，已执行停机")

        except Exception as e:
            await add_log("error", "traffic", f"[{account.name}] 流量巡检失败: {e}")


# ==================== 实例保活 ====================
async def keep_alive_check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Account).where(Account.enabled == True, Account.keep_alive == True)
        )
        accounts = result.scalars().all()

    for account in accounts:
        if not account.instance_id:
            continue
        try:
            client = AliyunClient(
                account.access_key_id,
                account.access_key_secret,
                account.region_id,
                account.site_type,
            )
            status = await client.get_instance_status(account.instance_id)

            # 更新状态
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.instance_id == account.instance_id)
                    .values(status=status, updated_at=datetime.utcnow())
                )
                await db.commit()

            # 非预期停机则重新拉起
            if status == "Stopped":
                await client.start_instance(account.instance_id)
                await add_log("warning", "keepalive", f"[{account.name}] 实例被回收，已自动拉起")
                await send_tg_notify(
                    f"⚡ <b>保活触发</b>\n账户: {account.name}\n实例: {account.instance_id}\n已自动重启"
                )
        except Exception as e:
            await add_log("error", "keepalive", f"[{account.name}] 保活检测失败: {e}")


# ==================== 定时开关机 ====================
async def scheduled_power():
    now = datetime.now().strftime("%H:%M")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        if not account.instance_id:
            continue
        client = AliyunClient(
            account.access_key_id,
            account.access_key_secret,
            account.region_id,
            account.site_type,
        )
        try:
            if account.auto_start_time and account.auto_start_time == now:
                await client.start_instance(account.instance_id)
                await add_log("info", "scheduler", f"[{account.name}] 定时开机执行")

            if account.auto_stop_time and account.auto_stop_time == now:
                await client.stop_instance(account.instance_id, account.shutdown_mode)
                await add_log("info", "scheduler", f"[{account.name}] 定时关机执行")
        except Exception as e:
            await add_log("error", "scheduler", f"[{account.name}] 定时任务失败: {e}")


# ==================== 同步实例列表 ====================
async def sync_instances():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        try:
            client = AliyunClient(
                account.access_key_id,
                account.access_key_secret,
                account.region_id,
                account.site_type,
            )
            instances = await client.get_instances()
            async with AsyncSessionLocal() as db:
                for inst in instances:
                    result = await db.execute(
                        select(Instance).where(Instance.instance_id == inst["instance_id"])
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        # 检测IP变化，触发DDNS
                        if existing.public_ip != inst["public_ip"] and inst["public_ip"]:
                            if account.cf_zone_id and account.cf_api_token and account.cf_record_name:
                                try:
                                    await client.update_cf_dns(
                                        account.cf_zone_id,
                                        account.cf_api_token,
                                        account.cf_record_name,
                                        inst["public_ip"],
                                    )
                                    await add_log("info", "ddns", f"[{account.name}] DDNS更新: {inst['public_ip']}")
                                except Exception as e:
                                    await add_log("error", "ddns", f"[{account.name}] DDNS更新失败: {e}")
                        existing.status = inst["status"]
                        existing.public_ip = inst["public_ip"]
                        existing.instance_name = inst["instance_name"]
                        existing.is_spot = inst["is_spot"]
                        existing.last_synced = datetime.utcnow()
                    else:
                        new_inst = Instance(
                            account_id=account.id,
                            **{k: v for k, v in inst.items()}
                        )
                        db.add(new_inst)
                await db.commit()
        except Exception as e:
            await add_log("error", "system", f"[{account.name}] 实例同步失败: {e}")


def start_scheduler():
    # 流量巡检每10分钟
    scheduler.add_job(traffic_check, IntervalTrigger(minutes=10), id="traffic_check", replace_existing=True)
    # 保活每2分钟
    scheduler.add_job(keep_alive_check, IntervalTrigger(minutes=2), id="keep_alive", replace_existing=True)
    # 定时开关机每分钟检查
    scheduler.add_job(scheduled_power, IntervalTrigger(minutes=1), id="scheduled_power", replace_existing=True)
    # 实例同步每5分钟
    scheduler.add_job(sync_instances, IntervalTrigger(minutes=5), id="sync_instances", replace_existing=True)
    scheduler.start()
