# Implantação

O projeto foi preparado para execução por Docker Compose, mas o ambiente atual não possibilitou validação de instalação limpa, build e operação de todos os serviços. **Não exponha ao público antes da validação integral**.

Etapas sugeridas: (1) configurar servidor isolado e Docker, (2) DNS e HTTPS com proxy e certificados válidos, (3) configurar segredos robustos fora do repositório, (4) verificar limites/termos da API gratuita XposedOrNot, consentimento dos e-mails monitorados e SMTP real, (5) migrar banco, (6) executar testes SQLite/PG/Redis, (7) Playwright e auditoria, (8) backup/restauração, (9) simular falha do provedor e do worker, (10) revisar LGPD, monitoramento e resposta a incidentes.

Comando inicial: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d`, após preparar `.env` com `ENVIRONMENT=production`, `FRONTEND_URL=https://dominio`, `COOKIE_SECURE=true` e SMTP externo. **O override não cria HTTPS; não abra a porta HTTP ao público.**

Use proteção de backups, política de retenção, observabilidade, rate limit distribuído testado, hardening de imagens, autenticação adicional do servidor e scanners CI antes de aprovar. A etapa de deploy automático está pendente; o workflow é apenas CI experimental e não entrega produção automaticamente.
