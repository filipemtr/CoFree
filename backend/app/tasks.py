"""Scheduled monitor checks; no plaintext Vault secrets ever enter these tasks."""
from celery import Celery
from datetime import timedelta
from sqlalchemy import or_
from .settings import get_settings
from .db import SessionLocal
from .models import MonitoredEmail, MonitoringPreference, utcnow
from .services import scan_monitor

s = get_settings()
celery = Celery('cofree', broker=s.redis_url, backend=s.redis_url)
celery.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_track_started=True,
                   broker_connection_retry_on_startup=True, timezone='UTC',
                   beat_schedule={'scan-due-monitors': {'task': 'cofree.tasks.scan_due', 'schedule': 300.0}})


@celery.task(name='cofree.tasks.scan_one', bind=True, max_retries=4)
def scan_one(self, monitor_id: str):
    with SessionLocal() as db:
        row = db.get(MonitoredEmail, monitor_id)
        if not row:
            return 'deleted'
        return scan_monitor(db, row)


@celery.task(name='cofree.tasks.scan_due')
def scan_due():
    with SessionLocal() as db:
        due = (db.query(MonitoredEmail)
               .outerjoin(MonitoringPreference, MonitoringPreference.user_id == MonitoredEmail.user_id)
               .filter(MonitoredEmail.next_check <= utcnow())
               .filter(or_(MonitoringPreference.user_id.is_(None), MonitoringPreference.email_enabled.is_(True)))
               .order_by(MonitoredEmail.next_check.asc()).limit(2).all())
        ids = [row.id for row in due]
        for row in due:
            row.status = 'queued'
            row.next_check = utcnow() + timedelta(minutes=10)
        db.commit()
    for monitor_id in ids:
        scan_one.delay(monitor_id)
    return {'queued': len(ids)}
