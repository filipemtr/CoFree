# CoFree — melhorias integradas (4 nov 2026)

Este documento descreve as mudanças implementadas **a partir do ZIP fornecido pelo usuário**. Não confundir implementação com validação de implantação em máquina real.

## Frontend / identidade visual

- Tema escuro **Midnight Sentinel** em todas as telas, com contrastes azul/ciano/verde e painéis de segurança.
- Favicon e marca gráfica própria em `frontend/public/favicon.svg`, referenciado em `frontend/index.html` e utilizado no componente da marca.
- Dashboard com distribuição **real** dos status de e-mails; não usa números fictícios. Cards e navegação atualizados.
- Efeitos visuais com atenção a teclado e `prefers-reduced-motion`; responsividade básica para celular.

## Cadastro

- Verificação de senha de **12+ caracteres** em cadastro e redefinição **antes do envio**.
- Mensagem específica e regras visuais: mínimo 12, recomendação de 16 e confirmação coincidente.
- Tradução dos erros estruturados `422` do Pydantic/FastAPI em português (`frontend/src/lib/errors.ts`); valores enviados nunca são exibidos na mensagem.

## Senhas expostas (manual)

- Rota **`/app/senhas`** no menu lateral; pesquisa de qualquer senha informada, com resultado de ocorrência e recomendações.
- API oficial gratuita **Pwned Passwords**. O navegador calcula SHA-1 e envia somente **5 caracteres do hash**, via `GET /range/{prefix}`, com `Add-Padding: true`. O sufixo é comparado localmente.
- **Nem senha em claro nem hash completo são enviados ao backend, persistidos ou transmitidos ao provedor.** O método verifica apenas se a senha está numa lista conhecida; ausência de correspondência não garante segurança.
- Gerador antigo preserva seu botão de consulta; o código da verificação foi separado em `frontend/src/crypto/pwned.ts` para ser reutilizado e testado.

## Monitoramento automático

**Configurações > Monitoramento automático:** alternâncias separadas para e-mails e senhas, com intervalos **1 hora, 1 dia, 1 semana ou 1 mês**.

**E-mails:** configurações persistidas no PostgreSQL em `monitoring_preferences`; migração Alembic `af43b7d1c202`. Os próximos agendamentos são recalculados, salvo backoff imposto pelo provedor. O Celery Beat seleciona só endereços habilitados e vence a cada 5 minutos; workers consultam XposedOrNot com limite Redis compartilhado. Frequências são *metas*, não garantias: a API pública possui cotas e pode impor adiamentos. Não se deve forçar chamadas para contornar a cota.

**Senhas:** devido à criptografia local do Vault, o backend **não consegue ler segredos** nem verificá-los quando o cofre está bloqueado. Após opt-in, o navegador, **na página do Vault aberto e desbloqueado**, consulta as senhas descriptografadas localmente (se ainda não verificadas no intervalo). Repete verificações enquanto a aba continua aberta e visível e reavalia ao retornar. Registra **apenas** em `localStorage` local do dispositivo: horário da última análise, número de senhas consultadas e quantas eram comprometidas. Não guarda senhas nem hashes. Os resultados locais não são sincronizados entre dispositivos nem geram alertas SMTP com o site fechado. Se a consulta falhar, não avança o horário da última verificação. O backend guarda somente opt-in e periodicidade.

**Status visual** no Vault mostra a última consulta e a próxima janela esperada. Para e-mails, a lista exibe última/próxima consulta, quando aplicável.

## Correção de healthchecks

O Dockerfile do backend tem healthcheck HTTP em 8000; ele era herdado por Celery, cujos processos não servem HTTP. O Compose agora define healthcheck de ping específico para worker e desabilita o check HTTP herdado para Beat. Para Beat, é preciso acompanhar os logs (`docker compose logs beat`).

## Validar após extrair

1. Preserve o `.env` **do seu computador** (não está neste pacote). Use `.env.example` se ainda não tiver.
2. `docker compose up --build -d` — o serviço `migrate` aplica a nova migração antes do backend.
3. `docker compose ps` (incluindo worker healthy; beat up sem healthcheck).
4. `/cadastro`: testar menos e mais de 12 caracteres e erros em português.
5. `/app/senhas`: consultar uma senha de **teste**, sem usar credenciais reais em máquinas compartilhadas.
6. `/app/configuracoes`: ativar e salvar ambas as frequências; atualizar a página e confirmar persistência.
7. `/app/emails`: cadastrar e verificar e-mails; conferir próxima execução e histórico.
8. `/app/vault`: adicionar credencial fictícia, habilitar automação de senhas, desbloquear o cofre e conferir a consulta local.
9. F12 > Rede: verificar que **somente** URLs `https://api.pwnedpasswords.com/range/XXXXX` são usadas para senhas, e nenhuma senha é enviada em requisições.
10. Executar testes do backend e frontend, descritos abaixo.

## Testes executados neste ambiente

- `pytest -q` no backend, suíte completa com os testes adicionais: **40 passaram, 3 ignorados** (testes que precisam do pacote Redis opcional neste ambiente).
- `node --experimental-strip-types --test frontend/tests/*.mjs`: **6 testes passaram** (privacidade/parsing da consulta e mensagens de erro).
- TSX e TS analisados sintaticamente com o parser TypeScript. **Build `npm run build` não validado** por impossibilidade de resolver `registry.npmjs.org` neste ambiente; CI/Docker do usuário devem confirmar.
- E2E com Playwright incluído, mas não executado neste ambiente; dependem de Docker e navegador disponíveis.

O ZIP **não inclui** `.env`, bancos locais SQLite nem chaves de produção. O arquivo `.env.example` não contém credenciais reais.

## Correção de horários (4 nov 2026)

- **Problema:** registros como `2026-11-04T16:59:00` são instantes em UTC gerados pelo backend, mas vinham sem indicação de fuso. O JavaScript interpretava como hora local, exibindo 16:59 em vez de 13:59 num navegador em `America/Recife` (UTC−3).
- **Correção:** função central `frontend/src/lib/dates.ts` considera UTC apenas os timestamps ISO do servidor sem `Z` ou deslocamento; preserva valores que já vêm com `Z` ou `-03:00`. O navegador exibe o instante no fuso local configurado pelo usuário.
- **Áreas afetadas:** histórico de verificações, horários de última/próxima verificação, notificações, sessões e análise local do Vault.
- **Dados e agendamento:** nenhuma migração ou alteração dos horários armazenados é necessária. O Celery continua trabalhando em UTC; apenas a apresentação muda.
- **Teste:** `frontend/tests/dates.test.mjs` cobre UTC sem fuso, offsets explícitos e o caso Recife 16:59 UTC → 13:59.
- **Aplicação no Docker:** substitua o projeto preservando `.env` e volumes; execute `sudo docker compose up -d --build frontend`, sem `down -v`.
