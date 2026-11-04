# E-mail e notificações SMTP

Implementação em `backend/app/emailer.py`, via `smtplib`, com timeout e suporte a `SMTP_SSL` ou `STARTTLS`, remetente configurável e mensagens MIME multipart (HTML + texto).

**Fluxos implementados:** confirmação de conta, redefinição de senha, aviso de exposição nova (sem incluir dados secretos). Falhas retornam falso e são registradas sem revelar tokens, endereço de destino ou senha.

**Desenvolvimento:** por padrão, o Compose cria serviço `mailpit` com interface local em `http://localhost:8025` e SMTP em `mailpit:1025`. Esse é um SMTP de teste real de transporte dentro do Compose; ele não entrega mensagens na internet.

**Produção:** configurar `SMTP_HOST`, `SMTP_PORT`, `SMTP_SENDER`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`/`SMTP_SSL`. Para entregabilidade, validar SPF/DKIM/DMARC do domínio do remetente e limites do fornecedor.

**Pendência significativa:** a integração atual chama SMTP sincronamente após o commit; ainda não existe uma fila independente, reenvio de falhas ou gestão de templates transacionais com rastreabilidade completa. Não declarar notificação entregue quando o transportador SMTP não confirma o envio, nem confundir confirmação de envio SMTP com entrega final na caixa do destinatário.
