import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from jose import jwt
from passlib.context import CryptContext

from models.database import init_db, get_db, Account, Instance, Log, Settings
from core.aliyun import AliyunClient
from scheduler.jobs import start_scheduler, sync_instances, traffic_check, add_log

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-change-me")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_token(username: str):
    expire = datetime.utcnow() + timedelta(days=7)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未授权")
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    return user

app = FastAPI(title="AliCDT Manager", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    await init_db()
    start_scheduler()

class LoginRequest(BaseModel):
    username: str
    password: str

class AccountCreate(BaseModel):
    name: str
    access_key_id: str
    access_key_secret: Optional[str] = None
    region_id: str
    site_type: str = "international"
    instance_id: Optional[str] = None
    traffic_limit_gb: float = 200.0
    threshold_percent: float = 95.0
    shutdown_mode: str = "StopCharging"
    keep_alive: bool = False
    auto_start_time: Optional[str] = None
    auto_stop_time: Optional[str] = None

class SettingUpdate(BaseModel):
    key: str
    value: str

@app.get("/api/auth/initialized")
async def is_initialized(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == "admin_password_hash"))
    return {"initialized": result.scalar_one_or_none() is not None}

@app.post("/api/auth/init")
async def init_admin(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == "admin_password_hash"))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="已初始化，请直接登录")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    hashed = pwd_context.hash(req.password)
    db.add(Settings(key="admin_username", value=req.username))
    db.add(Settings(key="admin_password_hash", value=hashed))
    await db.commit()
    return {"token": create_token(req.username), "username": req.username}

@app.post("/api/auth/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings).where(Settings.key == "admin_username"))
    username_row = result.scalar_one_or_none()
    result = await db.execute(select(Settings).where(Settings.key == "admin_password_hash"))
    password_row = result.scalar_one_or_none()
    if not username_row or not password_row:
        raise HTTPException(status_code=403, detail="系统未初始化")
    if req.username != username_row.value or not pwd_context.verify(req.password, password_row.value):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": create_token(req.username), "username": req.username}

@app.get("/api/accounts")
async def list_accounts(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account))
    accounts = result.scalars().all()
    return [
        {k: v for k, v in acc.__dict__.items() if k != "_sa_instance_state" and k != "access_key_secret"}
        for acc in accounts
    ]

@app.post("/api/accounts")
async def create_account(data: AccountCreate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not data.access_key_secret:
        raise HTTPException(status_code=400, detail="新建账户必须填写 AccessKey Secret")
    acc = Account(**data.model_dump())
    db.add(acc)
    await db.commit()
    await db.refresh(acc)
    await sync_instances()
    return {"id": acc.id, "message": "账户已添加"}

@app.put("/api/accounts/{account_id}")
async def update_account(account_id: int, data: AccountCreate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404, detail="账户不存在")
    update_data = data.model_dump()
    if not update_data.get("access_key_secret"):
        update_data.pop("access_key_secret")
    for k, v in update_data.items():
        setattr(acc, k, v)
    await db.commit()
    return {"message": "更新成功"}

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Instance).where(Instance.account_id == account_id))
    await db.execute(delete(Account).where(Account.id == account_id))
    await db.commit()
    return {"message": "删除成功"}

@app.get("/api/instances")
async def list_instances(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instance))
    instances = result.scalars().all()
    return [{k: v for k, v in i.__dict__.items() if k != "_sa_instance_state"} for i in instances]

@app.post("/api/instances/sync")
async def manual_sync(user=Depends(get_current_user)):
    await sync_instances()
    await traffic_check()
    return {"message": "同步完成"}

@app.post("/api/instances/{instance_id}/start")
async def start_instance(instance_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instance).where(Instance.instance_id == instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404)
    result = await db.execute(select(Account).where(Account.id == inst.account_id))
    acc = result.scalar_one_or_none()
    client = AliyunClient(acc.access_key_id, acc.access_key_secret, acc.region_id, acc.site_type)
    await client.start_instance(instance_id)
    await add_log("info", "system", f"手动开机: {instance_id}")
    return {"message": "开机指令已发送"}

@app.post("/api/instances/{instance_id}/stop")
async def stop_instance(instance_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instance).where(Instance.instance_id == instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404)
    result = await db.execute(select(Account).where(Account.id == inst.account_id))
    acc = result.scalar_one_or_none()
    client = AliyunClient(acc.access_key_id, acc.access_key_secret, acc.region_id, acc.site_type)
    await client.stop_instance(instance_id, acc.shutdown_mode)
    await add_log("info", "system", f"手动关机: {instance_id}")
    return {"message": "关机指令已发送"}

@app.delete("/api/instances/{instance_id}")
async def release_instance(instance_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instance).where(Instance.instance_id == instance_id))
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404)
    result = await db.execute(select(Account).where(Account.id == inst.account_id))
    acc = result.scalar_one_or_none()
    client = AliyunClient(acc.access_key_id, acc.access_key_secret, acc.region_id, acc.site_type)
    await client.delete_instance(instance_id)
    await db.execute(delete(Instance).where(Instance.instance_id == instance_id))
    await db.commit()
    await add_log("warning", "system", f"释放实例: {instance_id}")
    return {"message": "实例已释放"}

@app.get("/api/billing/{account_id}")
async def get_billing(account_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    acc = result.scalar_one_or_none()
    if not acc:
        raise HTTPException(status_code=404)
    client = AliyunClient(acc.access_key_id, acc.access_key_secret, acc.region_id, acc.site_type)
    balance = await client.get_balance()
    bill = await client.get_bill_overview()
    return {"balance": balance, "bill": bill}

@app.get("/api/settings")
async def get_settings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Settings))
    rows = result.scalars().all()
    return {r.key: r.value for r in rows if "password_hash" not in r.key}

@app.post("/api/settings")
async def update_settings(items: List[SettingUpdate], user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for item in items:
        result = await db.execute(select(Settings).where(Settings.key == item.key))
        row = result.scalar_one_or_none()
        if row:
            row.value = item.value
        else:
            db.add(Settings(key=item.key, value=item.value))
    await db.commit()
    return {"message": "保存成功"}

@app.post("/api/settings/change-password")
async def change_password(data: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_hash = pwd_context.hash(data.get("password", ""))
    result = await db.execute(select(Settings).where(Settings.key == "admin_password_hash"))
    row = result.scalar_one_or_none()
    if row:
        row.value = new_hash
    await db.commit()
    return {"message": "密码已更新"}

@app.get("/api/logs")
async def get_logs(category: Optional[str] = None, limit: int = 100, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(Log).order_by(Log.id.desc()).limit(limit)
    if category:
        query = select(Log).where(Log.category == category).order_by(Log.id.desc()).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [{k: v for k, v in l.__dict__.items() if k != "_sa_instance_state"} for l in logs]

@app.delete("/api/logs")
async def clear_logs(category: Optional[str] = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if category:
        await db.execute(delete(Log).where(Log.category == category))
    else:
        await db.execute(delete(Log))
    await db.commit()
    return {"message": "日志已清空"}

if os.path.exists("/app/frontend/dist"):
    app.mount("/assets", StaticFiles(directory="/app/frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        return FileResponse("/app/frontend/dist/index.html")
