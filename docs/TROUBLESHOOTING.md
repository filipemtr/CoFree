# Resolução de problemas

- **`docker: command not found`**: instale Docker Engine/Desktop e Docker Compose plugin, reinicie terminal e valide `docker info`.
- **`POSTGRES_PASSWORD is required`**: copie `.env.example` para `.env` e substitua placeholders por segredos próprios.
- **Frontend abre mas API falha**: `docker compose ps`, `docker compose logs backend migrate postgres`; confirme migrations e o healthcheck `/health`.
- **Registro feito sem e-mail**: verifique `SMTP_HOST`, `docker compose logs backend mailpit` e interface `localhost:8025`. Não há token de ativação mostrado na tela.
- **Login retorna 403**: confirme endereço usando link enviado por SMTP.
- **Login retorna 429**: limite de segurança por origem foi alcançado; aguarde a janela informada em Retry-After.
- **Scan indisponível ou adiado**: cota pública XposedOrNot atingida, Redis ou API indisponível; não significa ausência de vazamento. O servidor não precisa de chave de API paga.
- **Scan fica em fila**: investigue `docker compose logs worker beat redis`, configuração de broker, Redis e limites gratuitos XposedOrNot.
- **Vault não abre**: confira senha mestra ou chave de recuperação; suporte não pode descriptografar os dados.
- **`npm` não encontra registro**: verifique DNS, proxy e acesso à internet; não há `node_modules` nem assets gerados no ZIP.
- **Erro `Origin` ou CSRF**: confira `FRONTEND_URL` (origem exata), cookies habilitados e header `X-CSRF-Token` no frontend.
- **Falha de build Docker**: consulte erro completo de dependências/arquitetura; builds não foram validados localmente na criação desta entrega.


## Erro `activeAnimations` / `motion-dom` durante o build do frontend

Em instalações novas, `framer-motion@12.23.0` pode baixar uma versão de `motion-dom` incompatível porque a dependência transitiva utiliza um intervalo de versões aberto. O projeto fixa `motion-dom@12.22.0` e `motion-utils@12.19.0` via `overrides` no `frontend/package.json`, alinhado às dependências declaradas pelo Framer Motion 12.23.0. Rode `sudo docker compose build --no-cache frontend && sudo docker compose up -d` para reconstruir. O teste definitivo é o build do frontend no Docker; esta correção deve ser validada no ambiente do usuário.
