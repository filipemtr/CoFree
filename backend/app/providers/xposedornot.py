"""Adaptador para a API pública XposedOrNot: https://xposedornot.com/api_doc.

Retorno: nomes de vazamentos conhecidos. Resultado vazio não é garantia de segurança.
Não usar mocks no runtime; os testes injetam MockTransport do httpx.
"""

import logging
import time
from urllib.parse import quote
from uuid import uuid4

import httpx

from ..settings import get_settings

logger = logging.getLogger(__name__)
BASE_URL = 'https://api.xposedornot.com'


class ProviderError(Exception):
    """Indisponibilidade / limites: nunca representar como ausência de exposição."""

    def __init__(self, message: str, *, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


# Rolling windows shared by every Celery worker; margins protect free public quota
# (published limits: 2/sec, 25/hour, 100/day per IP, per endpoint).
_QUOTA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local nonce = ARGV[2]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - 86400000)
local rules = {{1000, 1}, {3600000, 24}, {86400000, 95}}
for _, rule in ipairs(rules) do
  local floor = now - rule[1]
  local count = redis.call('ZCOUNT', key, '(' .. tostring(floor), '+inf')
  if count >= rule[2] then
    local first = redis.call('ZRANGEBYSCORE', key, '(' .. tostring(floor), '+inf', 'WITHSCORES', 'LIMIT', 0, 1)
    if #first >= 2 then
      local wait = math.ceil((tonumber(first[2]) + rule[1] - now) / 1000)
      return math.max(wait, 1)
    end
    return 60
  end
end
redis.call('ZADD', key, now, nonce)
redis.call('PEXPIRE', key, 86400000)
return 0
"""


def _reserve_quota() -> None:
    """Reserve a single outbound API request atomically; fail closed without Redis."""
    try:
        import redis
    except ImportError as exc:
        raise ProviderError('Redis não instalado; consultas de vazamentos indisponíveis') from exc
    try:
        rc = redis.Redis.from_url(
            get_settings().redis_url, socket_connect_timeout=1.0,
            socket_timeout=1.0, decode_responses=True,
        )
        wait_seconds = int(rc.eval(
            _QUOTA_SCRIPT, 1, 'cofree:provider:xon:check-email',
            int(time.time() * 1000), uuid4().hex,
        ))
    except (redis.RedisError, ValueError, TypeError) as exc:
        logger.warning('XON quota backend unavailable: %s', type(exc).__name__)
        raise ProviderError('Controle de limites da API indisponível; consulta não realizada', retry_after=300) from exc
    if wait_seconds:
        raise ProviderError('Limite gratuito de consultas atingido; verificação adiada', retry_after=wait_seconds)


def _parse_response(status_code: int, payload: object, requested_email: str) -> list[str]:
    if not isinstance(payload, dict):
        raise ProviderError('Resposta inválida da API de vazamentos')

    # The documented "not found" payload occurs on the public API for a clean lookup.
    # Require this precise sentinel to distinguish it from generic 404s and broken APIs.
    if payload.get('Error') == 'Not found' and status_code in (200, 404):
        if 'email' not in payload or payload.get('email') is not None:
            raise ProviderError('Resposta inconsistente da API de vazamentos')
        return []

    if status_code != 200:
        raise ProviderError(f'API de vazamentos indisponível (HTTP {status_code})')
    if payload.get('status') != 'success' or not isinstance(payload.get('breaches'), list):
        raise ProviderError('Formato inesperado da API de vazamentos')
    response_email = payload.get('email')
    if not isinstance(response_email, str) or response_email.casefold() != requested_email.casefold():
        raise ProviderError('Resposta de consulta inconsistente com o e-mail solicitado')

    # XON v1 returns nested arrays, e.g. {"breaches": [["Adobe", "LinkedIn"]]}.
    # Also tolerate a flat list if the upstream simplifies its response.
    names: list[str] = []
    for part in payload['breaches']:
        entries = part if isinstance(part, list) else [part]
        for item in entries:
            if not isinstance(item, str) or not item.strip():
                raise ProviderError('Lista de exposições inválida da API')
            names.append(item.strip()[:240])
    return sorted(set(names))


def find_breaches(email: str, *, transport: httpx.BaseTransport | None = None,
                  limiter=None) -> list[str]:
    """Consult XON public API; no subscription or account API key required.

    `transport` and `limiter` are injectable test seams; production always uses
    an actual HTTPS client and a Redis shared sliding-window quota.
    """
    if not isinstance(email, str) or not email or len(email) > 320 or '@' not in email or any(c in email for c in '\r\n\t /?#'):
        raise ProviderError('Endereço de e-mail inválido')

    (limiter if limiter is not None else _reserve_quota)()
    url = f'{BASE_URL}/v1/check-email/{quote(email, safe="")}'
    try:
        with httpx.Client(timeout=httpx.Timeout(12.0), follow_redirects=False,
                          transport=transport) as client:
            response = client.get(url, headers={
                'User-Agent': 'CoFree/0.4 (academic monitoring project)',
                'Accept': 'application/json',
            })
        if response.status_code == 429:
            raw = response.headers.get('Retry-After', '')
            retry_after = int(raw) if raw.isascii() and raw.isdecimal() else 3600
            raise ProviderError('API de vazamentos com limite de requisições atingido',
                                retry_after=min(max(retry_after, 1), 86400))
        if response.status_code not in (200, 404):
            raise ProviderError(f'API de vazamentos indisponível (HTTP {response.status_code})',
                                retry_after=3600)
        payload = response.json()
        return _parse_response(response.status_code, payload, email)
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning('XON provider network/JSON failure: %s', type(exc).__name__)
        raise ProviderError('Falha na comunicação com a API de vazamentos', retry_after=3600) from exc
