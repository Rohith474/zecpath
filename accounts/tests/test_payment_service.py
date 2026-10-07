from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import (
    BillingHistory,
    CustomUser,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
)
from accounts.services.payment_service import PaymentService


class PaymentServiceRenewalTest(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="payment_test_user",
            password="testpassword123",
            role="Employer",
        )

        self.plan = SubscriptionPlan.objects.create(
            name="Test Pro Plan",
            description="Test subscription plan",
            price=Decimal("999.00"),
            currency="INR",
            billing_interval=SubscriptionPlan.MONTHLY,
            job_post_limit=20,
            ai_call_limit=100,
            analytics_access=True,
            features={
                "ai_interview": True,
                "advanced_analytics": True,
            },
            is_active=True,
        )

        now = timezone.now()

        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=UserSubscription.ACTIVE,
            started_at=now - timedelta(days=20),
            current_period_start=now - timedelta(days=20),
            current_period_end=now + timedelta(days=10),
        )

        self.payment_transaction = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.plan,
            subscription=None,
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_gateway="TestGateway",
            status=PaymentTransaction.PENDING,
            transaction_type=PaymentTransaction.RENEWAL,
        )

    def test_successful_renewal_extends_existing_subscription(self):
        old_subscription_id = self.subscription.id
        old_period_end = self.subscription.current_period_end

        result = PaymentService.handle_successful_payment(
            transaction_id=self.payment_transaction.id,
            gateway_transaction_id="test-renewal-001",
        )

        self.assertTrue(result["success"])

        self.subscription.refresh_from_db()
        self.payment_transaction.refresh_from_db()

        # No second subscription should be created.
        self.assertEqual(
            UserSubscription.objects.filter(
                user=self.user
            ).count(),
            1,
        )

        # The existing subscription must be reused.
        self.assertEqual(
            self.subscription.id,
            old_subscription_id,
        )

        # The renewal should extend the subscription period.
        self.assertGreater(
            self.subscription.current_period_end,
            old_period_end,
        )

        # Payment should be marked successful.
        self.assertEqual(
            self.payment_transaction.status,
            PaymentTransaction.SUCCESS,
        )

        # Payment should be linked to the existing subscription.
        self.assertEqual(
            self.payment_transaction.subscription_id,
            self.subscription.id,
        )

        # Gateway transaction ID should be stored.
        self.assertEqual(
            self.payment_transaction.gateway_transaction_id,
            "test-renewal-001",
        )

        # One billing history record should be created.
        self.assertEqual(
            BillingHistory.objects.filter(
                payment_transaction=self.payment_transaction
            ).count(),
            1,
        )

        billing_history = BillingHistory.objects.get(
            payment_transaction=self.payment_transaction
        )

        self.assertEqual(
            billing_history.subscription_id,
            self.subscription.id,
        )
  
        self.assertEqual(
            billing_history.status,
            BillingHistory.PAID,
        )
    
    def test_failed_payment_does_not_activate_subscription(self):
        payment_transaction = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.plan,
            subscription=None,
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_gateway="TestGateway",
            status=PaymentTransaction.PENDING,
            transaction_type=PaymentTransaction.SUBSCRIPTION,
        )

        subscription_count_before = UserSubscription.objects.filter(
            user=self.user
        ).count()

        result = PaymentService.handle_failed_payment(
            transaction_id=payment_transaction.id,
        )

        payment_transaction.refresh_from_db()

        self.assertTrue(result["success"])

        # Payment must be marked as failed.
        self.assertEqual(
            payment_transaction.status,
            PaymentTransaction.FAILED,
        )

        # No subscription should be created by the failed payment.
        self.assertEqual(
            UserSubscription.objects.filter(
                user=self.user
            ).count(),
            subscription_count_before,
        )

        # Payment must not be linked to a subscription.
        self.assertIsNone(
            payment_transaction.subscription_id,
        )

        # No paid billing history should be created for this payment.
        self.assertFalse(
            BillingHistory.objects.filter(
                payment_transaction=payment_transaction,
                status=BillingHistory.PAID,
            ).exists()
        )
    
    def test_refund_cancels_subscription_and_updates_billing_history(self):
        payment_transaction = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.plan,
            subscription=self.subscription,
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_gateway="TestGateway",
            gateway_transaction_id="test-payment-002",
            status=PaymentTransaction.SUCCESS,
            transaction_type=PaymentTransaction.SUBSCRIPTION,
        )

        billing_history = BillingHistory.objects.create(
            user=self.user,
            subscription=self.subscription,
            plan=self.plan,
            amount=self.plan.price,
            currency=self.plan.currency,
            billing_period_start=self.subscription.current_period_start,
            billing_period_end=self.subscription.current_period_end,
            status=BillingHistory.PAID,
            payment_transaction=payment_transaction,
        )

        result = PaymentService.handle_refund(
            transaction_id=payment_transaction.id,
        )

        payment_transaction.refresh_from_db()
        self.subscription.refresh_from_db()
        billing_history.refresh_from_db()

        self.assertTrue(result["success"])

        # Payment must be marked as refunded.
        self.assertEqual(
            payment_transaction.status,
            PaymentTransaction.REFUNDED,
        )

        # Billing history must be marked as refunded.
        self.assertEqual(
            billing_history.status,
            BillingHistory.REFUNDED,
        )

        # Subscription must be cancelled.
        self.assertEqual(
            self.subscription.status,
            UserSubscription.CANCELLED,
        )

        # Cancellation timestamp must be recorded.
        self.assertIsNotNone(
            self.subscription.cancelled_at,
        )

        # The subscription record itself must still exist.
        self.assertTrue(
            UserSubscription.objects.filter(
                id=self.subscription.id
            ).exists()
        )
    
    def test_successful_payment_is_idempotent(self):
        payment_transaction = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.plan,
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_gateway="TestGateway",
            status=PaymentTransaction.PENDING,
            transaction_type=PaymentTransaction.SUBSCRIPTION,
        )

        first_result = PaymentService.handle_successful_payment(
            transaction_id=payment_transaction.id,
            gateway_transaction_id="test-payment-idempotency",
        )

        subscription_count_after_first = (
            UserSubscription.objects.filter(
                user=self.user
            ).count()
        )

        billing_count_after_first = (
            BillingHistory.objects.filter(
                payment_transaction=payment_transaction
            ).count()
        )

        second_result = PaymentService.handle_successful_payment(
            transaction_id=payment_transaction.id,
            gateway_transaction_id="test-payment-idempotency",
        )

        payment_transaction.refresh_from_db()

        self.assertTrue(first_result["success"])
        self.assertTrue(second_result["success"])

        self.assertEqual(
            second_result["message"],
            "Payment was already processed.",
        )

        # Only one subscription should exist.
        self.assertEqual(
            UserSubscription.objects.filter(
                user=self.user
            ).count(),
            subscription_count_after_first,
        )

        # Only one billing record should exist.
        self.assertEqual(
            BillingHistory.objects.filter(
                payment_transaction=payment_transaction
            ).count(),
            billing_count_after_first,
        )

        # Payment remains successful.
        self.assertEqual(
            payment_transaction.status,
            PaymentTransaction.SUCCESS,
        )


    def test_refund_is_idempotent(self):
        payment_transaction = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.plan,
            subscription=self.subscription,
            amount=self.plan.price,
            currency=self.plan.currency,
            payment_gateway="TestGateway",
            gateway_transaction_id="test-refund-idempotency",
            status=PaymentTransaction.SUCCESS,
            transaction_type=PaymentTransaction.SUBSCRIPTION,
        )

        BillingHistory.objects.create(
            user=self.user,
            subscription=self.subscription,
            plan=self.plan,
            amount=self.plan.price,
            currency=self.plan.currency,
            billing_period_start=self.subscription.current_period_start,
            billing_period_end=self.subscription.current_period_end,
            status=BillingHistory.PAID,
            payment_transaction=payment_transaction,
        )

        first_result = PaymentService.handle_refund(
            transaction_id=payment_transaction.id,
        )

        billing_count_after_first = (
            BillingHistory.objects.filter(
                payment_transaction=payment_transaction
            ).count()
        )

        second_result = PaymentService.handle_refund(
            transaction_id=payment_transaction.id,
        )

        payment_transaction.refresh_from_db()
        self.subscription.refresh_from_db()

        self.assertTrue(first_result["success"])
        self.assertTrue(second_result["success"])

        self.assertEqual(
            second_result["message"],
            "Payment was already refunded.",
        )

        # Only one billing record should exist.
        self.assertEqual(
            BillingHistory.objects.filter(
                payment_transaction=payment_transaction
            ).count(),
            billing_count_after_first,
        )

        # Payment remains refunded.
        self.assertEqual(
            payment_transaction.status,
            PaymentTransaction.REFUNDED,
        )

        # Subscription remains cancelled.
        self.assertEqual(
            self.subscription.status,
            UserSubscription.CANCELLED,
        )

