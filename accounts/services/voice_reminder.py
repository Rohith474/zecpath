class VoiceReminderService:

    @staticmethod
    def trigger_voice_reminder(interview, reminder):
        """
        Prepare a voice reminder hook for future telephony integration.

        This does not place a real phone call yet.
        """

        return {
            "success": True,
            "message": "Voice reminder hook prepared.",
            "interview_id": interview.id,
            "reminder_id": reminder.id,
            "reminder_type": reminder.reminder_type,
            "scheduled_at": interview.scheduled_at,
            "phone_number": interview.application.candidate.user.phone_number,
        }