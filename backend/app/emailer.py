import html
import logging
import smtplib
from email.message import EmailMessage
from .settings import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, content: str) -> bool:
    """Send SMTP message; fail transparently if unconfigured. Never log recipient or tokens."""
    s = get_settings()
    if not s.smtp_host:
        logger.warning('SMTP unavailable: mail not sent')
        return False
    msg = EmailMessage()
    msg['To'], msg['From'], msg['Subject'] = to, s.smtp_sender, subject
    msg.set_content(content)
    msg.add_alternative(f'<html lang="pt-BR"><body style="font-family:Arial,sans-serif;background:#f4f7fb;padding:32px"><main style="background:white;max-width:550px;padding:32px;margin:auto;border-radius:16px"><h1 style="color:#172c52">CoFree</h1><p style="white-space:pre-wrap">{html.escape(content)}</p><small>Proteção digital por Vela</small></main></body></html>', subtype='html')
    try:
        if s.smtp_ssl:
            client = smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=12)
        else:
            client = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=12)
        with client:
            if s.smtp_starttls:
                client.starttls()
            if s.smtp_username:
                client.login(s.smtp_username, s.smtp_password)
            client.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception('SMTP delivery failed (recipient omitted)')
        return False


def send_action_link(email: str, kind: str, token: str) -> bool:
    from urllib.parse import quote
    s = get_settings()
    path = 'verificar-email' if kind == 'verify' else 'redefinir-senha'
    link = f'{s.frontend_url}/{path}?token={quote(token)}'
    title = 'Verifique seu e-mail' if kind == 'verify' else 'Redefina sua senha'
    return send_email(email, f'CoFree | {title}', f'{title}\n\nAcesse o link abaixo para continuar:\n{link}\n\nSe você não solicitou esta ação, ignore esta mensagem.')
