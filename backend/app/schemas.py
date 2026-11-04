from pydantic import BaseModel, EmailStr, Field, field_validator


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class Login(BaseModel):
    email: EmailStr
    password: str


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResetPassword(TokenInput):
    password: str = Field(min_length=12, max_length=256)


class EmailInput(BaseModel):
    email: EmailStr


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=256)


class Preferences(BaseModel):
    notify_exposures: bool


class VaultSetup(BaseModel):
    salt: str = Field(min_length=20, max_length=100)
    iterations: int = Field(ge=2, le=8)
    memory_kib: int = Field(ge=32768, le=262144)
    wrapped_key: str = Field(min_length=40, max_length=2048)
    recovery_wrapped_key: str = Field(min_length=40, max_length=2048)
    recovery_salt: str = Field(min_length=20, max_length=100)
    version: int = 1


class VaultItemIn(BaseModel):
    id: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    ciphertext: str = Field(min_length=24, max_length=50000)
    nonce: str = Field(min_length=12, max_length=80)


class VaultRotate(VaultSetup):
    pass


class PasswordConfirm(BaseModel):
    current_password: str


class MonitoringPreferenceUpdate(BaseModel):
    email_enabled: bool
    email_interval: str
    password_enabled: bool
    password_interval: str

    @field_validator('email_interval', 'password_interval')
    @classmethod
    def interval_supported(cls, value: str) -> str:
        if value not in ('1h', '24h', '7d', '30d'):
            raise ValueError('Escolha 1 hora, 1 dia, 1 semana ou 1 mês')
        return value
