from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg

from accounts.models import (
    AIAnswerEvaluation,
    ATSScore,
)

ATS_WEIGHT = 0.60
INTERVIEW_WEIGHT = 0.40


def get_success_classification(score):
    if score >= 80:
        return "High Potential"

    if score >= 60:
        return "Moderate Potential"

    return "Low Potential"



def get_interview_status(application):
    """
    Return a recruiter-friendly interview status based
    on the actual AICall status.
    """

    try:
        ai_call = application.ai_call
    except ObjectDoesNotExist:
        return "Not Scheduled"

    if ai_call.status == ai_call.SCHEDULED:
        return "Scheduled"

    if ai_call.status == ai_call.IN_PROGRESS:
        return "In Progress"

    if ai_call.status == ai_call.COMPLETED:
        evaluations_exist = AIAnswerEvaluation.objects.filter(
            answer__ai_call=ai_call
        ).exists()

        if evaluations_exist:
            return "Completed"

        return "Evaluation Pending"

    if ai_call.status == ai_call.RETRY_SCHEDULED:
        return "Retry Scheduled"

    if ai_call.status == ai_call.FAILED:
        return "Failed"

    return "Unknown"


def get_candidate_success_report(application):
    ats_score = (
        ATSScore.objects
        .filter(
            candidate=application.candidate,
            job=application.job,
        )
        .first()
    )

    if ats_score:
        ats_match_percentage = float(ats_score.match_percentage)
        skill_score = float(ats_score.skill_score)
        experience_score = float(ats_score.experience_score)
        education_score = float(ats_score.education_score)
        matched_skill_count = ats_score.matched_skill_count

    else:
        ats_match_percentage = 0.0
        skill_score = 0.0
        experience_score = 0.0
        education_score = 0.0
        matched_skill_count = 0

    evaluations = (
        AIAnswerEvaluation.objects
        .filter(
            answer__ai_call__application=application
        )
    )

    evaluation_summary = evaluations.aggregate(
        average_score=Avg("final_score"),
        average_confidence=Avg("confidence"),
    )

    average_interview_score = evaluation_summary["average_score"]
    average_confidence = evaluation_summary["average_confidence"]
    evaluated_answer_count = evaluations.count()

    if average_interview_score is not None:
        average_interview_score = float(average_interview_score)

        success_score = (
            (ats_match_percentage * ATS_WEIGHT)
            + (average_interview_score * INTERVIEW_WEIGHT)
        )

        score_basis = "ATS + AI Interview"

    else:
        success_score = ats_match_percentage
        score_basis = "ATS only"

    success_score = round(success_score, 2)

    classification = get_success_classification(success_score)

    interview_status = get_interview_status(application)

    return {
        "candidate_id": application.candidate_id,
        "candidate": application.candidate.user.username,

        "job_id": application.job_id,
        "job_title": application.job.title,

        "ats": {
            "match_percentage": ats_match_percentage,
            "skill_score": skill_score,
            "experience_score": experience_score,
            "education_score": education_score,
            "matched_skill_count": matched_skill_count,
        },

        "interview": {
            "status": interview_status,
            "evaluated": evaluated_answer_count > 0,
            "average_score": (
                round(average_interview_score, 2)
                if average_interview_score is not None
                else None
            ),
            "average_confidence": (
                round(float(average_confidence), 2)
                if average_confidence is not None
                else None
            ),
            "evaluated_answers": evaluated_answer_count,
        },

        "success": {
            "score": success_score,
            "classification": classification,
            "score_basis": score_basis,
        },

        "application_status": application.status,
    }