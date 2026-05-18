from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update, delete
from models.database import AsyncSessionLocal, Account, Instance, Log, Settings
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


async def traffic_check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        try:
            client = AliyunClient(
                account.access_key_id, account.access_key_secret,
                account.region_id, account.site_type,
            )
            traffic_gb = await client.get_cdt_traffic()
            limit = account.traffic_limit_gb or 200.0
            percent = round(traffic_gb / limit * 100, 2)

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.account_id == account.id)
                    .values(traffic_used_gb=traffic_gb, traffic_percent=percent, last_synced=datetime.utcnow())
                )
                await db.commit()

            await add_log("info", "traffic", f"[{account.name}] 流量: {traffic_gb}GB / {percent}%")

            if percent >= account.threshold_percent:
                if account.instance_id:
                    await client.stop_instance(account.instance_id, account.shutdown_mode)
                    await send_tg_notify(
                        f"🚨 <b>流量熔断</b>\n账户: {account.name}\n已用: {traffic_gb}GB ({percent}%)\n已自动停机"
                    )
                    await add_log("warning", "traffic", f"[{account.name}] 熔断触发，已停机")
        except Exception as e:
            await add_log("error", "traffic", f"[{account.name}] 流量巡检失败: {e}")


async def keep_alive_check():
    """每1分钟执行，实时查询实例状态，发现停机立即拉起"""
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
                account.access_key_id, account.access_key_secret,
                account.region_id, account.site_type,
            )
            # 直接调 API 实时获取状态，不依赖数据库缓存
            status = await client.get_instance_status(account.instance_id)

            # 同步状态到数据库
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.instance_id == account.instance_id)
                    .values(status=status, updated_at=datetime.utcnow())
                )
                await db.commit()

            if status == "Stopped":
                await add_log("warning", "keepalive", f"[{account.name}] 检测到停机，正在拉起...")
                await client.start_instance(account.instance_id)
                await add_log("warning", "keepalive", f"[{account.name}] 已发送开机指令")
                await send_tg_notify(
                    f"⚡ <b>保活触发</b>\n账户: {account.name}\n实例: {account.instance_id}\n已自动重启"
                )
        except Exception as e:
            await add_log("error", "keepalive", f"[{account.name}] 保活检测失败: {e}")


async def scheduled_power():
    now = datetime.now().strftime("%H:%M")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        if not account.instance_id:
            continue
        client = AliyunClient(
            account.access_key_id, account.access_key_secret,
            account.region_id, account.site_type,
        )
        try:
            if account.auto_start_time and account.auto_start_time == now:
                await client.start_instance(account.instance_id)
                await add_log("info", "scheduler", f"[{account.name}] 定时开机")
            if account.auto_stop_time and account.auto_stop_time == now:
                await client.stop_instance(account.instance_id, account.shutdown_mode)
                await add_log("info", "scheduler", f"[{account.name}] 定时关机")
        except Exception as e:
            await add_log("error", "scheduler", f"[{account.name}] 定时任务失败: {e}")


async def sync_instances():
    """每2分钟同步一次实例列表和状态"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    for account in accounts:
        try:
            client = AliyunClient(
                account.access_key_id, account.access_key_secret,
                account.region_id, account.site_type,
            )
            instances = await client.get_instances()
            async with AsyncSessionLocal() as db:
                for inst in instances:
                    result = await db.execute(
                        select(Instance).where(Instance.instance_id == inst["instance_id"])
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.status = inst["status"]
                        existing.public_ip = inst["public_ip"]
                        existing.instance_name = inst.get("instance_name") or existing.instance_name
                        existing.is_spot = inst["is_spot"]
                        existing.bandwidth_mbps = inst["bandwidth_mbps"]
                        existing.last_synced = datetime.utcnow()
                    else:
                        new_inst = Instance(account_id=account.id, **inst)
                        db.add(new_inst)
                await db.commit()
        except Exception as e:
            await add_log("error", "system", f"[{account.name}] 实例同步失败: {e}")


def start_scheduler():
    # 流量巡检每10分钟
    scheduler.add_job(traffic_check, IntervalTrigger(minutes=10), id="traffic_check", replace_existing=True)
    # 保活每1分钟，实时查API
    scheduler.add_job(keep_alive_check, IntervalTrigger(minutes=1), id="keep_alive", replace_existing=True)
    # 定时开关机每分钟检查
    scheduler.add_job(scheduled_power, IntervalTrigger(minutes=1), id="scheduled_power", replace_existing=True)
    # 实例状态同步每2分钟
    scheduler.add_job(sync_instances, IntervalTrigger(minutes=2), id="sync_instances", replace_existing=True)
    scheduler.start()
