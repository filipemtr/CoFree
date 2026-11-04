# Auditoria de segurança e evidências

## Ferramentas propostas e configuradas em CI

| Ferramenta | Alvo | Estado desta entrega |
|---|---|---|
| OWASP ZAP baseline | DAST contra `http://localhost:3000` em runner Docker isolado | Workflow escrito; NÃO EXECUTADO |
| Semgrep | Código Python, JavaScript, TypeScript | Workflow escrito; NÃO EXECUTADO |
| Trivy | Sistema de arquivos/dependências | Workflow escrito; NÃO EXECUTADO |
| Bandit | Código Python | Workflow escrito; NÃO EXECUTADO |
| Ruff | lint Python | Requisito incluído; binário indisponível neste ambiente |
| npm audit | dependências frontend | Workflow escrito; NÃO EXECUTADO |
| pytest segurança | auth, csrf, idor, rate limit, revogação, vault | 36 testes backend aprovados, 3 ignorados (dependências Celery/Redis ausentes) |

O workflow não garante aprovação até rodar de fato no GitHub e corrigir incompatibilidades das actions, versões e regras. Recomenda-se também revisar manualmente segurança de cookies, dados pessoais, CSP, dependências, CSRF de rotas públicas, fluxo de recuperação de Vault, imutabilidade de auditoria e conformidade LGPD.

**Vulnerabilidades conhecidas / riscos abertos:** consulte `SECURITY.md`. Não declarar ausência de vulnerabilidades porque testes automatizados passaram. Relatórios ZAP/Trivy/Semgrep produzidos por varreduras reais **não existem** nesta entrega.

**Comandos ilustrativos para ambiente de auditoria:** `semgrep scan --config auto --error backend/app frontend/src`, `trivy fs --severity HIGH,CRITICAL .`, `docker compose up --build -d` seguido por ZAP baseline contra apenas o próprio contêiner local. Não executar ZAP destrutivo na XposedOrNot, no HIBP Pwned Passwords ou em sistemas externos.
