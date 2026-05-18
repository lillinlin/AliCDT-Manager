from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    access_key_id = Column(String, nullable=False)
    access_key_secret = Column(String, nullable=False)
    region_id = Column(String, nullable=False)
    site_type = Column(String, default="international")
    instance_id = Column(String, nullable=True)
    traffic_limit_gb = Column(Float, default=200.0)
    threshold_percent = Column(Float, default=95.0)
    shutdown_mode = Column(String, default="StopCharging")
    keep_alive = Column(Boolean, default=False)
    auto_start_time = Column(String, nullable=True)
    auto_stop_time = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Instance(Base):
    __tablename__ = "instances"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    instance_id = Column(String, nullable=False, unique=True)
    instance_name = Column(String, nullable=True)
    region_id = Column(String, nullable=True)
    status = Column(String, default="Unknown")
    public_ip = Column(String, nullable=True)
    instance_type = Column(String, nullable=True)
    bandwidth_mbps = Column(Integer, default=0)
    traffic_used_gb = Column(Float, default=0.0)
    traffic_percent = Column(Float, default=0.0)
    is_spot = Column(Boolean, default=False)
    last_synced = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BillingCache(Base):
    __tablename__ = "billing_cache"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    cache_type = Column(String, nullable=False)
    billing_cycle = Column(String, default="")
    data = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, default="info")
    category = Column(String, default="system")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)

DATABASE_URL = "sqlite+aiosqlite:////app/data/guard.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
