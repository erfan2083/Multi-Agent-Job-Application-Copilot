from __future__ import annotations

from datetime import datetime
from core.config import settings
from services.storage import storage_service


class EmailService:
    def send_or_dry_run(self, to_email: str, subject: str, body: str) -> str:
        if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
            filename = f"dryrun_{datetime.utcnow().timestamp()}.eml"
            content = f"To: {to_email}\nSubject: {subject}\n\n{body}"
            return storage_service.write_text("emails", filename, content)
        # MVP intentionally keeps SMTP send unimplemented for safety.
        raise NotImplementedError("SMTP send scaffolded but disabled in MVP")


email_service = EmailService()
