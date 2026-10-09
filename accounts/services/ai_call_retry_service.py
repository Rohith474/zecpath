from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import AICall


def get_next_retry_time(config):
    """
    Calculate the next retry time while respecting
    the configured call window.
    """

    retry_time = timezone.now() + timedelta(
        minutes=config.retry_interval_minutes
    )

    local_retry_time = timezone.localtime(
        retry_time
    )

    retry_date = local_retry_time.date()
    retry_clock_time = local_retry_time.time()

    # Retry is inside the call window
    if (
        config.call_start_time
        <= retry_clock_time
        <= config.call_end_time
    ):
        return retry_time

    # Retry is before the call window
    if retry_clock_time < config.call_start_time:
        scheduled_datetime = datetime.combine(
            retry_date,
            config.call_start_time,
        )

        return timezone.make_aware(
            scheduled_datetime,
            timezone.get_current_timezone(),
        )

    # Retry is after the call window
    next_day = retry_date + timedelta(days=1)

    scheduled_datetime = datetime.combine(
        next_day,
        config.call_start_time,
    )

    return timezone.make_aware(
        scheduled_datetime,
        timezone.get_current_timezone(),
    )
def handle_missed_ai_call(ai_call):
    """
    Handle a missed AI screening call.

    If attempts remain, schedule a retry.
    Otherwise, mark the AI call as failed.
    """

    # ----------------------------------------
    # Verify call status
    # ----------------------------------------

    if ai_call.status != AICall.IN_PROGRESS:

        return {
            "success": False,
            "message": (
                "AI call is not currently in progress."
            ),
        }

    # ----------------------------------------
    # Get AI interview configuration
    # ----------------------------------------

    config = ai_call.config

    if not config:

        return {
            "success": False,
            "message": (
                "AI interview configuration "
                "is not available."
            ),
        }

    # ----------------------------------------
    # Mark call as missed
    # ----------------------------------------

    ai_call.status = AICall.MISSED

    # ----------------------------------------
    # Check remaining attempts
    # ----------------------------------------

    if ai_call.attempt_count < config.max_call_attempts:

        # ----------------------------------------
        # Calculate retry time
        # ----------------------------------------

        next_retry_time = get_next_retry_time(
        config
        )
        # ----------------------------------------
        # Schedule retry
        # ----------------------------------------

        ai_call.status = AICall.RETRY_SCHEDULED

        ai_call.next_retry_at = next_retry_time

        ai_call.scheduled_at = next_retry_time

        ai_call.save()

        return {
            "success": True,
            "message": (
                "AI call was missed. "
                "Retry scheduled successfully."
            ),
            "ai_call_id": ai_call.id,
            "status": ai_call.status,
            "attempt_count": ai_call.attempt_count,
            "next_retry_at": ai_call.next_retry_at,
        }

    # ----------------------------------------
    # Maximum attempts reached
    # ----------------------------------------

    ai_call.status = AICall.FAILED

    ai_call.failure_reason = (
        "Maximum AI call attempts reached."
    )

    ai_call.save()

    return {
        "success": True,
        "message": (
            "Maximum call attempts reached. "
            "AI call marked as failed."
        ),
        "ai_call_id": ai_call.id,
        "status": ai_call.status,
        "attempt_count": ai_call.attempt_count,
        "failure_reason": ai_call.failure_reason,
    }