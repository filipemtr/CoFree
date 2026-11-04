# CoFree — guia de instalação (edição acadêmica com XposedOrNot)

Este guia instala o **CoFree** no computador usando **Docker Compose** e a API pública **XposedOrNot**, que **não exige API Key nem assinatura para consultas básicas de e-mails vazados**. O serviço gratuito tem limites compartilhados por IP. A verificação de senhas pelo **HIBP Pwned Passwords** continua gratuita e ocorre no navegador, sem expor a senha original.

> **Importante:** esta é uma aplicação acadêmica em desenvolvimento, não um serviço homologado para produção. Nunca cadastre senhas reais de uso pessoal, profissional ou bancário antes de finalizar a auditoria do Vault e da implantação. Consulte `docs/RELATORIO_FINAL.md`.

## 1. Requisitos

- **Docker Engine + Docker Compose v2** (ou Docker Desktop com Compose integrado).
- Internet durante a primeira construção para baixar imagens e dependências. Internet também é necessária para consultas reais à XposedOrNot.
- Aproximadamente **4 GB de RAM livre** (mais pode ser necessário para builds) e espaço em disco para imagens e volumes.
- Portas **3000** (CoFree) e **8025** (Mailpit, somente desenvolvimento) livres no computador.

**Não é necessário instalar** Python, Node, PostgreSQL, Redis, Celery ou npm no computador para rodar pelo Docker.

### Linux (Ubuntu, Debian e Zorin OS)

Instale o Docker Engine e o **Compose plugin** seguindo as instruções oficiais para sua distribuição:

- https://docs.docker.com/engine/install/
- https://docs.docker.com/compose/install/linux/

Depois execute:

```bash
docker --version
docker compose version
docker info
```

Se o Docker exigir permissões de administrador, use `sudo docker compose ...` ou configure seu usuário segundo as orientações oficiais; entrar no grupo `docker` concede privilégios elevados ao usuário.

### Windows 10/11

1. Habilite o WSL2 com `wsl --install` no PowerShell administrativo (se ainda não estiver disponível).
2. Instale o Docker Desktop e habilite **WSL2 backend** e a integração com sua distribuição Ubuntu.
3. Extraia o projeto de preferência no sistema de arquivos Linux do WSL2, abra o terminal Ubuntu e rode `docker compose version`.
4. Use o comando `cp` no shell do WSL. Se executar pelo PowerShell, copie com `Copy-Item .env.example .env`.

Documentação: https://docs.docker.com/desktop/setup/install/windows-install/

### macOS (Intel ou Apple Silicon)

