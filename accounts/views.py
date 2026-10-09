from rest_framework import (
    generics,
    serializers,
    status,
)
import hashlib
import json
import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .filters import JobFilter
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser
from .utils.resume_parser import extract_resume_text
from .utils.resume_nlp import parse_resume_data

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth


#ats
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)

from accounts.services.ai_answer_evaluation import AIAnswerEvaluationService
from .services.ats_ranking import get_ranked_candidates
from .services.candidate_success_report import get_candidate_success_report
from .services.ats_scoring import calculate_and_save_ats_score
from .services.batch_processing import process_pending_applications
from accounts.services.ai_call_scheduler import (
    process_scheduled_ai_calls,
)
from accounts.services.ai_call_result_service import (
    complete_ai_call,
)
from accounts.services.ai_call_retry_service import (
    handle_missed_ai_call,
)
from accounts.services.ai_screening_report_service import (
    save_ai_screening_report,
)
from accounts.services.scheduled_interview import (
    ScheduledInterviewService,
)


from accounts.services.recruiter_analytics import RecruiterAnalyticsService
from .services.interview_reminder import InterviewReminderService
from .services.ai_candidate_report import AICandidateReportService
from accounts.services.subscription_service import SubscriptionService
from accounts.services.payment_service import PaymentService

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.exceptions import PermissionDenied
from django.conf import settings

from accounts.tasks import send_email_task

from django.shortcuts import (
    get_object_or_404,
    render,
)
from django.http import FileResponse
from django.db.models import Q, Count

from .serializers import (
    RegisterSerializer,
    CandidateProfileSerializer,
    PublicCandidateProfileSerializer,
    EmployerProfileSerializer,
    PublicEmployerProfileSerializer,
    JobSerializer,
    ApplicationSerializer,
    ApplicationStatusSerializer,
    CandidateDashboardSerializer,
    SavedJobSerializer,
    EmployerCandidateReviewSerializer,
    AIInterviewConfigSerializer,
    InterviewScheduleSerializer,
)

from .permissions import (
    IsAdmin,
    IsEmployer,
    IsCandidate,
    HasAdvancedAnalyticsAccess,
    HasAIInterviewAccess,
    HasAIInterviewReportsAccess,
    HasAIAnswerEvaluationAccess,
    HasEnterpriseReportsAccess,
)
from .throttles import PremiumUserRateThrottle
from .models import (
    CandidateProfile,
    EmployerProfile,
    CustomUser,
    Job,
    Application,
    ApplicationResumeParse,
    SavedJob,
    AuditLog,
    ResumeParse,
    Notification,
    EmailLog,
    AIInterviewConfig,
    AICall,
    InterviewSchedule,
    AIScreeningReport,
    AIInterviewAnswer,
    AIAnswerEvaluation,
    AICandidateReport,
    PaymentTransaction,
    SubscriptionPlan,
    UserSubscription,
    RefundRequest,
    ScheduledInterviewSession,
)


# ----------------------------
# Authentication APIs
# ----------------------------

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer


class LoginView(TokenObtainPairView):
    pass


# ----------------------------
# Role Based APIs
# ----------------------------

class AdminView(APIView):

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response({
            "message": f"Welcome Admin {request.user.username}"
        })


class EmployerView(APIView):

    permission_classes = [IsAuthenticated, IsEmployer]

    def get(self, request):
        return Response({
            "message": f"Welcome Employer {request.user.username}"
        })


class CandidateView(APIView):

    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):
        return Response({
            "message": f"Welcome Candidate {request.user.username}"
        })


# ----------------------------
# Reusable Mixins
# ----------------------------

class CandidateProfileMixin:
    def get_object(self):
        return get_object_or_404(
            CandidateProfile,
            user=self.request.user,
            is_deleted=False,
        )


class EmployerProfileMixin:

    def get_object(self):
        return EmployerProfile.objects.get(user=self.request.user)


# ----------------------------
# Candidate Profile APIs
# ----------------------------

class CandidateProfileCreateView(generics.CreateAPIView):

    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated, IsCandidate]

    parser_classes = (
        MultiPartParser,
        FormParser,
    )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ----------------------------
# Protected Candidate Resume API
# ----------------------------

class CandidateResumeDownloadView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get(self, request):

        # --------------------------------
        # Get the authenticated candidate
        # --------------------------------

        candidate = get_object_or_404(
            CandidateProfile,
            user=request.user,
            is_deleted=False,
        )

        # --------------------------------
        # Check whether resume exists
        # --------------------------------

        if not candidate.resume:

            return Response(
                {
                    "success": False,
                    "message":
                    "No resume found for this candidate.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------
        # Return protected resume file
        # --------------------------------

        return FileResponse(
            candidate.resume.open("rb"),
            as_attachment=True,
            filename=candidate.resume.name.split("/")[-1],
        )

class CandidateProfileDetailView(
    CandidateProfileMixin,
    generics.RetrieveAPIView,
):

    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated, IsCandidate]


class CandidateProfileUpdateView(
    CandidateProfileMixin,
    generics.UpdateAPIView,
):

    serializer_class = CandidateProfileSerializer
    permission_classes = [IsAuthenticated, IsCandidate]

    parser_classes = (
        MultiPartParser,
        FormParser,
    )


class CandidateProfileDeleteView(
    CandidateProfileMixin,
    generics.DestroyAPIView,
):

    permission_classes = [IsAuthenticated, IsCandidate]

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


# ----------------------------
# Candidate List API
# ----------------------------

class CandidateListView(generics.ListAPIView):

    serializer_class = (
        PublicCandidateProfileSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsEmployer | IsAdmin,
    ]

    queryset = (
        CandidateProfile.objects
        .select_related("user")
        .filter(
            is_deleted=False
        )
         .order_by("id")
    )

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "experience",
    ]

    search_fields = [
        "skills",
        "education",
        "user__username",
    ]

    ordering_fields = [
        "experience",
    ]

# ----------------------------
# Employer Profile APIs
# ----------------------------

class EmployerProfileCreateView(generics.CreateAPIView):

    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated, IsEmployer]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class JobCreateView(generics.CreateAPIView):

    serializer_class = JobSerializer
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def perform_create(self, serializer):

        employer_profile = EmployerProfile.objects.get(
            user=self.request.user
        )

        if not SubscriptionService.can_post_job(
            self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Your active subscription does not allow you to post another job."
            )

        serializer.save(
            employer=employer_profile
        )

class JobUpdateView(generics.UpdateAPIView):

    serializer_class = JobSerializer
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def get_object(self):

        employer_profile = EmployerProfile.objects.get(
            user=self.request.user
        )

        return get_object_or_404(
            Job,
            id=self.kwargs["pk"],
            employer=employer_profile,
        )

class JobStatusUpdateView(generics.UpdateAPIView):

    serializer_class = JobSerializer
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def get_object(self):

        employer_profile = EmployerProfile.objects.get(
            user=self.request.user
        )

        return get_object_or_404(
            Job,
            id=self.kwargs["pk"],
            employer=employer_profile,
        )

    def patch(self, request, *args, **kwargs):

        job = self.get_object()

        status = request.data.get("status")

        if status not in [Job.ACTIVE, Job.CLOSED]:
            return Response(
                {
                    "error": "Status must be Active or Closed."
                },
                status=400,
            )

        job.status = status
        job.save()

        serializer = self.get_serializer(job)

        return Response(serializer.data)
# ----------------------------
# Public Job Listing APIs
# ----------------------------

