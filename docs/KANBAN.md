# Kanban do CoFree

Método adotado: **Kanban**, sem sprints. Limite de trabalho em andamento recomendado: 3 cartões. Fluxo: **A fazer → Em andamento → Em revisão/teste → Concluído**. Cada cartão possui descrição, dependências, aceitação, testes e documentação; só chega a Concluído após execução e aprovação das verificações.

| Estado | Entrega / próximo item | Critério para concluir |
|---|---|---|
| Concluído (backend local) | Auth, recuperação, sessões, CSRF, CRUD e autorização; 16 pytest | 16/16 aprovados em SQLite |
| Em revisão/teste | Frontend React, UI responsiva, Vault criptografado e integração com API | Typecheck, build, testes do browser, revisão visual |
| Em revisão/teste | Compose Postgres/Redis/SMTP, Celery e migrations | `docker compose up`, healthchecks, persistência e E2E |
| Em revisão/teste | Integração XposedOrNot gratuita, respostas e quotas | Contratos locais aprovados; ainda falta ensaio real com 200/404/429 e Redis/Celery via Docker |
| A fazer | Fila SMTP, retry/backoff+jitter/circuit breaker, execução dos limites Redis | Testes de falhas, concorrência e deduplicação |
| A fazer | Gestão robusta de chaves, recuperação/rotação completa, dispositivos | Testes criptográficos E2E e ameaça revisada |
| A fazer | Execução e revisão CI GitHub Actions, Semgrep, Trivy, ZAP | Logs reais, relatórios e correções |
| A fazer | Termos/LGPD, observabilidade, hardening de produção | Política operacional e revisão jurídica |

Antes de mover um cartão, executar **Implementar → Testar → Corrigir → Testar novamente → Documentar → Aprovar**. Testes E2E e auditoria que ainda não rodaram não aparecem como concluídos.

## Release novembro/2026 — implementação concluída, validação de implantação pendente

- [x] Feedback em português e 12 caracteres no cadastro/redefinição.
- [x] Página dedicada de consulta de senhas vazadas com k-anonymity.
- [x] Frequências independentes e opt-in para e-mails/senhas (1h/24h/7d/30d).
- [x] E-mails agendados por Celery e persistência de preferências.
- [x] Verificação local das senhas do Vault enquanto aberto/desbloqueado; limitação documentada.
- [x] Tema escuro, favicon original, dashboard com indicadores reais e estados visuais.
- [x] Testes unitários e migração incluídos e executados em ambiente local.
- [ ] Executar Docker/Vite/Playwright reais e auditorias de segurança na máquina de destino; ausência de dependências neste ambiente não permite atestar essas etapas.
