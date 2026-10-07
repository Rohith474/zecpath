from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import (
    CandidateInterviewAvailability,
    InterviewSchedule,
    InterviewReminder,
    EmailLog,
    Notification,
)
from accounts.tasks import send_email_task
from accounts.services.interview_reminder import (
    InterviewReminderService,
)

class InterviewSchedulingService:
    """
    Handles AI interview scheduling.
    """

    @staticmethod
    def schedule_interview(application):
        """
        Schedule an AI interview using the candidate's
        preferred availability.
        """

        # ----------------------------------------
        # Check candidate availability
        # ----------------------------------------

        try:
            availability = (
                CandidateInterviewAvailability.objects.get(
                    application=application
                )
            )

        except CandidateInterviewAvailability.DoesNotExist:

            return {
                "success": False,
                "message": (
                    "Candidate interview availability "
                    "has not been provided."
                ),
            }

        # ----------------------------------------
        # Check existing interview schedule
        # ----------------------------------------

        if InterviewSchedule.objects.filter(
            application=application
        ).exists():

            return {
                "success": False,
                "message": (
                    "An interview is already scheduled "
                    "for this application."
                ),
            }

        # ----------------------------------------
        # Build scheduled datetime
        # ----------------------------------------

        scheduled_datetime = datetime.combine(
            availability.preferred_date,
            availability.preferred_time,
        )

        scheduled_datetime = timezone.make_aware(
            scheduled_datetime,
            timezone.get_current_timezone(),
        )

        # ----------------------------------------
        # Validate date/time
        # ----------------------------------------

        if scheduled_datetime <= timezone.now():

            return {
                "success": False,
                "message": (
                    "The requested interview date and time "
                    "must be in the future."
                ),
            }

        # ----------------------------------------
        # Check scheduling conflict
        # ----------------------------------------

        new_duration = application.job.ai_interview_duration

        new_end_datetime = (
            scheduled_datetime
            + timedelta(minutes=new_duration)
        )

        existing_schedules = (
            InterviewSchedule.objects.filter(
                status=InterviewSchedule.SCHEDULED,
            )
            .exclude(
                application=application
            )
            .select_related("application__job")
        )

        for existing_schedule in existing_schedules:

            existing_start = existing_schedule.scheduled_at

            existing_duration = (
                existing_schedule.application.job.ai_interview_duration
            )

            existing_end = (
                existing_start
                + timedelta(minutes=existing_duration)
            )

            # Check whether the two interview time ranges overlap
            if (
                existing_start < new_end_datetime
                and existing_end > scheduled_datetime
            ):

                return {
                    "success": False,
                    "message": (
                        "The requested interview time conflicts "
                        "with another scheduled interview. "
                        "Please choose another time."
                    ),
                }

        # ----------------------------------------
        # Create interview schedule
        # ----------------------------------------

        interview = InterviewSchedule.objects.create(
            application=application,
            scheduled_at=scheduled_datetime,
            status=InterviewSchedule.SCHEDULED,
        )

        # ----------------------------------------
        # Update application status
        # ----------------------------------------

        application.status = application.INTERVIEW

        application.save(
            update_fields=["status"]
        )

        # ----------------------------------------
        # Create candidate notification
        # ----------------------------------------

        candidate = application.candidate
        candidate_user = candidate.user
        job = application.job

        Notification.objects.create(
            candidate=candidate,
            application=application,
            message=(
                f"Your AI interview for {job.title} has been "
                f"scheduled for "
                f"{scheduled_datetime.strftime('%d %B %Y at %I:%M %p')}."
            ),
        )

        # ----------------------------------------
        # Create EmailLog
        # ----------------------------------------

        email_log = EmailLog.objects.create(
            recipient_email=candidate_user.email,
            subject=f"AI Interview Scheduled - {job.title}",
            template_name="emails/interview_scheduled.txt",
            context={
                "candidate_name": (
                    candidate_user.get_full_name()
                    or candidate_user.username
                ),
                "job_title": job.title,
                "interview_date": scheduled_datetime.strftime(
                    "%d %B %Y"
                ),
                "interview_time": scheduled_datetime.strftime(
                    "%I:%M %p"
                ),
                "interview_duration": job.ai_interview_duration,
                "meeting_link": (
                    interview.meeting_link
                    or "Interview access details will be provided "
                       "before the interview."
                ),
                "instructions": (
                    interview.instructions
                    or (
                        "Please ensure your camera, microphone, "
                        "and internet connection are working "
                        "before the interview."
                    )
                ),
            },
            status=EmailLog.PENDING,
        )

        # ----------------------------------------
        # Send email asynchronously
        # ----------------------------------------

        send_email_task.delay(
            email_log.id
        )
        reminder_result = InterviewReminderService.create_reminders_for_interview(
        interview
        )

        # ----------------------------------------
        # Return scheduling result
        # ----------------------------------------

        return {
            "success": True,
            "message": (
                "AI interview scheduled successfully "
                "and confirmation email triggered."
            ),
            "interview_id": interview.id,
            "scheduled_at": interview.scheduled_at,
            "status": interview.status,
            "email_log_id": email_log.id,
            "email_status": email_log.status,
            "reminder_result": reminder_result,
        }