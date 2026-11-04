from datetime import timedelta
from sqlalchemy.orm import Session as DbSession
from .models import MonitoredEmail, Check, Exposure, Notification, User, AuditEvent, MonitoringPreference, utcnow
from .providers.xposedornot import find_breaches, ProviderError


INTERVAL_HOURS = {'1h': 1, '24h': 24, '7d': 168, '30d': 720}


def monitoring_preference(db: DbSession, user_id: str) -> MonitoringPreference:
    pref = db.get(MonitoringPreference, user_id)
    if pref is None:
        pref = MonitoringPreference(user_id=user_id, email_enabled=True, email_interval='24h',
                                    password_enabled=False, password_interval='7d')
        db.add(pref)
        db.flush()
    return pref


def next_email_check(db: DbSession, monitor: MonitoredEmail):
    pref = db.get(MonitoringPreference, monitor.user_id)
    if pref is not None and not pref.email_enabled:
        return None
    interval = INTERVAL_HOURS.get(pref.email_interval if pref is not None else '24h', 24)
    return utcnow() + timedelta(hours=interval)


def audit(db: DbSession, user_id: str, action: str):
    db.add(AuditEvent(user_id=user_id, action=action))


def scan_monitor(db: DbSession, monitor: MonitoredEmail) -> str:
    """Idempotent scan. On provider error preserves existing exposures, records error state."""
    try:
        breaches = find_breaches(monitor.email)
    except ProviderError as e:
        monitor.status = 'unavailable'
        db.add(Check(monitor_id=monitor.id, status='unavailable', detail=str(e)[:250]))
        monitor.next_check = utcnow() + timedelta(seconds=max(60, e.retry_after or 3600))
        db.commit()
        return 'unavailable'

    known = {e.breach_name for e in db.query(Exposure).filter_by(monitor_id=monitor.id)}
    fresh = set(breaches) - known
    for name in sorted(fresh):
        db.add(Exposure(monitor_id=monitor.id, breach_name=name))
        db.add(Notification(user_id=monitor.user_id, title='Nova exposição identificada', message=f'Um e-mail monitorado foi encontrado no vazamento {name}. Verifique suas contas.'))
    monitor.status = 'exposed' if breaches else 'clear'
    monitor.last_checked = utcnow()
    monitor.next_check = next_email_check(db, monitor)
    db.add(Check(monitor_id=monitor.id, status=monitor.status, detail=f'{len(breaches)} exposições conhecidas'))
    if fresh:
        audit(db, monitor.user_id, 'exposure.new')
    db.commit()
    if fresh:
        owner = db.get(User, monitor.user_id)
        if owner and owner.notify_exposures:
            # Notification stays in app even if SMTP fails.
            from .emailer import send_email
            send_email(owner.email, 'CoFree | Nova exposição identificada', f'Identificamos {len(fresh)} nova(s) exposição(ões) em um e-mail monitorado. Acesse sua conta para ver os detalhes.')
    return monitor.status
