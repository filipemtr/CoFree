from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DbSession
from ..db import get_db
from ..models import User, Session, ActionToken, AuditEvent, utcnow
from ..dependencies import current_user, current_session
from ..schemas import Register, Login, EmailInput, TokenInput, ResetPassword, ProfileUpdate, PasswordChange, PasswordConfirm, Preferences
from ..security import hash_password, verify_password, new_action_token, validate_action_token, new_session
from ..emailer import send_action_link
from ..services import audit
from ..settings import get_settings

router = APIRouter(prefix='/auth', tags=['Autenticação'])


def normalize(email: str) -> str:
    return email.lower().strip()


def public_user(user: User):
    return {'id': user.id, 'email': user.email, 'name': user.name, 'verified': user.verified, 'notify_exposures': user.notify_exposures}


def clear_cookies(response: Response):
    response.delete_cookie('cofree_session', path='/')
    response.delete_cookie('cofree_csrf', path='/')


@router.post('/register', status_code=201)
def register(body: Register, db: DbSession = Depends(get_db)):
    email = normalize(body.email)
    if db.query(User).filter_by(email=email).first():
        return {'message': 'Se os dados permitirem, enviaremos instruções para seu e-mail.'}
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    raw, token = new_action_token(user.id, 'verify', 60)
    db.add(token)
    audit(db, user.id, 'account.register')
    db.commit()
    sent = send_action_link(email, 'verify', raw)
    return {'message': 'Conta criada. Verifique seu e-mail para ativá-la.', 'email_delivered': sent}


@router.post('/verify')
def verify(body: TokenInput, db: DbSession = Depends(get_db)):
    token = validate_action_token(db, body.token, 'verify')
    if not token:
        raise HTTPException(400, 'Link inválido, expirado ou já utilizado')
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(400, 'Link inválido')
    user.verified = True
    token.used_at = utcnow()
    audit(db, user.id, 'account.verify')
    db.commit()
    return {'message': 'E-mail confirmado com sucesso'}


@router.post('/resend-verification')
def resend(body: EmailInput, db: DbSession = Depends(get_db)):
    user = db.query(User).filter_by(email=normalize(body.email)).first()
    if user and not user.verified:
        latest = db.query(ActionToken).filter_by(user_id=user.id, kind='verify').order_by(ActionToken.id.desc()).all()
        if not any(t.expires_at > utcnow() + timedelta(minutes=55) and t.used_at is None for t in latest):
            for t in latest:
                if t.used_at is None:
                    t.used_at = utcnow()
            raw, token = new_action_token(user.id, 'verify', 60)
            db.add(token)
            db.commit()
            send_action_link(user.email, 'verify', raw)
    return {'message': 'Se a conta existir e não estiver verificada, enviaremos um novo link.'}


@router.post('/login')
def login(body: Login, request: Request, response: Response, db: DbSession = Depends(get_db)):
    user = db.query(User).filter_by(email=normalize(body.email)).first()
    # Constant-time-ish dummy hash when account doesn't exist to reduce enumeration via timing.
    dummy = '$argon2id$v=19$m=65536,t=3,p=2$rnrNXJBC0XFvZ+QESbiSkw$caaxN/VbUAMwcNYQ33Ya1lRG+iUR3hgXf1KcGYnZi+g'
    ok = verify_password(body.password, user.password_hash if user else dummy)
    if not user or not ok:
        raise HTTPException(401, 'Credenciais inválidas')
    if not user.verified:
        raise HTTPException(403, 'Confirme seu e-mail antes de entrar')
    token, csrf, record = new_session(user.id, request.headers.get('user-agent', 'Desconhecido'))
    db.add(record)
    audit(db, user.id, 'session.login')
    db.commit()
    settings = get_settings()
    response.set_cookie('cofree_session', token, httponly=True, secure=settings.cookie_secure, samesite='lax', max_age=604800, path='/')
    response.set_cookie('cofree_csrf', csrf, httponly=False, secure=settings.cookie_secure, samesite='lax', max_age=604800, path='/')
    return public_user(user)


@router.post('/logout')
def logout(response: Response, db: DbSession = Depends(get_db), session: Session = Depends(current_session)):
    session.revoked_at = utcnow()
    audit(db, session.user_id, 'session.logout')
    db.commit()
    clear_cookies(response)
    return {'message': 'Sessão encerrada'}


