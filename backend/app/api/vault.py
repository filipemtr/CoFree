import base64
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession
from ..db import get_db
from ..models import VaultConfig, VaultItem, User
from ..schemas import VaultSetup, VaultItemIn
from ..dependencies import verified_user
from ..services import audit

router = APIRouter(prefix='/vault', tags=['Vault criptografado'])


def validate_base64(value: str, min_bytes: int, max_bytes: int):
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(422, 'Payload criptográfico inválido') from exc
    if not min_bytes <= len(raw) <= max_bytes:
        raise HTTPException(422, 'Payload criptográfico inválido')


def check_setup(body: VaultSetup):
    validate_base64(body.salt, 16, 64)
    validate_base64(body.recovery_salt, 16, 64)
    validate_base64(body.wrapped_key, 48, 1024)
    validate_base64(body.recovery_wrapped_key, 48, 1024)
    if body.version != 1:
        raise HTTPException(422, 'Versão criptográfica não suportada')


def public_config(row: VaultConfig):
    return {key: getattr(row, key) for key in ('salt', 'iterations', 'memory_kib', 'wrapped_key', 'recovery_wrapped_key', 'recovery_salt', 'version')}


def public_item(row: VaultItem):
    return {'id': row.id, 'ciphertext': row.ciphertext, 'nonce': row.nonce, 'created_at': row.created_at, 'updated_at': row.updated_at}


@router.get('/config')
def config(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.get(VaultConfig, user.id)
    return public_config(row) if row else None


@router.post('/config', status_code=201)
def setup(body: VaultSetup, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    check_setup(body)
    if db.get(VaultConfig, user.id):
        raise HTTPException(409, 'Vault já criado')
    db.add(VaultConfig(user_id=user.id, **body.model_dump()))
    audit(db, user.id, 'vault.initialize')
    db.commit()
    return {'message': 'Vault criado com dados cifrados'}


@router.put('/config')
def rotate(body: VaultSetup, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    check_setup(body)
    row = db.get(VaultConfig, user.id)
    if not row:
        raise HTTPException(404, 'Vault não encontrado')
    # Server stores only replacement wrappers. Client must prove old key locally, never send it.
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    audit(db, user.id, 'vault.rewrap')
    db.commit()
    return {'message': 'Chaves encapsuladas atualizadas'}


@router.get('/items')
def list_items(db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    if not db.get(VaultConfig, user.id):
        return []
    return [public_item(row) for row in db.query(VaultItem).filter_by(user_id=user.id).order_by(VaultItem.updated_at.desc()).all()]


@router.post('/items', status_code=201)
def create_item(body: VaultItemIn, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    if not db.get(VaultConfig, user.id):
        raise HTTPException(409, 'Configure o Vault primeiro')
    validate_base64(body.nonce, 12, 12)
    validate_base64(body.ciphertext, 17, 37500)
    if db.get(VaultItem, body.id):
        raise HTTPException(409, 'Identificador de credencial já utilizado')
    row = VaultItem(user_id=user.id, **body.model_dump())
    db.add(row)
    audit(db, user.id, 'vault.item_create')
    db.commit()
    return public_item(row)


@router.put('/items/{item_id}')
def update_item(item_id: str, body: VaultItemIn, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.query(VaultItem).filter_by(user_id=user.id, id=item_id).first()
    if not row:
        raise HTTPException(404, 'Credencial não encontrada')
    if body.id != item_id:
        raise HTTPException(422, 'Identificador do pacote não corresponde ao registro')
    validate_base64(body.nonce, 12, 12)
    validate_base64(body.ciphertext, 17, 37500)
    row.ciphertext, row.nonce = body.ciphertext, body.nonce
    audit(db, user.id, 'vault.item_update')
    db.commit()
    return public_item(row)


@router.delete('/items/{item_id}')
def delete_item(item_id: str, db: DbSession = Depends(get_db), user: User = Depends(verified_user)):
    row = db.query(VaultItem).filter_by(user_id=user.id, id=item_id).first()
    if not row:
        raise HTTPException(404, 'Credencial não encontrada')
    db.delete(row)
    audit(db, user.id, 'vault.item_delete')
    db.commit()
    return {'message': 'Credencial removida'}
