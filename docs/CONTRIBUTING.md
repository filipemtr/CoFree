# Contribuição e desenvolvimento

Fluxo Kanban em `docs/KANBAN.md`. Alterações devem descrever objetivo, critério de aceite, risco, teste e documentação correspondente. Prioridades de revisão: confidencialidade do Vault, isolamento de usuários, sessões, API externa e resiliência.

Backend: Python 3.12, FastAPI, tipagem onde possível, SQLAlchemy 2, Alembic, pytest, Ruff e Bandit. Frontend: TypeScript estrito, React, React Router, Framer Motion, CSS modular e acessibilidade; verifique build TypeScript e Playwright.

```bash
cd backend && pytest -q
cd ../frontend && npm run build
cd .. && docker compose config
```

Nunca publique `.env`, secrets ou dumps. Não remova testes para obter build verde. Todo bug corrigido deve ganhar caso de regressão; todas as novas migrations precisam de revisão. Regras de aceite incluem execução e relatório real, não apenas presença de arquivos.
