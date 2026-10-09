from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from accounts.models import (
    AIAnswerEvaluation,
    AICall,
    AICandidateReport,
    ATSScore,
)


class AICandidateReportService:

    ATS_WEIGHT = Decimal("0.60")
    AI_CALL_WEIGHT = Decimal("0.40")

    @staticmethod
    def _calculate_ai_call_score(ai_call):
        evaluations = AIAnswerEvaluation.objects.filter(
            answer__ai_call=ai_call
        )

        if not evaluations.exists():
            return Decimal("0.00"), 0

        total = sum(
            (evaluation.final_score for evaluation in evaluations),
            Decimal("0.00"),
        )

        count = evaluations.count()

        score = (
            total / Decimal(count)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        return score, count

    @staticmethod
    def _generate_strengths(ats_score, ai_call_score, evaluations):
        strengths = []

        if ats_score.skill_score >= Decimal(70):
            strengths.append(
                "Strong alignment with the required job skills."
            )

        if ats_score.experience_score >= Decimal(70):
            strengths.append(
                "Relevant experience alignment with the job requirements."
            )

        if ats_score.education_score >= Decimal(70):
            strengths.append(
                "Education background meets the expected criteria."
            )

        if ai_call_score >= Decimal(70):
            strengths.append(
                "Strong performance across AI interview responses."
            )

        high_quality_answers = evaluations.filter(
            final_score__gte=70
        ).count()

        if high_quality_answers:
            strengths.append(
                f"{high_quality_answers} AI interview response(s) "
                "demonstrated strong evaluation scores."
            )

        if not strengths:
            strengths.append(
                "Candidate data is available for recruiter review."
            )

        return strengths

    @staticmethod
    def _generate_risks(ats_score, ai_call_score, evaluations):
        risks = []

        if ats_score.skill_score < Decimal(50):
            risks.append(
                "Low alignment with the required job skills."
            )

        if ats_score.experience_score < Decimal(50):
            risks.append(
                "Limited alignment with the required experience."
            )

        if ats_score.education_score < Decimal(50):
            risks.append(
                "Education score is below the reporting threshold."
            )

        if ai_call_score < Decimal(50):
            risks.append(
                "AI interview performance requires recruiter review."
            )

        low_quality_answers = evaluations.filter(
            final_score__lt=50
        ).count()

        if low_quality_answers:
            risks.append(
                f"{low_quality_answers} AI interview response(s) "
                "received a score below 50."
            )

        if not risks:
            risks.append(
                "No major automated risk indicators were identified."
            )

        return risks

    @staticmethod
    def _generate_summary(
        application,
        ats_score,
        ai_call_score,
        overall_score,
        strengths,
        risks,
        evaluation_count,
    ):
        candidate = application.candidate
        candidate_user = candidate.user
        job = application.job

        candidate_name = (
            candidate_user.get_full_name()
            or candidate_user.username
        )

        return (
            f"{candidate_name} was evaluated for the {job.title} role. "
            f"The candidate received an ATS score of {ats_score.match_percentage}% "
            f"and an AI interview score of {ai_call_score}%. "
            f"The aggregated report score is {overall_score}%. "
            f"{evaluation_count} AI interview response(s) were evaluated. "
            f"The report identified {len(strengths)} strength indicator(s) "
            f"and {len(risks)} risk indicator(s) for recruiter review."
        )

    @staticmethod
    @transaction.atomic
    def generate_report(application):
        ats_score = (
            ATSScore.objects
            .filter(
                candidate=application.candidate,
                job=application.job,
            )
            .first()
        )

        if not ats_score:
            return {
                "success": False,
                "message": "ATS score not found for this application.",
            }

        ai_call = (
            AICall.objects
            .filter(application=application)
            .order_by("-created_at")
            .first()
        )

        if not ai_call:
            return {
                "success": False,
                "message": "AI interview call not found for this application.",
            }

        ai_call_score, evaluation_count = (
            AICandidateReportService._calculate_ai_call_score(
                ai_call
            )
        )

        evaluations = AIAnswerEvaluation.objects.filter(
            answer__ai_call=ai_call
        )
        average_relevance = Decimal("0.00")
        average_completeness = Decimal("0.00")
        average_keyword = Decimal("0.00")
        average_confidence = Decimal("0.00")

        if evaluation_count:
            average_relevance = (
                sum(
                    (evaluation.relevance_score for evaluation in evaluations),
                    Decimal("0.00"),
                )
                / Decimal(evaluation_count)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            average_completeness = (
                sum(
                    (evaluation.completeness_score for evaluation in evaluations),
                    Decimal("0.00"),
                )
                / Decimal(evaluation_count)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            average_keyword = (
                sum(
                    (evaluation.keyword_score for evaluation in evaluations),
                    Decimal("0.00"),
                )
                / Decimal(evaluation_count)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            average_confidence = (
                sum(
                    (evaluation.confidence for evaluation in evaluations),
                    Decimal("0.00"),
                )
                / Decimal(evaluation_count)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        ats_match = Decimal(
            str(ats_score.match_percentage)
        )

        overall_score = (
            (ats_match * AICandidateReportService.ATS_WEIGHT)
            + (
                ai_call_score
                * AICandidateReportService.AI_CALL_WEIGHT
            )
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        strengths = AICandidateReportService._generate_strengths(
            ats_score,
            ai_call_score,
            evaluations,
        )

        risks = AICandidateReportService._generate_risks(
            ats_score,
            ai_call_score,
            evaluations,
        )

        summary = AICandidateReportService._generate_summary(
            application,
            ats_score,
            ai_call_score,
            overall_score,
            strengths,
            risks,
            evaluation_count,
        )

        report_data = {
            "candidate": {
                "id": application.candidate.id,
                "name": (
                    application.candidate.user.get_full_name()
                    or application.candidate.user.username
                ),
                "email": application.candidate.user.email,
            },
            "job": {
                "id": application.job.id,
                "title": application.job.title,
            },
            "application": {
                "id": application.id,
                "status": application.status,
            },
            "ats": {
                "skill_score": float(ats_score.skill_score),
                "experience_score": float(
                    ats_score.experience_score
                ),
                "education_score": float(
                    ats_score.education_score
                ),
                "match_percentage": float(
                    ats_score.match_percentage
                ),
            },
            "ai_interview": {
            "call_id": ai_call.id,
            "call_status": ai_call.status,
            "score": float(ai_call_score),
            "evaluated_answers": evaluation_count,
            "evaluation_breakdown": {
                "average_relevance": float(average_relevance),
                "average_completeness": float(average_completeness),
                "average_keyword": float(average_keyword),
                "average_confidence": float(average_confidence),
            },
        },
            "overall_score": float(overall_score),
            "strengths": strengths,
            "risks": risks,
            "summary": summary,
        }

        report, created = AICandidateReport.objects.update_or_create(
            application=application,
            defaults={
                "ats_score": ats_match,
                "ai_call_score": ai_call_score,
                "overall_score": overall_score,
                "strengths": strengths,
                "risks": risks,
                "summary": summary,
                "report_data": report_data,
            },
        )

        return {
            "success": True,
            "created": created,
            "report_id": report.id,
            "data": report_data,
        }