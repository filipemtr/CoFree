# Integrações externas — versão acadêmica gratuita

## Monitoramento de e-mails: XposedOrNot (sem API Key)

Documentação: https://xposedornot.com/api_doc  |  Código: `backend/app/providers/xposedornot.py`.

O `scan_monitor` continua desacoplado da API: chama `find_breaches(email)`, recebe `list[str]` com nomes de exposições e realiza persistência, deduplicação, histórico e notificações. O agendamento continua nos serviços Celery. A substituição do antigo HIBP pago exigiu somente trocar o adaptador e remover o bloqueio por chave de API; não houve alteração de schema ou migration.

Endpoint público: `GET https://api.xposedornot.com/v1/check-email/{email}`. O cliente usa HTTPS, `httpx` com timeout de 12 s e redirects desabilitados. Não transmite senhas do Vault. Resposta de sucesso documentada:

```json
{"status":"success","email":"user@example.com","breaches":[["Adobe","LinkedIn"]]}
```

A API também documenta a resposta `{"Error":"Not found","email":null}` para ausência de exposição. O adaptador considera somente essa resposta específica (com HTTP 200 ou 404) ou um sucesso sem nomes como resultado vazio. Erros genéricos HTTP 404, formatos diferentes, erro HTTP 429, 5xx, timeout e JSON inválido **não** são convertidos em resultados negativos. A UI distingue `clear` de `unavailable`. A consulta retorna nomes; campos avançados como dados expostos por categoria não são enriquecidos automaticamente nesta integração.

### Cotas gratuitas e filas

Segundo documentação consultada em 04/11/2026, o endpoint gratuito aplica **2 req/s, 25 req/h e 100 req/dia por IP**. O CoFree reserva limite conservador em um **script Lua atômico Redis/ZSET**, compartilhado pelos workers:

| Janela móvel | Teto CoFree | Teto publicado |
|---|---:|---:|
| 1 segundo | 1 | 2 |
| 1 hora | 24 | 25 |
| 24 horas | 95 | 100 |

A reserva ocorre *antes* da requisição HTTP, inclusive em caso de timeout. Se o Redis estiver indisponível, o monitoramento falha fechado como `unavailable` e não faz consultas sem controle de cota. A resposta HTTP 429 utiliza `Retry-After` em segundos quando disponível; agendamento de nova tentativa é persistido. O `scan_due` seleciona até 2 endereços vencidos por rodada de 5 minutos, para não gerar rajadas. Outros clientes no mesmo IP podem consumir a cota da XposedOrNot e ainda causar 429. Não há bypass de limites para testes públicos.

Este limite gratuito é adequado ao uso pessoal/acadêmico em baixo volume; não oferece garantia de intervalo fixo de monitoramento para vários usuários. **Ainda não há verificação de posse individual de cada e-mail monitorado:** apenas a conta principal exige confirmação. Em uma implantação pública, antes de monitorar outros endereços, implementar desafio de confirmação/autorização por endereço e revisar a base legal de tratamento de dados. A API envia o endereço completo ao fornecedor, conforme sua política de privacidade.

### Testes

Os testes de contrato com `httpx.MockTransport` cobrem: `200` com nomes e deduplicação, `200/404` com `Not found`, sucesso vazio, HTTP `429` e `Retry-After`, 401/403/5xx, resposta inconsistente, JSON inválido, timeout, negação antes da requisição e reserva via Redis. Integração real na rede, latência e cota do provedor não foram validadas aqui. MockTransport é usado **somente nos testes**, não no runtime.

## Senhas comprometidas: HIBP Pwned Passwords (gratuito)

Documentação: https://haveibeenpwned.com/API/v3#PwnedPasswords

O navegador calcula SHA-1 da senha *localmente* e envia apenas os 5 primeiros caracteres hexadecimais do hash a `https://api.pwnedpasswords.com/range/{prefix}` com `Add-Padding: true`. Compara os sufixos localmente. **Não envia senha original, hash completo nem dados do Vault** para o backend ou para o fornecedor. Essa funcionalidade **não depende da API paga de busca de e-mails do HIBP** e permanece intacta.

## SMTP

`backend/app/emailer.py`: SMTP parametrizado pelo `.env`, com Mailpit para receber mensagens de desenvolvimento, e SMTP externo para uma implantação apropriada. Sem SMTP configurado, não se deve afirmar que o e-mail foi entregue. Consulte `SMTP.md`.

## Pwned Passwords — verificação manual e automática local (novembro/2026)

O frontend agora expõe `/app/senhas` e compartilha `src/crypto/pwned.ts` com o gerador de senhas e o monitoramento local do Vault. A chamada gratuita usa `GET https://api.pwnedpasswords.com/range/{prefix5}`, `Add-Padding: true`, comparação do sufixo no navegador. Não requer chave de API. Automações de Vault só ocorrem com o cofre desbloqueado e visível; não existem jobs backend de senhas.
