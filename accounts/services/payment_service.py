from datetime import timedelta

from django.db import transaction
from django.utils import timezone
import razorpay
from django.conf import settings

from accounts.models import (
    BillingHistory,
    CustomUser,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
    RefundRequest,
    AuditLog,
)
from accounts.services.logging_service import LoggingService


class PaymentService:
    REFUND_WINDOW_DAYS = 7
    @staticmethod
    def check_refund_eligibility(payment_transaction):
        if payment_transaction.status != PaymentTransaction.SUCCESS:
            return {
                "eligible": False,
                "message": "Only successful payments can be refunded.",
            }

        refund_deadline = (
            payment_transaction.created_at
            + timedelta(days=PaymentService.REFUND_WINDOW_DAYS)
        )

        if timezone.now() > refund_deadline:
            return {
                "eligible": False,
                "message": "The refund period for this payment has expired.",
                "refund_deadline": refund_deadline,
            }

        if payment_transaction.razorpay_refund_id:
            return {
                "eligible": False,
                "message": "A refund has already been initiated for this payment.",
            }

        if hasattr(payment_transaction, "refund_request"):
            return {
                "eligible": False,
                "message": "A refund request already exists for this payment.",
            }

        return {
            "eligible": True,
            "message": "Payment is eligible for a refund.",
            "refund_deadline": refund_deadline,
        }
    @staticmethod
    @transaction.atomic
    def create_refund_request(
        payment_transaction_id,
        user,
        reason,
    ):
        payment_transaction = (
        PaymentTransaction.objects
        .select_for_update()
        .get(id=payment_transaction_id)
    )

        if payment_transaction.user_id != user.id:
            return {
                "success": False,
                "message": "You cannot request a refund for this payment.",
            }

        if not reason or not reason.strip():
            return {
                "success": False,
                "message": "Refund reason is required.",
            }

        eligibility = PaymentService.check_refund_eligibility(
            payment_transaction
        )

        if not eligibility["eligible"]:
            return {
                "success": False,
                "message": eligibility["message"],
            }

        refund_request = RefundRequest.objects.create(
            user=user,
            payment_transaction=payment_transaction,
            reason=reason.strip(),
            status=RefundRequest.PENDING,
        )
        LoggingService.create_audit_log(
            admin=user,
            actor_type="USER",
            action="REFUND_REQUEST_CREATED",
            target_type="RefundRequest",
            target_id=refund_request.id,
            description=(
                f"Refund request #{refund_request.id} was created "
                f"for payment transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "refund_request_id": refund_request.id,
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
                "reason": refund_request.reason,
            },
        )

        return {
            "success": True,
            "message": "Refund request submitted successfully.",
            "refund_request_id": refund_request.id,
            "payment_transaction_id": payment_transaction.id,
            "status": refund_request.status,
            "refund_deadline": eligibility["refund_deadline"],
        }
    @staticmethod
    def get_razorpay_client():
        return razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

    @staticmethod
    def _get_period_end(start, plan):
        if plan.billing_interval == SubscriptionPlan.MONTHLY:
            return start + timedelta(days=30)

        return start + timedelta(days=365)
    @staticmethod
    def create_payment_transaction(
        user,
        plan,
        transaction_type=PaymentTransaction.SUBSCRIPTION,
        payment_gateway="",
    ):
        payment_transaction = PaymentTransaction.objects.create(
            user=user,
            plan=plan,
            subscription=None,
            amount=plan.price,
            currency=plan.currency,
            payment_gateway=payment_gateway,
            status=PaymentTransaction.PENDING,
            transaction_type=transaction_type,
        )

        PaymentService.detect_suspicious_transaction(
            payment_transaction
        )

        return payment_transaction
    @staticmethod
    def detect_suspicious_transaction(payment_transaction):
        """
        Detect suspicious payment activity based on:
        1. 3 or more failed transactions by the same user
           within the last 1 hour.
        2. 2 or more pending transactions by the same user
           for the same plan.
        """

        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)

        suspicious_reasons = []

        # --------------------------------------------------
        # Rule 1: Repeated payment failures
        # --------------------------------------------------

        failed_transaction_count = (
            PaymentTransaction.objects.filter(
                user=payment_transaction.user,
                status=PaymentTransaction.FAILED,
                created_at__gte=one_hour_ago,
                created_at__lte=now,
            )
            .count()
        )

        if failed_transaction_count >= 3:
            suspicious_reasons.append(
                "Repeated payment failures: "
                f"{failed_transaction_count} failed transactions "
                "within the last 1 hour."
            )

        # --------------------------------------------------
        # Rule 2: Multiple pending transactions
        # --------------------------------------------------

        pending_transaction_count = (
            PaymentTransaction.objects.filter(
                user=payment_transaction.user,
                plan=payment_transaction.plan,
                status=PaymentTransaction.PENDING,
            )
            .count()
        )

        if pending_transaction_count >= 2:
            suspicious_reasons.append(
                "Multiple pending transactions: "
                f"{pending_transaction_count} pending transactions "
                "for the same user and plan."
            )

        # --------------------------------------------------
        # No suspicious activity detected
        # --------------------------------------------------

        if not suspicious_reasons:
            return {
                "success": True,
                "suspicious": False,
                "reasons": [],
            }

        # --------------------------------------------------
        # Prevent duplicate audit logs for the same
        # suspicious transaction.
        # --------------------------------------------------

        existing_audit_log = AuditLog.objects.filter(
            action="SUSPICIOUS_TRANSACTION",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
        ).exists()

        if existing_audit_log:
            return {
                "success": True,
                "suspicious": True,
                "reasons": suspicious_reasons,
                "payment_transaction_id": payment_transaction.id,
                "audit_log_created": False,
            }

        # --------------------------------------------------
        # Create financial audit log
        # --------------------------------------------------

        LoggingService.create_audit_log(
            admin=payment_transaction.user,
            actor_type="SECURITY",
            action="SUSPICIOUS_TRANSACTION",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
            description=(
                f"Suspicious payment activity detected for "
                f"payment transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "user_id": payment_transaction.user_id,
                "plan_id": payment_transaction.plan_id,
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
                "status": payment_transaction.status,
                "transaction_type": payment_transaction.transaction_type,
                "failed_transaction_count": failed_transaction_count,
                "pending_transaction_count": pending_transaction_count,
                "reasons": suspicious_reasons,
            },
        )

        return {
            "success": True,
            "suspicious": True,
            "reasons": suspicious_reasons,
            "payment_transaction_id": payment_transaction.id,
            "audit_log_created": True,
        }
    @staticmethod
    def create_razorpay_order(payment_transaction):
        client = PaymentService.get_razorpay_client()

        amount_in_paise = int(
            payment_transaction.amount * 100
        )

        order_data = {
            "amount": amount_in_paise,
            "currency": payment_transaction.currency,
            "receipt": f"payment_{payment_transaction.id}",
        }

        razorpay_order = client.order.create(
            data=order_data
        )

        payment_transaction.payment_gateway = "Razorpay"
        payment_transaction.gateway_order_id = (
            razorpay_order["id"]
        )

        payment_transaction.save(
            update_fields=[
                "payment_gateway",
                "gateway_order_id",
                "updated_at",
            ]
        )

        return razorpay_order
    @staticmethod
    def create_razorpay_refund(payment_transaction):
        if payment_transaction.status != PaymentTransaction.SUCCESS:
            return {
                "success": False,
                "message": "Only successful payments can be refunded.",
            }

        if payment_transaction.payment_gateway != "Razorpay":
            return {
                "success": False,
                "message": "This payment was not processed through Razorpay.",
            }

        if not payment_transaction.gateway_transaction_id:
            return {
                "success": False,
                "message": "Razorpay payment ID is missing.",
            }

        # Prevent duplicate refund requests while a previous refund is
        # already pending or has already been processed.
        if payment_transaction.razorpay_refund_id:
            return {
                "success": False,
                "message": "A Razorpay refund has already been initiated for this payment.",
                "payment_transaction_id": payment_transaction.id,
                "razorpay_payment_id": payment_transaction.gateway_transaction_id,
                "razorpay_refund_id": payment_transaction.razorpay_refund_id,
            }

        client = PaymentService.get_razorpay_client()

        try:
            razorpay_refund = client.payment.refund(
                payment_transaction.gateway_transaction_id,
                {
                    "amount": int(payment_transaction.amount * 100),
                },
            )
        except Exception as exc:
            return {
                "success": False,
                "message": "Unable to create Razorpay refund.",
                "error": str(exc),
            }

        refund_id = razorpay_refund.get("id")

        if not refund_id:
            return {
                "success": False,
                "message": "Razorpay did not return a refund ID.",
            }

        payment_transaction.razorpay_refund_id = refund_id
        payment_transaction.save(
            update_fields=["razorpay_refund_id", "updated_at"]
        )

        LoggingService.create_audit_log(
            admin=payment_transaction.user,
            actor_type="USER",
            action="REFUND_INITIATED",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
            description=(
                f"Razorpay refund initiated for payment "
                f"transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "razorpay_payment_id": (
                    payment_transaction.gateway_transaction_id
                ),
                "razorpay_refund_id": refund_id,
                "refund_status": razorpay_refund.get("status"),
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
            },
        )

        return {
            "success": True,
            "message": "Razorpay refund initiated successfully.",
            "payment_transaction_id": payment_transaction.id,
            "razorpay_payment_id": payment_transaction.gateway_transaction_id,
            "razorpay_refund_id": refund_id,
            "refund_status": razorpay_refund.get("status"),
        }
    @staticmethod
    def verify_razorpay_payment(
        payment_transaction,
        razorpay_payment_id,
        razorpay_order_id,
        razorpay_signature,
    ):
        if payment_transaction.status != PaymentTransaction.PENDING:
            return {
                "success": False,
                "message": "Payment transaction cannot be verified.",
            }

        if payment_transaction.gateway_order_id != razorpay_order_id:
            return {
                "success": False,
                "message": "Razorpay order ID does not match the payment transaction.",
            }

        client = PaymentService.get_razorpay_client()

        # ----------------------------------------
        # Step 1: Verify Razorpay signature
        # ----------------------------------------

        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
        except razorpay.errors.SignatureVerificationError:
            return {
                "success": False,
                "message": "Razorpay payment signature verification failed.",
            }

        # ----------------------------------------
        # Step 2: Fetch payment directly from Razorpay
        # ----------------------------------------

        try:
            razorpay_payment = client.payment.fetch(
                razorpay_payment_id
            )
        except Exception:
            return {
                "success": False,
                "message": "Unable to fetch payment details from Razorpay.",
            }

        # ----------------------------------------
        # Step 3: Verify payment belongs to
        #         the expected Razorpay order
        # ----------------------------------------

        if razorpay_payment.get("order_id") != razorpay_order_id:
            return {
                "success": False,
                "message": "Razorpay payment does not belong to the expected order.",
            }

        # ----------------------------------------
        # Step 4: Verify payment amount
        # ----------------------------------------

        expected_amount = int(
            payment_transaction.amount * 100
        )

        if razorpay_payment.get("amount") != expected_amount:
            return {
                "success": False,
                "message": "Razorpay payment amount does not match the transaction amount.",
            }

        # ----------------------------------------
        # Step 5: Verify payment currency
        # ----------------------------------------

        if razorpay_payment.get("currency") != payment_transaction.currency:
            return {
                "success": False,
                "message": "Razorpay payment currency does not match the transaction currency.",
            }

        # ----------------------------------------
        # Step 6: Verify payment was captured
        # ----------------------------------------

        if razorpay_payment.get("status") != "captured":
            return {
                "success": False,
                "message": "Razorpay payment has not been captured.",
            }

        if not razorpay_payment.get("captured"):
            return {
                "success": False,
                "message": "Razorpay payment is not marked as captured.",
            }

        # ----------------------------------------
        # Step 7: Mark local payment as successful
        # ----------------------------------------

        result = PaymentService.handle_successful_payment(
            transaction_id=payment_transaction.id,
            gateway_transaction_id=razorpay_payment_id,
        )

        return result
    @staticmethod
    @transaction.atomic
    def handle_failed_payment(
        transaction_id,
    ):
        payment_transaction = (
            PaymentTransaction.objects
            .select_for_update()
            .get(id=transaction_id)
        )

        if payment_transaction.status == PaymentTransaction.FAILED:
            return {
                "success": True,
                "message": "Payment was already marked as failed.",
                "payment_transaction_id": payment_transaction.id,
            }

        if payment_transaction.status != PaymentTransaction.PENDING:
            return {
                "success": False,
                "message": "Payment transaction cannot be marked as failed.",
            }

        payment_transaction.status = PaymentTransaction.FAILED

        payment_transaction.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        LoggingService.create_audit_log(
            admin=payment_transaction.user,
            actor_type="SYSTEM",
            action="PAYMENT_FAILED",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
            description=(
                f"Payment failed for payment "
                f"transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "gateway_order_id": payment_transaction.gateway_order_id,
                "gateway_transaction_id": (
                    payment_transaction.gateway_transaction_id
                ),
                "payment_gateway": payment_transaction.payment_gateway,
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
            },
        )

        PaymentService.detect_suspicious_transaction(
            payment_transaction
        )

        return {
            "success": True,
            "message": "Payment marked as failed.",
            "payment_transaction_id": payment_transaction.id,
        }
    @staticmethod
    @transaction.atomic
    def handle_refund(transaction_id, razorpay_refund_id=None):
        payment_transaction = (
            PaymentTransaction.objects
            .select_for_update()
            .get(id=transaction_id)
        )

        if payment_transaction.status == PaymentTransaction.REFUNDED:
            return {
                "success": True,
                "message": "Payment was already refunded.",
                "payment_transaction_id": payment_transaction.id,
                "razorpay_refund_id": payment_transaction.razorpay_refund_id,
            }

        if payment_transaction.status != PaymentTransaction.SUCCESS:
            return {
                "success": False,
                "message": "Only successful payments can be refunded.",
            }

        if razorpay_refund_id:
            payment_transaction.razorpay_refund_id = razorpay_refund_id

        payment_transaction.status = PaymentTransaction.REFUNDED

        payment_transaction.save(
            update_fields=[
                "status",
                "razorpay_refund_id",
                "updated_at",
            ]
        )

        BillingHistory.objects.filter(
            payment_transaction=payment_transaction,
            status=BillingHistory.PAID,
        ).update(
            status=BillingHistory.REFUNDED
        )

        refund_request = (
            RefundRequest.objects
            .filter(
                payment_transaction=payment_transaction,
                status=RefundRequest.PROCESSING,
            )
            .first()
        )

        if refund_request:
            refund_request.status = RefundRequest.COMPLETED
            refund_request.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

        subscription = payment_transaction.subscription

        if subscription:
            subscription.status = UserSubscription.CANCELLED
            subscription.cancelled_at = timezone.now()
            subscription.save(
                update_fields=[
                    "status",
                    "cancelled_at",
                    "updated_at",
                ]
            )

        LoggingService.create_audit_log(
            admin=payment_transaction.user,
            actor_type="SYSTEM",
            action="REFUND_COMPLETED",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
            description=(
                f"Refund completed for payment "
                f"transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "refund_request_id": (
                    refund_request.id
                    if refund_request
                    else None
                ),
                "razorpay_payment_id": (
                    payment_transaction.gateway_transaction_id
                ),
                "razorpay_refund_id": (
                    payment_transaction.razorpay_refund_id
                ),
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
                "subscription_id": (
                    subscription.id
                    if subscription
                    else None
                ),
            },
        )

        return {
            "success": True,
            "message": "Payment refunded and subscription cancelled.",
            "payment_transaction_id": payment_transaction.id,
            "razorpay_refund_id": payment_transaction.razorpay_refund_id,
            "subscription_id": (
                subscription.id
                if subscription
                else None
            ),
            "refund_request_id": (
                refund_request.id
                if refund_request
                else None
            ),
        }
    
    @staticmethod
    @transaction.atomic
    def handle_failed_refund(
        transaction_id,
    ):
        payment_transaction = (
            PaymentTransaction.objects
            .select_for_update()
            .get(id=transaction_id)
        )

        if payment_transaction.status == PaymentTransaction.REFUNDED:
            return {
                "success": False,
                "message": "Payment has already been refunded.",
                "payment_transaction_id": payment_transaction.id,
            }

        if payment_transaction.status != PaymentTransaction.SUCCESS:
            return {
                "success": False,
                "message": "Only successful payments can have a failed refund.",
            }

        LoggingService.create_audit_log(
            admin=payment_transaction.user,
            actor_type="SYSTEM",
            action="REFUND_FAILED",
            target_type="PaymentTransaction",
            target_id=payment_transaction.id,
            description=(
                f"Razorpay refund failed for payment "
                f"transaction #{payment_transaction.id}."
            ),
            metadata={
                "payment_transaction_id": payment_transaction.id,
                "razorpay_payment_id": (
                    payment_transaction.gateway_transaction_id
                ),
                "razorpay_refund_id": (
                    payment_transaction.razorpay_refund_id
                ),
                "amount": str(payment_transaction.amount),
                "currency": payment_transaction.currency,
            },
        )

        return {
            "success": True,
            "message": "Refund failure recorded. Payment remains successful.",
            "payment_transaction_id": payment_transaction.id,
        }
    @staticmethod
    @transaction.atomic
    def handle_successful_payment(
        transaction_id,
        gateway_transaction_id="",
    ):
        # ----------------------------------------
        # Lock the user first.
        #
        # This prevents two simultaneous successful
        # payments for the same user from creating
        # duplicate active subscriptions.
        # ----------------------------------------

        payment_transaction = (
            PaymentTransaction.objects
            .select_related("user")
            .get(id=transaction_id)
        )

        locked_user = (
            CustomUser.objects
            .select_for_update()
            .get(id=payment_transaction.user_id)
        )

        # ----------------------------------------
        # Lock the payment transaction after the
        # user row has been locked.
        # ----------------------------------------

        payment_transaction = (
            PaymentTransaction.objects
            .select_for_update()
            .select_related("plan")
            .get(id=transaction_id)
        )

        if payment_transaction.status == PaymentTransaction.SUCCESS:
            return {
                "success": True,
                "message": "Payment was already processed.",
                "payment_transaction_id": payment_transaction.id,
            }

        if payment_transaction.status != PaymentTransaction.PENDING:
            return {
                "success": False,
                "message": "Payment transaction cannot be completed.",
            }

        plan = payment_transaction.plan
        now = timezone.now()

        # ----------------------------------------
        # Initial subscription payment
        # ----------------------------------------

        if payment_transaction.transaction_type == PaymentTransaction.SUBSCRIPTION:

            # ----------------------------------------
            # Check for an existing usable subscription
            # for the same user and same plan.
            #
            # ACTIVE, TRIALING and PAST_DUE subscriptions
            # can be reused.
            #
            # PAST_DUE is important because a successful
            # payment during the grace period should
            # reactivate the existing subscription instead
            # of creating a duplicate subscription.
            # ----------------------------------------

            subscription = (
                UserSubscription.objects
                .select_for_update()
                .filter(
                    user=locked_user,
                    plan=plan,
                    status__in=[
                        UserSubscription.ACTIVE,
                        UserSubscription.TRIALING,
                        UserSubscription.PAST_DUE,
                    ],
                )
                .order_by("-current_period_end")
                .first()
            )

            if subscription:
                # ----------------------------------------
                # Continue from the existing period end
                # when it is still in the future.
                #
                # If the subscription is already past its
                # period end, start the new period now.
                # ----------------------------------------

                billing_period_start = max(
                    now,
                    subscription.current_period_end,
                )

                billing_period_end = PaymentService._get_period_end(
                    billing_period_start,
                    plan,
                )

                subscription.status = UserSubscription.ACTIVE
                subscription.current_period_start = (
                    billing_period_start
                )
                subscription.current_period_end = (
                    billing_period_end
                )
                subscription.grace_period_end = None
                subscription.cancelled_at = None

                subscription.save(
                    update_fields=[
                        "status",
                        "current_period_start",
                        "current_period_end",
                        "grace_period_end",
                        "cancelled_at",
                        "updated_at",
                    ]
                )

                message = (
                    "Payment processed and existing subscription extended."
                )

            else:
                # ----------------------------------------
                # No usable subscription exists.
                # Create a new subscription.
                # ----------------------------------------

                billing_period_start = now

                billing_period_end = PaymentService._get_period_end(
                    billing_period_start,
                    plan,
                )

                subscription = UserSubscription.objects.create(
                    user=locked_user,
                    plan=plan,
                    status=UserSubscription.ACTIVE,
                    started_at=now,
                    current_period_start=billing_period_start,
                    current_period_end=billing_period_end,
                )

                message = (
                    "Payment processed and subscription activated."
                )

        # ----------------------------------------
        # Subscription renewal
        # ----------------------------------------

        elif payment_transaction.transaction_type == PaymentTransaction.RENEWAL:

            subscription = (
                UserSubscription.objects
                .select_for_update()
                .filter(
                    user=locked_user,
                    plan=plan,
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
                return {
                    "success": False,
                    "message": "No existing subscription found for renewal.",
                }

            # Continue from the existing period end when possible.
            # If the subscription has already expired, start
            # the renewed period now.
            billing_period_start = max(
                now,
                subscription.current_period_end,
            )

            billing_period_end = PaymentService._get_period_end(
                billing_period_start,
                plan,
            )

            subscription.status = UserSubscription.ACTIVE
            subscription.current_period_start = billing_period_start
            subscription.current_period_end = billing_period_end
            subscription.grace_period_end = None
            subscription.cancelled_at = None

            subscription.save(
                update_fields=[
                    "status",
                    "current_period_start",
                    "current_period_end",
                    "grace_period_end",
                    "cancelled_at",
                    "updated_at",
                ]
            )

            message = "Payment processed and subscription renewed."

        else:
            return {
                "success": False,
                "message": "Unsupported payment transaction type.",
            }

        # ----------------------------------------
        # Mark payment as successful
        # ----------------------------------------

        payment_transaction.subscription = subscription
        payment_transaction.status = PaymentTransaction.SUCCESS
        payment_transaction.gateway_transaction_id = (
            gateway_transaction_id
        )

        payment_transaction.save(
            update_fields=[
                "subscription",
                "status",
                "gateway_transaction_id",
                "updated_at",
            ]
        )

        # ----------------------------------------
        # Create billing history
        # ----------------------------------------

        BillingHistory.objects.create(
            user=locked_user,
            subscription=subscription,
            plan=plan,
            amount=payment_transaction.amount,
            currency=payment_transaction.currency,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            status=BillingHistory.PAID,
            payment_transaction=payment_transaction,
        )

        return {
            "success": True,
            "message": message,
            "payment_transaction_id": payment_transaction.id,
            "subscription_id": subscription.id,
        }
        