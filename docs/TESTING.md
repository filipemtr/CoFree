# Plano de testes e execução efetiva

## Resultados observados na criação do pacote

Comando executado: `cd backend && pytest -q --disable-warnings`.

**Resultado desta adaptação (04/11/2026):** `36 passed, 3 skipped in 7.40s` em pytest. Os três skips são testes dependentes de Celery e do pacote Redis, não disponíveis neste ambiente; executar o mesmo comando na imagem Docker com dependências instaladas. O ambiente de testes utiliza SQLite via SQLAlchemy, `TestClient` FastAPI, interceptação de mensagem SMTP por monkeypatch e adaptador XposedOrNot simulado apenas nos testes com `httpx.MockTransport`, e stub apenas nos testes de regras de negócio.

Cobertura funcional dos casos: Argon2id; registro/verificação/login/logout; token de verificação de uso único; CSRF ausente/inválido; sessão revogada; recuperação de senha de uso único e expiração; alteração de senha; não-enumeração de cadastro duplicado; rate limit; duplicidade de e-mail; isolamento de usuários; serviço de scan com resultados simulados em teste (e idempotência); falha XposedOrNot não equivale a e-mail seguro; enfileiramento independe de API Key, contrato 200/404/429, timeout e resposta malformada; configuração Vault, CRUD cifrado e validação de envelope; exclusão cascata.

**Não executados nesta sessão:** testes completos com Postgres/Redis/Celery, SMTP via Mailpit, E2E Playwright, análise Semgrep/Trivy/ZAP, builds Docker e frontend TypeScript. No pacote original foram feitos parsing YAML e análise sintática TypeScript limitada. Esses testes **não substituem** `docker compose config`, typecheck nem build npm; nesta revisão não houve instalação Docker ou dependências npm.

## Execução reproduzível

```bash
cd backend
python -m pip install -r requirements-dev.txt
pytest -q
# ou totalmente Docker:
cd ..
docker compose --profile tests run --rm backend-tests
```

## Próximos testes obrigatórios antes de implantação

1. PostgreSQL real: migração, transações, exclusão cascata e concorrência.
2. Redis: janelas de rate limit em vários workers, fail-closed em produção.
3. Celery: enfileiramento, retries, reinícios e idempotência sob concorrência.
4. SMTP: Mailpit + provedor externo e falhas/timeout.
5. Vault: biblioteca libsodium carregada no navegador, teste AES-GCM/AAD/Argon2id, recuperação em dispositivo diferente, rotação e perda de chaves.
6. Playwright: múltiplos browsers/viewport, falhas de API, acessibilidade e cenários de ponta a ponta.
7. Docker: build, healthchecks, persistência, restauração, clean install.
8. SAST/DAST/SCA: Semgrep, Trivy, OWASP ZAP e revisão humana.

## Testes de regressão da atualização (novembro/2026)

- `cd backend && pytest -q tests/test_schedules.py`: permissões, validação das quatro frequências, ativação/desativação e reagendamento.
- `cd frontend && npm run test:unit`: consulta por prefixo SHA-1, ausência de vazamento de texto puro na requisição, erros do provedor e tradução de HTTP 422.
- `cd frontend && npm run test:e2e`: testes de validação do cadastro, verificador de senhas com resposta interceptada e persistência das frequências (precisam de navegador e stack em execução).

Falta executar build Docker/Vite e E2E nesta máquina de geração. Esses itens não devem ser considerados aprovados até rodarem no ambiente-alvo.
