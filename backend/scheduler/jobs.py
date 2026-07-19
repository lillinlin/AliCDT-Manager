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

            trigger_reason = None

            if percent >= account.threshold_percent and not account.manual_stopped:
                trigger_reason = f"流量超阈值 {traffic_gb}GB/{percent}%（阈值{account.threshold_percent}%）"

            if not trigger_reason and account.outstanding_threshold and account.outstanding_threshold > 0 and not account.manual_stopped:
                try:
                    bill = await client.get_bill_overview()
                    outstanding = bill.get("total_outstanding", 0)
                    if outstanding >= account.outstanding_threshold:
                        symbol = bill.get("symbol", "$")
                        trigger_reason = f"待还金额超阈值 {symbol}{outstanding}（阈值{symbol}{account.outstanding_threshold}）"
                except Exception:
                    pass

            if trigger_reason and account.instance_id:
                async with AsyncSessionLocal() as db:
                    inst_result = await db.execute(
                        select(Instance).where(Instance.instance_id == account.instance_id)
                    )
                    inst = inst_result.scalar_one_or_none()

                if inst and inst.status != "Stopped":
                    await client.stop_instance(account.instance_id, account.shutdown_mode)
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(Account).where(Account.id == account.id).values(manual_stopped=True)
                        )
                        await db.commit()
                    await send_tg_notify(
                        f"🚨 <b>熔断触发</b>\n"
                        f"账户: {account.name}\n"
                        f"原因: {trigger_reason}\n"
                        f"动作: 自动停机（{account.shutdown_mode}）"
                    )
                    await add_important_log("traffic", f"[{account.name}] 熔断: {trigger_reason}，已停机")

        except Exception:
            pass


async def keep_alive_check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Account).where(Account.enabled == True, Account.keep_alive == True)
        )
        accounts = result.scalars().all()

    for account in accounts:
        if not account.instance_id:
            continue
        if account.manual_stopped:
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

        except Exception:
            pass


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
            if account.auto_stop_time and account.auto_stop_time == now:
                await client.stop_instance(account.instance_id, account.shutdown_mode)
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Account).where(Account.id == account.id).values(manual_stopped=True)
                    )
                    await db.commit()
                await add_important_log("scheduler", f"[{account.name}] 定时关机执行 {now}")
                await send_tg_notify(f"⏰ <b>定时关机</b>\n账户: {account.name}\n时间: {now}")

            if account.auto_start_time and account.auto_start_time == now:
                await client.start_instance(account.instance_id)
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(Account).where(Account.id == account.id).values(manual_stopped=False)
                    )
                    await db.commit()
                await add_important_log("scheduler", f"[{account.name}] 定时开机执行 {now}")
                await send_tg_notify(f"⏰ <b>定时开机</b>\n账户: {account.name}\n时间: {now}")

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
                        existing.is_spot = inst["is_spot"]
                        existing.bandwidth_mbps = inst["bandwidth_mbps"]
                        existing.last_synced = datetime.utcnow()
                    else:
                        new_inst = Instance(account_id=account.id, **inst)
                        db.add(new_inst)
                await db.commit()
        except Exception:
            pass


async def monthly_reset():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()

    restarted = []
    for account in accounts:
        if not account.manual_stopped:
            continue
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Account).where(Account.id == account.id).values(manual_stopped=False)
                )
                await db.commit()

            if account.instance_id:
                client = AliyunClient(
                    account.access_key_id, account.access_key_secret,
                    account.region_id, account.site_type,
                )
                await client.start_instance(account.instance_id)
                restarted.append(account.name)

        except Exception:
            pass

    if restarted:
        await send_tg_notify(
            f"🔄 <b>每月流量重置</b>\n"
            f"新的一个月开始，以下账户已自动恢复并启动：\n"
            + "\n".join(f"  • {name}" for name in restarted)
        )
        await add_important_log("system", f"每月重置，已恢复并启动: {', '.join(restarted)}")


async def _do_daily_report():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Account).where(Account.enabled == True))
        accounts = result.scalars().all()
        result2 = await db.execute(select(Instance))
        instances = result2.scalars().all()

    instance_map = {i.account_id: i for i in instances}

    lines = [
        "📊 <b>每日流量汇报</b>",
        f"🕛 {datetime.now().strftime('%Y-%m-%d %H:%M')} 北京时间",
        "━━━━━━━━━━━━━━━━",
    ]

    for account in accounts:
        inst = instance_map.get(account.id)
        status_icon = "🟢" if (inst and inst.status == "Running") else "🔴"

        if inst:
            bar_filled = int((inst.traffic_percent or 0) / 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            display_name = inst.instance_name or account.name
            block = (
                f"{status_icon} <b>{display_name}</b>\n"
                f"  📡 流量: {inst.traffic_used_gb:.2f}GB / {account.traffic_limit_gb}GB\n"
                f"  [{bar}] {inst.traffic_percent:.1f}%  熔断: {account.threshold_percent}%\n"
                f"  🖥 状态: {inst.status}  地域: {inst.region_id or '—'}"
            )
            try:
                client = AliyunClient(
                    account.access_key_id, account.access_key_secret,
                    account.region_id, account.site_type,
                )
                balance = await client.get_balance()
                bill = await client.get_bill_overview()
                symbol = balance.get("symbol", "$") if balance else "$"
                avail = balance.get("available_amount", 0) if balance else 0
                outst = bill.get("total_outstanding", 0) if bill else 0
                block += f"\n  💰 余额: {symbol}{avail}  待还: {symbol}{outst}"
            except Exception:
                block += "\n  💰 账单获取失败"
        else:
            block = f"⚪ <b>{account.name}</b>\n  暂无实例数据"

        lines.append(block)
        lines.append("━━━━━━━━━━━━━━━━")

    await send_tg_notify("\n".join(lines))
    await add_important_log("system", "每日流量汇报已发送")


async def daily_traffic_report():
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
    scheduler.add_job(monthly_reset, CronTrigger(day=1, hour=0, minute=1), id="monthly_reset", replace_existing=True)
    scheduler.start()
