from datetime import timedelta

from django.db import models
from django.utils import timezone

from accounts.models import (
    EmailLog,
    InterviewReminder,
    InterviewSchedule,
)


class InterviewReminderService:

    REMINDER_WINDOWS = {
        InterviewReminder.REMINDER_24_HOURS: timedelta(hours=24),
        InterviewReminder.REMINDER_1_HOUR: timedelta(hours=1),
        InterviewReminder.REMINDER_AT_TIME: timedelta(0),
        }

    @staticmethod
    def create_reminders_for_interview(interview):
        """
        Create reminder records for a scheduled interview.
        """

        if interview.status != InterviewSchedule.SCHEDULED:
            return {
                "success": False,
                "message": "Reminders can only be created for scheduled interviews.",
            }

        scheduled_at = interview.scheduled_at

        created_reminders = []

        for reminder_type, time_before in (
            InterviewReminderService.REMINDER_WINDOWS.items()
        ):

            reminder_time = scheduled_at - time_before

            reminder, created = InterviewReminder.objects.get_or_create(
                interview=interview,
                reminder_type=reminder_type,
                interview_scheduled_at=scheduled_at,
                defaults={
                    "scheduled_for": reminder_time,
                    "status": InterviewReminder.PENDING,
                },
            )

            if created:
                created_reminders.append(reminder.id)

        return {
            "success": True,
            "message": "Interview reminders created successfully.",
            "interview_id": interview.id,
            "reminder_ids": created_reminders,
        }

    @staticmethod
    def process_due_reminders():
        """
        Find and process interview reminders that are due.
        """

        now = timezone.now()

        reminders = InterviewReminder.objects.select_related(
            "interview",
            "interview__application",
            "interview__application__candidate",
            "interview__application__candidate__user",
            "interview__application__job",
        ).filter(
            status=InterviewReminder.PENDING,
            scheduled_for__lte=now,
            interview__status=InterviewSchedule.SCHEDULED,
            interview_scheduled_at=models.F("interview__scheduled_at"),
        )

        results = []

        for reminder in reminders:
            result = InterviewReminderService.send_reminder(reminder)
            results.append(result)

        return results

    @staticmethod
    def send_reminder(reminder):
        """
        Send a single interview reminder.
        """

        interview = reminder.interview
        application = interview.application
        candidate = application.candidate
        candidate_user = candidate.user
        job = application.job

        if reminder.reminder_type == InterviewReminder.REMINDER_24_HOURS:
            reminder_label = "24-hour"
        elif reminder.reminder_type == InterviewReminder.REMINDER_1_HOUR:
            reminder_label = "1-hour"
        else:
            reminder_label = "interview-time"

        if interview.status != InterviewSchedule.SCHEDULED:
            reminder.status = InterviewReminder.FAILED
            reminder.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return {
                "success": False,
                "reminder_id": reminder.id,
                "message": "Interview is no longer scheduled.",
            }

        if reminder.interview_scheduled_at != interview.scheduled_at:
            reminder.status = InterviewReminder.FAILED
            reminder.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            return {
                "success": False,
                "reminder_id": reminder.id,
                "message": "Interview was rescheduled.",
            }

        existing_email_log = reminder.email_log

        if existing_email_log:

            if existing_email_log.status == EmailLog.SENT:

                reminder.status = InterviewReminder.SENT
                reminder.sent_at = (
                    existing_email_log.sent_at
                    or timezone.now()
                )

                reminder.save(
                    update_fields=[
                        "status",
                        "sent_at",
                        "updated_at",
                    ]
                )

                return {
                    "success": True,
                    "reminder_id": reminder.id,
                    "message": "Reminder email was already sent.",
                }

            email_log = existing_email_log

        else:

            email_log = EmailLog.objects.create(
                recipient_email=candidate_user.email,
                subject=(
                    f"Your AI Interview Is Starting Now - {job.title}"
                    if reminder.reminder_type == InterviewReminder.REMINDER_AT_TIME
                    else f"AI Interview Reminder - {job.title}"
                ),
                template_name="emails/interview_reminder.txt",
                context={
                    "candidate_name": (
                        candidate_user.get_full_name()
                        or candidate_user.username
                    ),
                    "job_title": job.title,
                    "interview_date": (
                        interview.scheduled_at.strftime(
                            "%d %B %Y"
                        )
                    ),
                    "interview_time": (
                        interview.scheduled_at.strftime(
                            "%I:%M %p"
                        )
                    ),
                    "interview_duration": (
                        job.ai_interview_duration
                    ),
                    "meeting_link": (
                        interview.meeting_link
                        or (
                            "Interview access details will be "
                            "provided before the interview."
                        )
                    ),
                },
                status=EmailLog.PENDING,
            )

            reminder.email_log = email_log

            reminder.save(
                update_fields=[
                    "email_log",
                    "updated_at",
                ]
            )

        from accounts.tasks import send_email_task
        
        send_email_task.delay(email_log.id)

        return {
            "success": True,
            "reminder_id": reminder.id,
            "email_log_id": email_log.id,
            "message": (
                f"{reminder_label} interview reminder triggered."
            ),
        }