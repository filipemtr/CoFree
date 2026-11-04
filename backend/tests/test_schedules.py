"""Schedule preferences, server-side email cadence and opt-in boundaries."""
from datetime import timedelta
from app.db import SessionLocal
from app.models import MonitoredEmail, MonitoringPreference, utcnow
from app.services import scan_monitor
from .conftest import create_account, csrf
from app import services


def test_default_schedule_and_frequency_validation(client, fresh_database):
    create_account(client, fresh_database)
    resp=client.get('/api/monitoring/preferences')
    assert resp.status_code==200
    assert resp.json()=={'email_enabled':True,'email_interval':'24h','password_enabled':False,'password_interval':'7d'}
    invalid=client.put('/api/monitoring/preferences',json={
        'email_enabled':True,'email_interval':'5min','password_enabled':True,'password_interval':'7d'
    },headers=csrf(client))
    assert invalid.status_code==422
    assert client.get('/api/monitoring/preferences').json()['email_interval']=='24h'


def test_disable_enable_email_monitoring_and_next_check(client, fresh_database, monkeypatch):
    create_account(client, fresh_database)
    created=client.post('/api/emails',json={'email':'scheduled@example.com'},headers=csrf(client))
    assert created.status_code==201
    ident=created.json()['id']
    assert created.json()['next_check']
    off=client.put('/api/monitoring/preferences',headers=csrf(client),json={
        'email_enabled':False,'email_interval':'1h','password_enabled':True,'password_interval':'30d'
    })
    assert off.status_code==200
    assert off.json()['password_enabled'] is True
    assert client.get('/api/emails').json()[0]['next_check'] is None
    added=client.post('/api/emails',json={'email':'other@example.com'},headers=csrf(client))
    assert added.status_code==201 and added.json()['next_check'] is None
    monkeypatch.setattr(services,'find_breaches',lambda email:[])
    with SessionLocal() as db:
        row=db.get(MonitoredEmail,ident)
        assert scan_monitor(db,row)=='clear'
        assert row.next_check is None
    enabled=client.put('/api/monitoring/preferences',headers=csrf(client),json={
        'email_enabled':True,'email_interval':'1h','password_enabled':True,'password_interval':'7d'
    })
    assert enabled.status_code==200
    with SessionLocal() as db:
        row=db.get(MonitoredEmail,ident)
        assert row.next_check is not None
        assert row.next_check > utcnow() + timedelta(minutes=50)
        assert db.get(MonitoringPreference,row.user_id).email_interval=='1h'
        another=db.query(MonitoredEmail).filter_by(email='other@example.com').one()
        assert another.next_check is not None


def test_schedule_api_requires_verified_session(client):
    assert client.get('/api/monitoring/preferences').status_code==401
    assert client.put('/api/monitoring/preferences',json={
        'email_enabled':False,'email_interval':'24h','password_enabled':False,'password_interval':'7d'
    }).status_code==401


def test_email_intervals_all_accepted(client, fresh_database):
    create_account(client,fresh_database)
    for interval in ('1h','24h','7d','30d'):
        resp=client.put('/api/monitoring/preferences',headers=csrf(client),json={
            'email_enabled':True,'email_interval':interval,'password_enabled':False,'password_interval':interval
        })
        assert resp.status_code==200
        assert resp.json()['email_interval']==interval
