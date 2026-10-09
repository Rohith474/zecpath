from accounts.models import (
    Application,
    EmailLog,
    Notification,
)
from accounts.tasks import (
    send_email_task,
    trigger_ai_call_task,
)

from .eligibility import is_eligible_for_shortlisting


def auto_process_application(application):
    """
    Automatically shortlist or reject an application
    based on its ATS score and eligibility criteria.
    """

    # ----------------------------------------
    # Get ATS score
    # ----------------------------------------

    ats_score = application.candidate.ats_scores.filter(
        job=application.job
    ).first()

    if not ats_score:

        return {
            "success": False,
            "message": "ATS score not found.",
        }

    # ----------------------------------------
    # Check eligibility
    # ----------------------------------------

    eligible = is_eligible_for_shortlisting(
        ats_score
    )

    # ----------------------------------------
    # Auto shortlist
    # ----------------------------------------

    if eligible:

        application.status = Application.SHORTLISTED
        application.save()

        # ----------------------------------------
        # Create in-app notification
        # ----------------------------------------

        Notification.objects.create(
            candidate=application.candidate,
            application=application,
            message=(
                f"We are pleased to inform you that your application "
                f"for the position of '{application.job.title}' has "
                f"been shortlisted following our initial review. "
                f"The employer may contact you regarding the next steps "
                f"in the selection process."
            ),
        )

        # ----------------------------------------
        # Create EmailLog
        # ----------------------------------------

        email_log = EmailLog.objects.create(
            recipient_email=application.candidate.user.email,
            subject="Your Application Has Been Shortlisted",
            template_name="emails/application_shortlisted.txt",
            context={
                "candidate_name": (
                    application.candidate.user.username
                ),
                "job_title": application.job.title,
            },
            status=EmailLog.PENDING,
        )

        # ----------------------------------------
        # Send email through Celery
        # ----------------------------------------

        send_email_task.delay(
            email_log.id
        )
       # ----------------------------------------
        # Trigger AI screening call
        # ----------------------------------------

        ai_call_task = trigger_ai_call_task.delay(
            application.id
        )

        return {
            "success": True,
            "action": "shortlisted",
            "match_percentage": float(
                ats_score.match_percentage
            ),
            "ai_call_task_id": ai_call_task.id,
        }
    # ----------------------------------------
    # Auto reject
    # ----------------------------------------

    application.status = Application.REJECTED
    application.save()

    # ----------------------------------------
    # Create in-app notification
    # ----------------------------------------

    Notification.objects.create(
        candidate=application.candidate,
        application=application,
        message=(
            f"Thank you for your interest in the position of "
            f"'{application.job.title}'. After careful consideration, "
            f"we regret to inform you that your application will not "
            f"be progressing to the next stage at this time. "
            f"We appreciate your interest and wish you every success "
            f"in your future career endeavors."
        ),
    )

    # ----------------------------------------
    # Create EmailLog
    # ----------------------------------------

    email_log = EmailLog.objects.create(
        recipient_email=application.candidate.user.email,
        subject="Update on Your Job Application",
        template_name="emails/application_rejected.txt",
        context={
            "candidate_name": (
                application.candidate.user.username
            ),
            "job_title": application.job.title,
        },
        status=EmailLog.PENDING,
    )

    # ----------------------------------------
    # Send email through Celery
    # ----------------------------------------

    send_email_task.delay(
        email_log.id
    )

    return {
        "success": True,
        "action": "rejected",
        "match_percentage": float(
            ats_score.match_percentage
        ),
    }