@router.get('/me')
def me(user: User = Depends(current_user)):
    return public_user(user)


@router.patch('/me')
def update_profile(body: ProfileUpdate, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    user.name = body.name.strip()
    audit(db, user.id, 'account.update')
    db.commit()
    return public_user(user)


@router.patch('/preferences')
def update_preferences(body: Preferences, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    user.notify_exposures = body.notify_exposures
    db.commit()
    return public_user(user)


@router.post('/password/change')
def change_password(body: PasswordChange, response: Response, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, 'Senha atual incorreta')
    user.password_hash = hash_password(body.new_password)
    db.query(Session).filter_by(user_id=user.id, revoked_at=None).update({'revoked_at': utcnow()}, synchronize_session=False)
    audit(db, user.id, 'account.password_changed')
    db.commit()
    clear_cookies(response)
    return {'message': 'Senha alterada. Todas as sessões foram encerradas.'}


@router.post('/password/forgot')
def forgot(body: EmailInput, db: DbSession = Depends(get_db)):
    user = db.query(User).filter_by(email=normalize(body.email)).first()
    if user:
        db.query(ActionToken).filter_by(user_id=user.id, kind='reset', used_at=None).update({'used_at': utcnow()}, synchronize_session=False)
        raw, record = new_action_token(user.id, 'reset', 30)
        db.add(record)
        db.commit()
        send_action_link(user.email, 'reset', raw)
    return {'message': 'Se o endereço estiver cadastrado, você receberá instruções.'}


@router.post('/password/reset')
def reset(body: ResetPassword, db: DbSession = Depends(get_db)):
    token = validate_action_token(db, body.token, 'reset')
    if not token:
        raise HTTPException(400, 'Link inválido, expirado ou já utilizado')
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(400, 'Link inválido')
    user.password_hash = hash_password(body.password)
    token.used_at = utcnow()
    db.query(Session).filter_by(user_id=user.id, revoked_at=None).update({'revoked_at': utcnow()}, synchronize_session=False)
    audit(db, user.id, 'account.password_reset')
    db.commit()
    return {'message': 'Senha redefinida. Entre novamente.'}


@router.get('/sessions')
def get_sessions(db: DbSession = Depends(get_db), user: User = Depends(current_user), session: Session = Depends(current_session)):
    rows = db.query(Session).filter_by(user_id=user.id).order_by(Session.created_at.desc()).limit(60).all()
    return [{'id': x.id, 'created_at': x.created_at, 'last_seen': x.last_seen, 'expires_at': x.expires_at,
             'user_agent': x.user_agent, 'current': x.id == session.id, 'revoked': x.revoked_at is not None} for x in rows]


@router.delete('/sessions/{session_id}')
def revoke_session(session_id: str, response: Response, db: DbSession = Depends(get_db), user: User = Depends(current_user), current: Session = Depends(current_session)):
    target = db.query(Session).filter_by(id=session_id, user_id=user.id).first()
    if not target:
        raise HTTPException(404, 'Sessão não encontrada')
    target.revoked_at = utcnow()
    audit(db, user.id, 'session.revoke')
    db.commit()
    if target.id == current.id:
        clear_cookies(response)
    return {'message': 'Sessão revogada'}


@router.delete('/sessions')
def revoke_sessions(response: Response, others: bool = False, db: DbSession = Depends(get_db), user: User = Depends(current_user), current: Session = Depends(current_session)):
    q = db.query(Session).filter_by(user_id=user.id, revoked_at=None)
    if others:
        q = q.filter(Session.id != current.id)
    q.update({'revoked_at': utcnow()}, synchronize_session=False)
    audit(db, user.id, 'session.revoke_many')
    db.commit()
    if not others:
        clear_cookies(response)
    return {'message': 'Sessões revogadas'}


@router.delete('/me')
def delete_account(body: PasswordConfirm, response: Response, db: DbSession = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, 'Senha incorreta')
    # ON DELETE CASCADE applies on PostgreSQL. SQLite test database enables FK pragma.
    db.delete(user)
    db.commit()
    clear_cookies(response)
    return {'message': 'Conta excluída'}
