from decimal import Decimal

from .interview_providers import (
    InterviewQuestionProvider,
    InterviewAnswerEvaluationProvider,
    InterviewMonitoringProvider,
)


class DevelopmentInterviewQuestionProvider(
    InterviewQuestionProvider
):
    """
    Temporary provider used until a real AI question
    generation provider is integrated.

    It deliberately implements the same interface that
    the future AI provider will use.
    """

    def generate_questions(
        self,
        job,
        question_count=3,
    ):
        questions = [
            (
                f"Explain your experience and background "
                f"relevant to the {job.title} role."
            ),
            (
                f"Explain your practical experience with "
                f"the following skills required for this job: "
                f"{job.skills}."
            ),
            (
                f"Describe a project or situation where you "
                f"demonstrated skills relevant to this job. "
                f"How did your experience help you solve the "
                f"problem?"
            ),
        ]

        return questions[:question_count]


class DevelopmentInterviewAnswerEvaluationProvider(
    InterviewAnswerEvaluationProvider
):
    """
    Temporary deterministic evaluator used until a real
    AI answer evaluation provider is integrated.

    This provider does not claim to be an AI model.
    It only allows the complete backend workflow to be
    developed and tested.
    """

    def evaluate_answer(
        self,
        question,
        answer,
        job,
    ):
        answer_text = (answer or "").strip()

        if not answer_text:
            return {
                "score": Decimal("0.00"),
                "feedback": "No answer was provided.",
            }

        answer_words = answer_text.split()

        score = Decimal("40.00")

        # Basic completeness signal.
        if len(answer_words) >= 20:
            score += Decimal("20.00")

        if len(answer_words) >= 50:
            score += Decimal("10.00")

        # Match job skills against the candidate answer.
        answer_lower = answer_text.lower()

        skills = [
            skill.strip().lower()
            for skill in job.skills.split(",")
            if skill.strip()
        ]

        matched_skills = [
            skill
            for skill in skills
            if skill in answer_lower
        ]

        if skills:
            keyword_score = (
                Decimal(len(matched_skills))
                / Decimal(len(skills))
            ) * Decimal("30.00")

            score += keyword_score

        score = min(score, Decimal("100.00"))

        feedback = (
            f"Development evaluation based on answer "
            f"completeness and job-skill relevance. "
            f"Matched {len(matched_skills)} job skill(s)."
        )

        return {
            "score": score.quantize(Decimal("0.01")),
            "feedback": feedback,
        }


class DevelopmentInterviewMonitoringProvider(
    InterviewMonitoringProvider
):
    """
    Temporary monitoring provider.

    It provides the interface required by the interview
    system but does not perform real camera or cheating
    detection.

    A future AI/video provider will replace this class.
    """

    def start_monitoring(self, session):
        return {
            "success": True,
            "monitoring_started": True,
        }

    def process_event(
        self,
        session,
        event_type,
        event_data=None,
    ):
        return {
            "success": True,
            "event_type": event_type,
            "event_data": event_data or {},
        }

    def stop_monitoring(self, session):
        return {
            "success": True,
            "monitoring_stopped": True,
        }