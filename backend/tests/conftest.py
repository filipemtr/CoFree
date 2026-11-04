import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

os.environ['DATABASE_URL'] = 'sqlite:///./test_cofree.db'
os.environ['ENVIRONMENT'] = 'test'
os.environ['SMTP_HOST'] = ''

from app.db import Base, engine
from app import models
from app.main import app, _buckets
from app.api import auth


@pytest.fixture(autouse=True)
def fresh_database(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _buckets.clear()
    captured = []
    monkeypatch.setattr(auth, 'send_action_link', lambda email, kind, token: captured.append((email, kind, token)) or True)
    yield captured
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def create_account(client, outbox, email='usuario@example.com', password='MinhaSenhaSuperForte123!'):
    result=client.post('/api/auth/register',json={'name':'Pessoa de Teste','email':email,'password':password})
    assert result.status_code==201, result.text
    token = outbox[-1][2]
    assert client.post('/api/auth/verify',json={'token':token}).status_code==200
    response=client.post('/api/auth/login',json={'email':email,'password':password})
    assert response.status_code==200, response.text
    return response.json()


def csrf(client):
    return {'X-CSRF-Token':client.cookies.get('cofree_csrf','')}
