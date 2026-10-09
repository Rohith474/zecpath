import requests
from django.conf import settings

from accounts.services.ai_provider import AIProvider


class OpenAIProvider(AIProvider):
    """
    OpenAI implementation of the AIProvider interface.

    This class communicates with the external OpenAI API.
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_LLM_MODEL

    def _get_headers(self):
        """
        Return authentication headers for OpenAI API requests.
        """

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _validate_configuration(self):
        """
        Validate required OpenAI configuration.
        """

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not configured."
            )

        if not self.model:
            raise ValueError(
                "OPENAI_LLM_MODEL is not configured."
            )

    def generate_text(self, prompt):
        """
        Generate text using the configured OpenAI model.
        """

        self._validate_configuration()

        if not prompt:
            raise ValueError("Prompt is required.")

        url = f"{self.BASE_URL}/responses"

        payload = {
            "model": self.model,
            "input": prompt,
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=30,
        )

        if response.status_code == 429:
            raise RuntimeError(
                "OpenAI API rate limit reached."
            )

        if not response.ok:
            raise RuntimeError(
                f"OpenAI API request failed: "
                f"{response.status_code} - {response.text}"
            )

        data = response.json()

        output_text = data.get("output_text")

        if output_text:
            return output_text

        return ""
    
    def start_screening(self, ai_call):
        """
        Start an AI screening session.
        """

        config = ai_call.config

        prompt = (
            "You are conducting an AI job interview.\n"
            f"Language: {config.language}\n"
            f"Tone: {config.tone}\n"
            f"Speaking speed: {config.speaking_speed}\n"
            "Start the interview professionally.\n"
            "Ask the candidate to introduce themselves."
        )

        return self.generate_text(prompt)

    def process_response(
        self,
        ai_call,
        question,
        answer,
    ):
        """
        Process a candidate response and generate
        the next interview question.
        """

        if not question:
            raise ValueError("Question is required.")

        if not answer:
            raise ValueError("Answer is required.")

        config = ai_call.config

        prompt = (
            "You are conducting a professional AI job interview.\n"
            f"Language: {config.language}\n"
            f"Tone: {config.tone}\n\n"
            f"Previous question: {question}\n"
            f"Candidate answer: {answer}\n\n"
            "Generate the next relevant interview question."
        )

        return self.generate_text(prompt)

    def analyze_screening(self, ai_call):
        """
        Analyze the completed AI interview.
        """

        from accounts.models import AIInterviewAnswer

        answers = AIInterviewAnswer.objects.filter(
            ai_call=ai_call
        ).order_by("question_order")

        if not answers.exists():
            raise ValueError(
                "No interview answers found."
            )

        conversation = []

        for item in answers:
            conversation.append(
                f"Question: {item.question_text}\n"
                f"Answer: {item.answer_text}"
            )

        prompt = (
            "Analyze the following job interview.\n\n"
            + "\n\n".join(conversation)
            + "\n\n"
            "Provide a professional summary of the candidate's "
            "performance, strengths, weaknesses, and suitability "
            "for the role."
        )

        return self.generate_text(prompt)