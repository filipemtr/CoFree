
import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .settings import get_settings
from .api import auth, monitoring, vault


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

s = get_settings()


# ============================================================
# VALIDAÇÕES DE SEGURANÇA EM PRODUÇÃO
# ============================================================

if s.environment == "production":
    if (
        len(s.app_secret) < 32
        or "development-only" in s.app_secret
        or "CHANGE_ME" in s.app_secret
    ):
        raise RuntimeError(
            "APP_SECRET precisa ser configurada em produção"
        )

    if not s.cookie_secure:
        raise RuntimeError(
            "COOKIE_SECURE deve ser true em produção HTTPS"
        )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="CoFree API",
    version="0.3.0",
    description=(
        "Proteção de credenciais e monitoramento "
        "de exposição digital — Vela"
    )
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.frontend_url],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "PUT",
        "DELETE"
    ],
    allow_headers=[
        "Content-Type",
        "X-CSRF-Token"
    ]
)


# ============================================================
# RATE LIMITING - FALLBACK DE DESENVOLVIMENTO
# ============================================================

# Em produção, o Redis é obrigatório para o rate limiting.
# O fallback em memória é utilizado apenas quando o Redis
# estiver indisponível no ambiente de desenvolvimento.

_buckets: dict[str, deque] = defaultdict(deque)


# ============================================================
# MIDDLEWARE DE SEGURANÇA
# ============================================================

@app.middleware("http")
async def harden(request: Request, call_next):

    path = request.url.path

    # --------------------------------------------------------
    # LIMITES DE REQUISIÇÕES
    # --------------------------------------------------------

    limits = {
        "/api/auth/login": (6, 60),
        "/api/auth/register": (4, 300),
        "/api/auth/password/forgot": (4, 300),
        "/api/auth/resend-verification": (4, 300)
    }

    rule = next(
        (
            (n, w)
            for prefix, (n, w) in limits.items()
            if path == prefix
        ),
        (80, 60)
    )

    # --------------------------------------------------------
    # RATE LIMITING COM REDIS
    # --------------------------------------------------------

    if path.startswith("/api/") and request.method != "OPTIONS":

        source = (
            request.client.host
            if request.client
            else "unknown"
        )

        key = f"rl:{path}:{source}"

        try:
            import redis

            rc = redis.Redis.from_url(
                s.redis_url,
                socket_connect_timeout=0.2,
                socket_timeout=0.2
            )

            window = int(time.time() // rule[1])
            rkey = f"{key}:{window}"

            count = rc.incr(rkey)

            if count == 1:
                rc.expire(rkey, rule[1] + 1)

        except Exception:

            if s.environment == "production":
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Proteção de tráfego indisponível"
                    }
                )

            bucket = _buckets[key]
            now = time.monotonic()

            while bucket and bucket[0] < now - rule[1]:
                bucket.popleft()

            bucket.append(now)
            count = len(bucket)

        if count > rule[0]:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Muitas solicitações. "
                        "Tente novamente mais tarde."
                    )
                },
                headers={
                    "Retry-After": str(rule[1])
                }
            )

    # --------------------------------------------------------
    # EXECUTA A REQUISIÇÃO
    # --------------------------------------------------------

    response = await call_next(request)

    # --------------------------------------------------------
    # CONTENT SECURITY POLICY (CSP)
    # --------------------------------------------------------

    # Política restritiva padrão para todas as rotas da API.
    csp = (
        "default-src 'none'; "
        "frame-ancestors 'none'"
    )

    # O Swagger e o ReDoc precisam carregar JavaScript e CSS.
    # Esta exceção se aplica somente à documentação.
    if path in ("/docs", "/redoc"):

        csp = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net; "
            "img-src 'self' data: "
            "https://fastapi.tiangolo.com; "
            "connect-src 'self'; "
            "font-src 'self' data: "
            "https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'"
        )

    # --------------------------------------------------------
    # CABEÇALHOS HTTP DE SEGURANÇA
    # --------------------------------------------------------

    response.headers.update({
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": (
            "camera=(), microphone=(), geolocation=()"
        ),
        "Cache-Control": "no-store",
        "Content-Security-Policy": csp
    })

    return response


# ============================================================
# HEALTHCHECK
# ============================================================

@app.get("/health", tags=["Sistema"])
def health():
    return {
        "status": "ok",
        "service": "cofree-api"
    }


# ============================================================
# ROTAS DA APLICAÇÃO
# ============================================================

app.include_router(
    auth.router,
    prefix="/api"
)

app.include_router(
    monitoring.router,
    prefix="/api"
)

app.include_router(
    vault.router,
    prefix="/api"
)
