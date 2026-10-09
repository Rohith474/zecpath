from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import (
    AICall,
    AIInterviewConfig,
)
from accounts.services.eligibility import (
    is_eligible_for_ai_call,
)
from accounts.services.subscription_service import (
    SubscriptionService,
)


def get_next_valid_call_time(config):
    """
    Determine when an AI call should be scheduled.

    Rules:
    - If the current time is inside the configured
      call window, schedule the call immediately.
    - If the current time is before the call window,
      schedule the call at today's start time.
    - If the current time is after the call window,
      schedule the call at tomorrow's start time.
    """

    now = timezone.localtime()

    current_time = now.time()

    # ----------------------------------------
    # Current time is before call window
    # ----------------------------------------

    if current_time < config.call_start_time:

        scheduled_datetime = datetime.combine(
            now.date(),
            config.call_start_time,
        )

        return timezone.make_aware(
            scheduled_datetime,
            timezone.get_current_timezone(),
        )

    # ----------------------------------------
    # Current time is inside call window
    # ----------------------------------------

    if (
        config.call_start_time
        <= current_time
        <= config.call_end_time
    ):

        return now

    # ----------------------------------------
    # Current time is after call window
    # Schedule for tomorrow
    # ----------------------------------------

    tomorrow = now.date() + timedelta(days=1)

    scheduled_datetime = datetime.combine(
        tomorrow,
        config.call_start_time,
    )

    return timezone.make_aware(
        scheduled_datetime,
        timezone.get_current_timezone(),
    )


def trigger_ai_call_for_application(application):
    """
    Create an AI screening call record for a
    shortlisted application.

    The call is scheduled according to the
    employer's configured call window.

    Actual voice API integration will be added
    in a future milestone.
    """

    # ----------------------------------------
    # Only shortlisted candidates are eligible
    # ----------------------------------------

    eligible, message = is_eligible_for_ai_call(
    application
    )

    if not eligible:
        return {
            "success": False,
            "message": message,
        }
    # ----------------------------------------
    # Check whether AI call already exists
    # ----------------------------------------

    if hasattr(application, "ai_call"):

        return {
            "success": False,
            "message": (
                "AI call already exists for this "
                "application."
            ),
            "ai_call_id": application.ai_call.id,
        }

    # ----------------------------------------
    # Get active AI interview configuration
    # ----------------------------------------

    try:

        config = AIInterviewConfig.objects.get(
            job=application.job,
            is_active=True,
        )

    except AIInterviewConfig.DoesNotExist:

        return {
            "success": False,
            "message": (
                "No active AI interview configuration "
                "found for this job."
            ),
        }
    
    # ----------------------------------------
    # Check subscription feature access
    # ----------------------------------------

    employer_user = application.job.employer.user

    if not SubscriptionService.has_feature(
        employer_user,
        "ai_interview",
    ):

        return {
            "success": False,
            "message": (
                "An active subscription with AI interview "
                "access is required."
            ),
        }

    # ----------------------------------------
    # Check AI call subscription limit
    # ----------------------------------------

    if not SubscriptionService.can_create_ai_call(
        employer_user
    ):

        return {
            "success": False,
            "message": (
                "AI interview call limit has been reached "
                "for the current billing period."
            ),
        }
    # ----------------------------------------
    # Determine valid call time
    # ----------------------------------------

    scheduled_time = get_next_valid_call_time(
        config
    )

    # ----------------------------------------
    # Create AI call workflow
    # ----------------------------------------

    ai_call = AICall.objects.create(
        application=application,
        config=config,
        status=AICall.SCHEDULED,
        scheduled_at=scheduled_time,
    )

    return {
        "success": True,
        "message": (
            "AI call workflow created successfully."
        ),
        "ai_call_id": ai_call.id,
        "status": ai_call.status,
        "scheduled_at": ai_call.scheduled_at,
    }