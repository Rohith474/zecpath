from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from accounts.models import (
    InterviewSchedule,
    ScheduledInterviewAnswer,
    ScheduledInterviewQuestion,
    ScheduledInterviewSession,
)
from accounts.services.interview_provider_factory import (
    InterviewProviderFactory,
)

class ScheduledInterviewService:
    """
    Handles the execution lifecycle of a scheduled interview.

    The service uses a question provider so that the current
    development provider can later be replaced by a real AI
    question provider without changing the interview workflow.
    """

    QUESTION_COUNT = 3
    @staticmethod
    @transaction.atomic
    def start_interview(interview_id):
        """
        Start a scheduled interview for the authenticated
        candidate.

        The interview must belong to the candidate and must
        be scheduled and ready to start.
        """

        # ----------------------------------------
        # Get interview
        # ----------------------------------------

        interview = (
            InterviewSchedule.objects
            .select_related(
                "application",
                "application__job",
                "application__candidate",
                "application__candidate__user",
            )
            .select_for_update()
            .filter(
                pk=interview_id,
            )
            .first()
        )

        if not interview:

            return {
                "success": False,
                "message": "Interview schedule not found.",
            }

        

        # ----------------------------------------
        # Validate interview status
        # ----------------------------------------

        if interview.status != InterviewSchedule.SCHEDULED:

            return {
                "success": False,
                "message": (
                    "Only scheduled interviews can be started."
                ),
            }

        # ----------------------------------------
        # Validate interview time
        # ----------------------------------------

        if interview.scheduled_at > timezone.now():

            return {
                "success": False,
                "message": (
                    "The interview cannot be started before "
                    "the scheduled time."
                ),
            }

        # ----------------------------------------
        # Get or create interview session
        # ----------------------------------------

        session, created = (
            ScheduledInterviewSession.objects
            .select_for_update()
            .get_or_create(
                interview=interview,
                defaults={
                    "status": (
                        ScheduledInterviewSession.NOT_STARTED
                    ),
                },
            )
        )

        # ----------------------------------------
        # Prevent duplicate start
        # ----------------------------------------

        if session.status != ScheduledInterviewSession.NOT_STARTED:

            return {
                "success": False,
                "message": (
                    "This interview has already been started "
                    "or completed."
                ),
                "session_id": session.id,
                "status": session.status,
            }

        # ----------------------------------------
        # Generate interview questions
        # ----------------------------------------

        question_provider = (
            InterviewProviderFactory.get_question_provider()
        )

        questions = question_provider.generate_questions(
            interview.application.job,
            question_count=(
                ScheduledInterviewService.QUESTION_COUNT
            ),
        )

        if len(questions) != (
            ScheduledInterviewService.QUESTION_COUNT
        ):

            return {
                "success": False,
                "message": (
                    "Unable to generate the required interview "
                    "questions."
                ),
            }

        # ----------------------------------------
        # Save questions
        # ----------------------------------------

        for order, question_text in enumerate(
            questions,
            start=1,
        ):

            ScheduledInterviewQuestion.objects.create(
                session=session,
                question_order=order,
                question_text=question_text,
            )

        # ----------------------------------------
        # Start session
        # ----------------------------------------

        session.status = (
            ScheduledInterviewSession.IN_PROGRESS
        )

        session.started_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "started_at",
                "updated_at",
            ]
        )

        # ----------------------------------------
        # Return first question
        # ----------------------------------------

        first_question = (
            ScheduledInterviewQuestion.objects
            .get(
                session=session,
                question_order=1,
            )
        )

        return {
            "success": True,
            "message": "Interview started successfully.",
            "session_id": session.id,
            "status": session.status,
            "started_at": session.started_at,
            "question": {
                "id": first_question.id,
                "order": first_question.question_order,
                "text": first_question.question_text,
            },
        }
    
    @staticmethod
    @transaction.atomic
    def submit_answer(session_id, question_id, answer_text):
        answer_text = (answer_text or "").strip()

        if not answer_text:
            return {
                "success": False,
                "message": "Answer cannot be empty.",
            }

        session = (
            ScheduledInterviewSession.objects
            .select_for_update()
            .select_related(
                "interview",
                "interview__application",
                "interview__application__job",
            )
            .filter(pk=session_id)
            .first()
        )

        if not session:
            return {
                "success": False,
                "message": "Interview session not found.",
            }

        if session.status != ScheduledInterviewSession.IN_PROGRESS:
            return {
                "success": False,
                "message": (
                    "Answers can only be submitted while "
                    "the interview is in progress."
                ),
            }

        question = (
            ScheduledInterviewQuestion.objects
            .filter(
                pk=question_id,
                session=session,
            )
            .first()
        )

        if not question:
            return {
                "success": False,
                "message": "The question does not belong to this interview session.",
            }

        if ScheduledInterviewAnswer.objects.filter(
            question=question
        ).exists():
            return {
                "success": False,
                "message": "An answer has already been submitted for this question.",
            }

        answer = ScheduledInterviewAnswer.objects.create(
            question=question,
            answer_text=answer_text,
        )

        next_question = (
            ScheduledInterviewQuestion.objects
            .filter(
                session=session,
                question_order__gt=question.question_order,
            )
            .exclude(answer__isnull=False)
            .order_by("question_order")
            .first()
        )

        if next_question:
            return {
                "success": True,
                "message": "Answer submitted successfully.",
                "answer_id": answer.id,
                "completed": False,
                "next_question": {
                    "id": next_question.id,
                    "order": next_question.question_order,
                    "text": next_question.question_text,
                },
            }

        completion_result = ScheduledInterviewService.complete_interview(
            session_id=session.id
        )

        if not completion_result["success"]:
            return {
                "success": False,
                "message": completion_result["message"],
                "answer_id": answer.id,
            }

        return {
            "success": True,
            "message": "Interview completed successfully.",
            "answer_id": answer.id,
            "completed": True,
            "next_question": None,
            "result": completion_result["result"],
            "overall_score": completion_result["overall_score"],
            "threshold": completion_result["threshold"],
        }
    @staticmethod
    @transaction.atomic
    def complete_interview(session_id):
        """
        Evaluate all submitted answers, calculate the overall
        interview score, compare it with the configured threshold,
        and complete the interview.
        """

        # ----------------------------------------
        # Get session
        # ----------------------------------------

        session = (
            ScheduledInterviewSession.objects
            .select_for_update()
            .select_related(
                "interview",
                "interview__application",
                "interview__application__job",
            )
            .filter(
                pk=session_id,
            )
            .first()
        )

        if not session:

            return {
                "success": False,
                "message": "Interview session not found.",
            }

        # ----------------------------------------
        # Validate session status
        # ----------------------------------------

        if session.status != ScheduledInterviewSession.IN_PROGRESS:

            return {
                "success": False,
                "message": (
                    "Only interviews currently in progress "
                    "can be completed."
                ),
            }

        # ----------------------------------------
        # Get all questions
        # ----------------------------------------

        questions = (
            ScheduledInterviewQuestion.objects
            .filter(
                session=session,
            )
            .prefetch_related("answer")
            .order_by(
                "question_order",
            )
        )

        question_count = questions.count()

        if question_count != ScheduledInterviewService.QUESTION_COUNT:

            return {
                "success": False,
                "message": (
                    "The interview does not contain the required "
                    "number of questions."
                ),
            }

        # ----------------------------------------
        # Verify all answers exist
        # ----------------------------------------

        answers = []

        for question in questions:

            try:
                answer = question.answer

            except ScheduledInterviewAnswer.DoesNotExist:

                return {
                    "success": False,
                    "message": (
                        f"Question {question.question_order} "
                        "has not been answered."
                    ),
                }

            answers.append(answer)

        # ----------------------------------------
        # Get job
        # ----------------------------------------

        job = session.interview.application.job

        # ----------------------------------------
        # Evaluation provider
        # ----------------------------------------

        evaluation_provider = (
            InterviewProviderFactory.get_evaluation_provider()
        )

        total_score = Decimal("0.00")

        # ----------------------------------------
        # Evaluate each answer
        # ----------------------------------------

        for question, answer in zip(
            questions,
            answers,
        ):

            evaluation = (
                evaluation_provider.evaluate_answer(
                    question=question.question_text,
                    answer=answer.answer_text,
                    job=job,
                )
            )

            score = Decimal(
                str(evaluation["score"])
            )

            answer.score = score

            answer.evaluation_feedback = (
                evaluation.get(
                    "feedback",
                    "",
                )
            )

            answer.evaluated_at = timezone.now()

            answer.save(
                update_fields=[
                    "score",
                    "evaluation_feedback",
                    "evaluated_at",
                ]
            )

            total_score += score

        # ----------------------------------------
        # Calculate overall score
        # ----------------------------------------

        overall_score = (
            total_score
            / Decimal(question_count)
        ).quantize(
            Decimal("0.01")
        )

        # ----------------------------------------
        # Get threshold
        # ----------------------------------------

        threshold = session.threshold

        # ----------------------------------------
        # Determine result
        # ----------------------------------------

        if overall_score >= threshold:

            result = ScheduledInterviewSession.PASSED

        else:

            result = ScheduledInterviewSession.RESULT_FAILED

        # ----------------------------------------
        # Complete session
        # ----------------------------------------

        session.status = (
            ScheduledInterviewSession.COMPLETED
        )

        session.result = result

        session.overall_score = overall_score

        session.completed_at = timezone.now()

        session.save(
            update_fields=[
                "status",
                "result",
                "overall_score",
                "completed_at",
                "updated_at",
            ]
        )

        # ----------------------------------------
        # Complete scheduled interview
        # ----------------------------------------

        interview = session.interview

        interview.status = InterviewSchedule.COMPLETED

        interview.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        # ----------------------------------------
        # Return result
        # ----------------------------------------

        return {
            "success": True,
            "message": "Interview completed successfully.",
            "session_id": session.id,
            "status": session.status,
            "result": session.result,
            "overall_score": session.overall_score,
            "threshold": session.threshold,
            "completed_at": session.completed_at,
            "answers": [
                {
                    "question_id": answer.question.id,
                    "question_order": (
                        answer.question.question_order
                    ),
                    "score": answer.score,
                    "feedback": (
                        answer.evaluation_feedback
                    ),
                }
                for answer in answers
            ],
        }