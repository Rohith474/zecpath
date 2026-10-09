import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.models import EmailLog

logger = logging.getLogger(__name__)

def send_email_notification(
    subject,
    template_name,
    context,
    recipient_email,
    email_log=None,
):
    """
    Send an email notification and update the
    associated EmailLog.

    If an EmailLog is provided, the same log is
    reused across retry attempts.
    """

    # ----------------------------------------
    # Create EmailLog only if one was not
    # already provided
    # ----------------------------------------

    if email_log is None:

        email_log = EmailLog.objects.create(
            recipient_email=recipient_email,
            subject=subject,
            template_name=template_name,
            context=context,
            status=EmailLog.PENDING,
        )

    # ----------------------------------------
    # Record this delivery attempt FIRST
    # ----------------------------------------

    email_log.attempts += 1
    email_log.status = EmailLog.PENDING
    email_log.error_message = ""

    email_log.save(
        update_fields=[
            "attempts",
            "status",
            "error_message",
            "updated_at",
        ]
    )

    try:

        # ----------------------------------------
        # Render email template
        # ----------------------------------------

        message = render_to_string(
            template_name,
            context,
        )

        # ----------------------------------------
        # Send email through SMTP
        # ----------------------------------------

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        # ----------------------------------------
        # Mark email as successfully sent
        # ----------------------------------------

        email_log.status = EmailLog.SENT
        email_log.sent_at = timezone.now()

        email_log.save(
            update_fields=[
                "status",
                "sent_at",
                "updated_at",
            ]
        )

        return {
            "success": True,
            "message": "Email sent successfully.",
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
        }

    except Exception as error:
        logger.exception("Email notification delivery failed.")

        # ----------------------------------------
        # Record failure
        # ----------------------------------------

        email_log.status = EmailLog.FAILED
        email_log.error_message = str(error)

        email_log.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )

        return {
            "success": False,
            "error": str(error),
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
        }