class JobListView(generics.ListAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_class = JobFilter

    search_fields = [
        "title",
        "description",
        "skills",
        "location",
    ]

    ordering_fields = [
        "created_at",
        "salary_min",
        "salary_max",
        "experience",
    ]
    def get_queryset(self):

        allowed_employer_ids = (
            SubscriptionService
            .get_employer_ids_with_candidate_capacity()
        )

        return (
            Job.objects
            .select_related(
                "employer",
                "employer__user",
            )
            .filter(
                status=Job.ACTIVE,
                employer_id__in=allowed_employer_ids,
            )
            .order_by("-created_at")
        )
    
# ----------------------------
# APPLY JOB APIs
# ----------------------------
class ApplyJobView(generics.CreateAPIView):

    serializer_class = ApplicationSerializer

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]
    def perform_create(self, serializer):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        job = get_object_or_404(
            Job,
            pk=self.kwargs["job_id"],
        )

        # ----------------------------------------
        # Check job status
        # ----------------------------------------

        if job.status != Job.ACTIVE:

            raise serializers.ValidationError(
                {
                    "detail":
                    "This job is no longer accepting applications."
                }
            )

        # ----------------------------------------
        # Prevent duplicate application
        # ----------------------------------------

        if Application.objects.filter(
            candidate=candidate,
            job=job,
        ).exists():

            raise serializers.ValidationError(
                {
                    "detail":
                    "You have already applied for this job."
                }
            )

        # ----------------------------------------
        # Determine resume
        #
        # If a new resume is uploaded,
        # use it.
        #
        # Otherwise use the candidate's
        # current profile resume.
        # ----------------------------------------

        uploaded_resume = self.request.FILES.get(
            "resume"
        )

        if uploaded_resume:

            resume_file = uploaded_resume

        else:

            resume_file = candidate.resume

        # ----------------------------------------
        # Resume is required
        # ----------------------------------------

        if not resume_file:

            raise serializers.ValidationError(
                {
                    "detail":
                    "Please upload a resume or add a resume to your profile before applying."
                }
            )

        # ----------------------------------------
        # Determine file type
        # ----------------------------------------

        filename = resume_file.name.lower()

        if filename.endswith(".pdf"):

            file_type = "pdf"

        elif filename.endswith(".docx"):

            file_type = "docx"

        else:

            raise serializers.ValidationError(
                {
                    "detail":
                    "Only PDF and DOCX resumes are supported."
                }
            )

        # ----------------------------------------
        # Parse the resume that will actually
        # be submitted with this application
        # ----------------------------------------

        try:

            raw_text, cleaned_text = extract_resume_text(
                resume_file,
                file_type,
            )

            parsed_data = parse_resume_data(
                cleaned_text
            )

        except Exception:
            raise serializers.ValidationError(
                {
                    "detail":
                    "Unable to parse the submitted resume. "
                    "Please check your file and try again."
                }
            )

        # ----------------------------------------
        # Candidate access limit + application
        #
        # Lock the employer row so concurrent
        # applications for the same employer
        # cannot pass the quota check together.
        # ----------------------------------------

        with transaction.atomic():

            employer = (
                EmployerProfile.objects
                .select_for_update()
                .get(
                    pk=job.employer_id
                )
            )

            accessible_candidate_user_ids = (
                SubscriptionService
                .get_accessible_candidate_user_ids(
                    employer.user
                )
            )

            candidate_user_id = candidate.user_id

            if (
                candidate_user_id
                not in accessible_candidate_user_ids
            ):

                subscription = (
                    SubscriptionService
                    .get_active_subscription(
                        employer.user
                    )
                )

                if not subscription:

                    raise serializers.ValidationError(
                        {
                            "detail":
                            "The employer does not have an active subscription."
                        }
                    )

                candidate_limit = (
                    subscription.plan.candidate_access_limit
                )

                if (
                    candidate_limit is not None
                    and len(accessible_candidate_user_ids)
                    >= candidate_limit
                ):

                    raise serializers.ValidationError(
                        {
                            "detail":
                            "This employer has reached the maximum number of candidates allowed by their subscription plan."
                        }
                    )

            # ----------------------------------------
            # Create application
            # ----------------------------------------

            application = serializer.save(
                candidate=candidate,
                job=job,
                resume_snapshot=resume_file,
            )

        # ----------------------------------------
        # Store application-specific parsed resume
        # ----------------------------------------

        ApplicationResumeParse.objects.create(
            application=application,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            parsed_data=parsed_data,
        )

        # ----------------------------------------
        # Calculate ATS score
        # ----------------------------------------

        calculate_and_save_ats_score(
            job,
            application,
        )

        # ----------------------------------------
        # Send application submitted email
        # ----------------------------------------

        email_log = EmailLog.objects.create(
            recipient_email=candidate.user.email,
            subject="Application Submitted Successfully",
            template_name="emails/application_submitted.txt",
            context={
                "candidate_name": candidate.user.username,
                "job_title": job.title,
            },
            status=EmailLog.PENDING,
        )

        send_email_task.delay(
            email_log.id
        )
    
class FeaturedJobListView(generics.ListAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        allowed_employer_ids = (
            SubscriptionService
            .get_employer_ids_with_candidate_capacity()
        )

        return (
            Job.objects
            .select_related(
                "employer",
                "employer__user",
            )
            .filter(
                status=Job.ACTIVE,
                employer_id__in=allowed_employer_ids,
            )
            .order_by("-salary_max")[:5]
        )

class LatestJobListView(generics.ListAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        allowed_employer_ids = (
            SubscriptionService
            .get_employer_ids_with_candidate_capacity()
        )

        return (
            Job.objects
            .select_related(
                "employer",
                "employer__user",
            )
            .filter(
                status=Job.ACTIVE,
                employer_id__in=allowed_employer_ids,
            )
            .order_by("-created_at")[:10]
        )

class EmployerProfileDetailView(
    EmployerProfileMixin,
    generics.RetrieveAPIView,
):

    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated, IsEmployer]


class EmployerProfileUpdateView(
    EmployerProfileMixin,
    generics.UpdateAPIView,
):

    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated, IsEmployer]


class EmployerProfileDeleteView(
    EmployerProfileMixin,
    generics.DestroyAPIView,
):

    permission_classes = [IsAuthenticated, IsEmployer]

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


# ----------------------------
# Employer List API
# ----------------------------

class EmployerListView(generics.ListAPIView):

    serializer_class = (
        PublicEmployerProfileSerializer
    )

    permission_classes = [
        IsAuthenticated,
    ]

    queryset = (
        EmployerProfile.objects
        .select_related("user")
        .filter(
            is_deleted=False
        )
        .order_by("company_name")
    )

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = [
        "company_size",
        "is_verified",
    ]

    search_fields = [
        "company_name",
        "domain",
        "user__username",
    ]

    ordering_fields = [
        "company_size",
        "company_name",
    ]
# ----------------------------
# Employer Dashboard APIs
# ----------------------------

class EmployerDashboardJobListView(generics.ListAPIView):

    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, IsEmployer]

    def get_queryset(self):

        employer = get_object_or_404(
            EmployerProfile,
            user=self.request.user,
        )

        return (
            Job.objects
            .filter(employer=employer)
            .select_related(
                "employer",
                "employer__user",
            )
            .order_by("-created_at")
        )

# ----------------------------
# Admin Approve Employer API
# ----------------------------

class AdminApproveEmployerView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def patch(self, request, pk):

        employer = get_object_or_404(
            EmployerProfile,
            pk=pk,
        )

        employer.is_verified = True
        employer.save()

        AuditLog.objects.create(
        admin=request.user,
        action="APPROVE_EMPLOYER",
        target_type="Employer",
        target_id=employer.id,
        description=f"Employer '{employer.company_name}' was approved.",
     )

        return Response(
            {
                "message": "Employer approved successfully.",
                "employer_id": employer.id,
                "company_name": employer.company_name,
                "is_verified": employer.is_verified,
            }
        )
# ----------------------------
# Admin Block User API
# ----------------------------

class AdminBlockUserView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def patch(self, request, pk):

        user = get_object_or_404(
            CustomUser,
            pk=pk,
        )

        if user.is_superuser:
            return Response(
                {
                    "message": "Superusers cannot be blocked."
                },
                status=400,
            )

        user.is_active = False
        user.save()

        AuditLog.objects.create(
        admin=request.user,
        action="BLOCK_USER",
        target_type="User",
        target_id=user.id,
        description=f"User '{user.username}' was blocked.",
        )

        return Response(
            {
                "message": "User blocked successfully.",
                "user_id": user.id,
                "username": user.username,
                "is_active": user.is_active,
            }
        )
# ----------------------------
# Admin Flag User API
# ----------------------------

class AdminFlagUserView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def patch(self, request, pk):

        user = get_object_or_404(
            CustomUser,
            pk=pk,
        )

        if user.is_superuser:
            return Response(
                {
                    "message": "Superusers cannot be flagged."
                },
                status=400,
            )

        user.is_flagged = True
        user.save()

        AuditLog.objects.create(
        admin=request.user,
        action="FLAG_USER",
        target_type="User",
        target_id=user.id,
        description=f"User '{user.username}' was flagged.",
        )

        return Response(
            {
                "message": "User flagged successfully.",
                "user_id": user.id,
                "username": user.username,
                "is_flagged": user.is_flagged,
            },
            status=200,
        )
# ----------------------------
# Admin Job Management API
# ----------------------------

class AdminManageJobView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def patch(self, request, pk):

        job = get_object_or_404(
            Job,
            pk=pk,
        )

        job.status = Job.CLOSED
        job.save()

        AuditLog.objects.create(
            admin=request.user,
            action="REMOVE_JOB",
            target_type="Job",
            target_id=job.id,
            description=f"Job '{job.title}' was removed from active listings.",
        )

        return Response(
            {
                "message": "Job removed from active listings.",
                "job_id": job.id,
                "status": job.status,
            },
            status=200,
        )
# ----------------------------
# Admin Platform Statistics API
# ----------------------------

class AdminPlatformStatsView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get(self, request):

        total_users = CustomUser.objects.count()

        total_candidates = CustomUser.objects.filter(
            role=CustomUser.CANDIDATE
        ).count()

        total_employers = CustomUser.objects.filter(
            role=CustomUser.EMPLOYER
        ).count()

        total_jobs = Job.objects.count()

        total_applications = Application.objects.count()

        active_jobs = Job.objects.filter(
            status=Job.ACTIVE
        ).count()

        blocked_users = CustomUser.objects.filter(
            is_active=False
        ).count()

        return Response(
            {
                "total_users": total_users,
                "total_candidates": total_candidates,
                "total_employers": total_employers,
                "total_jobs": total_jobs,
                "total_applications": total_applications,
                "active_jobs": active_jobs,
                "blocked_users": blocked_users,
            }
        )
# ----------------------------
# Admin User Growth API
# ----------------------------

