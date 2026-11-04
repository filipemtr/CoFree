import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_exposures: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActionToken(Base):
    __tablename__ = 'action_tokens'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)


class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str] = mapped_column(String(240), default='Desconhecido')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)


class MonitoredEmail(Base):
    __tablename__ = 'monitored_emails'
    __table_args__ = (UniqueConstraint('user_id', 'email', name='uq_owner_email'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    email: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(32), default='pending')
    last_checked: Mapped[datetime | None] = mapped_column(DateTime)
    next_check: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MonitoringPreference(Base):
    """User opt-in scheduling. No Vault password data or password hashes are stored."""
    __tablename__ = 'monitoring_preferences'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_interval: Mapped[str] = mapped_column(String(8), default='24h', nullable=False)
    password_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_interval: Mapped[str] = mapped_column(String(8), default='7d', nullable=False)


class Check(Base):
    __tablename__ = 'checks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitor_id: Mapped[str] = mapped_column(ForeignKey('monitored_emails.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str | None] = mapped_column(String(250))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Exposure(Base):
    __tablename__ = 'exposures'
    __table_args__ = (UniqueConstraint('monitor_id', 'breach_name', name='uq_monitor_breach'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    monitor_id: Mapped[str] = mapped_column(ForeignKey('monitored_emails.id', ondelete='CASCADE'), index=True)
    breach_name: Mapped[str] = mapped_column(String(240))
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VaultConfig(Base):
    __tablename__ = 'vault_configs'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    salt: Mapped[str] = mapped_column(String(100))
    iterations: Mapped[int] = mapped_column(Integer)
    memory_kib: Mapped[int] = mapped_column(Integer)
    wrapped_key: Mapped[str] = mapped_column(Text)
    recovery_wrapped_key: Mapped[str] = mapped_column(Text)
    recovery_salt: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)


class VaultItem(Base):
    __tablename__ = 'vault_items'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(String(450))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    action: Mapped[str] = mapped_column(String(90))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


Index('ix_check_time', Check.monitor_id, Check.created_at)
