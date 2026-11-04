from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import func
from ..db import get_db
from ..models import MonitoredEmail, Check, Exposure, User, Notification, VaultItem, MonitoringPreference, utcnow
from ..dependencies import verified_user
from ..schemas import EmailInput, MonitoringPreferenceUpdate
from ..services import audit, monitoring_preference, INTERVAL_HOURS

router = APIRouter(tags=['Monitoramento'])


def serialize_monitor(m):
    return {'id': m.id, 'email': m.email, 'status': m.status, 'last_checked': m.last_checked,
            'next_check': m.next_check, 'created_at': m.created_at}


@router.get('/emails')
def list_emails(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    return [serialize_monitor(m) for m in db.query(MonitoredEmail).filter_by(user_id=user.id).order_by(MonitoredEmail.created_at.desc())]


@router.post('/emails', status_code=201)
def add_email(body: EmailInput, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    email = body.email.lower().strip()
    if db.query(MonitoredEmail).filter_by(user_id=user.id, email=email).first():
        raise HTTPException(409, 'Este endereço já está sendo monitorado')
    if db.query(MonitoredEmail).filter_by(user_id=user.id).count() >= 25:
        raise HTTPException(403, 'Limite de 25 endereços atingido')
    pref = db.get(MonitoringPreference, user.id)
    row = MonitoredEmail(user_id=user.id, email=email, status='pending', next_check=utcnow() if pref is None or pref.email_enabled else None)
    db.add(row)
    audit(db, user.id, 'monitor.add')
    db.commit()
    return serialize_monitor(row)


@router.delete('/emails/{monitor_id}')
def remove_email(monitor_id: str, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.query(MonitoredEmail).filter_by(id=monitor_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, 'Endereço não encontrado')
    db.delete(row)
    audit(db, user.id, 'monitor.remove')
    db.commit()
    return {'message': 'Endereço removido e histórico associado excluído'}


@router.post('/emails/{monitor_id}/scan', status_code=202)
def scan_email(monitor_id: str, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.query(MonitoredEmail).filter_by(id=monitor_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, 'Endereço não encontrado')
    if row.status == 'queued':
        return {'message': 'Verificação já está na fila', 'status': 'queued'}
    if row.status == 'unavailable' and row.next_check and row.next_check > utcnow():
        raise HTTPException(429, 'API indisponível ou cota gratuita esgotada. Aguarde a próxima tentativa.')
    # Throttle manual re-scans; errors respect the persisted retry window above.
    if row.last_checked and row.last_checked > utcnow() - timedelta(minutes=1):
        raise HTTPException(429, 'Aguarde antes de verificar novamente')
    from ..tasks import scan_one
    try:
        scan_one.delay(row.id)
    except Exception as e:
        raise HTTPException(503, 'Fila de verificações indisponível') from e
    row.status = 'queued'
    db.commit()
    return {'message': 'Verificação agendada', 'status': 'queued'}


@router.get('/emails/{monitor_id}/history')
def monitor_history(monitor_id: str, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    owner = db.query(MonitoredEmail).filter_by(id=monitor_id, user_id=user.id).first()
    if not owner:
        raise HTTPException(404, 'Endereço não encontrado')
    checks = db.query(Check).filter_by(monitor_id=monitor_id).order_by(Check.created_at.desc()).limit(100).all()
    exposures = db.query(Exposure).filter_by(monitor_id=monitor_id).order_by(Exposure.discovered_at.desc()).all()
    return {'monitor': serialize_monitor(owner), 'checks': [{'id': x.id, 'status': x.status, 'detail': x.detail, 'created_at': x.created_at} for x in checks],
            'exposures': [{'id': x.id, 'breach_name': x.breach_name, 'discovered_at': x.discovered_at} for x in exposures]}


@router.get('/dashboard')
def dashboard(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    monitors = db.query(MonitoredEmail).filter_by(user_id=user.id).all()
    ids = [x.id for x in monitors]
    count = db.query(Exposure).filter(Exposure.monitor_id.in_(ids)).count() if ids else 0
    events = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(5).all()
    return {'monitored_emails': len(monitors), 'exposures': count, 'vault_items': db.query(VaultItem).filter_by(user_id=user.id).count(),
            'pending_checks': sum(x.status in ('pending', 'queued', 'unavailable') for x in monitors),
            'email_health': {key: sum(x.status == key for x in monitors) for key in ('clear', 'exposed', 'pending', 'queued', 'unavailable')},
            'emails': [serialize_monitor(x) for x in monitors[:5]],
            'notifications': [{'id': x.id, 'title': x.title, 'message': x.message, 'created_at': x.created_at} for x in events]}


@router.get('/notifications')
def notifications(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    rows = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return [{'id': x.id, 'title': x.title, 'message': x.message, 'read': x.read, 'created_at': x.created_at} for x in rows]


@router.post('/notifications/{notification_id}/read')
def mark_read(notification_id: str, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.query(Notification).filter_by(id=notification_id, user_id=user.id).first()
    if not row:
        raise HTTPException(404, 'Notificação não encontrada')
    row.read = True
    db.commit()
    return {'message': 'Notificação lida'}


@router.get('/monitoring/preferences')
def get_monitoring_preferences(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    pref = monitoring_preference(db, user.id)
    db.commit()
    return preference_response(pref)


def preference_response(pref: MonitoringPreference):
    return {'email_enabled': pref.email_enabled, 'email_interval': pref.email_interval,
            'password_enabled': pref.password_enabled, 'password_interval': pref.password_interval}


@router.put('/monitoring/preferences')
def update_monitoring_preferences(body: MonitoringPreferenceUpdate,
                                  db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    pref = monitoring_preference(db, user.id)
    email_changed = pref.email_interval != body.email_interval or pref.email_enabled != body.email_enabled
    pref.email_enabled = body.email_enabled
    pref.email_interval = body.email_interval
    pref.password_enabled = body.password_enabled
    pref.password_interval = body.password_interval
    if email_changed:
        emails = db.query(MonitoredEmail).filter_by(user_id=user.id).all()
        now = utcnow()
        for monitor in emails:
            if not body.email_enabled:
                monitor.next_check = None
            elif monitor.status == 'unavailable' and monitor.next_check and monitor.next_check > now:
                # Never bypass a provider-imposed backoff by changing the interval.
                continue
            else:
                due_at = (monitor.last_checked + timedelta(hours=INTERVAL_HOURS[body.email_interval])) if monitor.last_checked else now
                monitor.next_check = max(now, due_at)
    audit(db, user.id, 'monitoring.preferences.update')
    db.commit()
    return preference_response(pref)
