# Contratos de API

Base: `/api`. JSON/HTTP. Sessões autenticadas via cookie HttpOnly `cofree_session` e alterações de estado autenticadas exigem cabeçalho `X-CSRF-Token` igual ao cookie `cofree_csrf` emitido no login. Erros padronizados por FastAPI com `detail` e status HTTP. OpenAPI é gerado automaticamente em `/openapi.json` e `/docs` via proxy.

| Método | Rota | Objetivo |
|---|---|---|
| POST | `/auth/register` | registrar conta e tentar enviar verificação SMTP |
| POST | `/auth/verify` | confirmar token de e-mail de uso único |
| POST | `/auth/resend-verification` | pedir novo link de confirmação |
| POST | `/auth/login` | autenticar, emitir cookies de sessão e CSRF |
| POST | `/auth/logout` | revogar sessão atual |
| GET/PATCH/DELETE | `/auth/me` | consulta, atualização e exclusão da conta |
| PATCH | `/auth/preferences` | preferências de notificações |
| POST | `/auth/password/change` | alterar senha e revogar todas as sessões |
| POST | `/auth/password/forgot` | solicitar recuperação sem enumeração |
| POST | `/auth/password/reset` | redefinir por token de uso único |
| GET | `/auth/sessions` | listar sessões atuais/encerradas |
| DELETE | `/auth/sessions/{id}` | revogar uma sessão |
| DELETE | `/auth/sessions?others=true` | revogar todas as outras sessões |
| GET/POST | `/emails` | listar / adicionar monitoramento |
| DELETE | `/emails/{id}` | remover endereço e histórico |
| POST | `/emails/{id}/scan` | agendar consulta real via Celery |
| GET | `/emails/{id}/history` | exposições e verificações |
| GET | `/dashboard` | números agregados e últimas notificações |
| GET | `/notifications` | listar notificações |
| POST | `/notifications/{id}/read` | marcar como lida |
| GET/POST/PUT | `/vault/config` | obter / criar / substituir wrappers cifrados |
| GET/POST | `/vault/items` | listar / criar itens cifrados |
| PUT/DELETE | `/vault/items/{id}` | editar / excluir ciphertext |

**Autorização:** operações de monitoramento e Vault exigem usuário com e-mail verificado. Endpoints sujeitos a limites Redis e a 401, 403, 404, 409, 422, 429 e 503 conforme o caso.

**Dados de exposições:** resposta de `scan` é `202` quando enfileirada. O resultado só aparece após processamento. A XposedOrNot não exige API Key. O `scan` enfileira com `202`; a consulta feita pelo worker pode registrar `unavailable` por cota gratuita, timeout ou indisponibilidade de Redis/API. Um `429` na requisição manual pode significar espera até uma nova tentativa. Nenhum erro deve ser representado como `clear`.

**Exemplo de resposta de dashboard:** `{ "monitored_emails": 0, "exposures": 0, "vault_items": 0, "pending_checks": 0, "emails": [], "notifications": [] }` (estrutura ilustrativa, não é dado real de usuário).

## Monitoramento configurável (novembro/2026)

Requer sessão autenticada e e-mail confirmado.

- `GET /api/monitoring/preferences` — retorna `email_enabled`, `email_interval`, `password_enabled`, `password_interval`.
- `PUT /api/monitoring/preferences` — substitui os quatro campos (todos obrigatórios); aceita somente `1h`, `24h`, `7d` e `30d` como intervalos.

Exemplo:

```json
{"email_enabled": true, "email_interval":"24h", "password_enabled": true, "password_interval":"7d"}
```

As configurações do monitoramento de senhas são apenas preferências. **A senha do Vault não é enviada ao backend.** A consulta automática de senhas é executada localmente com o cofre desbloqueado. A resposta de `GET /api/dashboard` inclui `email_health` com contagens pelos estados `clear`, `exposed`, `pending`, `queued`, `unavailable`.
