"""Email-related tasks."""
from celery import shared_task


@shared_task
def send_email(to: str, subject: str, body: str) -> dict:
    """
    Placeholder email send. Replace with real email provider integration.
    """
    # TODO: integrate with SES/SendGrid/etc.
    return {"to": to, "subject": subject}
