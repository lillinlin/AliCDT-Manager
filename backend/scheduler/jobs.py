from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from models.database import AsyncSessionLocal, Account, Instance, Log, Settings
from core.aliyun import AliyunClient
import httpx

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


async def add_important_log(category: str, message: str):
    async with AsyncSessionLocal() as db:
        log = Log(level="info", category=category, message=message)
        db.add(log)
        await db.commit()


async def add_log(level: str, category: str, message: str):
    if level == "info":
        return
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
        async with AsyncSessionLocal() as db:
            db.add(Log(level="warning", category="notify", message=f"TG通知发送失败: {e}"))
            await db.commit()


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

            if percent >= account.threshold_percent:
                if account.instance_id:
                    await client.stop_instance(account.instance_id, account.shutdown_mode)
                    await send_tg_notify(
                        f"🚨 <b>流量熔断触发</b>\n"
                        f"账户: {account.name}\n"
                        f"已用: {traffic_gb}GB ({percent}%)\n"
                        f"阈值: {account.threshold_percent}%\n"
                        f"动作: 自动停机（{account.shutdown_mode}）"
                    )
                    await add_important_log("traffic", f"[{account.name}] 流量熔断 {traffic_gb}GB/{percent}%，已停机")

        except Exception as e:
            async with AsyncSessionLocal() as db:
                db.add(Log(level="error", category="traffic", message=f"[{account.name}] 流量巡检失败: {e}"))
                await db.commit()


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
                account.access_key_id, account.access_key_secret,
                account.region_id, account.site_type,
            )
            status = await client.get_instance_status(account.instance_id)

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.instance_id == account.instance_id)
                    .values(status=status, updated_at=datetime.utcnow())
                )
                await db.commit()

            if status == "Stopped":
                await client.start_instance(account.instance_id)
                await send_tg_notify(
                    f"⚡ <b>保活触发</b>\n"
                    f"账户: {account.name}\n"
                    f"实例: {account.instance_id}\n"
                    f"检测到停机，已自动拉起"
                )
                await add_important_log("keepalive", f"[{account.name}] 实例 {account.instance_id} 被回收，已自动拉起")

        except Exception as e:
            async with AsyncSessionLocal() as db:
                db.add(Log(level="error", category="keepalive", message=f"[{account.name}] 保活检测失败: {e}"))
                await db.commit()


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
                await add_important_log("scheduler", f"[{account.name}] 定时开机执行 {now}")
                await send_tg_notify(f"⏰ <b>定时开机</b>\n账户: {account.name}\n时间: {now}")

            if account.auto_stop_time and account.auto_stop_time == now:
                await client.stop_instance(account.instance_id, account.shutdown_mode)
                await add_important_log("scheduler", f"[{account.name}] 定时关机执行 {now}")
                await send_tg_notify(f"⏰ <b>定时关机</b>\n账户: {account.name}\n时间: {now}")

        except Exception as e:
            async with AsyncSessionLocal() as db:
                db.add(Log(level="error", category="scheduler", message=f"[{account.name}] 定时任务失败: {e}"))
                await db.commit()


async def sync_instances():
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
            async with AsyncSessionLocal() as db:
                db.add(Log(level="error", category="system", message=f"[{account.name}] 实例同步失败: {e}"))
                await db.commit()


async def _do_daily_report():
    """实际发送逻辑，不检查开关，测试和定时任务都可以调用"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()
        result2 = await db.execute(select(Instance))
        instances = result2.scalars().all()

    instance_map = {i.account_id: i for i in instances}

    lines = [
        "📊 <b>每日流量汇报</b>",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} (北京时间)",
        "",
    ]

    for account in accounts:
        inst = instance_map.get(account.id)
        if inst:
            bar_filled = int((inst.traffic_percent or 0) / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            status_icon = "🟢" if inst.status == "Running" else "🔴"
            lines.append(
                f"{status_icon} <b>{account.name}</b>\n"
                f"  流量: {inst.traffic_used_gb:.2f}GB / {account.traffic_limit_gb}GB\n"
                f"  [{bar}] {inst.traffic_percent:.1f}%\n"
                f"  熔断阈值: {account.threshold_percent}%\n"
                f"  状态: {inst.status}"
            )
        else:
            lines.append(f"⚪ <b>{account.name}</b>\n  暂无实例数据")

    await send_tg_notify("\n".join(lines))
    await add_important_log("system", "每日流量汇报已发送")


async def daily_traffic_report():
    """定时任务调用，受开关控制"""
    enabled = await get_setting("tg_daily_report", "0")
    if enabled != "1":
        return
    await _do_daily_report()


def start_scheduler():
    scheduler.add_job(traffic_check, IntervalTrigger(minutes=10), id="traffic_check", replace_existing=True)
    scheduler.add_job(keep_alive_check, IntervalTrigger(minutes=1), id="keep_alive", replace_existing=True)
    scheduler.add_job(scheduled_power, IntervalTrigger(minutes=1), id="scheduled_power", replace_existing=True)
    scheduler.add_job(sync_instances, IntervalTrigger(minutes=2), id="sync_instances", replace_existing=True)
    scheduler.add_job(daily_traffic_report, CronTrigger(hour=0, minute=0), id="daily_report", replace_existing=True)
    scheduler.start()
