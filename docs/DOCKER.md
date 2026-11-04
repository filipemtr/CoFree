# Containers e operação

Serviços em `docker-compose.yml`: `postgres` (com volume persistente), `redis` (volume e AOF), `mailpit` (somente desenvolvimento), `migrate` (job Alembic), `backend`, `worker` (Celery), `beat` (Celery Beat), `frontend` (Nginx SPA) e `backend-tests` (perfil testes).

- Rede `internal` privada do Compose; nenhum mapeamento público de PostgreSQL/Redis.
- A interface HTTP é mapeada para `127.0.0.1:3000`; Mailpit para `127.0.0.1:8025`.
- Backend usa Python 3.12 e usuário não root; frontend Node 22 em build multi-stage e Nginx Alpine runtime.
- Healthcheck em Postgres, Redis, backend e frontend. O job de migração deve concluir antes do backend iniciar.
- Imagens têm tags específicas em vez de `latest`.

**Inicialização:** `docker compose config && docker compose up --build -d`. **Teste do backend no container:** `docker compose --profile tests run --rm backend-tests`. **Logs:** `docker compose logs --tail=100 -f`. **Encerramento:** `docker compose down` sem `-v`.

**Produção:** override `docker-compose.prod.yml` é preparação inicial, não solução de produção completa. Necessita HTTPS com reverse proxy, rotinas de backup/restore, gestor de segredos, monitoramento, hardening e auditoria. O Docker Engine não estava disponível durante a construção do pacote; construção, healthchecks, migrations em PostgreSQL e persistência não foram validados por execução Docker aqui.
