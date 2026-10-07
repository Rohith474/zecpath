class AIProvider:
    """
    Interface for integrating an external AI
    interview provider in the future.
    """

    def start_screening(self, ai_call):
        """
        Start an AI screening session.
        """
        raise NotImplementedError(
            "AI provider must implement start_screening()."
        )

    def process_response(
        self,
        ai_call,
        question,
        answer,
    ):
        """
        Process a candidate response.
        """
        raise NotImplementedError(
            "AI provider must implement process_response()."
        )

    def analyze_screening(self, ai_call):
        """
        Analyze the completed screening session.
        """
        raise NotImplementedError(
            "AI provider must implement analyze_screening()."
        )
