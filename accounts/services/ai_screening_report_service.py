from accounts.models import (
    AICall,
    AIScreeningReport,
)


def save_ai_screening_report(
    ai_call,
    overall_score=None,
    summary="",
    recommendation="",
    analysis=None,
):
    """
    Store or update an AI screening report
    received from an external AI provider.
    """

    if ai_call.status != AICall.COMPLETED:
        return {
            "success": False,
            "message": (
                "AI call must be completed "
                "before creating a screening report."
            ),
        }

    if analysis is None:
        analysis = {}

    report, created = (
        AIScreeningReport.objects.update_or_create(
            ai_call=ai_call,
            defaults={
                "overall_score": overall_score,
                "summary": summary,
                "recommendation": recommendation,
                "analysis": analysis,
            },
        )
    )

    return {
        "success": True,
        "message": (
            "AI screening report "
            "created successfully."
            if created
            else
            "AI screening report "
            "updated successfully."
        ),
        "report_id": report.id,
        "ai_call_id": ai_call.id,
        "overall_score": report.overall_score,
        "summary": report.summary,
        "recommendation": report.recommendation,
        "analysis": report.analysis,
    }