import hmac
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession
from .db import get_db
from datetime import timedelta
from .models import User, Session, utcnow
from .security import digest, csrf_matches
from .settings import get_settings


def current_session(request: Request, db: DbSession = Depends(get_db)) -> Session:
    token = request.cookies.get('cofree_session')
    if not token:
        raise HTTPException(401, 'Entre na sua conta para continuar')
    session = db.query(Session).filter(Session.token_hash == digest(token)).first()
    if not session or session.revoked_at or session.expires_at <= utcnow():
        raise HTTPException(401, 'Sessão inválida ou expirada')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        supplied = request.headers.get('X-CSRF-Token', '')
        cookie = request.cookies.get('cofree_csrf', '')
        if not csrf_matches(supplied, cookie, session.csrf_hash):
            raise HTTPException(403, 'Token CSRF ausente ou inválido')
        origin = request.headers.get('origin', '')
        if origin and not hmac.compare_digest(origin.rstrip('/'), get_settings().frontend_url.rstrip('/')):
            raise HTTPException(403, 'Origem não autorizada')
    if session.last_seen < utcnow() - timedelta(minutes=1):
        session.last_seen = utcnow()
        db.commit()
    return session


def current_user(db: DbSession = Depends(get_db), session: Session = Depends(current_session)) -> User:
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Conta indisponível')
    return user


def verified_user(user: User = Depends(current_user)) -> User:
    if not user.verified:
        raise HTTPException(403, 'Verifique seu endereço de e-mail antes de continuar')
    return user
