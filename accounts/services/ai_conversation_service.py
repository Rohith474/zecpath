from django.utils import timezone

from accounts.models import (
    AICall,
    AIInterviewAnswer,
    AIInterviewSession,
    CallLog,
    AuditLog,
)


def get_or_create_interview_session(ai_call):
    """
    Get the existing AI interview session for an AI call
    or create a new session.
    """

    session, created = AIInterviewSession.objects.get_or_create(
        ai_call=ai_call,
        defaults={
            "status": "Started",
        },
    )

    if created:
        CallLog.objects.create(
            session=session,
            event="CALL_CREATED",
            message="AI interview session created.",
        )

    return session
def log_ai_call_trigger(
    ai_call,
    admin=None,
    reason="",
):
    """
    Create an audit log when an AI call is triggered.
    """

    if not ai_call:
        return {
            "success": False,
            "message": "AI call is required.",
        }

    audit_log = AuditLog.objects.create(
        admin=admin,
        action="AI_CALL_TRIGGERED",
        target_type="AICall",
        target_id=ai_call.id,
        description=(
            reason
            if reason
            else "AI call was triggered."
        ),
    )

    return {
        "success": True,
        "audit_log_id": audit_log.id,
        "action": audit_log.action,
        "target_id": audit_log.target_id,
    }

def start_interview_session(ai_call):
    """
    Start an AI interview session.
    """

    if ai_call.status != AICall.IN_PROGRESS:
        return {
            "success": False,
            "message": (
                "AI call is not currently in progress."
            ),
        }

    session = get_or_create_interview_session(ai_call)

    session.status = "In Progress"
    session.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    CallLog.objects.create(
        session=session,
        event="CALL_STARTED",
        message="AI interview session started.",
    )

    return {
        "success": True,
        "session_id": session.id,
        "status": session.status,
    }


def store_ai_response(
    ai_call,
    question,
    answer,
):
    """
    Store a question and answer received
    from an external AI provider.
    """

    if ai_call.status != AICall.IN_PROGRESS:
        return {
            "success": False,
            "message": (
                "AI call is not currently in progress."
            ),
        }

    if not question:
        return {
            "success": False,
            "message": "Question is required.",
        }

    if not answer:
        return {
            "success": False,
            "message": "Answer is required.",
        }

    next_order = (
        AIInterviewAnswer.objects.filter(
            ai_call=ai_call
        ).count()
        + 1
    )

    ai_answer = AIInterviewAnswer.objects.create(
        ai_call=ai_call,
        question_order=next_order,
        question_text=question,
        answer_text=answer,
    )

    return {
        "success": True,
        "answer_id": ai_answer.id,
        "question_order": ai_answer.question_order,
        "question": ai_answer.question_text,
        "answer": ai_answer.answer_text,
    }


def store_call_log(
    ai_call,
    event,
    message="",
    metadata=None,
):
    """
    Store an AI call event in the call log.
    """

    session = get_or_create_interview_session(ai_call)

    call_log = CallLog.objects.create(
        session=session,
        event=event,
        message=message,
        metadata=metadata or {},
    )

    return {
        "success": True,
        "call_log_id": call_log.id,
        "event": call_log.event,
    }


def store_transcript(
    ai_call,
    transcript_data,
):
    """
    Store structured transcript data for an AI interview session.
    """

    session = get_or_create_interview_session(ai_call)

    if not transcript_data:
        return {
            "success": False,
            "message": "Transcript data is required.",
        }

    session.transcript = transcript_data
    session.save(
        update_fields=[
            "transcript",
            "updated_at",
        ]
    )

    return {
        "success": True,
        "session_id": session.id,
        "message": "Transcript stored successfully.",
    }


def complete_interview_session(ai_call):
    """
    Mark an AI interview session as completed.
    """

    try:
        session = ai_call.interview_session
    except AIInterviewSession.DoesNotExist:
        return {
            "success": False,
            "message": "AI interview session does not exist.",
        }

    session.status = "Completed"
    session.ended_at = timezone.now()

    session.save(
        update_fields=[
            "status",
            "ended_at",
            "updated_at",
        ]
    )

    CallLog.objects.create(
        session=session,
        event="CALL_COMPLETED",
        message="AI interview session completed.",
    )

    return {
        "success": True,
        "session_id": session.id,
        "status": session.status,
        "ended_at": session.ended_at,
    }


def fail_interview_session(
    ai_call,
    reason,
):
    """
    Mark an AI interview session as failed.
    """

    try:
        session = ai_call.interview_session
    except AIInterviewSession.DoesNotExist:
        return {
            "success": False,
            "message": "AI interview session does not exist.",
        }

    session.status = "Failed"
    session.ended_at = timezone.now()

    session.save(
        update_fields=[
            "status",
            "ended_at",
            "updated_at",
        ]
    )

    CallLog.objects.create(
        session=session,
        event="CALL_FAILED",
        message=reason,
    )

    return {
        "success": True,
        "session_id": session.id,
        "status": session.status,
        "reason": reason,
    }