class AdminUserGrowthView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get(self, request):

        user_growth = (
            CustomUser.objects
            .values(
                "date_joined__year",
                "date_joined__month",
                "role",
            )
            .annotate(
                total=Count("id")
            )
            .order_by(
                "date_joined__year",
                "date_joined__month",
            )
        )

        growth_data = {}

        for item in user_growth:

            year = item["date_joined__year"]
            month = item["date_joined__month"]
            role = item["role"]
            total = item["total"]

            month_key = f"{year}-{month:02d}"

            if month_key not in growth_data:

                growth_data[month_key] = {
                    "month": month_key,
                    "candidates": 0,
                    "employers": 0,
                }

            if role == CustomUser.CANDIDATE:

                growth_data[month_key]["candidates"] = total

            elif role == CustomUser.EMPLOYER:

                growth_data[month_key]["employers"] = total

        return Response(
            {
                "user_growth": list(
                    growth_data.values()
                )
            }
        )
# ----------------------------
# Admin Job Activity API
# ----------------------------

class AdminJobActivityView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get(self, request):

        total_jobs = Job.objects.count()

        active_jobs = Job.objects.filter(
            status=Job.ACTIVE
        ).count()

        closed_jobs  = Job.objects.filter(
            status=Job.CLOSED
        ).count()

        job_activity = (
            Job.objects
            .values(
                "created_at__year",
                "created_at__month",
            )
            .annotate(
                total=Count("id")
            )
            .order_by(
                "created_at__year",
                "created_at__month",
            )
        )

        monthly_activity = []

        for item in job_activity:

            year = item["created_at__year"]
            month = item["created_at__month"]

            monthly_activity.append({
                "month": f"{year}-{month:02d}",
                "jobs_created": item["total"],
            })

        return Response({
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "closed_jobs": closed_jobs,
            "monthly_activity": monthly_activity,
        })
# ----------------------------
# Admin Audit Log API
# ----------------------------

