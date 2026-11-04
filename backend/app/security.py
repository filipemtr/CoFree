import hashlib
import hmac
import secrets
from datetime import timedelta
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError
from .models import utcnow, ActionToken, Session

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def new_action_token(user_id: str, kind: str, minutes: int = 30) -> tuple[str, ActionToken]:
    token = secrets.token_urlsafe(40)
    row = ActionToken(user_id=user_id, kind=kind, token_hash=digest(token), expires_at=utcnow() + timedelta(minutes=minutes))
    return token, row


def validate_action_token(db, raw: str, kind: str):
    row = db.query(ActionToken).filter(ActionToken.token_hash == digest(raw), ActionToken.kind == kind).first()
    if row is None or row.used_at is not None or row.expires_at <= utcnow():
        return None
    return row


def new_session(user_id: str, agent: str) -> tuple[str, str, Session]:
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    record = Session(user_id=user_id, token_hash=digest(token), csrf_hash=digest(csrf),
                     user_agent=agent[:240], expires_at=utcnow() + timedelta(days=7))
    return token, csrf, record


def csrf_matches(csrf_header: str, csrf_cookie: str, stored_hash: str) -> bool:
    return bool(csrf_header and csrf_cookie and hmac.compare_digest(csrf_header, csrf_cookie) and hmac.compare_digest(digest(csrf_header), stored_hash))
