from django.db import transaction
from django.utils import timezone

from accounts.models import (
    AICall,
    AIInterviewAnswer,
    AIInterviewSession,
    AIQuestionJobMapping,
)
from accounts.services.interview_availability import (
    InterviewAvailabilityService,
)


class AIQuestionEngine:
    """
    Dynamic AI screening question engine.

    Responsibilities:
    - Load questions for a job
    - Track current question state
    - Process candidate responses
    - Apply conditional branching
    - Generate follow-up questions
    - Return the next question
    """

    def __init__(self, ai_call):
        self.ai_call = ai_call

    def get_question_set(self):
        """
        Get the active question set configured for
        the job associated with this AI call.
        """

        category_order = {
            "Introduction": 1,
            "Experience": 2,
            "Skills": 3,
            "Availability": 4,
            "Salary": 5,
        }

        mappings = (
            AIQuestionJobMapping.objects
            .filter(
                job=self.ai_call.application.job,
                is_active=True,
                question__is_active=True,
            )
            .select_related("question")
            .order_by(
                "question__order",
                "question__id",
            )
        )

        questions = [mapping.question for mapping in mappings]

        questions.sort(
            key=lambda question: (
                category_order.get(
                    question.category,
                    99,
                ),
                question.order,
                question.id,
            )
        )

        return questions

    def get_session(self):
        """
        Get or create the AI interview session.
        """

        session, _created = (
            AIInterviewSession.objects.get_or_create(
                ai_call=self.ai_call,
                defaults={
                    "status": "In Progress",
                    "transcript": {},
                },
            )
        )

        return session

    def get_flow_state(self):
        """
        Get the current question-flow state.
        """

        session = self.get_session()

        transcript = session.transcript or {}

        state = transcript.get(
            "question_flow",
            {},
        )

        return {
            "current_question_index": state.get(
                "current_question_index",
                0,
            ),
            "current_category": state.get(
                "current_category"
            ),
            "waiting_for_follow_up": state.get(
                "waiting_for_follow_up",
                False,
            ),
            "follow_up_question": state.get(
                "follow_up_question"
            ),
        }

    def save_flow_state(
        self,
        current_question_index,
        current_category=None,
        waiting_for_follow_up=False,
        follow_up_question=None,
    ):
        """
        Save the current question-flow state.
        """

        session = self.get_session()

        transcript = session.transcript or {}

        transcript["question_flow"] = {
            "current_question_index": (
                current_question_index
            ),
            "current_category": current_category,
            "waiting_for_follow_up": (
                waiting_for_follow_up
            ),
            "follow_up_question": (
                follow_up_question
            ),
        }

        session.transcript = transcript

        session.save(
            update_fields=[
                "transcript",
                "updated_at",
            ]
        )

    def get_answered_questions(self):
        """
        Get questions already answered during
        this AI interview.
        """

        return AIInterviewAnswer.objects.filter(
            ai_call=self.ai_call
        ).order_by("question_order")

    def get_current_question_index(self):
        """
        Return the current question index.
        """

        state = self.get_flow_state()

        return state["current_question_index"]

    def get_current_question(self):
        """
        Return the question currently waiting
        for a candidate response.
        """

        questions = self.get_question_set()

        if not questions:
            return {
                "success": False,
                "message": (
                    "No questions are configured "
                    "for this job."
                ),
            }

        state = self.get_flow_state()

        if state["waiting_for_follow_up"]:
            return {
                "success": True,
                "question_order": (
                    state["current_question_index"] + 1
                ),
                "category": state["current_category"],
                "question": state["follow_up_question"],
                "flow_type": "follow_up",
            }

        current_index = state[
            "current_question_index"
        ]

        if current_index >= len(questions):
            return {
                "success": False,
                "message": (
                    "AI screening question flow "
                    "completed."
                ),
            }

        question = questions[current_index]

        return {
            "success": True,
            "question_id": question.id,
            "question_order": current_index + 1,
            "category": question.category,
            "question": question.question_text,
            "flow_type": "main",
        }

    def _needs_follow_up(
        self,
        question,
        answer,
    ):
        """
        Determine whether a candidate response
        requires a follow-up question.
        """

        if not answer:
            return False

        answer_text = answer.lower().strip()

        if question.category == "Experience":
            experience_keywords = [
                "yes",
                "experience",
                "worked",
                "project",
                "company",
                "developer",
            ]

            return any(
                keyword in answer_text
                for keyword in experience_keywords
            )

        if question.category == "Skills":
            skill_keywords = [
                "python",
                "java",
                "javascript",
                "django",
                "react",
                "sql",
                "machine learning",
                "api",
            ]

            return any(
                keyword in answer_text
                for keyword in skill_keywords
            )

        if question.category == "Salary":
            salary_keywords = [
                "salary",
                "lakh",
                "lpa",
                "per annum",
                "expected",
                "inr",
                "₹",
            ]

            return any(
                keyword in answer_text
                for keyword in salary_keywords
            )

        return False

    def _generate_follow_up(
        self,
        question,
        answer,
    ):
        """
        Generate a contextual follow-up question.
        """

        if question.category == "Experience":
            return (
                "Can you describe one of the most "
                "important projects or responsibilities "
                "from that experience?"
            )

        if question.category == "Skills":
            return (
                "Can you explain how you used one of "
                "those technical skills in a real project?"
            )

        if question.category == "Availability":
            return (
                "Please provide a specific interview "
                "date and time. For example: "
                "September 24, 2026 at 10:30 AM."
            )

        if question.category == "Salary":
            return (
                "What factors are important to you when "
                "considering the compensation for this role?"
            )

        return None

    def process_response(self, answer):
        if not answer:
            return {
                "success": False,
                "message": "Candidate answer is required."
            }

        with transaction.atomic():

            # ----------------------------------------
            # Lock this specific AI call
            # ----------------------------------------

            self.ai_call = (
                AICall.objects
                .select_for_update()
                .get(pk=self.ai_call.pk)
            )

            # ----------------------------------------
            # Validate AI call status after acquiring
            # the database lock
            # ----------------------------------------

            if self.ai_call.status != AICall.IN_PROGRESS:
                return {
                    "success": False,
                    "message": "AI call is not currently in progress."
                }

            # ----------------------------------------
            # Get current question after acquiring
            # the lock
            # ----------------------------------------

            current_question_result = self.get_current_question()

            if not current_question_result["success"]:
                return current_question_result

            state = self.get_flow_state()

            current_index = state["current_question_index"]
            questions = self.get_question_set()

            current_question = None

            if state["waiting_for_follow_up"]:
                question_text = state["follow_up_question"]
                category = state["current_category"]

            else:
                current_question = questions[current_index]
                question_text = current_question.question_text
                category = current_question.category

            # ----------------------------------------
            # Calculate next answer order
            # ----------------------------------------

            next_order = (
                AIInterviewAnswer.objects
                .filter(ai_call=self.ai_call)
                .count()
                + 1
            )

            # ----------------------------------------
            # Store answer
            # ----------------------------------------

            stored_answer = AIInterviewAnswer.objects.create(
                ai_call=self.ai_call,
                question_order=next_order,
                question_text=question_text,
                answer_text=answer,
            )

            # ----------------------------------------
            # Process interview availability
            # ----------------------------------------

            if category == "Availability":

                availability_result = (
                    InterviewAvailabilityService.save_availability(
                        application=self.ai_call.application,
                        answer=answer,
                    )
                )

                if not availability_result["success"]:

                    return {
                        "success": False,
                        "answer_id": stored_answer.id,
                        "question_order": next_order,
                        "answered_question": question_text,
                        "answer": answer,
                        "flow_type": "availability_required",
                        "message": availability_result["message"],
                        "next_question": (
                            "Please provide a specific interview "
                            "date and time. For example: "
                            "September 24, 2026 at 10:30 AM."
                        ),
                        "next_category": "Availability",
                    }

            # ----------------------------------------
            # Check whether a follow-up is required
            # ----------------------------------------

            if (
                not state["waiting_for_follow_up"]
                and current_question
                and self._needs_follow_up(
                    current_question,
                    answer
                )
            ):

                follow_up_question = self._generate_follow_up(
                    current_question,
                    answer
                )

                if follow_up_question:

                    self.save_flow_state(
                        current_question_index=current_index,
                        current_category=category,
                        waiting_for_follow_up=True,
                        follow_up_question=follow_up_question,
                    )

                    return {
                        "success": True,
                        "answer_id": stored_answer.id,
                        "question_order": next_order,
                        "answered_question": question_text,
                        "answer": answer,
                        "flow_type": "follow_up",
                        "next_question": follow_up_question,
                        "next_category": category,
                    }

            # ----------------------------------------
            # Move to next main question
            # ----------------------------------------

            next_index = current_index + 1

            self.save_flow_state(
                current_question_index=next_index,
                current_category=None,
                waiting_for_follow_up=False,
                follow_up_question=None,
            )

            next_question_result = self.get_current_question()

            # ----------------------------------------
            # More questions remain
            # ----------------------------------------

            if next_question_result["success"]:

                return {
                    "success": True,
                    "answer_id": stored_answer.id,
                    "question_order": next_order,
                    "answered_question": question_text,
                    "answer": answer,
                    "flow_type": "next_question",
                    "next_question": next_question_result["question"],
                    "next_category": next_question_result["category"],
                }

            # ----------------------------------------
            # Question flow completed
            # ----------------------------------------

            session = self.get_session()

            session.status = "Completed"
            session.ended_at = timezone.now()

            session.save(
                update_fields=[
                    "status",
                    "ended_at",
                    "updated_at",
                ]
            )

            self.ai_call.status = AICall.COMPLETED

            # ----------------------------------------
            # Also record completion time
            # ----------------------------------------

            self.ai_call.completed_at = timezone.now()

            self.ai_call.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            return {
                "success": True,
                "answer_id": stored_answer.id,
                "question_order": next_order,
                "answered_question": question_text,
                "answer": answer,
                "flow_type": "completed",
                "message": "AI screening question flow completed.",
            }