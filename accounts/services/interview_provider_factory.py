from accounts.services.development_interview_provider import (
    DevelopmentInterviewAnswerEvaluationProvider,
    DevelopmentInterviewMonitoringProvider,
    DevelopmentInterviewQuestionProvider,
)


class InterviewProviderFactory:
    """
    Central provider selection point.

    Development providers are used currently.
    Real AI providers can replace them later without
    changing the interview service.
    """

    @staticmethod
    def get_question_provider():
        return DevelopmentInterviewQuestionProvider()

    @staticmethod
    def get_evaluation_provider():
        return DevelopmentInterviewAnswerEvaluationProvider()

    @staticmethod
    def get_monitoring_provider():
        return DevelopmentInterviewMonitoringProvider()