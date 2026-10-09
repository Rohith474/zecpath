import logging

from celery import shared_task
from django.utils import timezone

from accounts.models import (
    Application,
    CandidateProfile,
    EmailLog,
    ResumeParse,
)
from accounts.services.ai_call_scheduler import (
    process_scheduled_ai_calls,
)
from accounts.services.ai_call_service import (
    trigger_ai_call_for_application,
)
from accounts.services.email_service import (
    send_email_notification,
)
from accounts.services.interview_reminder import (
    InterviewReminderService,
)
from accounts.services.logging_service import LoggingService
from accounts.utils.resume_nlp import parse_resume_data
from accounts.utils.resume_parser import extract_resume_text

logger = logging.getLogger(__name__)
@shared_task(
    bind=True,
    max_retries=2,
)
def send_email_task(
    self,
    email_log_id,
):
    """
    Send an email in the background.

    Maximum total attempts:
        Attempt 1
        Attempt 2
        Attempt 3

    The same EmailLog is reused for all attempts.
    """

    # ----------------------------------------
    # Get existing EmailLog
    # ----------------------------------------

    try:

        email_log = EmailLog.objects.get(
            id=email_log_id
        )

    except EmailLog.DoesNotExist:

        return {
            "success": False,
            "message": "Email log not found.",
        }

    # ----------------------------------------
    # Do not resend already sent email
    # ----------------------------------------

    if email_log.status == EmailLog.SENT:

        return {
            "success": True,
            "message": "Email has already been sent.",
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
        }

    # ----------------------------------------
    # Send email
    # ----------------------------------------

    result = send_email_notification(
        subject=email_log.subject,
        template_name=email_log.template_name,
        context=email_log.context,
        recipient_email=email_log.recipient_email,
        email_log=email_log,
    )

    # ----------------------------------------
    # Successful email
    # ----------------------------------------

    if result.get("success"):

        try:
            reminder = email_log.interview_reminder

            reminder.status = reminder.SENT
            reminder.sent_at = (
                email_log.sent_at
                or timezone.now()
            )

            reminder.save(
                update_fields=[
                    "status",
                    "sent_at",
                    "updated_at",
                ]
            )

        except Exception:
            logger.exception(
                "Failed to update interview reminder after email delivery."
            )

        return result

    # ----------------------------------------
    # Check whether 3 total attempts
    # have already been completed
    # ----------------------------------------

    if email_log.attempts >= 3:

        email_log.status = EmailLog.FAILED
        email_log.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )
        LoggingService.log_failure(
            component="EmailTask",
            message="Email failed after maximum attempts.",
            metadata={
                "email_log_id": email_log.id,
                "attempts": email_log.attempts,
                "recipient": email_log.recipient_email,
                "subject": email_log.subject,
                "retry": False,
                "final_failure": True,
            },
        )

        return {
            "success": False,
            "message": "Email failed after 3 attempts.",
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
        }

    # ----------------------------------------
    # Retry
    # ----------------------------------------

    LoggingService.log_failure(
        component="EmailTask",
        message="Email sending failed. Retrying.",
        metadata={
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
            "recipient": email_log.recipient_email,
            "subject": email_log.subject,
            "retry": True,
        },
    )

    try:

        raise self.retry(
            countdown=10,
        )

    except self.MaxRetriesExceededError:

        # ----------------------------------------
        # Maximum Celery retries reached
        # ----------------------------------------

        email_log.status = EmailLog.FAILED

        email_log.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )
        LoggingService.log_failure(
            component="EmailTask",
            message="Celery maximum retries exceeded.",
            metadata={
                "email_log_id": email_log.id,
                "attempts": email_log.attempts,
                "recipient": email_log.recipient_email,
                "subject": email_log.subject,
                "retry": False,
                "final_failure": True,
            },
        )

        return {
            "success": False,
            "message": "Email failed after 3 attempts.",
            "email_log_id": email_log.id,
            "attempts": email_log.attempts,
        }
    
@shared_task
def resume_parsing_task(candidate_id):
    """
    Parse a candidate's stored resume in the background.
    """

    # ----------------------------------------
    # Get candidate
    # ----------------------------------------

    try:

        candidate = CandidateProfile.objects.get(
            id=candidate_id
        )

    except CandidateProfile.DoesNotExist:

        return {
            "success": False,
            "message": "Candidate profile not found.",
        }

    # ----------------------------------------
    # Check resume
    # ----------------------------------------

    if not candidate.resume:

        return {
            "success": False,
            "message": "Candidate does not have a resume.",
        }

    # ----------------------------------------
    # Determine file type
    # ----------------------------------------

    resume_file = candidate.resume

    file_name = resume_file.name.lower()

    if file_name.endswith(".pdf"):

        file_type = "pdf"

    elif file_name.endswith(".docx"):

        file_type = "docx"

    else:

        return {
            "success": False,
            "message": "Only PDF and DOCX resumes are supported.",
        }

    # ----------------------------------------
    # Extract resume text
    # ----------------------------------------

    try:

        raw_text, cleaned_text = extract_resume_text(
            resume_file,
            file_type,
        )

        # ----------------------------------------
        # Parse structured resume data
        # ----------------------------------------

        parsed_data = parse_resume_data(
            cleaned_text
        )

    except Exception as e:
        logger.exception("Resume parsing task failed.")

        return {
            "success": False,
            "message": "Failed to parse resume.",
            "error": str(e),
        }

    # ----------------------------------------
    # Store parsed resume
    # ----------------------------------------

    resume_parse, created = (
        ResumeParse.objects.update_or_create(
            candidate=candidate,
            defaults={
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "parsed_data": parsed_data,
            },
        )
    )

    # ----------------------------------------
    # Return result
    # ----------------------------------------

    return {
        "success": True,
        "message": (
            "Resume parsed and stored successfully."
        ),
        "candidate_id": candidate.id,
        "resume_parse_id": resume_parse.id,
        "created": created,
    }

@shared_task
def trigger_ai_call_task(application_id):
    """
    Trigger an AI interview call for an application
    in the background.
    """

    # ----------------------------------------
    # Get application
    # ----------------------------------------

    try:

        application = Application.objects.select_related(
            "candidate",
            "job",
        ).get(
            id=application_id
        )

    except Application.DoesNotExist:

        return {
            "success": False,
            "message": "Application not found.",
        }

    # ----------------------------------------
    # Trigger AI call
    # ----------------------------------------

    try:

        result = trigger_ai_call_for_application(
            application
        )

        return result

    except Exception as e:
        logger.exception("Failed to trigger AI call task.")

        return {
            "success": False,
            "message": "Failed to trigger AI call.",
            "error": str(e),
        }
    
@shared_task
def process_scheduled_ai_calls_task():
    """
    Process scheduled AI calls in the background.
    """
    try:
        results = process_scheduled_ai_calls()

        return {
            "success": True,
            "processed_count": len(results),
            "results": results,
        }

    except Exception as e:
        logger.exception("Failed to process scheduled AI calls task.")
        return {
            "success": False,
            "message": "Failed to process scheduled AI calls.",
            "error": str(e),
        }
@shared_task
def process_interview_reminders_task():
    """
    Process due AI interview reminders in the background.
    """

    try:
        results = InterviewReminderService.process_due_reminders()

        return {
            "success": True,
            "processed_count": len(results),
            "results": results,
        }

    except Exception as e:
        logger.exception("Failed to process interview reminders task.")
        return {
            "success": False,
            "message": "Failed to process interview reminders.",
            "error": str(e),
        }
