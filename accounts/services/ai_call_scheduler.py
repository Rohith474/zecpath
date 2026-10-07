from django.db.models import Q
from django.utils import timezone

from accounts.models import AICall


def process_scheduled_ai_calls():
    """
    Process AI calls whose scheduled time has arrived.

    Handles:
    - Newly scheduled AI calls
    - Retry scheduled AI calls
    """

    now = timezone.now()

    # ----------------------------------------
    # Find due AI calls
    # ----------------------------------------

    ai_calls = (
        AICall.objects
        .filter(
            Q(
                status=AICall.SCHEDULED,
                scheduled_at__lte=now,
            )
            |
            Q(
                status=AICall.RETRY_SCHEDULED,
                next_retry_at__lte=now,
            )
        )
        .select_related(
            "application",
            "application__candidate",
            "application__candidate__user",
            "application__job",
            "config",
        )
    )

    results = []

    # ----------------------------------------
    # Process each AI call
    # ----------------------------------------

    for ai_call in ai_calls:

        # ----------------------------------------
        # Move call to In Progress
        # ----------------------------------------

        ai_call.status = AICall.IN_PROGRESS

        # ----------------------------------------
        # Increase attempt count
        # ----------------------------------------

        ai_call.attempt_count += 1

        # ----------------------------------------
        # Record attempt time
        # ----------------------------------------

        ai_call.last_attempt_at = now

        # ----------------------------------------
        # Clear retry time
        # ----------------------------------------

        ai_call.next_retry_at = None

        ai_call.save()

        results.append(
            {
                "ai_call_id": ai_call.id,
                "candidate": (
                    ai_call.application
                    .candidate
                    .user
                    .username
                ),
                "job": (
                    ai_call.application
                    .job
                    .title
                ),
                "status": ai_call.status,
                "attempt_count": (
                    ai_call.attempt_count
                ),
            }
        )

    return results