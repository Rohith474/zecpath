from accounts.services.ai_question_engine import AIQuestionEngine


class AIFlowManager:
    """
    High-level manager for the AI screening conversation.

    The flow manager coordinates the question engine
    without duplicating its question or branching logic.
    """

    def __init__(self, ai_call):
        self.ai_call = ai_call
        self.engine = AIQuestionEngine(ai_call)

    def start_flow(self):
        """
        Start or resume the AI screening flow.
        """

        return self.engine.get_current_question()

    def get_current_question(self):
        """
        Return the question currently expected
        from the candidate.
        """

        return self.engine.get_current_question()

    def submit_answer(self, answer):
        """
        Submit a candidate answer and continue
        the screening flow.
        """

        return self.engine.process_response(answer)

    def get_flow_status(self):
        """
        Return the current state of the AI screening flow.
        """

        state = self.engine.get_flow_state()

        current_question = (
            self.engine.get_current_question()
        )

        if (
            current_question.get("success")
            is False
            and state["current_question_index"]
            >= len(self.engine.get_question_set())
        ):
            status = "Completed"

        elif state["waiting_for_follow_up"]:
            status = "Waiting for Follow-up Answer"

        else:
            status = "In Progress"

        return {
            "success": True,
            "status": status,
            "current_question_index": (
                state["current_question_index"]
            ),
            "current_category": (
                state["current_category"]
            ),
            "waiting_for_follow_up": (
                state["waiting_for_follow_up"]
            ),
            "current_question": current_question,
        }