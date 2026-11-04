# Segurança e modelo de ameaças

Esta é uma **implementação sob validação**, não certificação de segurança. Referências: OWASP Top 10, OWASP ASVS, OWASP API Security Top 10, práticas de segurança da informação e LGPD.

## Medidas técnicas presentes

- **Credenciais de acesso:** Argon2id server-side (`argon2-cffi`, memória 64 MiB, custo 3) com salt aleatório por hash; nunca armazenar senha original.
- **Sessões:** identificadores aleatórios emitidos em cookies HttpOnly/SameSite=Lax; somente SHA-256 do token armazenado; revogação checada no banco a cada requisição protegida; expiração de sete dias.
- **CSRF:** token aleatório por sessão, cookie legível exclusivamente para cabeçalho `X-CSRF-Token`, hash persistido, validação de `Origin` quando presente. A ausência do token em mutações autenticadas resulta em HTTP 403.
- **Rate limiting:** janela fixa com contadores atômicos no Redis; retorno 429 + Retry-After. Em modo produção, falha de Redis impede uso da API; em desenvolvimento/testes há fallback local de processo único.
- **Isolamento:** buscas por recurso exigem id + owner (`user_id`), reduzindo IDOR/BOLA. Teste negativo cobre acesso cruzado.
- **Headers:** CSP restritiva, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy e Cache-Control.
- **Vault:** somente ciphertext e wrappers de chaves no servidor; AES-GCM autentica conteúdo e detecta corrupção de bytes cifrados; cliente possui a chave enquanto desbloqueado.
- **Logs:** eventos de auditoria tipados, sem salvar senhas ou tokens.
- **Integrações:** XposedOrNot HTTPS, controles Redis de cota e timeouts/falhas explícitos; dados externos não são confundidos com verificação segura.

## Lacunas e riscos conhecidos

1. Auditoria de criptografia independente e modelagem aprofundada de ameaças ainda pendentes. Não utilizar o Vault para segredos de alto impacto sem revisão e E2E criptográfico real.
2. Ausência de MFA na autenticação principal e detecção de sessão suspeita baseada em IP/device fingerprint.
3. Rate limiting por IP e rota é básico e carece de testes distribuídos e controles granulares por usuário/endpoint.
4. O endpoint que reencapsula wrappers não exige reautenticação recente no backend; mitigar antes de produção sensível.
5. A aplicação ainda não tem política automatizada de retenção, exportação de dados e DPO operacional.
6. React e imagens Docker não foram compilados/escaneados neste ambiente. A auditoria ZAP/Semgrep/Trivy não foi executada.
7. Código JavaScript de terceiros servido pelo frontend poderia comprometer um Vault desbloqueado: CSP, SRI quando apropriado, revisão de dependências e avaliação do supply-chain são críticos.
8. Ainda é preciso testar recuperação com outro dispositivo real, rotação de chave, acessibilidade e múltiplos navegadores.
9. Autenticação de login e registro em rotas públicas exige defesa adicional contra login CSRF/abuso por origem, idealmente com políticas de origem e monitoramento.
10. Não há verificação explícita da titularidade de endereços de monitoramento adicionais. Revisar privacidade/consentimento e uso da API de terceiros.

## Regras de operação

- Exigir HTTPS e cookies `Secure` na implantação pública.
- Nunca colocar `.env`, backups, senhas ou API keys no Git ou no ZIP.
- Não publicar Postgres/Redis diretamente. Encerrar todas as sessões após incidente.
- Monitorar erros 429/503 do XposedOrNot; nunca apresentar erro como ausência de exposição.
- Revisar incidentes, backups, controle de acesso e direito de exclusão com assessoria jurídica antes de uso real.

## Verificação de senhas (novembro/2026)

A pesquisa manual e a verificação periódica do Vault utilizam o endpoint de k-anonymity do Pwned Passwords e **não enviam texto puro nem hash SHA-1 completo ao provedor ou ao backend**. São enviados somente cinco caracteres hexadecimais do hash SHA-1. O SHA-1 aqui é usado apenas para índice de consulta do corpus; **não** para armazenar credenciais. O backend continua usando o hash de senha de login previsto no seu módulo de autenticação, sem alterações.

Verificação periódica de senhas não funciona com a aplicação fechada nem com Vault bloqueado. Optamos por limitar a funcionalidade a disponibilizar ao servidor material que comprometeria o modelo de criptografia local. Somente data, quantidade e contagem agregada de resultados são armazenadas localmente no navegador; sua remoção pode ocorrer ao limpar os dados do site.

O release omite `.env` e bancos de dados locais do ZIP distribuído. Verifique mudanças na política de CSP antes de implantar em produção.
