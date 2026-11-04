import base64
import uuid
from .conftest import create_account, csrf
from app.db import SessionLocal
from app.models import VaultItem, VaultConfig


def b64(size):
    return base64.b64encode(bytes([42])*size).decode()


def setup():
    return {'salt':b64(16),'iterations':3,'memory_kib':65536,'wrapped_key':b64(72),
            'recovery_wrapped_key':b64(72),'recovery_salt':b64(16),'version':1}


def item():
    return {'id':str(uuid.uuid4()),'ciphertext':b64(80),'nonce':b64(12)}


def test_vault_requires_config_and_stores_ciphertext(client,fresh_database):
    create_account(client,fresh_database)
    assert client.post('/api/vault/items',headers=csrf(client),json=item()).status_code==409
    assert client.post('/api/vault/config',headers=csrf(client),json=setup()).status_code==201
    assert client.post('/api/vault/config',headers=csrf(client),json=setup()).status_code==409
    assert client.get('/api/vault/config').json()==setup()
    response=client.post('/api/vault/items',headers=csrf(client),json=item())
    assert response.status_code==201
    assert response.json()['ciphertext']==item()['ciphertext']
    with SessionLocal() as db:
        stored=db.query(VaultItem).one()
        assert stored.ciphertext==item()['ciphertext']
        assert not hasattr(stored,'password')
    assert len(client.get('/api/vault/items').json())==1
    ident=response.json()['id']
    updated=item();updated['id']=ident
    assert client.put('/api/vault/items/'+ident,headers=csrf(client),json=updated).status_code==200
    assert client.delete('/api/vault/items/'+ident,headers=csrf(client)).status_code==200
    assert client.get('/api/vault/items').json()==[]


def test_invalid_crypto_payload_rejected(client,fresh_database):
    create_account(client,fresh_database)
    bad=setup();bad['salt']='not-base64'
    assert client.post('/api/vault/config',headers=csrf(client),json=bad).status_code==422
    assert client.post('/api/vault/config',headers=csrf(client),json=setup()).status_code==201
    bad=item();bad['nonce']='!!!notbase64!!!'
    assert client.post('/api/vault/items',headers=csrf(client),json=bad).status_code==422


def test_cross_user_isolation(client,fresh_database):
    first=create_account(client,fresh_database,email='first@example.com')
    assert client.post('/api/vault/config',headers=csrf(client),json=setup()).status_code==201
    ident=client.post('/api/vault/items',headers=csrf(client),json=item()).json()['id']
    monitor=client.post('/api/emails',headers=csrf(client),json={'email':'private@example.com'}).json()['id']
    assert client.post('/api/auth/logout',headers=csrf(client)).status_code==200
    create_account(client,fresh_database,email='second@example.com')
    assert client.get('/api/vault/config').json() is None
    assert client.get('/api/vault/items').json()==[]
    updated=item();updated['id']=ident
    assert client.put('/api/vault/items/'+ident,headers=csrf(client),json=updated).status_code==404
    assert client.delete('/api/vault/items/'+ident,headers=csrf(client)).status_code==404
    assert client.get(f'/api/emails/{monitor}/history').status_code==404
    assert client.delete(f'/api/emails/{monitor}',headers=csrf(client)).status_code==404


def test_account_deletion_cascades(client,fresh_database):
    create_account(client,fresh_database)
    client.post('/api/vault/config',headers=csrf(client),json=setup())
    client.post('/api/vault/items',headers=csrf(client),json=item())
    client.post('/api/emails',headers=csrf(client),json={'email':'private@example.com'})
    response=client.request('DELETE','/api/auth/me',headers=csrf(client),json={'current_password':'MinhaSenhaSuperForte123!'})
    assert response.status_code==200, response.text
    with SessionLocal() as db:
        assert db.query(VaultItem).count()==0
        assert db.query(VaultConfig).count()==0
