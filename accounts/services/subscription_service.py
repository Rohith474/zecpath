from datetime import timedelta

from django.db.models import (
    Count,
    F,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.models import (
    AICall,
    Application,
    EmployerProfile,
    Job,
    UserSubscription,
)


class SubscriptionService:

    GRACE_PERIOD_DAYS = 3
    @staticmethod
    def process_subscription_expiry(subscription):
        now = timezone.now()

        if subscription.status not in [
            UserSubscription.ACTIVE,
            UserSubscription.TRIALING,
            UserSubscription.PAST_DUE,
        ]:
            return subscription

        # ----------------------------------------
        # Subscription period has not expired yet.
        # ----------------------------------------

        if subscription.current_period_end >= now:
            return subscription

        # ----------------------------------------
        # Start the grace period.
        # ----------------------------------------

        if subscription.status in [
            UserSubscription.ACTIVE,
            UserSubscription.TRIALING,
        ]:
            subscription.status = UserSubscription.PAST_DUE

        if subscription.grace_period_end is None:
            subscription.grace_period_end = (
                subscription.current_period_end
                + timedelta(
                    days=SubscriptionService.GRACE_PERIOD_DAYS
                )
            )

            subscription.save(
                update_fields=[
                    "status",
                    "grace_period_end",
                    "updated_at",
                ]
            )

        # ----------------------------------------
        # Grace period has expired.
        # ----------------------------------------

        if subscription.grace_period_end < now:
            subscription.status = UserSubscription.EXPIRED

            subscription.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        return subscription
    @staticmethod
    def get_active_subscription(user):
        subscription = (
            UserSubscription.objects
            .select_related("plan")
            .filter(
                user=user,
                status__in=[
                    UserSubscription.ACTIVE,
                    UserSubscription.TRIALING,
                    UserSubscription.PAST_DUE,
                ],
            )
            .order_by("-current_period_end")
            .first()
        )

        if not subscription:
            return None

        subscription = SubscriptionService.process_subscription_expiry(
            subscription
        )

        if subscription.status == UserSubscription.EXPIRED:
            return None

        if subscription.status == UserSubscription.CANCELLED:
            return None

        return subscription

    @staticmethod
    def has_feature(user, feature_name):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return False

        return subscription.plan.features.get(feature_name, False)

    @staticmethod
    def get_job_post_limit(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return 0

        return subscription.plan.job_post_limit

    @staticmethod
    def get_ai_call_limit(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return 0

        return subscription.plan.ai_call_limit

    @staticmethod
    def can_post_job(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return False

        limit = subscription.plan.job_post_limit

        if limit is None:
            return True

        job_count = Job.objects.filter(
            employer__user=user,
            created_at__gte=subscription.current_period_start,
            created_at__lte=subscription.current_period_end,
        ).count()

        return job_count < limit

    @staticmethod
    def can_access_candidate(user, candidate_user_id):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return False

        limit = subscription.plan.candidate_access_limit

        # Enterprise / unlimited plan
        if limit is None:
            return True

        # Check whether this candidate is already within
        # the employer's accessible candidate set.
        existing_candidate_ids = (
            Application.objects
            .filter(
                job__employer__user=user,
                applied_at__gte=subscription.current_period_start,
                applied_at__lte=subscription.current_period_end,
            )
            .values("candidate__user_id")
            .distinct()
            .order_by("candidate__user_id")[:limit]
        )

        allowed_candidate_ids = {
            row["candidate__user_id"]
            for row in existing_candidate_ids
        }

        return candidate_user_id in allowed_candidate_ids
    @staticmethod
    def get_accessible_candidate_user_ids(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return set()

        limit = subscription.plan.candidate_access_limit

        # Enterprise / unlimited plan
        if limit is None:
            return set(
                Application.objects
                .filter(
                    job__employer__user=user,
                    applied_at__gte=subscription.current_period_start,
                    applied_at__lte=subscription.current_period_end,
                )
                .values_list(
                    "candidate__user_id",
                    flat=True,
                )
                .distinct()
            )

        # Get the first candidates who applied during
        # the current billing period.
        applications = (
            Application.objects
            .filter(
                job__employer__user=user,
                applied_at__gte=subscription.current_period_start,
                applied_at__lte=subscription.current_period_end,
            )
            .order_by(
                "applied_at",
                "id",
            )
            .values(
                "candidate__user_id",
            )
        )

        accessible_candidate_ids = []

        for application in applications:
            candidate_user_id = application["candidate__user_id"]

            if candidate_user_id in accessible_candidate_ids:
                continue

            accessible_candidate_ids.append(
                candidate_user_id
            )

            if len(accessible_candidate_ids) >= limit:
                break

        return set(accessible_candidate_ids)
    
    @staticmethod
    def can_receive_new_candidates(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return False

        limit = subscription.plan.candidate_access_limit

        # Enterprise / unlimited plan
        if limit is None:
            return True

        candidate_count = (
            Application.objects
            .filter(
                job__employer__user=user,
                applied_at__gte=subscription.current_period_start,
                applied_at__lte=subscription.current_period_end,
            )
            .values("candidate__user_id")
            .distinct()
            .count()
        )

        return candidate_count < limit
    
    @staticmethod
    def get_employer_ids_with_candidate_capacity():
        now = timezone.now()

        candidate_count_subquery = (
            Application.objects
            .filter(
                job__employer__user_id=OuterRef("user_id"),
                applied_at__gte=OuterRef("current_period_start"),
                applied_at__lte=OuterRef("current_period_end"),
            )
            .values(
                "job__employer__user_id",
            )
            .annotate(
                candidate_count=Count(
                    "candidate__user_id",
                    distinct=True,
                ),
            )
            .values(
                "candidate_count",
            )[:1]
        )

        subscriptions = (
            UserSubscription.objects
            .select_related("plan")
            .filter(
                status__in=[
                    UserSubscription.ACTIVE,
                    UserSubscription.TRIALING,
                    UserSubscription.PAST_DUE,
                ],
            )
            .filter(
                Q(current_period_end__gte=now)
                | Q(
                    grace_period_end__isnull=False,
                    grace_period_end__gte=now,
                )
                | Q(
                    grace_period_end__isnull=True,
                    current_period_end__gte=(
                        now
                        - timedelta(
                            days=SubscriptionService.GRACE_PERIOD_DAYS
                        )
                    ),
                )
            )
            .annotate(
                    candidate_count=Coalesce(
                        Subquery(candidate_count_subquery),
                        0,
                    ),
                     )
            .filter(
                Q(plan__candidate_access_limit__isnull=True)
                | Q(
                    candidate_count__lt=F(
                        "plan__candidate_access_limit"
                    )
                )
            )
            .values_list(
                "user_id",
                flat=True,
            )
        )

        return set(
            EmployerProfile.objects
            .filter(
                user_id__in=subscriptions,
            )
            .values_list(
                "id",
                flat=True,
            )
        )
    
    @staticmethod
    def can_create_ai_call(user):
        subscription = SubscriptionService.get_active_subscription(user)

        if not subscription:
            return False

        limit = subscription.plan.ai_call_limit

        if limit is None:
            return True

        ai_call_count = AICall.objects.filter(
            application__job__employer__user=user,
            created_at__gte=subscription.current_period_start,
            created_at__lte=subscription.current_period_end,
        ).count()

        return ai_call_count < limit