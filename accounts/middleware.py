from .services.subscription_service import SubscriptionService


class SubscriptionMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.subscription = None

        if request.user.is_authenticated:
            request.subscription = (
                SubscriptionService
                .get_active_subscription(
                    request.user
                )
            )

        response = self.get_response(request)

        return response