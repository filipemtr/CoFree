# Playwright — testes E2E

Configuração: `frontend/playwright.config.ts`; testes: `frontend/e2e/cofree.spec.ts`. Testes declarados:

- Cadastro, recebimento de mensagem no Mailpit, confirmação por link real, login, monitoramento e revogação de sessão.
- Inicialização do Vault no browser, exibição única da recuperação, criptografia de uma credencial, bloqueio e desbloqueio.
- Landing page e verificação básica responsiva.

Projetos Chromium desktop e viewport mobile. Em falhas, há screenshot e trace. Para executar, inicialize todos os serviços Docker, inclusive Mailpit, e depois:

```bash
cd frontend
npm install
npx playwright install chromium
npx playwright test --project=chromium
```

O serviço precisa responder em `http://localhost:3000`; Mailpit API em `http://localhost:8025`. `BASE_URL` e `MAILPIT_URL` são configuráveis.

**Status:** roteiros E2E escritos, **não executados**; existem riscos de seletor, compatibilidade ou sincronização ainda não observados. Só marcar aprovados após executar, revisar traces e corrigir falhas. Não usar cenários com dados simulados para provar consulta externa real da XposedOrNot.
