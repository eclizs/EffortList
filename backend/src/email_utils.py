from email.message import EmailMessage
from html import escape
from urllib.parse import urlencode

import aiosmtplib

from .config import settings


async def send_email(
    to_email: str,
    subject: str,
    plain_text: str,
    html_content: str | None = None
) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(plain_text)

    if html_content:
        message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.mail_server,
        port=settings.mail_port,
        username=settings.mail_username or None,
        password=settings.mail_password.get_secret_value() or None,
        start_tls=settings.mail_use_tls,
        timeout=settings.mail_timeout_seconds,
    )


async def send_password_reset_email(to_email: str, token: str) -> None:
    reset_url = (
        f"{settings.frontend_url.rstrip('/')}/reset-password?"
        f"{urlencode({'token': token})}"
    )
    expiration = settings.reset_token_expire_minutes
    escaped_reset_url = escape(reset_url, quote=True)

    await send_email(
        to_email=to_email,
        subject="Reset your EffortList password",
        plain_text=(
            "A password reset was requested for your EffortList account.\n\n"
            f"Reset your password: {reset_url}\n\n"
            f"This link expires in {expiration} minutes. If you did not request "
            "this, you can ignore this email."
        ),
        html_content=(
            '<!doctype html><html lang="en"><body style="margin:0;padding:0;'
            'background-color:#f4f6f8;color:#172033;font-family:Arial,'
            'Helvetica,sans-serif;">'
            '<div style="display:none;max-height:0;overflow:hidden;opacity:0;">'
            "Reset your EffortList password."
            "</div>"
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="width:100%;background-color:#f4f6f8;border-collapse:collapse;">'
            '<tr><td align="center" style="padding:40px 16px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="width:100%;max-width:560px;background-color:#ffffff;'
            'border:1px solid #dce2ea;border-radius:16px;border-collapse:separate;'
            'overflow:hidden;">'
            '<tr><td style="padding:22px 32px;background-color:#315fbd;'
            'color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">'
            "Effort<span style=\"color:#dbe7ff;\">List</span>"
            "</td></tr>"
            '<tr><td style="padding:36px 32px 32px;">'
            '<p style="margin:0 0 8px;color:#315fbd;font-size:12px;font-weight:700;'
            'letter-spacing:1.4px;text-transform:uppercase;">Account recovery</p>'
            '<h1 style="margin:0 0 16px;color:#172033;font-size:28px;line-height:1.2;'
            'letter-spacing:-0.6px;">Reset your password</h1>'
            '<p style="margin:0 0 26px;color:#657083;font-size:16px;line-height:1.6;">'
            "We received a request to reset the password for your EffortList account."
            "</p>"
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            'style="border-collapse:separate;"><tr><td style="background-color:#315fbd;'
            'border-radius:10px;">'
            f'<a href="{escaped_reset_url}" style="display:inline-block;'
            'padding:13px 22px;color:#ffffff;font-size:16px;font-weight:700;'
            'text-decoration:none;border-radius:10px;">Reset password</a>'
            "</td></tr></table>"
            f'<p style="margin:24px 0 0;color:#657083;font-size:14px;line-height:1.6;">'
            f"This link expires in <strong>{expiration} minutes</strong>. "
            "If you did not request a password reset, you can safely ignore this email."
            "</p>"
            '<hr style="margin:28px 0 20px;border:0;border-top:1px solid #dce2ea;">'
            '<p style="margin:0 0 8px;color:#98a2b3;font-size:12px;line-height:1.5;">'
            "If the button does not work, copy and paste this link into your browser:"
            "</p>"
            f'<a href="{escaped_reset_url}" style="color:#315fbd;'
            'font-size:12px;line-height:1.5;overflow-wrap:anywhere;word-break:break-all;">'
            f"{escape(reset_url)}</a>"
            "</td></tr></table>"
            '<p style="margin:18px 0 0;color:#98a2b3;font-size:12px;">'
            "This is an automated message from EffortList."
            "</p>"
            "</td></tr></table></body></html>"
        ),
    )