class AdminAuditLogView(generics.ListAPIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get_queryset(self):

        queryset = (
            AuditLog.objects
            .select_related("admin")
            .order_by("-created_at")
        )

        actor_type = self.request.query_params.get(
            "actor_type"
        )

        action = self.request.query_params.get(
            "action"
        )

        target_type = self.request.query_params.get(
            "target_type"
        )

        if actor_type:
            queryset = queryset.filter(
                actor_type=actor_type
            )

        if action:
            queryset = queryset.filter(
                action=action
            )

        if target_type:
            queryset = queryset.filter(
                target_type=target_type
            )

        return queryset

    def list(self, request, *args, **kwargs):

        audit_logs = self.get_queryset()

        data = []

        for log in audit_logs:

            data.append({
                "id": log.id,

                "actor_type": log.actor_type,

                "admin": (
                    log.admin.username
                    if log.admin
                    else "System"
                ),

                "action": log.action,

                "target_type": log.target_type,

                "target_id": log.target_id,

                "description": log.description,

                "ip_address": log.ip_address,

                "metadata": log.metadata,

                "created_at": log.created_at,
            })

        return Response({
            "audit_logs": data
        })
# ----------------------------
# Admin Billing Transactions API
# ----------------------------

class AdminBillingTransactionView(generics.ListAPIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get_queryset(self):

        queryset = (
            PaymentTransaction.objects
            .select_related(
                "user",
                "plan",
                "subscription",
            )
            .order_by("-created_at")
        )

        status_filter = self.request.query_params.get(
            "status"
        )

        transaction_type = self.request.query_params.get(
            "transaction_type"
        )

        user_id = self.request.query_params.get(
            "user_id"
        )

        plan_id = self.request.query_params.get(
            "plan_id"
        )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        if transaction_type:
            queryset = queryset.filter(
                transaction_type=transaction_type
            )

        if user_id:
            queryset = queryset.filter(
                user_id=user_id
            )

        if plan_id:
            queryset = queryset.filter(
                plan_id=plan_id
            )

        return queryset

    def list(self, request, *args, **kwargs):

        transactions = self.get_queryset()

        data = []

        for transaction in transactions:

            data.append({
                "id": transaction.id,

                "user": (
                    transaction.user.username
                    if transaction.user
                    else None
                ),

                "plan": (
                    transaction.plan.name
                    if transaction.plan
                    else None
                ),

                "amount": transaction.amount,

                "currency": transaction.currency,

                "payment_gateway": transaction.payment_gateway,

                "gateway_order_id": (
                    transaction.gateway_order_id
                ),

                "gateway_transaction_id": (
                    transaction.gateway_transaction_id
                ),

                "status": transaction.status,

                "transaction_type": (
                    transaction.transaction_type
                ),

                "created_at": transaction.created_at,

                "updated_at": transaction.updated_at,
            })

        return Response({
            "transactions": data
        })
# ----------------------------
# Admin Billing Subscriptions API
# ----------------------------

class AdminBillingSubscriptionView(generics.ListAPIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get_queryset(self):

        queryset = (
            UserSubscription.objects
            .select_related(
                "user",
                "plan",
            )
            .order_by("-created_at")
        )

        status_filter = self.request.query_params.get(
            "status"
        )

        user_id = self.request.query_params.get(
            "user_id"
        )

        plan_id = self.request.query_params.get(
            "plan_id"
        )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        if user_id:
            queryset = queryset.filter(
                user_id=user_id
            )

        if plan_id:
            queryset = queryset.filter(
                plan_id=plan_id
            )

        return queryset

    def list(self, request, *args, **kwargs):

        subscriptions = self.get_queryset()

        data = []

        for subscription in subscriptions:

            data.append({
                "id": subscription.id,

                "user": (
                    subscription.user.username
                    if subscription.user
                    else None
                ),

                "plan": (
                    subscription.plan.name
                    if subscription.plan
                    else None
                ),

                "status": subscription.status,

                "started_at": subscription.started_at,

                "current_period_start": (
                    subscription.current_period_start
                ),

                "current_period_end": (
                    subscription.current_period_end
                ),

                "grace_period_end": (
                    subscription.grace_period_end
                ),

                "cancelled_at": (
                    subscription.cancelled_at
                ),

                "created_at": subscription.created_at,

                "updated_at": subscription.updated_at,
            })

        return Response({
            "subscriptions": data
        })
class AdminRefundRequestView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get(self, request):

        refund_requests = (
            RefundRequest.objects
            .select_related(
                "user",
                "payment_transaction",
                "payment_transaction__plan",
                "reviewed_by",
            )
            .order_by("-created_at")
        )

        status_filter = request.query_params.get("status")
        user_id = request.query_params.get("user_id")

        if status_filter:
            refund_requests = refund_requests.filter(
                status=status_filter
            )

        if user_id:
            refund_requests = refund_requests.filter(
                user_id=user_id
            )

        data = []

        for refund_request in refund_requests:

            payment_transaction = (
                refund_request.payment_transaction
            )

            data.append(
                {
                    "id": refund_request.id,
                    "user_id": refund_request.user_id,
                    "username": refund_request.user.username,
                    "payment_transaction_id": (
                        payment_transaction.id
                    ),
                    "amount": float(
                        payment_transaction.amount
                    ),
                    "currency": payment_transaction.currency,
                    "plan": (
                        payment_transaction.plan.name
                        if payment_transaction.plan
                        else None
                    ),
                    "reason": refund_request.reason,
                    "status": refund_request.status,
                    "reviewed_by": (
                        refund_request.reviewed_by.username
                        if refund_request.reviewed_by
                        else None
                    ),
                    "reviewed_at": refund_request.reviewed_at,
                    "admin_note": refund_request.admin_note,
                    "created_at": refund_request.created_at,
                    "updated_at": refund_request.updated_at,
                    "razorpay_refund_id": (
                        payment_transaction.razorpay_refund_id
                    ),
                }
            )

        return Response(
            {
                "success": True,
                "count": len(data),
                "refund_requests": data,
            },
            status=status.HTTP_200_OK,
        )
class AdminRefundRequestReviewView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    @transaction.atomic
    def post(self, request, refund_request_id):

        action = request.data.get("action")
        admin_note = request.data.get("admin_note", "")

        if action not in ["approve", "reject"]:
            return Response(
                {
                    "success": False,
                    "message": "action must be either approve or reject.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund_request = get_object_or_404(
            RefundRequest.objects.select_for_update(),
            id=refund_request_id,
        )

        if refund_request.status != RefundRequest.PENDING:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Only pending refund requests can be reviewed."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == "reject":

            if not admin_note.strip():
                return Response(
                    {
                        "success": False,
                        "message": (
                            "admin_note is required when rejecting "
                            "a refund request."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            refund_request.status = RefundRequest.REJECTED
            refund_request.reviewed_by = request.user
            refund_request.reviewed_at = timezone.now()
            refund_request.admin_note = admin_note.strip()

            refund_request.save(
                update_fields=[
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "admin_note",
                    "updated_at",
                ]
            )

            AuditLog.objects.create(
                admin=request.user,
                actor_type="ADMIN",
                action="REFUND_REQUEST_REJECTED",
                target_type="RefundRequest",
                target_id=refund_request.id,
                description=(
                    f"Admin rejected refund request "
                    f"#{refund_request.id}."
                ),
                ip_address=request.META.get("REMOTE_ADDR"),
                metadata={
                    "refund_request_id": refund_request.id,
                    "payment_transaction_id": (
                        refund_request.payment_transaction_id
                    ),
                    "admin_note": refund_request.admin_note,
                },
            )

            return Response(
                {
                    "success": True,
                    "message": "Refund request rejected successfully.",
                    "refund_request_id": refund_request.id,
                    "status": refund_request.status,
                },
                status=status.HTTP_200_OK,
            )

        payment_transaction = (
            refund_request.payment_transaction
        )

        refund_result = PaymentService.create_razorpay_refund(
            payment_transaction
        )

        if not refund_result["success"]:
            return Response(
                {
                    "success": False,
                    "message": refund_result["message"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund_request.status = RefundRequest.PROCESSING
        refund_request.reviewed_by = request.user
        refund_request.reviewed_at = timezone.now()

        if admin_note.strip():
            refund_request.admin_note = admin_note.strip()

        refund_request.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "admin_note",
                "updated_at",
            ]
        )

        AuditLog.objects.create(
            admin=request.user,
            actor_type="ADMIN",
            action="REFUND_REQUEST_APPROVED",
            target_type="RefundRequest",
            target_id=refund_request.id,
            description=(
                f"Admin approved refund request "
                f"#{refund_request.id}."
            ),
            ip_address=request.META.get("REMOTE_ADDR"),
            metadata={
                "refund_request_id": refund_request.id,
                "payment_transaction_id": (
                    refund_request.payment_transaction_id
                ),
                "razorpay_refund_id": (
                    payment_transaction.razorpay_refund_id
                ),
                "refund_status": (
                    refund_result.get("refund_status")
                ),
                "admin_note": refund_request.admin_note,
            },
        )

        return Response(
            {
                "success": True,
                "message": (
                    "Refund approved and Razorpay refund "
                    "initiated successfully."
                ),
                "refund_request_id": refund_request.id,
                "payment_transaction_id": payment_transaction.id,
                "status": refund_request.status,
                "razorpay_refund_id": (
                    payment_transaction.razorpay_refund_id
                ),
                "refund_status": (
                    refund_result.get("refund_status")
                ),
            },
            status=status.HTTP_200_OK,
        )
# ----------------------------
# Admin Billing Revenue API
# ----------------------------

class AdminBillingRevenueView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAdmin,
    ]

    def get(self, request):

        # ----------------------------------------
        # Revenue summary
        # ----------------------------------------

        successful_transactions = (
            PaymentTransaction.objects
            .filter(
                status=PaymentTransaction.SUCCESS
            )
        )

        refunded_transactions = (
            PaymentTransaction.objects
            .filter(
                status=PaymentTransaction.REFUNDED
            )
        )

        gross_revenue = (
            successful_transactions.aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        refunded_amount = (
            refunded_transactions.aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        net_revenue = (
            gross_revenue - refunded_amount
        )

        # ----------------------------------------
        # Daily revenue
        # ----------------------------------------

        daily_revenue = (
            successful_transactions
            .annotate(
                date=TruncDate("created_at")
            )
            .values("date")
            .annotate(
                revenue=Sum("amount"),
                transaction_count=Count("id"),
            )
            .order_by("-date")
        )

        daily_data = []

        for item in daily_revenue:

            daily_data.append({
                "date": item["date"],
                "revenue": item["revenue"],
                "transaction_count": item[
                    "transaction_count"
                ],
            })

        # ----------------------------------------
        # Monthly revenue
        # ----------------------------------------

        monthly_revenue = (
            successful_transactions
            .annotate(
                month=TruncMonth("created_at")
            )
            .values("month")
            .annotate(
                revenue=Sum("amount"),
                transaction_count=Count("id"),
            )
            .order_by("-month")
        )

        monthly_data = []

        for item in monthly_revenue:

            monthly_data.append({
                "month": item["month"],
                "revenue": item["revenue"],
                "transaction_count": item[
                    "transaction_count"
                ],
            })

        # ----------------------------------------
        # Plan-wise revenue
        # ----------------------------------------

        plan_revenue = (
            successful_transactions
            .values(
                "plan_id",
                "plan__name",
            )
            .annotate(
                revenue=Sum("amount"),
                transaction_count=Count("id"),
            )
            .order_by("-revenue")
        )

        plan_data = []

        for item in plan_revenue:

            plan_data.append({
                "plan_id": item["plan_id"],
                "plan": item["plan__name"],
                "revenue": item["revenue"],
                "transaction_count": item[
                    "transaction_count"
                ],
            })

        return Response({
            "summary": {
                "gross_revenue": gross_revenue,
                "refunded_amount": refunded_amount,
                "net_revenue": net_revenue,
            },
            "daily_revenue": daily_data,
            "monthly_revenue": monthly_data,
            "plan_wise_revenue": plan_data,
        })
# ----------------------------
# Employer Applicant List API
# ----------------------------

class EmployerApplicantListView(generics.ListAPIView):

    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    
    def get_queryset(self):

        employer = get_object_or_404(
            EmployerProfile,
            user=self.request.user,
        )

        job = get_object_or_404(
            Job,
            pk=self.kwargs["job_id"],
            employer=employer,
        )

        accessible_candidate_user_ids = (
            SubscriptionService
            .get_accessible_candidate_user_ids(
                self.request.user
            )
        )

        return (
            Application.objects
            .filter(
                job=job,
                candidate__user_id__in=accessible_candidate_user_ids,
            )
            .select_related(
                "candidate",
                "candidate__user",
                "job",
            )
            .order_by("-applied_at")
        )
    
class RecruiterJobAnalyticsView(APIView):
    permission_classes = [IsAuthenticated,HasAdvancedAnalyticsAccess,]

    def get(self, request):
        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        data = RecruiterAnalyticsService.get_job_wise_metrics(
            employer
        )

        return Response({
            "success": True,
            "jobs": data,
        })
# ----------------------------
# Employer Candidate Review API
# ----------------------------

class EmployerCandidateReviewView(
    generics.RetrieveAPIView
):

    serializer_class = (
        EmployerCandidateReviewSerializer
    )

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def get_queryset(self):

        employer = get_object_or_404(
            EmployerProfile,
            user=self.request.user,
        )

        return (
            Application.objects
            .filter(
                job__employer=employer
            )
            .select_related(
                "candidate",
                "candidate__user",
                "job",
            )
            .prefetch_related(
                "candidate__ats_scores"
            )
        )

# ----------------------------
# Application Tracking APIs
# ----------------------------

class MyApplicationsView(generics.ListAPIView):

    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsCandidate]

    def get_queryset(self):

        candidate = CandidateProfile.objects.get(
            user=self.request.user
        )

        return (
            Application.objects.select_related(
                "candidate",
                "candidate__user",
                "job",
                "job__employer",
            )
            .filter(candidate=candidate)
            .order_by("-applied_at")
        )

# ----------------------------
# Candidate Notifications API
# ----------------------------

class CandidateNotificationListView(
    generics.ListAPIView
):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get_queryset(self):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        return (
            Notification.objects
            .filter(candidate=candidate)
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):

        notifications = self.get_queryset()

        data = []

        for notification in notifications:

            data.append({
                "id": notification.id,
                "application_id": notification.application.id,
                "job": notification.application.job.title,
                "message": notification.message,
                "created_at": notification.created_at,
            })

        return Response({
            "count": notifications.count(),
            "notifications": data,
        })
# ----------------------------
# Mark Notification as Read API
# ----------------------------

class MarkNotificationAsReadView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def patch(self, request, pk):

        candidate = get_object_or_404(
            CandidateProfile,
            user=request.user,
        )

        notification = get_object_or_404(
            Notification,
            pk=pk,
            candidate=candidate,
        )

        # ----------------------------------------
        # Mark notification as read
        # ----------------------------------------

        if notification.is_read:

            return Response(
                {
                    "success": False,
                    "message":
                    "Notification is already marked as read.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        notification.is_read = True
        notification.save()

        return Response(
            {
                "success": True,
                "message":
                "Notification marked as read.",
                "notification_id": notification.id,
                "is_read": notification.is_read,
            },
            status=status.HTTP_200_OK,
        )
    
class ApplicationDetailView(generics.RetrieveAPIView):

    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated, IsCandidate]

    def get_queryset(self):

        candidate = CandidateProfile.objects.get(
            user=self.request.user
        )

        return Application.objects.select_related(
            "candidate",
            "candidate__user",
            "job",
            "job__employer",
        ).filter(
            candidate=candidate
        )

class ApplicationStatusUpdateView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def patch(self, request, pk):

        serializer = ApplicationStatusSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        application = get_object_or_404(
            Application.objects.select_related(
                "candidate",
                "candidate__user",
                "job",
                "job__employer",
                "job__employer__user",
            ),
            pk=pk,
        )

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Verify employer owns this job
        # ----------------------------------------

        if application.job.employer != employer:

            return Response(
                {
                    "detail":
                    "You are not allowed to update this application."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = serializer.validated_data["status"]
        
        # ----------------------------------------
        # Prevent unnecessary update
        # ----------------------------------------

        if application.status == new_status:

            return Response(
                {
                    "success": False,
                    "message":
                    "The application already has this status.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Employer manual override
        # ----------------------------------------

        application.status = new_status
        application.is_manual_override = True
        application.save()

        # ----------------------------------------
        # Professional notification messages
        # ----------------------------------------

        notification_messages = {

            Application.SHORTLISTED: (
                f"We are pleased to inform you that your application "
                f"for the position of '{application.job.title}' has "
                f"been shortlisted following an additional review by "
                f"the employer. You may be contacted regarding the "
                f"next steps in the selection process."
            ),

            Application.REJECTED: (
                f"Thank you for your interest in the position of "
                f"'{application.job.title}'. After further review, "
                f"we regret to inform you that your application will "
                f"not be progressing further in the selection process. "
                f"We appreciate your time and interest."
            ),

            Application.INTERVIEW: (
                f"Congratulations! Your application for "
                f"'{application.job.title}' has progressed to the "
                f"interview stage. The employer will contact you with "
                f"further details regarding the interview process."
            ),

            Application.SELECTED: (
                f"Congratulations! We are delighted to inform you "
                f"that you have been selected for the position of "
                f"'{application.job.title}'. The employer will contact "
                f"you regarding the next steps."
            ),
        }

        message = notification_messages.get(
            new_status,
            (
                f"Your application status for "
                f"'{application.job.title}' has been updated to "
                f"'{new_status}'."
            ),
        )

        # ----------------------------------------
        # Create notification
        # ----------------------------------------

        Notification.objects.create(
            candidate=application.candidate,
            application=application,
            message=message,
        )

        return Response(
            {
                "success": True,
                "message":
                "Application status updated successfully.",
                "application_id": application.id,
                "status": application.status,
                "is_manual_override":
                application.is_manual_override,
                "updated_at":
                application.status_updated_at,
            },
            status=status.HTTP_200_OK,
        )
# ----------------------------
# Save Job API
# ----------------------------

class SaveJobView(generics.CreateAPIView):

    serializer_class = SavedJobSerializer
    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def perform_create(self, serializer):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        job = get_object_or_404(
            Job,
            pk=self.kwargs["job_id"],
        )

        if SavedJob.objects.filter(
            candidate=candidate,
            job=job,
        ).exists():

            raise serializers.ValidationError(
                {
                    "detail":
                    "You have already saved this job."
                }
            )

        serializer.save(
            candidate=candidate,
            job=job,
        )
# ----------------------------
# Remove Saved Job API+
# ----------------------------

class RemoveSavedJobView(generics.DestroyAPIView):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get_object(self):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        return get_object_or_404(
            SavedJob,
            candidate=candidate,
            job_id=self.kwargs["job_id"],
        )

    def delete(self, request, *args, **kwargs):

        saved_job = self.get_object()

        saved_job.delete()

        return Response(
            {
                "message": "Job removed from saved jobs successfully."
            },
            status=200,
        )
# ----------------------------
# My Saved Jobs API
# ----------------------------

class MySavedJobsView(generics.ListAPIView):

    serializer_class = SavedJobSerializer

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get_queryset(self):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        return (
            SavedJob.objects
            .filter(candidate=candidate)
            .select_related(
                "job",
                "job__employer",
                "job__employer__user",
            )
            .order_by("-saved_at")
        )
# ----------------------------
# Job Recommendation API
# ----------------------------
class RecommendedJobsView(generics.ListAPIView):

    serializer_class = JobSerializer

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get_queryset(self):

        candidate = get_object_or_404(
            CandidateProfile,
            user=self.request.user,
        )

        allowed_employer_ids = (
            SubscriptionService
            .get_employer_ids_with_candidate_capacity()
        )

        skills = [
            skill.strip()
            for skill in candidate.skills.split(",")
            if skill.strip()
        ]

        applied_jobs = Application.objects.filter(
            candidate=candidate
        ).values_list(
            "job_id",
            flat=True,
        )

        query = Q()

        for skill in skills:
            query |= Q(skills__icontains=skill)

        return (
            Job.objects
            .filter(
                query,
                status=Job.ACTIVE,
                employer_id__in=allowed_employer_ids,
            )
            .exclude(
                id__in=applied_jobs,
            )
            .select_related(
                "employer",
                "employer__user",
            )
            .distinct()
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):

        from django.core.cache import cache

        candidate = get_object_or_404(
            CandidateProfile,
            user=request.user,
        )

        allowed_employer_ids = sorted(
            SubscriptionService
            .get_employer_ids_with_candidate_capacity()
        )

        allowed_employers_hash = hashlib.sha256(
            ",".join(
                str(employer_id)
                for employer_id in allowed_employer_ids
            ).encode()
        ).hexdigest()[:16]

        cache_key = (
            f"recommended_jobs_candidate_{candidate.id}"
            f"_employers_{allowed_employers_hash}"
        )

        cached_data = cache.get(cache_key)

        if cached_data is not None:

            return Response(cached_data)

        queryset = self.get_queryset()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        data = serializer.data
        cache.set(
            cache_key,
            data,
            300,
        )

        return Response(data)
    
# ----------------------------
# Candidate Dashboard API
# ----------------------------

class CandidateDashboardView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def get(self, request):

        candidate = get_object_or_404(
            CandidateProfile,
            user=request.user,
        )

        applications = Application.objects.filter(
            candidate=candidate
        )
        saved_jobs = SavedJob.objects.filter(
            candidate=candidate
        ).count()


        dashboard = {

            
            "total_applications": applications.count(),

            "saved_jobs": saved_jobs,

            "applied": applications.filter(
                status=Application.APPLIED
            ).count(),

            "shortlisted": applications.filter(
                status=Application.SHORTLISTED
            ).count(),

            "interview_scheduled": applications.filter(
                status=Application.INTERVIEW
            ).count(),

            "selected": applications.filter(
                status=Application.SELECTED
            ).count(),

            "rejected": applications.filter(
                status=Application.REJECTED
            ).count(),
        }

        serializer = CandidateDashboardSerializer(dashboard)

        return Response(serializer.data)
# ----------------------------
# Resume Text Extraction API
# ----------------------------

class ResumeTextExtractionView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    def post(self, request):

        resume_file = request.FILES.get("resume")

        if not resume_file:
            return Response(
                {
                    "success": False,
                    "message": "Resume file is required.",
                },
                status=400,
            )

        filename = resume_file.name.lower()

        if filename.endswith(".pdf"):
            file_type = "pdf"

        elif filename.endswith(".docx"):
            file_type = "docx"

        else:
            return Response(
                {
                    "success": False,
                    "message": "Only PDF and DOCX files are supported.",
                },
                status=400,
            )

        try:

            # ---------------------------------
            # Step 1: Extract and clean text
            # ---------------------------------

            raw_text, cleaned_text = extract_resume_text(
                resume_file,
                file_type,
            )

            # ---------------------------------
            # Step 2: Parse structured resume data
            # ---------------------------------

            parsed_data = parse_resume_data(
                cleaned_text
            )

            # ---------------------------------
            # Step 3: Get candidate profile
            # ---------------------------------

            candidate = get_object_or_404(
                CandidateProfile,
                user=request.user,
            )

            # ---------------------------------
            # Step 4: Store parsed resume
            # ---------------------------------

            resume_parse, created = ResumeParse.objects.update_or_create(
                candidate=candidate,
                defaults={
                    "raw_text": raw_text,
                    "cleaned_text": cleaned_text,
                    "parsed_data": parsed_data,
                },
            )

            # ---------------------------------
            # Step 5: Return response
            # ---------------------------------

            return Response(
                {
                    "success": True,
                    "message": "Resume parsed and stored successfully.",
                    "filename": resume_file.name,
                    "file_type": file_type,
                    "resume_parse_id": resume_parse.id,
                    "raw_text": raw_text,
                    "cleaned_text": cleaned_text,
                    "parsed_data": parsed_data,
                },
                status=200,
            )

        except Exception as e:

            return Response(
                {
                    "success": False,
                    "message": "Failed to parse resume.",
                    "error": str(e),
                },
                status=500,
            )
# --------------- ATS Ranking service ---------------

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
])
def ranked_candidates_api(request, job_id):
    """
    Return ATS-ranked candidates for a specific job.

    Security:
    - Only authenticated employers can access this API.
    - An employer can only view ranked candidates
      for their own jobs.
    """

    # --------------------------------
    # Check user role
    # --------------------------------

    if request.user.role != CustomUser.EMPLOYER:
        return Response(
            {
                "error": (
                    "Only employers can view "
                    "ranked candidates."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get employer profile
    # --------------------------------

    try:

        employer_profile = (
            request.user.employer_profile
        )

    except EmployerProfile.DoesNotExist:

        return Response(
            {
                "error": (
                    "Employer profile not found."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get job owned by employer
    # --------------------------------

    try:

        job = Job.objects.get(
            id=job_id,
            employer=employer_profile,
        )

    except Job.DoesNotExist:

        return Response(
            {
                "error": (
                    "Job not found or you do not "
                    "have permission to access it."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )
    # --------------------------------
    # Get ranked candidates
    # --------------------------------

    ranked_candidates = get_ranked_candidates(
        job
    )

    # --------------------------------
    # Limit information for Free users
    # --------------------------------

    basic_candidates = [
        {
            "candidate_id": candidate["candidate_id"],
            "rank": candidate["rank"],
            "match_percentage": candidate["match_percentage"],
        }
        for candidate in ranked_candidates
    ]

    # --------------------------------
    # Return response
    # --------------------------------
        

    return Response(
        {
            "job_id": job.id,
            "job_title": job.title,

            "total_candidates": len(
                ranked_candidates
            ),

            "candidates": basic_candidates,
        },

        status=status.HTTP_200_OK,
    )
@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    HasAdvancedAnalyticsAccess,
])
@throttle_classes([
    PremiumUserRateThrottle,
])
def premium_ranked_candidates_api(request, job_id):
    """
    Return detailed ranked candidates for a specific job.

    Security:
    - Only authenticated employers can access this API.
    - Requires advanced analytics access.
    - An employer can only view rankings for their own jobs.
    - Premium requests are rate limited.
    """

    # --------------------------------
    # Validate employer role
    # --------------------------------

    if request.user.role != CustomUser.EMPLOYER:
        return Response(
            {
                "error": "Only employers can view premium ranked candidates."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get employer profile
    # --------------------------------

    try:
        employer_profile = request.user.employer_profile

    except EmployerProfile.DoesNotExist:
        return Response(
            {
                "error": "Employer profile not found."
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get employer's job
    # --------------------------------

    try:
        job = Job.objects.get(
            id=job_id,
            employer=employer_profile,
        )

    except Job.DoesNotExist:
        return Response(
            {
                "error": (
                    "Job not found or you do not have "
                    "permission to access it."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # --------------------------------
    # Get ranked candidates
    # --------------------------------

    ranked_candidates = get_ranked_candidates(job)

    # --------------------------------
    # Return premium ranking details
    # --------------------------------

    return Response(
        {
            "job_id": job.id,
            "job_title": job.title,
            "total_candidates": len(ranked_candidates),
            "candidates": ranked_candidates,
        },
        status=status.HTTP_200_OK,
    )
# --------------------------------
# Candidate Success Report API
# --------------------------------

@api_view(["GET"])
@permission_classes([
    IsAuthenticated,
    HasAdvancedAnalyticsAccess,
])
@throttle_classes([
    PremiumUserRateThrottle,
])
def candidate_success_report_api(request, job_id):
    """
    Return candidate success reports for a specific job.

    Security:
    - Only authenticated employers can access this API.
    - An employer can only view reports
      for their own jobs.
    """

    # --------------------------------
    # Check user role
    # --------------------------------

    if request.user.role != CustomUser.EMPLOYER:
        return Response(
            {
                "error": (
                    "Only employers can view "
                    "candidate success reports."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get employer profile
    # --------------------------------

    try:

        employer_profile = (
            request.user.employer_profile
        )

    except EmployerProfile.DoesNotExist:

        return Response(
            {
                "error": (
                    "Employer profile not found."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # --------------------------------
    # Get job owned by employer
    # --------------------------------

    try:

        job = Job.objects.get(
            id=job_id,
            employer=employer_profile,
        )

    except Job.DoesNotExist:

        return Response(
            {
                "error": (
                    "Job not found or you do not "
                    "have permission to access it."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # --------------------------------
    # Get applications for this job
    # --------------------------------

    applications = (
        Application.objects
        .filter(job=job)
        .select_related(
            "candidate__user",
            "job",
            "ai_call",
        )
        .order_by("applied_at", "id")
    )

    # --------------------------------
    # Generate candidate reports
    # --------------------------------

    candidate_reports = [
        get_candidate_success_report(application)
        for application in applications
    ]

    # --------------------------------
    # Return response
    # --------------------------------

    return Response(
        {
            "job_id": job.id,
            "job_title": job.title,

            "total_candidates": len(
                candidate_reports
            ),

            "candidates": candidate_reports,
        },

        status=status.HTTP_200_OK,
    )
# ----------------------------
# Batch Application Processing API
# ----------------------------
class BatchProcessApplicationsView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request, job_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get the specific job and verify that
        # it belongs to this employer
        # ----------------------------------------

        job = get_object_or_404(
            Job,
            pk=job_id,
            employer=employer,
        )

        # ----------------------------------------
        # Process only pending applications
        # for this specific job
        # ----------------------------------------

        results = process_pending_applications(
            job
        )

        return Response(
            {
                "success": True,
                "job_id": job.id,
                "job_title": job.title,
                "total_processed": len(results),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
# ----------------------------
# AI Interview Configuration API
# ----------------------------

class AIInterviewConfigView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
        HasAIInterviewAccess,
    ]

    def get_job_and_employer(self):

        job = get_object_or_404(
            Job,
            pk=self.kwargs["job_id"],
        )

        employer = get_object_or_404(
            EmployerProfile,
            user=self.request.user,
        )

        # ----------------------------------------
        # Verify job ownership
        # ----------------------------------------

        if job.employer != employer:

            raise PermissionDenied(
                "You are not allowed to configure "
                "AI settings for this job."
            )

        return job

    # ----------------------------------------
    # Get AI configuration
    # ----------------------------------------

    def get(self, request, job_id):

        job = self.get_job_and_employer()

        config = get_object_or_404(
            AIInterviewConfig,
            job=job,
        )

        serializer = AIInterviewConfigSerializer(
            config
        )

        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )

    # ----------------------------------------
    # Create AI configuration
    # ----------------------------------------

    def post(self, request, job_id):

        job = self.get_job_and_employer()

        # ----------------------------------------
        # Prevent duplicate configuration
        # ----------------------------------------

        if AIInterviewConfig.objects.filter(
            job=job
        ).exists():

            return Response(
                {
                    "success": False,
                    "message":
                    "AI interview configuration "
                    "already exists for this job.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AIInterviewConfigSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save(
            job=job
        )

        return Response(
            {
                "success": True,
                "message":
                "AI interview configuration "
                "created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ----------------------------------------
    # Update AI configuration
    # ----------------------------------------

    def patch(self, request, job_id):

        job = self.get_job_and_employer()

        config = get_object_or_404(
            AIInterviewConfig,
            job=job,
        )

        serializer = AIInterviewConfigSerializer(
            config,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            {
                "success": True,
                "message":
                "AI interview configuration "
                "updated successfully.",
                "data": serializer.data,
            }
        )
# ----------------------------
# AI Call Scheduler API
# ----------------------------

class ProcessScheduledAICallsView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):

        results = process_scheduled_ai_calls()

        return Response(
            {
                "success": True,
                "total_processed": len(results),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )
# ----------------------------
# Complete AI Call API
# ----------------------------

class CompleteAICallView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request, ai_call_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get AI call and verify job ownership
        # ----------------------------------------

        ai_call = get_object_or_404(
            AICall.objects.select_related(
                "application",
                "application__job",
            ),
            pk=ai_call_id,
            application__job__employer=employer,
        )

        # ----------------------------------------
        # Get optional result
        # ----------------------------------------

        result = request.data.get(
            "result",
            "Passed",
        )

        # ----------------------------------------
        # Complete AI call
        # ----------------------------------------

        ai_call_result = complete_ai_call(
            ai_call,
            result=result,
        )

        return Response(
            ai_call_result,
            status=status.HTTP_200_OK,
        )
# ----------------------------
# Missed AI Call API
# ----------------------------

class MissedAICallView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request, ai_call_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get AI call and verify job ownership
        # ----------------------------------------

        ai_call = get_object_or_404(
            AICall.objects.select_related(
                "application",
                "application__job",
                "config",
            ),
            pk=ai_call_id,
            application__job__employer=employer,
        )

        # ----------------------------------------
        # Handle missed AI call
        # ----------------------------------------

        result = handle_missed_ai_call(
            ai_call
        )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
# ----------------------------
# AI Screening Report API
# ----------------------------

class AIScreeningReportView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
        HasAIInterviewReportsAccess,
    ]

    def post(self, request, ai_call_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get AI call and verify job ownership
        # ----------------------------------------

        ai_call = get_object_or_404(
            AICall.objects.select_related(
                "application",
                "application__job",
            ),
            pk=ai_call_id,
            application__job__employer=employer,
        )

        # ----------------------------------------
        # Get AI-generated screening result
        # ----------------------------------------

        overall_score = request.data.get(
            "overall_score"
        )

        summary = request.data.get(
            "summary",
            "",
        )

        recommendation = request.data.get(
            "recommendation",
            "",
        )

        analysis = request.data.get(
            "analysis",
            {},
        )

        # ----------------------------------------
        # Validate analysis format
        # ----------------------------------------

        if not isinstance(analysis, dict):

            return Response(
                {
                    "success": False,
                    "message":
                    "Analysis must be a JSON object.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Save AI screening report
        # ----------------------------------------

        result = save_ai_screening_report(
            ai_call=ai_call,
            overall_score=overall_score,
            summary=summary,
            recommendation=recommendation,
            analysis=analysis,
        )

        if not result["success"]:

            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )
# ----------------------------
# Interview Scheduling API
# ----------------------------

class InterviewScheduleView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request, application_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get application and verify ownership
        # ----------------------------------------

        application = get_object_or_404(
            Application.objects.select_related(
                "candidate",
                "candidate__user",
                "job",
            ),
            pk=application_id,
            job__employer=employer,
        )

        # ----------------------------------------
        # Candidate must be shortlisted
        # ----------------------------------------

        if application.status != Application.SHORTLISTED:

            return Response(
                {
                    "success": False,
                    "message":
                    "Only shortlisted candidates can be scheduled for an interview.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Prevent duplicate interview schedule
        # ----------------------------------------

        if InterviewSchedule.objects.filter(
            application=application
        ).exists():

            return Response(
                {
                    "success": False,
                    "message":
                    "An interview is already scheduled for this application.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Validate interview data
        # ----------------------------------------

        serializer = InterviewScheduleSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        # ----------------------------------------
        # Create interview schedule
        # ----------------------------------------

        interview = serializer.save(
            application=application,
            status=InterviewSchedule.SCHEDULED,
        )

        # ----------------------------------------
        # Update application status
        # ----------------------------------------

        application.status = Application.INTERVIEW
        application.save()

        # ----------------------------------------
        # Return response
        # ----------------------------------------

        return Response(
            {
                "success": True,
                "message":
                "Interview scheduled successfully.",
                "data":
                InterviewScheduleSerializer(
                    interview
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
class AIAnswerEvaluationView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
        HasAIAnswerEvaluationAccess,
    ]

    def get(self, request, answer_id):

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get answer and verify job ownership
        # ----------------------------------------

        answer = get_object_or_404(
            AIInterviewAnswer.objects.select_related(
                "ai_call",
                "ai_call__application",
                "ai_call__application__job",
            ),
            id=answer_id,
            ai_call__application__job__employer=employer,
        )

        # ----------------------------------------
        # Get evaluation
        # ----------------------------------------

        evaluation = AIAnswerEvaluation.objects.filter(
            answer=answer
        ).first()

        if not evaluation:
            evaluation = AIAnswerEvaluationService(
                answer
            ).evaluate()

        # ----------------------------------------
        # Return evaluation
        # ----------------------------------------

        return Response(
            {
                "success": True,
                "answer_id": answer.id,
                "question_order": answer.question_order,
                "question": answer.question_text,
                "answer": answer.answer_text,
                "evaluation": {
                    "relevance_score": float(
                        evaluation.relevance_score
                    ),
                    "completeness_score": float(
                        evaluation.completeness_score
                    ),
                    "keyword_score": float(
                        evaluation.keyword_score
                    ),
                    "final_score": float(
                        evaluation.final_score
                    ),
                    "confidence": float(
                        evaluation.confidence
                    ),
                    "annotations": evaluation.annotations,
                },
            },
            status=status.HTTP_200_OK,
        )
class AISubmitAnswerView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsEmployer,
        HasAIInterviewAccess,
    ]

    def post(self, request, answer_id=None):

        # ----------------------------------------
        # Validate required data
        # ----------------------------------------

        ai_call_id = request.data.get("ai_call_id")
        answer_text = request.data.get("answer")

        if not ai_call_id:
            return Response(
                {
                    "success": False,
                    "message": "ai_call_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not answer_text:
            return Response(
                {
                    "success": False,
                    "message": "answer is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Get authenticated employer
        # ----------------------------------------

        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        # ----------------------------------------
        # Get AI call and verify job ownership
        # ----------------------------------------

        ai_call = get_object_or_404(
            AICall.objects.select_related(
                "application",
                "application__job",
            ),
            id=ai_call_id,
            application__job__employer=employer,
        )

        # ----------------------------------------
        # Submit answer through existing flow manager
        # ----------------------------------------

        from accounts.services.ai_flow_manager import AIFlowManager

        flow_manager = AIFlowManager(ai_call)

        result = flow_manager.submit_answer(
            answer_text.strip()
        )

        if not result.get("success"):
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Get the newly stored answer
        # ----------------------------------------
        answer_id = result.get("answer_id")

        if not answer_id:
            return Response(
                {
                    "success": False,
                    "message": "Answer ID was not returned.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        answer = AIInterviewAnswer.objects.filter(
            id=answer_id,
            ai_call=ai_call,
        ).first()

        if not answer:
            return Response(
                {
                    "success": False,
                    "message": "Answer was not found.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
                
        # ----------------------------------------
        # Evaluate submitted answer
        # ----------------------------------------

        evaluation = AIAnswerEvaluationService(
            answer
        ).evaluate()

        # ----------------------------------------
        # Return answer + evaluation + next question
        # ----------------------------------------

        response_data = {
            "success": True,
            "answer": {
                "id": answer.id,
                "question_order": answer.question_order,
                "question": answer.question_text,
                "answer": answer.answer_text,
            },
            "evaluation": {
                "relevance_score": float(
                    evaluation.relevance_score
                ),
                "completeness_score": float(
                    evaluation.completeness_score
                ),
                "keyword_score": float(
                    evaluation.keyword_score
                ),
                "final_score": float(
                    evaluation.final_score
                ),
                "confidence": float(
                    evaluation.confidence
                ),
                "annotations": evaluation.annotations,
            },
            "flow": {
                "flow_type": result.get("flow_type"),
                "next_question": result.get("next_question"),
                "next_category": result.get("next_category"),
                "message": result.get("message"),
            },
        }

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )
class InterviewReminderStatusView(APIView):
    permission_classes = [IsAuthenticated, IsEmployer]

    def get(self, request, interview_id):
        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        interview = get_object_or_404(
            InterviewSchedule.objects.select_related(
                "application",
                "application__job",
            ),
            id=interview_id,
            application__job__employer=employer,
        )

        reminders = interview.reminders.select_related(
            "email_log"
        ).order_by("scheduled_for")

        data = []

        for reminder in reminders:
            data.append({
                "id": reminder.id,
                "reminder_type": reminder.reminder_type,
                "scheduled_for": reminder.scheduled_for,
                "status": reminder.status,
                "email_log_id": reminder.email_log_id,
                "email_status": (
                    reminder.email_log.status
                    if reminder.email_log
                    else None
                ),
                "sent_at": reminder.sent_at,
            })

        return Response({
            "success": True,
            "interview_id": interview.id,
            "reminders": data,
        })
class AICandidateReportView(APIView):
    permission_classes = [IsAuthenticated, IsEmployer,HasEnterpriseReportsAccess,]

    def post(self, request, application_id):
        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        application = get_object_or_404(
            Application.objects.select_related(
                "candidate",
                "candidate__user",
                "job",
            ),
            id=application_id,
            job__employer=employer,
        )

        result = AICandidateReportService.generate_report(
            application
        )

        if not result.get("success"):
            return Response(
                result,
                status=400,
            )

        return Response(
            result,
            status=201 if result.get("created") else 200,
        )

    def get(self, request, application_id):
        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        application = get_object_or_404(
            Application.objects.select_related(
                "candidate",
                "candidate__user",
                "job",
            ),
            id=application_id,
            job__employer=employer,
        )

        report = get_object_or_404(
            AICandidateReport,
            application=application,
        )

        return Response({
            "success": True,
            "report_id": report.id,
            "data": report.report_data,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        })
class RecruiterTimeAnalyticsView(APIView):
    permission_classes = [IsAuthenticated,HasAdvancedAnalyticsAccess,]

    def get(self, request):
        employer = get_object_or_404(
            EmployerProfile,
            user=request.user,
        )

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {
                    "success": False,
                    "message": "Both start_date and end_date are required.",
                },
                status=400,
            )

        try:
            start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d",
            ).date()

            end_date = datetime.strptime(
                end_date,
                "%Y-%m-%d",
            ).date()

        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": "Dates must be in YYYY-MM-DD format.",
                },
                status=400,
            )

        if start_date > end_date:
            return Response(
                {
                    "success": False,
                    "message": "start_date cannot be later than end_date.",
                },
                status=400,
            )

        data = RecruiterAnalyticsService.get_time_based_metrics(
            employer,
            start_date=start_date,
            end_date=end_date,
        )

        return Response(
            {
                "success": True,
                "analytics": data,
            }
        )
class VerifyRazorpayPaymentView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request):

        transaction_id = request.data.get("transaction_id")
        razorpay_payment_id = request.data.get(
            "razorpay_payment_id"
        )
        razorpay_order_id = request.data.get(
            "razorpay_order_id"
        )
        razorpay_signature = request.data.get(
            "razorpay_signature"
        )

        if not all(
            [
                transaction_id,
                razorpay_payment_id,
                razorpay_order_id,
                razorpay_signature,
            ]
        ):
            return Response(
                {
                    "success": False,
                    "message": "transaction_id, razorpay_payment_id, razorpay_order_id, and razorpay_signature are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_transaction = PaymentTransaction.objects.get(
                id=transaction_id,
                user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Payment transaction not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        result = PaymentService.verify_razorpay_payment(
            payment_transaction=payment_transaction,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
            razorpay_signature=razorpay_signature,
        )

        if not result["success"]:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
class CreateRefundRequestView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request):

        payment_transaction_id = request.data.get(
            "payment_transaction_id"
        )
        reason = request.data.get("reason")

        if not payment_transaction_id:
            return Response(
                {
                    "success": False,
                    "message": "payment_transaction_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reason or not reason.strip():
            return Response(
                {
                    "success": False,
                    "message": "Refund reason is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_transaction = PaymentTransaction.objects.get(
                id=payment_transaction_id,
                user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Payment transaction not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        result = PaymentService.create_refund_request(
            payment_transaction_id=payment_transaction.id,
            user=request.user,
            reason=reason,
        )

        if not result["success"]:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_201_CREATED,
        )
    
class FailRazorpayPaymentView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    def post(self, request):

        transaction_id = request.data.get("transaction_id")

        if not transaction_id:
            return Response(
                {
                    "success": False,
                    "message": "transaction_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment_transaction = PaymentTransaction.objects.get(
                id=transaction_id,
                user=request.user,
            )
        except PaymentTransaction.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Payment transaction not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        result = PaymentService.handle_failed_payment(
            transaction_id=payment_transaction.id,
        )

        if not result["success"]:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )
@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):

        # ----------------------------------------
        # Get Razorpay webhook signature
        # ----------------------------------------

        webhook_signature = request.headers.get(
            "X-Razorpay-Signature"
        )

        if not webhook_signature:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay webhook signature is missing.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Keep the raw request body for signature
        # verification.
        # ----------------------------------------

        raw_body = request.body

        client = PaymentService.get_razorpay_client()

        try:
            client.utility.verify_webhook_signature(
                raw_body.decode("utf-8"),
                webhook_signature,
                settings.RAZORPAY_WEBHOOK_SECRET,
            )
        except razorpay.errors.SignatureVerificationError:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay webhook signature verification failed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Parse webhook payload
        # ----------------------------------------

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response(
                {
                    "success": False,
                    "message": "Invalid webhook payload.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = payload.get("event")

        # ----------------------------------------
        # Supported payment events
        # ----------------------------------------

        if event not in [
            "payment.captured",
            "payment.failed",
            "refund.processed",
            "refund.failed",
        ]:
            return Response(
                {
                    "success": True,
                    "message": "Webhook event received but no action was required.",
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Handle processed refund webhook
        # ----------------------------------------

        if event == "refund.processed":

            refund_entity = (
                payload
                .get("payload", {})
                .get("refund", {})
                .get("entity", {})
            )

            razorpay_refund_id = refund_entity.get("id")
            razorpay_payment_id = refund_entity.get("payment_id")
            refund_status = refund_entity.get("status")

            if not razorpay_refund_id or not razorpay_payment_id:
                return Response(
                    {
                        "success": False,
                        "message": "Razorpay refund ID or payment ID is missing.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if refund_status != "processed":
                return Response(
                    {
                        "success": False,
                        "message": "Razorpay refund is not processed.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                payment_transaction = (
                    PaymentTransaction.objects.get(
                        gateway_transaction_id=razorpay_payment_id,
                        payment_gateway="Razorpay",
                    )
                )
            except PaymentTransaction.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "Payment transaction not found for the Razorpay payment.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            result = PaymentService.handle_refund(
                transaction_id=payment_transaction.id,
                razorpay_refund_id=razorpay_refund_id,
            )

            if not result["success"]:
                return Response(
                    result,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "success": True,
                    "message": "Razorpay refund webhook processed successfully.",
                    "payment_transaction_id": payment_transaction.id,
                    "subscription_id": result.get("subscription_id"),
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Handle failed refund webhook
        # ----------------------------------------

        if event == "refund.failed":

            refund_entity = (
                payload
                .get("payload", {})
                .get("refund", {})
                .get("entity", {})
            )

            razorpay_refund_id = refund_entity.get("id")
            razorpay_payment_id = refund_entity.get("payment_id")
            refund_status = refund_entity.get("status")

            if not razorpay_refund_id or not razorpay_payment_id:
                return Response(
                    {
                        "success": False,
                        "message": "Razorpay refund ID or payment ID is missing.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if refund_status != "failed":
                return Response(
                    {
                        "success": False,
                        "message": "Razorpay refund is not failed.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                payment_transaction = (
                    PaymentTransaction.objects.get(
                        gateway_transaction_id=razorpay_payment_id,
                        payment_gateway="Razorpay",
                    )
                )
            except PaymentTransaction.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "Payment transaction not found for the Razorpay payment.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            result = PaymentService.handle_failed_refund(
                transaction_id=payment_transaction.id,
            )

            if not result["success"]:
                return Response(
                    result,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "success": True,
                    "message": "Razorpay refund failure webhook processed successfully.",
                    "payment_transaction_id": payment_transaction.id,
                    "refund_id": razorpay_refund_id,
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Extract Razorpay payment entity
        # ----------------------------------------

        payment_entity = (
            payload
            .get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id")
        razorpay_amount = payment_entity.get("amount")
        razorpay_currency = payment_entity.get("currency")
        razorpay_status = payment_entity.get("status")
        razorpay_captured = payment_entity.get("captured")

        if not razorpay_payment_id or not razorpay_order_id:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay payment ID or order ID is missing.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Handle failed payment webhook
        # ----------------------------------------

        if event == "payment.failed":

            try:
                payment_transaction = PaymentTransaction.objects.get(
                    gateway_order_id=razorpay_order_id,
                    payment_gateway="Razorpay",
                )
            except PaymentTransaction.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "Payment transaction not found for the Razorpay order.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            result = PaymentService.handle_failed_payment(
                transaction_id=payment_transaction.id,
            )

            if not result["success"]:
                return Response(
                    result,
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "success": True,
                    "message": "Razorpay payment failure webhook processed successfully.",
                    "payment_transaction_id": payment_transaction.id,
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Find the local payment transaction
        # using the trusted Razorpay order ID.
        # ----------------------------------------

        try:
            payment_transaction = PaymentTransaction.objects.get(
                gateway_order_id=razorpay_order_id,
                payment_gateway="Razorpay",
            )
        except PaymentTransaction.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Payment transaction not found for the Razorpay order.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # ----------------------------------------
        # Idempotency:
        # If this webhook was already processed,
        # do not activate another subscription.
        # ----------------------------------------

        if payment_transaction.status == PaymentTransaction.SUCCESS:
            return Response(
                {
                    "success": True,
                    "message": "Webhook was already processed.",
                    "payment_transaction_id": payment_transaction.id,
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Only pending transactions can be completed.
        # ----------------------------------------

        if payment_transaction.status != PaymentTransaction.PENDING:
            return Response(
                {
                    "success": False,
                    "message": "Payment transaction cannot be completed from this webhook.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Verify amount
        # ----------------------------------------

        expected_amount = int(
            payment_transaction.amount * 100
        )

        if razorpay_amount != expected_amount:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay payment amount does not match the transaction amount.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Verify currency
        # ----------------------------------------

        if razorpay_currency != payment_transaction.currency:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay payment currency does not match the transaction currency.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Verify captured status
        # ----------------------------------------

        if razorpay_status != "captured" or not razorpay_captured:
            return Response(
                {
                    "success": False,
                    "message": "Razorpay payment is not captured.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Complete the local payment transaction
        # ----------------------------------------

        result = PaymentService.handle_successful_payment(
            transaction_id=payment_transaction.id,
            gateway_transaction_id=razorpay_payment_id,
        )

        if not result["success"]:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Razorpay payment webhook processed successfully.",
                "payment_transaction_id": payment_transaction.id,
                "subscription_id": result.get("subscription_id"),
            },
            status=status.HTTP_200_OK,
        )
class RazorpayPaymentView(APIView):
    permission_classes = [
    
    ]

    def get(self, request, plan_id):

        plan = get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )

        return render(
            request,
            "accounts/payment.html",
            {
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "plan": plan,
            },
        )
class CreateRazorpayOrderView(APIView):
    permission_classes = [
        IsAuthenticated,
        IsEmployer,
    ]

    @transaction.atomic
    def post(self, request):
        plan_id = request.data.get("plan_id")

        if not plan_id:
            return Response(
                {
                    "success": False,
                    "message": "plan_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan = get_object_or_404(
            SubscriptionPlan,
            id=plan_id,
            is_active=True,
        )

        if plan.price <= 0:
            return Response(
                {
                    "success": False,
                    "message": "This plan does not require a payment.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------
        # Lock the user row
        # ----------------------------------------
        locked_user = CustomUser.objects.select_for_update().get(
            id=request.user.id
        )

        # ----------------------------------------
        # Prevent duplicate pending transactions
        # for the same subscription plan
        # ----------------------------------------
        existing_transaction = (
            PaymentTransaction.objects
            .filter(
                user=locked_user,
                plan=plan,
                transaction_type=PaymentTransaction.SUBSCRIPTION,
                status=PaymentTransaction.PENDING,
            )
            .order_by("-id")
            .first()
        )

        if existing_transaction:
            return Response(
                {
                    "success": True,
                    "message": "A pending payment transaction already exists for this plan.",
                    "payment_transaction_id": existing_transaction.id,
                    "razorpay_order_id": (
                        existing_transaction.gateway_order_id
                    ),
                    "amount": int(
                        existing_transaction.amount * 100
                    ),
                    "currency": existing_transaction.currency,
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                },
                status=status.HTTP_200_OK,
            )

        # ----------------------------------------
        # Create a new local payment transaction
        # ----------------------------------------
        payment_transaction = (
            PaymentService.create_payment_transaction(
                user=locked_user,
                plan=plan,
                payment_gateway="Razorpay",
            )
        )

        # ----------------------------------------
        # Create Razorpay order
        # ----------------------------------------
        razorpay_order = PaymentService.create_razorpay_order(
            payment_transaction
        )

        return Response(
            {
                "success": True,
                "message": "Razorpay order created successfully.",
                "payment_transaction_id": payment_transaction.id,
                "razorpay_order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_201_CREATED,
        )
# interview related views !!
# ----------------------------------------
# Submit Scheduled Interview Answer API
# ----------------------------------------

class SubmitScheduledInterviewAnswerView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsCandidate,
    ]

    def post(self, request, session_id):

        question_id = request.data.get("question_id")
        answer_text = request.data.get("answer")

        if not question_id:
            return Response(
                {
                    "success": False,
                    "message": "question_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if answer_text is None:
            return Response(
                {
                    "success": False,
                    "message": "answer is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = (
            ScheduledInterviewSession.objects
            .select_related(
                "interview",
                "interview__application",
                "interview__application__candidate",
            )
            .filter(pk=session_id)
            .first()
        )

        if not session:
            return Response(
                {
                    "success": False,
                    "message": "Interview session not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.interview.application.candidate.user_id != request.user.id:
            return Response(
                {
                    "success": False,
                    "message": "You are not authorized to submit an answer for this interview.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        result = ScheduledInterviewService.submit_answer(
            session_id=session_id,
            question_id=question_id,
            answer_text=answer_text,
        )

        if not result["success"]:
            return Response(
                result,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            result,
            status=status.HTTP_200_OK,
        )