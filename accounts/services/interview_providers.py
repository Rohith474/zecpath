from abc import ABC, abstractmethod


class InterviewQuestionProvider(ABC):
    """
    Interface for generating interview questions.

    The current implementation can use a development provider.
    A real AI provider can be added later without changing
    the interview workflow.
    """

    @abstractmethod
    def generate_questions(self, job, question_count=3):
        """
        Generate interview questions based on the job.
        """
        raise NotImplementedError


class InterviewAnswerEvaluationProvider(ABC):
    """
    Interface for evaluating candidate answers.

    A future AI provider can implement this interface.
    """

    @abstractmethod
    def evaluate_answer(
        self,
        question,
        answer,
        job,
    ):
        """
        Evaluate one candidate answer against the job.
        """
        raise NotImplementedError


class InterviewMonitoringProvider(ABC):
    """
    Interface for monitoring the interview.

    A future AI/video monitoring provider can implement
    camera, face, cheating, and other monitoring checks.
    """

    @abstractmethod
    def start_monitoring(self, session):
        """
        Start monitoring an interview session.
        """
        raise NotImplementedError

    @abstractmethod
    def process_event(self, session, event_type, event_data=None):
        """
        Process a monitoring event.
        """
        raise NotImplementedError

    @abstractmethod
    def stop_monitoring(self, session):
        """
        Stop monitoring an interview session.
        """
        raise NotImplementedError