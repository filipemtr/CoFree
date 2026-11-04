from .conftest import create_account, csrf
from app.db import SessionLocal
from app.models import MonitoredEmail, Exposure, Check
from app.services import scan_monitor
from app.providers.xposedornot import ProviderError
from app import services


def test_email_add_duplicate_and_isolation(client,fresh_database):
    create_account(client,fresh_database)
    a=client.post('/api/emails',headers=csrf(client),json={'email':'outro@example.com'})
    assert a.status_code==201
    ident=a.json()['id']
    assert client.post('/api/emails',headers=csrf(client),json={'email':'outro@example.com'}).status_code==409
    assert len(client.get('/api/emails').json())==1
    assert client.delete('/api/emails/'+ident).status_code==403
    assert client.delete('/api/emails/'+ident,headers=csrf(client)).status_code==200
    assert client.get('/api/emails').json()==[]


def test_scan_and_idempotent_notifications(client,fresh_database,monkeypatch):
    create_account(client,fresh_database)
    ident=client.post('/api/emails',headers=csrf(client),json={'email':'check@example.com'}).json()['id']
    monkeypatch.setattr(services,'find_breaches',lambda email:['Adobe','Example'])
    monkeypatch.setattr('app.emailer.send_email',lambda *args: True)
    with SessionLocal() as db:
        assert scan_monitor(db,db.get(MonitoredEmail,ident))=='exposed'
        assert scan_monitor(db,db.get(MonitoredEmail,ident))=='exposed'
        assert db.query(Exposure).count()==2
        assert db.query(Check).count()==2
    assert len(client.get('/api/notifications').json())==2
    history=client.get(f'/api/emails/{ident}/history').json()
    assert len(history['exposures'])==2
    assert len(history['checks'])==2
    assert client.get('/api/dashboard').json()['exposures']==2


def test_provider_error_never_marked_safe(client,fresh_database,monkeypatch):
    create_account(client,fresh_database)
    ident=client.post('/api/emails',headers=csrf(client),json={'email':'check@example.com'}).json()['id']
    def failure(email):
        raise ProviderError('API indisponível')
    monkeypatch.setattr(services,'find_breaches',failure)
    with SessionLocal() as db:
        assert scan_monitor(db,db.get(MonitoredEmail,ident))=='unavailable'
        assert db.get(MonitoredEmail,ident).status=='unavailable'
    assert client.get('/api/dashboard').json()['exposures']==0


def test_scan_enqueues_without_paid_api_key(client, fresh_database, monkeypatch):
    import pytest
    pytest.importorskip("celery")
    from app.tasks import scan_one
    enqueued = []
    monkeypatch.setattr(scan_one, 'delay', lambda identifier: enqueued.append(identifier))
    create_account(client, fresh_database)
    ident = client.post('/api/emails', headers=csrf(client), json={'email': 'check@example.com'}).json()['id']
    result = client.post(f'/api/emails/{ident}/scan', headers=csrf(client))
    assert result.status_code == 202
    assert result.json()['status'] == 'queued'
    assert enqueued == [ident]
    assert client.post(f'/api/emails/{ident}/scan', headers=csrf(client)).json()['status'] == 'queued'


def test_provider_quota_error_preserves_state_and_sets_retry(client, fresh_database, monkeypatch):
    from datetime import timedelta
    from app.models import utcnow
    create_account(client, fresh_database)
    ident = client.post('/api/emails', headers=csrf(client), json={'email': 'quota@example.com'}).json()['id']
    monkeypatch.setattr(services, 'find_breaches', lambda email: ['Adobe'])
    monkeypatch.setattr('app.emailer.send_email', lambda *args: True)
    with SessionLocal() as db:
        scan_monitor(db, db.get(MonitoredEmail, ident))
    def over_limit(email):
        raise ProviderError('Cota excedida', retry_after=7200)
    monkeypatch.setattr(services, 'find_breaches', over_limit)
    with SessionLocal() as db:
        monitor = db.get(MonitoredEmail, ident)
        assert scan_monitor(db, monitor) == 'unavailable'
        assert monitor.next_check > utcnow() + timedelta(minutes=115)
        assert monitor.last_checked is not None
        assert db.query(Exposure).count() == 1
    result = client.post(f'/api/emails/{ident}/scan', headers=csrf(client))
    assert result.status_code == 429
