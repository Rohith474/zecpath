from django.utils import timezone

from accounts.models import AICall


def complete_ai_call(ai_call, result="Passed"):
    """
    Complete an AI screening call.

    This is currently a simulated workflow.
    Actual AI voice evaluation will be integrated
    in a future milestone.
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
    # Mark call as completed
    # ----------------------------------------

    ai_call.status = AICall.COMPLETED

    ai_call.completed_at = timezone.now()

    ai_call.save()

    return {
        "success": True,
        "message": (
            "AI call completed successfully."
        ),
        "ai_call_id": ai_call.id,
        "status": ai_call.status,
        "result": result,
        "completed_at": ai_call.completed_at,
    }