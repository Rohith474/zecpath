import logging

from rest_framework.permissions import BasePermission

from accounts.services.subscription_service import SubscriptionService


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == "Admin"
        )


class IsEmployer(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == "Employer"
        )


class IsCandidate(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == "Candidate"
        )
    
security_logger = logging.getLogger("security")


class LoggedPermission(BasePermission):
    """
    Base permission class that logs unauthorized
    and forbidden access attempts.
    """

    required_role = None

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            security_logger.warning(
                "SECURITY_EVENT | "
                "event=UNAUTHORIZED_ACCESS | "
                f"method={request.method} | "
                f"path={request.path} | "
                "status=401"
            )

            return False

        if self.required_role:
            if request.user.role != self.required_role:

                security_logger.warning(
                    "SECURITY_EVENT | "
                    "event=FORBIDDEN_ACCESS | "
                    f"user_id={request.user.id} | "
                    f"role={request.user.role} | "
                    f"required_role={self.required_role} | "
                    f"method={request.method} | "
                    f"path={request.path} | "
                    "status=403"
                )

                return False

        return True
class LoggedIsAdmin(LoggedPermission):
    required_role = "Admin"


class LoggedIsEmployer(LoggedPermission):
    required_role = "Employer"


class LoggedIsCandidate(LoggedPermission):
    required_role = "Candidate"
class HasSubscriptionFeature(LoggedPermission):

    required_role = "Employer"

    feature_name = None

    message = "Your active subscription does not include this feature."

    def has_permission(self, request, view):

        if not super().has_permission(request, view):
            return False

        if not self.feature_name:
            return False

        return SubscriptionService.has_feature(
            request.user,
            self.feature_name,
        )
class HasAIInterviewAccess(HasSubscriptionFeature):
    feature_name = "ai_interview"


class HasAIAnswerEvaluationAccess(HasSubscriptionFeature):
    feature_name = "ai_answer_evaluation"


class HasInterviewAvailabilityAccess(HasSubscriptionFeature):
    feature_name = "interview_availability"


class HasAIInterviewReportsAccess(HasSubscriptionFeature):
    feature_name = "ai_interview_reports"


class HasAdvancedAnalyticsAccess(HasSubscriptionFeature):
    feature_name = "advanced_analytics"


class HasEnterpriseAnalyticsAccess(HasSubscriptionFeature):
    feature_name = "enterprise_analytics"


class HasEnterpriseReportsAccess(HasSubscriptionFeature):
    feature_name = "enterprise_reports"