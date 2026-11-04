from app.db import SessionLocal
from app.models import User, Session, ActionToken, utcnow
from app.security import hash_password, verify_password, csrf_matches, digest
from .conftest import create_account, csrf

PASSWORD='MinhaSenhaSuperForte123!'


def test_password_argon2id():
    encoded=hash_password(PASSWORD)
    assert encoded.startswith('$argon2id$')
    assert verify_password(PASSWORD,encoded)
    assert not verify_password('wrong',encoded)


def test_registration_verification_login(client,fresh_database):
    outbox=fresh_database
    res=client.post('/api/auth/register',json={'name':'Fulano','email':'TEST@EXAMPLE.COM','password':PASSWORD})
    assert res.status_code==201
    assert outbox[-1][0]=='test@example.com'
    assert client.post('/api/auth/login',json={'email':'test@example.com','password':PASSWORD}).status_code==403
    token=outbox[-1][2]
    assert client.post('/api/auth/verify',json={'token':token}).status_code==200
    assert client.post('/api/auth/verify',json={'token':token}).status_code==400
    result=client.post('/api/auth/login',json={'email':'test@example.com','password':PASSWORD})
    assert result.status_code==200
    assert result.json()['verified']
    assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/auth/logout',headers=csrf(client)).status_code==200
    assert client.get('/api/auth/me').status_code==401


def test_csrf_and_session_revocation(client,fresh_database):
    create_account(client,fresh_database)
    assert client.post('/api/auth/logout').status_code==403
    assert client.patch('/api/auth/me',headers={'X-CSRF-Token':'invalid'},json={'name':'Changed'}).status_code==403
    assert client.patch('/api/auth/me',headers=csrf(client),json={'name':'Changed'}).status_code==200
    items=client.get('/api/auth/sessions').json()
    assert len(items)==1 and items[0]['current']
    assert client.delete('/api/auth/sessions/'+items[0]['id'],headers=csrf(client)).status_code==200
    assert client.get('/api/auth/me').status_code==401


def test_password_recovery_single_use_and_session_revoke(client,fresh_database):
    create_account(client,fresh_database)
    assert client.post('/api/auth/password/forgot',json={'email':'unknown@example.com'}).status_code==200
    assert client.post('/api/auth/password/forgot',json={'email':'usuario@example.com'}).status_code==200
    token=fresh_database[-1][2]
    assert client.post('/api/auth/password/reset',json={'token':token,'password':'UmaNovaSenhaSuperForte123!'}).status_code==200
    assert client.post('/api/auth/password/reset',json={'token':token,'password':'UmaOutraSenhaSuperForte123!'}).status_code==400
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={'email':'usuario@example.com','password':PASSWORD}).status_code==401
    assert client.post('/api/auth/login',json={'email':'usuario@example.com','password':'UmaNovaSenhaSuperForte123!'}).status_code==200


def test_password_change_revokes_all(client,fresh_database):
    create_account(client,fresh_database)
    assert client.post('/api/auth/password/change',headers=csrf(client),json={'current_password':PASSWORD,'new_password':'OutraSenhaSuperLonga123!'}).status_code==200
    assert client.get('/api/auth/me').status_code==401


def test_registration_duplicate_no_enumeration(client,fresh_database):
    create_account(client,fresh_database)
    response=client.post('/api/auth/register',json={'name':'Fulano','email':'usuario@example.com','password':PASSWORD})
    assert response.status_code==201
    assert 'já cadastrado' not in response.text


def test_rate_limiting(client):
    for _ in range(6):
        response=client.post('/api/auth/login',json={'email':'fail@example.com','password':'fail'})
        assert response.status_code==401
    response=client.post('/api/auth/login',json={'email':'fail@example.com','password':'fail'})
    assert response.status_code==429
    assert 'Retry-After' in response.headers


def test_action_token_expired(client,fresh_database):
    create_account(client,fresh_database)
    client.post('/api/auth/password/forgot',json={'email':'usuario@example.com'})
    raw=fresh_database[-1][2]
    with SessionLocal() as db:
        token=db.query(ActionToken).filter_by(token_hash=digest(raw)).first()
        token.expires_at=utcnow()
        db.commit()
    assert client.post('/api/auth/password/reset',json={'token':raw,'password':'SomeNewPassword12345!'}).status_code==400
