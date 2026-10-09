import logging
import time

import requests
from django.conf import settings

from accounts.services.ai_provider_openai import OpenAIProvider

logger = logging.getLogger(__name__)
class AIBridgeService:
    """
    Central service layer between the Django application
    and the configured AI provider.

    Handles:
    - AI API requests
    - retries
    - timeout errors
    - rate-limit errors
    - API failures
    - safe error responses
    """

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2

    def __init__(self):
        self.provider = OpenAIProvider()

    def _check_configuration(self):
        """
        Check whether the AI API configuration is available.
        """

        if not settings.OPENAI_API_KEY:
            return {
                "success": False,
                "message": "OPENAI_API_KEY is not configured.",
            }

        if not settings.OPENAI_LLM_MODEL:
            return {
                "success": False,
                "message": "OPENAI_LLM_MODEL is not configured.",
            }

        return None

    def generate_text(self, prompt):
        """
        Generate AI text with retry and error handling.
        """

        configuration_error = self._check_configuration()

        if configuration_error:
            return configuration_error

        if not prompt:
            return {
                "success": False,
                "message": "Prompt is required.",
            }

        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):

            try:
                result = self.provider.generate_text(prompt)

                return {
                    "success": True,
                    "result": result,
                    "attempt": attempt,
                }

            except requests.exceptions.Timeout:
                last_error = "AI API request timed out."

            except requests.exceptions.ConnectionError:
                last_error = "Unable to connect to the AI API."

            except RuntimeError as error:
                last_error = str(error)

            except ValueError as error:
                return {
                    "success": False,
                    "message": str(error),
                }

            except Exception:
                logger.exception("Unexpected error in AI bridge service.")
                last_error = "An unexpected AI service error occurred."

            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY_SECONDS)

        return {
            "success": False,
            "message": last_error
            or "AI service request failed.",
            "attempts": self.MAX_RETRIES,
        }

    def start_screening(self, ai_call):
        """
        Start an AI screening through the configured provider.
        """

        configuration_error = self._check_configuration()

        if configuration_error:
            return configuration_error

        try:
            result = self.provider.start_screening(ai_call)

            return {
                "success": True,
                "result": result,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "AI screening request timed out.",
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Unable to connect to the AI service.",
            }

        except RuntimeError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except Exception:
            logger.exception("Unexpected error in AI bridge service.")
            return {
                "success": False,
                "message": "Unable to start AI screening.",
            }

    def process_response(
        self,
        ai_call,
        question,
        answer,
    ):
        """
        Process a candidate answer through the configured provider.
        """

        configuration_error = self._check_configuration()

        if configuration_error:
            return configuration_error

        try:
            result = self.provider.process_response(
                ai_call,
                question,
                answer,
            )

            return {
                "success": True,
                "result": result,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "AI response processing timed out.",
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Unable to connect to the AI service.",
            }

        except RuntimeError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except Exception:
            logger.exception("Unexpected error in AI bridge service.")
            return {
                "success": False,
                "message": "Unable to process AI response.",
            }

    def analyze_screening(self, ai_call):
        """
        Analyze a completed screening through the configured provider.
        """

        configuration_error = self._check_configuration()

        if configuration_error:
            return configuration_error

        try:
            result = self.provider.analyze_screening(ai_call)

            return {
                "success": True,
                "result": result,
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "AI screening analysis timed out.",
            }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Unable to connect to the AI service.",
            }

        except RuntimeError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except ValueError as error:
            return {
                "success": False,
                "message": str(error),
            }

        except Exception:
            logger.exception("Unexpected error in AI bridge service.")
            return {
                "success": False,
                "message": "Unable to analyze AI screening.",
            }