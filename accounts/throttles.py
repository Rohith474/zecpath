from rest_framework.throttling import UserRateThrottle


class PremiumUserRateThrottle(UserRateThrottle):
    scope = "premium"