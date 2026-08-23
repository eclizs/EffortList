import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from backend.src.email_utils import send_email, send_password_reset_email


class EmailTests(unittest.TestCase):
    def test_send_email_uses_configured_smtp_connection(self) -> None:
        with (
            patch(
                "backend.src.email_utils.aiosmtplib.send",
                new=AsyncMock(),
            ) as smtp_send,
            patch("backend.src.email_utils.settings.mail_server", "smtp.example.com"),
            patch("backend.src.email_utils.settings.mail_port", 2525),
            patch("backend.src.email_utils.settings.mail_username", "smtp-user"),
            patch("backend.src.email_utils.settings.mail_password") as password,
            patch("backend.src.email_utils.settings.mail_use_tls", True),
        ):
            password.get_secret_value.return_value = "smtp-password"
            asyncio.run(
                send_email(
                    "recipient@example.com",
                    "Test subject",
                    "Plain body",
                    "<p>HTML body</p>",
                )
            )

        smtp_send.assert_awaited_once()
        call = smtp_send.await_args
        message = call.args[0]
        self.assertEqual(message["To"], "recipient@example.com")
        self.assertEqual(message["Subject"], "Test subject")
        self.assertTrue(message.is_multipart())
        self.assertEqual(call.kwargs["hostname"], "smtp.example.com")
        self.assertEqual(call.kwargs["port"], 2525)
        self.assertEqual(call.kwargs["username"], "smtp-user")
        self.assertEqual(call.kwargs["password"], "smtp-password")
        self.assertTrue(call.kwargs["start_tls"])

    def test_password_reset_message_contains_frontend_link(self) -> None:
        with (
            patch("backend.src.email_utils.send_email", new=AsyncMock()) as send,
            patch(
                "backend.src.email_utils.settings.frontend_url",
                "https://effortlist.example.com/",
            ),
        ):
            asyncio.run(send_password_reset_email("user@example.com", "signed.token"))

        send.assert_awaited_once()
        call = send.await_args.kwargs
        self.assertEqual(call["to_email"], "user@example.com")
        self.assertIn(
            "https://effortlist.example.com/reset-password?token=signed.token",
            call["plain_text"],
        )
        self.assertIn('role="presentation"', call["html_content"])
        self.assertIn("background-color:#315fbd", call["html_content"])
        self.assertIn(">Reset password</a>", call["html_content"])
        self.assertNotIn("<link", call["html_content"])


if __name__ == "__main__":
    unittest.main()