Instale Docker Desktop (https://docs.docker.com/desktop/setup/install/mac-install/), abra o aplicativo, aguarde o serviço iniciar e confirme `docker info` e `docker compose version` no Terminal.

## 2. Extração e configuração inicial

Extraia o arquivo `cofree-xposedornot.zip`. O ZIP contém uma pasta raiz chamada `cofree`. Abra um terminal nessa pasta, onde está `docker-compose.yml`:

```bash
cd cofree
cp .env.example .env
```

**Atenção:** `.env` contém segredos e não deve ser publicado nem enviado ao GitHub. Edite-o com um editor de texto e substitua, obrigatoriamente:

```dotenv
POSTGRES_PASSWORD=SUA_SENHA_ALEATORIA_DE_BANCO
APP_SECRET=OUTRO_SEGREDO_ALEATORIO_DE_32_OU_MAIS_CARACTERES
```

Para gerar dois valores aleatórios distintos em Linux/macOS/WSL:

```bash
openssl rand -hex 32
openssl rand -hex 32
```

Copie o primeiro para `POSTGRES_PASSWORD` e o segundo para `APP_SECRET`. Evite `%`, `@`, `#`, `:` ou `/` na senha do banco, pois ela é usada em URL. Caracteres hexadecimais não causam esse problema.

As configurações de **desenvolvimento local** já estão definidas no `.env.example`:

```dotenv
ENVIRONMENT=development
FRONTEND_URL=http://localhost:3000
COOKIE_SECURE=false
SMTP_HOST=mailpit
SMTP_PORT=1025
CHECK_INTERVAL_HOURS=24
```

`COOKIE_SECURE=false` é adequado **somente** para HTTP no computador local. Em implantação pública, utilize HTTPS e `COOKIE_SECURE=true`.

### A API XposedOrNot precisa de chave?

**Não.** Não há cadastro, assinatura ou `HIBP_API_KEY` para a consulta básica utilizada por este projeto. O backend consulta:

```text
GET https://api.xposedornot.com/v1/check-email/{email}
```

Documentação oficial: https://xposedornot.com/api_doc

O limite publicado para o endpoint gratuito, **por IP**, é de **2 requisições/segundo, 25/hora e 100/dia**. O CoFree usa um controle global no Redis, com margem (1/segundo, 24/hora e 95/dia), para que os workers não ultrapassem voluntariamente a cota. Consultas feitas por outros programas que compartilham o mesmo IP também consomem a cota do provedor. Se ela acabar, a verificação é adiada e o estado é **indisponível**, nunca "sem vazamentos".

O agendador Celery seleciona até **2 endereços vencidos a cada 5 minutos**, e cada endereço é reavaliado conforme `CHECK_INTERVAL_HOURS`. Com muitos endereços, os resultados poderão atrasar por causa do limite gratuito.

> **Privacidade:** a consulta envia o endereço de e-mail completo ao serviço XposedOrNot. Cadastre apenas e-mails sob seu controle ou para os quais há autorização válida. A aplicação ainda precisa de revisão de consentimento para monitorar e-mails de terceiros. As senhas do Vault **não** são enviadas a esse provedor.

## 3. Configurar e-mails de verificação (grátis no desenvolvimento)

Não é preciso contratar serviço SMTP para testar a aplicação no computador. O contêiner `mailpit` recebe as mensagens de cadastro e recuperação **localmente**.

- Caixa de entrada de teste: http://localhost:8025
- Remetente padrão: `CoFree <no-reply@cofree.local>`

Mailpit **não envia e-mails para a internet**. Para entrega real a caixas externas em ambiente apropriado, configure no `.env`:

```dotenv
SMTP_HOST=servidor.smtp.exemplo
SMTP_PORT=587
SMTP_USERNAME=usuario_smtp
SMTP_PASSWORD=senha_smtp
SMTP_SENDER=CoFree <no-reply@dominio-autorizado.com>
SMTP_STARTTLS=true
SMTP_SSL=false
```

Para porta 465, normalmente use `SMTP_SSL=true` e `SMTP_STARTTLS=false`, de acordo com o fornecedor. Não use credenciais pessoais em um repositório público e não utilize Mailpit em produção.

## 4. Iniciar o CoFree

Na pasta raiz do projeto:

```bash
docker compose config
docker compose up --build -d
docker compose ps
```

A primeira construção baixa e instala as dependências. O Compose inicia PostgreSQL, Redis, Mailpit, migrations, FastAPI, Celery Worker, Celery Beat e Nginx/React. O serviço `migrate` **deve encerrar com código zero** depois de criar/atualizar as tabelas; esse encerramento é normal.

Abra:

- **Aplicação:** http://localhost:3000
- **Caixa de e-mails de desenvolvimento:** http://localhost:8025
- **Verificação da API:** http://localhost:3000/health
- **Swagger da API:** http://localhost:3000/docs

Se o navegador mostrar erro de conexão ou `502`, diagnostique:

```bash
docker compose ps
docker compose logs --tail=120 postgres migrate redis backend worker beat frontend
```

## 5. Testar o fluxo acadêmico completo

1. Abra `http://localhost:3000` e crie uma conta de teste com um e-mail de sua propriedade.
2. Abra `http://localhost:8025`, encontre o e-mail de verificação e acesse o link. **No Mailpit, o destinatário de teste não precisa existir na internet.**
3. Volte ao CoFree e faça login.
4. Entre em **Meus e-mails**, cadastre um endereço que você tenha direito de consultar e solicite uma verificação.
5. A consulta é processada em segundo plano pelo Celery; pode aparecer como **pendente**, **na fila**, **exposto**, **sem exposição conhecida** ou **indisponível**. Consulte o histórico depois do processamento.
6. Se o provedor responder `429`, tiver problemas de rede ou houver falha no Redis, o CoFree registra indisponibilidade e programa nova tentativa. **Isso não prova que o e-mail está seguro.**
7. Experimente o gerador de senhas e a função **Verificar senha comprometida**, que usa o endpoint gratuito HIBP Pwned Passwords com k-anonymity no navegador.
8. Teste o Vault apenas com **credenciais fictícias** até completar auditoria criptográfica e testes em navegador.

O backend não cria exposições falsas para simular consultas reais. Nos testes automatizados, as respostas do provedor são simuladas **somente no teste**, por meio do `httpx.MockTransport`/monkeypatch.

### Verificar serviços e migrations

```bash
curl -f http://localhost:3000/health
docker compose exec postgres pg_isready -U cofree -d cofree
docker compose exec redis redis-cli ping
docker compose exec backend alembic current
docker compose logs --tail=80 worker beat
```

Esperado: HTTP 200 no `health`, Postgres aceitando conexões, `PONG` no Redis e migration registrada como `head`.

## 6. Executar testes

Para os testes de backend sem instalar Python na máquina:

```bash
docker compose --profile tests run --rm backend-tests
```

O contêiner de testes usa SQLite isolado e instala as dependências declaradas. Os testes cobrem autenticação, Vault, monitoramento e contrato da XposedOrNot, incluindo respostas `200`, `404`, `429`, falhas de rede e proteção contra falsos negativos.

Para compilar o frontend dentro de uma imagem Docker, utilize o build normal:

```bash
docker compose build frontend
```

O repositório também inclui Playwright e o workflow CI. Para executar os testes de navegador em uma máquina com Node 22 e Chromium instalado:

```bash
cd frontend
npm install
npx playwright install chromium
npx playwright test --project=chromium
```

Mantenha a aplicação e Mailpit ligados durante os E2E. O build, os testes em Docker, os E2E, o GitHub Actions e as auditorias **não foram executados nesta entrega local**; ver relatório para os resultados efetivamente alcançados.

## 7. Logs, reinicialização e parada

```bash
docker compose logs -f --tail=100 backend worker beat
docker compose restart backend worker beat
docker compose stop
docker compose start
docker compose down
```

Os dados persistem nos volumes `postgres_data` e `redis_data`. **Não use `docker compose down -v`**, pois apagará os volumes e poderá destruir os dados.

Para atualizar o código e reconstruir:

```bash
docker compose up --build -d
```

## 8. Backup e restauração

Na raiz do projeto (shell Linux/macOS/WSL):

```bash
sh infrastructure/scripts/backup.sh
# Confirme o nome real do arquivo de backup na pasta backups/.
sh infrastructure/scripts/restore.sh backups/cofree-AAAAmmddTHHMMSSZ.dump
```

A restauração sobrescreve objetos existentes; faça cópia adicional antes de restaurar. Mantenha backups **criptografados, privados e fora do computador principal**. Os scripts foram fornecidos, mas ainda precisam de ensaio real com PostgreSQL.

## 9. Erros frequentes

| Problema | Causa provável / solução |
|---|---|
| `docker: command not found` | Instale Docker e Compose conforme a seção 1. |
| `port is already allocated` | Libere as portas 3000 ou 8025. |
| Erro de variável `POSTGRES_PASSWORD` ou `APP_SECRET` | Verifique se criou `.env` na raiz e preencheu os segredos. |
| `502 Bad Gateway` | Verifique `docker compose ps` e os logs de `migrate`/`backend`. |
| E-mail de confirmação não chega na sua caixa Gmail | Em desenvolvimento ele aparece **somente no Mailpit**, porta 8025. |
| Monitoramento continua `queued` | Verifique `docker compose logs worker beat redis` e se o Redis está saudável. |
| Monitoramento `unavailable` | API externa, rede ou cota gratuita indisponível; aguarde a próxima verificação. Não é resultado negativo. |
| Provedor responde `429` | A cota gratuita por IP foi atingida, possivelmente por outras aplicações; evite scans repetidos. |
| Testes não conseguem iniciar | Verifique que o Docker está ativo e use `docker compose --profile tests run --rm backend-tests`. |
| Dados sumiram após alterar o Compose | Verifique volumes e evite `down -v`; restaure backup se necessário. |

## 10. Publicação externa e segurança

O arquivo `docker-compose.prod.yml` é apenas uma base de configuração; **não configura TLS nem torna o sistema automaticamente seguro**. Antes de disponibilizá-lo na internet, é necessário configurar HTTPS, URL e cookies seguros, SMTP legítimo, isolamento de serviços e backups, revisão de privacidade/LGPD, monitoramento, Playwright, ZAP, Semgrep, Trivy e auditoria criptográfica. A capacidade da API gratuita pode ser insuficiente para muitos usuários. Consulte `docs/DEPLOYMENT.md`, `docs/SECURITY.md` e `docs/RELATORIO_FINAL.md`.

### Referências oficiais

- XposedOrNot: https://xposedornot.com/api_doc
- Repositório da API: https://github.com/XposedOrNot/XposedOrNot-API
- HIBP Pwned Passwords (sem chave): https://haveibeenpwned.com/API/v3#PwnedPasswords
- Docker: https://docs.docker.com/


### Problema: `activeAnimations is not exported by motion-dom`

O projeto fixa as versões transitivas `motion-dom` e `motion-utils` no `frontend/package.json` com `overrides`. Se você estiver com uma versão anterior do ZIP, substitua a pasta do projeto pelo pacote corrigido, preserve o arquivo `.env` e reconstrua o frontend:

```bash
sudo docker compose build --no-cache frontend
sudo docker compose up -d
```

---

## Atualização: tema escuro, verificação de senhas e agendamento (novembro/2026)

A partir desta versão, **preserve seu próprio `.env` antes de substituir os arquivos**. O ZIP não contém `.env` e não altera automaticamente segredos existentes. Se necessário, crie-o com `cp .env.example .env` e mantenha o Mailpit local (`SMTP_HOST=mailpit`, `SMTP_PORT=1025`).

Após atualizar o projeto na mesma pasta, na raiz `cofree/`:

```bash
sudo docker compose config --quiet
sudo docker compose up --build -d
sudo docker compose ps
```

O serviço `migrate` aplicará a migração que cria `monitoring_preferences` e mantém os registros anteriores. **Não execute `docker compose down -v`**: `-v` apaga os volumes do PostgreSQL/Redis.

Abra:

- Site: http://localhost:3000
- Swagger: http://localhost:8000/docs (a porta do backend está publicada no loopback)
- Mailpit: http://localhost:8025
- Novo verificador: http://localhost:3000/app/senhas (requer login)
- Monitoramento automático: http://localhost:3000/app/configuracoes

As consultas de e-mails são executadas pelo servidor; as consultas periódicas às senhas do Vault rodam **apenas com o Vault desbloqueado e a aba ativa**, sem enviar segredos para o backend. Intervalos disponíveis: 1 hora, 1 dia, 1 semana, 1 mês. O agendamento de e-mails está sujeito aos limites da API XposedOrNot (portanto pode atrasar).

Testes locais: `cd backend && pytest -q`; `cd frontend && npm install && npm run build && npm run test:unit`. O E2E exige `npx playwright install chromium` e serviços funcionando (`npm run test:e2e`). Veja `docs/MELHORIAS_2026_11.md` para todas as mudanças, limitações e testes.

## Correção de exibição dos horários (4 nov 2026)

Os horários da API são registrados em UTC. O frontend interpreta as datas ISO sem fuso vindas da API como UTC e exibe o resultado no **fuso horário do navegador**. Por exemplo, `2026-11-04T16:59:00` corresponde a **13:59** em Recife (UTC−3).

Se tiver uma instalação anterior mostrando horário adiantado, atualize o frontend e force a atualização do navegador (`Ctrl+Shift+R`):

```bash
sudo docker compose up -d --build frontend
```

Não altere o relógio do container, nem modifique horários já salvos no PostgreSQL, nem remova volumes para corrigir apenas a apresentação. Se o navegador estiver configurado com um fuso diferente do seu, ajuste o sistema operacional.
