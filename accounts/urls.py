from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    LoginView,
    AdminView,
    EmployerView,
    CandidateView,

    CandidateProfileCreateView,
    EmployerProfileCreateView,
    CandidateProfileDetailView,
    CandidateProfileUpdateView,
    CandidateProfileDeleteView,
    CandidateNotificationListView,
    MarkNotificationAsReadView,

    EmployerProfileDetailView,
    EmployerProfileUpdateView,
    EmployerProfileDeleteView,

    CandidateListView,
    EmployerListView,

    JobCreateView,
    JobUpdateView,
    JobStatusUpdateView,
    JobListView,
    FeaturedJobListView,
    LatestJobListView,

    ApplyJobView,

    MyApplicationsView,
    ApplicationDetailView,
    ApplicationStatusUpdateView,

    EmployerDashboardJobListView,
    EmployerApplicantListView,
    EmployerCandidateReviewView,

    CandidateDashboardView,

    SaveJobView,
    RemoveSavedJobView,
    MySavedJobsView,
    RecommendedJobsView,

    AdminApproveEmployerView,
    AdminBlockUserView,
    AdminManageJobView,
    AdminPlatformStatsView,
    AdminUserGrowthView,
    AdminJobActivityView,
    AdminFlagUserView,
    AdminAuditLogView,
    AdminBillingTransactionView,
    AdminBillingSubscriptionView,
    AdminBillingRevenueView,
    AdminRefundRequestView,
    ResumeTextExtractionView,

    ranked_candidates_api,
    premium_ranked_candidates_api,
    candidate_success_report_api,
    BatchProcessApplicationsView,

    AIInterviewConfigView,
    ProcessScheduledAICallsView,
    CompleteAICallView,
    MissedAICallView,
    AIScreeningReportView,
    InterviewScheduleView,
    AIAnswerEvaluationView,
    AISubmitAnswerView,
    InterviewReminderStatusView,
    AICandidateReportView,
    RecruiterJobAnalyticsView,
    RecruiterTimeAnalyticsView,
    VerifyRazorpayPaymentView,
    CreateRazorpayOrderView,
    RazorpayPaymentView,
    FailRazorpayPaymentView,
    RazorpayWebhookView,
    CreateRefundRequestView,
    AdminRefundRequestReviewView,


  
    SubmitScheduledInterviewAnswerView,
)


urlpatterns = [

    # ----------------------------
    # Authentication APIs
    # ----------------------------

    path(
        "register/",
        RegisterView.as_view(),
        name="register",
    ),

    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
    "token/refresh/",
    TokenRefreshView.as_view(),
    name="token-refresh",
    ),

    # ----------------------------
    # Role Based APIs
    # ----------------------------

    path(
        "admin/",
        AdminView.as_view(),
        name="admin",
    ),

    path(
        "employer/",
        EmployerView.as_view(),
        name="employer",
    ),

    path(
        "candidate/",
        CandidateView.as_view(),
        name="candidate",
    ),


    # ----------------------------
    # Candidate Profile APIs
    # ----------------------------

    path(
        "candidate/profile/create/",
        CandidateProfileCreateView.as_view(),
        name="candidate-profile-create",
    ),

    path(
        "candidate/profile/",
        CandidateProfileDetailView.as_view(),
        name="candidate-profile",
    ),

    path(
        "candidate/profile/update/",
        CandidateProfileUpdateView.as_view(),
        name="candidate-profile-update",
    ),

    path(
        "candidate/profile/delete/",
        CandidateProfileDeleteView.as_view(),
        name="candidate-profile-delete",
    ),


    # ----------------------------
    # Employer Profile APIs
    # ----------------------------

    path(
        "employer/profile/create/",
        EmployerProfileCreateView.as_view(),
        name="employer-profile-create",
    ),

    path(
        "employer/profile/",
        EmployerProfileDetailView.as_view(),
        name="employer-profile",
    ),

    path(
        "employer/profile/update/",
        EmployerProfileUpdateView.as_view(),
        name="employer-profile-update",
    ),

    path(
        "employer/profile/delete/",
        EmployerProfileDeleteView.as_view(),
        name="employer-profile-delete",
    ),


    # ----------------------------
    # Candidate / Employer List APIs
    # ----------------------------

    path(
        "candidates/",
        CandidateListView.as_view(),
        name="candidate-list",
    ),

    path(
        "employers/",
        EmployerListView.as_view(),
        name="employer-list",
    ),


    # ----------------------------
    # Job Management APIs
    # ----------------------------

    path(
        "jobs/create/",
        JobCreateView.as_view(),
        name="job-create",
    ),

    path(
        "jobs/<int:pk>/update/",
        JobUpdateView.as_view(),
        name="job-update",
    ),

    path(
        "jobs/<int:pk>/status/",
        JobStatusUpdateView.as_view(),
        name="job-status",
    ),


    # ----------------------------
    # Public Job Listing APIs
    # ----------------------------

    path(
        "jobs/",
        JobListView.as_view(),
        name="job-list",
    ),

    path(
        "jobs/featured/",
        FeaturedJobListView.as_view(),
        name="featured-jobs",
    ),

    path(
        "jobs/latest/",
        LatestJobListView.as_view(),
        name="latest-jobs",
    ),


    # ----------------------------
    # Apply Job API
    # ----------------------------

    path(
        "jobs/<int:job_id>/apply/",
        ApplyJobView.as_view(),
        name="apply-job",
    ),


    # ----------------------------
    # Application Tracking APIs
    # ----------------------------

    path(
        "applications/",
        MyApplicationsView.as_view(),
        name="my-applications",
    ),

    path(
        "applications/<int:pk>/",
        ApplicationDetailView.as_view(),
        name="application-detail",
    ),

    path(
        "applications/<int:pk>/status/",
        ApplicationStatusUpdateView.as_view(),
        name="application-status-update",
    ),


    # ----------------------------
    # Employer Dashboard APIs
    # ----------------------------

    path(
        "dashboard/jobs/",
        EmployerDashboardJobListView.as_view(),
        name="dashboard-jobs",
    ),

    path(
        "dashboard/jobs/<int:job_id>/applicants/",
        EmployerApplicantListView.as_view(),
        name="dashboard-job-applicants",
    ),
    path(
    "dashboard/applications/<int:pk>/review/",
    EmployerCandidateReviewView.as_view(),
    name="employer-candidate-review",
    ),


    # ----------------------------
    # Candidate Dashboard API
    # ----------------------------

    path(
        "candidate/dashboard/",
        CandidateDashboardView.as_view(),
        name="candidate-dashboard",
    ),
    # ----------------------------
    # Candidate Notifications API
    # ----------------------------

    path(
        "candidate/notifications/",
        CandidateNotificationListView.as_view(),
        name="candidate-notifications",
    ),
    # ----------------------------
    # Notification APIs
    # ----------------------------

    path(
        "notifications/<int:pk>/read/",
        MarkNotificationAsReadView.as_view(),
        name="mark-notification-read",
    ),

    # ----------------------------
    # Saved Jobs APIs
    # ----------------------------

    path(
        "jobs/<int:job_id>/save/",
        SaveJobView.as_view(),
        name="save-job",
    ),

    path(
        "jobs/<int:job_id>/unsave/",
        RemoveSavedJobView.as_view(),
        name="unsave-job",
    ),

    path(
        "saved-jobs/",
        MySavedJobsView.as_view(),
        name="my-saved-jobs",
    ),


    # ----------------------------
    # Job Recommendation API
    # ----------------------------

    path(
        "jobs/recommended/",
        RecommendedJobsView.as_view(),
        name="recommended-jobs",
    ),


    # ----------------------------
    # Admin Privilege APIs
    # ----------------------------

    path(
        "admin/employers/<int:pk>/approve/",
        AdminApproveEmployerView.as_view(),
        name="admin-approve-employer",
    ),

    path(
        "admin/users/<int:pk>/block/",
        AdminBlockUserView.as_view(),
        name="admin-block-user",
    ),

    path(
        "admin/jobs/<int:pk>/manage/",
        AdminManageJobView.as_view(),
        name="admin-manage-job",
    ),
    path(
    "admin/stats/",
    AdminPlatformStatsView.as_view(),
    name="admin-platform-stats",
    ),
    path(
    "admin/user-growth/",
    AdminUserGrowthView.as_view(),
    name="admin-user-growth",
    ),
    path(
    "admin/job-activity/",
    AdminJobActivityView.as_view(),
    name="admin-job-activity",
    ),
    path(
    "admin/users/<int:pk>/flag/",
    AdminFlagUserView.as_view(),
    name="admin-flag-user",
    ),
    path(
    "admin/audit-logs/",
    AdminAuditLogView.as_view(),
    name="admin-audit-logs",
    ),
    path(
    "admin/billing/transactions/",
    AdminBillingTransactionView.as_view(),
    name="admin-billing-transactions",
    ),
    path(
    "admin/billing/subscriptions/",
    AdminBillingSubscriptionView.as_view(),
    name="admin-billing-subscriptions",
    ),
    path(
    "admin/billing/revenue/",
    AdminBillingRevenueView.as_view(),
    name="admin-billing-revenue",
    ),
    path(
    "admin/billing/refund-requests/",
    AdminRefundRequestView.as_view(),
    name="admin-refund-requests",
    ),
    path(
    "admin/billing/refund-requests/<int:refund_request_id>/review/",
    AdminRefundRequestReviewView.as_view(),
    name="admin-refund-request-review",
    ),
    path(
    "resume/parse/",
    ResumeTextExtractionView.as_view(),
    name="resume-parse",
    ),
    path(
    "jobs/<int:job_id>/ranked-candidates/",
    ranked_candidates_api,
    name="ranked-candidates",
    ),
    path(
    "jobs/<int:job_id>/premium-ranked-candidates/",
    premium_ranked_candidates_api,
    name="premium-ranked-candidates",
    ),
    path(
    "jobs/<int:job_id>/candidate-success-report/",
    candidate_success_report_api,
    name="candidate-success-report",
   ),

    # ----------------------------
    # Batch Processing API
    # ----------------------------
    path(
        "jobs/<int:job_id>/batch-process/",
        BatchProcessApplicationsView.as_view(),
        name="batch-process-applications",
    ),
    # ----------------------------
    # AI Interview Configuration API
    # ----------------------------

    path(
        "jobs/<int:job_id>/ai-config/",
        AIInterviewConfigView.as_view(),
        name="ai-interview-config",
    ),
    # ----------------------------
    # AI Call Scheduler API
    # ----------------------------

    path(
        "ai-calls/process-scheduled/",
        ProcessScheduledAICallsView.as_view(),
        name="process-scheduled-ai-calls",
    ),
    # ----------------------------
    # AI Call APIs
    # ----------------------------

    path(
        "ai-calls/<int:ai_call_id>/complete/",
        CompleteAICallView.as_view(),
        name="complete-ai-call",
    ),
    # ----------------------------
    # AI Call Retry APIs
    # ----------------------------

    path(
        "ai-calls/<int:ai_call_id>/missed/",
        MissedAICallView.as_view(),
        name="missed-ai-call",
    ),
    # ----------------------------
    # AI Screening Report API
    # ----------------------------

    path(
        "ai-calls/<int:ai_call_id>/screening-report/",
        AIScreeningReportView.as_view(),
        name="ai-screening-report",
    ),
    # ----------------------------
    # Interview Scheduling API
    # ----------------------------

    path(
        "applications/<int:application_id>/schedule-interview/",
        InterviewScheduleView.as_view(),
        name="schedule-interview",
    ),
    
    path(
    "ai/answers/<int:answer_id>/evaluation/",
    AIAnswerEvaluationView.as_view(),
    name="ai-answer-evaluation",
    ),
    path(
    "ai/answers/submit/",
    AISubmitAnswerView.as_view(),
    name="ai-submit-answer",
    ),
    path(
    "ai/interviews/<int:interview_id>/reminders/",
    InterviewReminderStatusView.as_view(),
    ),
    path(
    "ai/candidate-reports/<int:application_id>/",
    AICandidateReportView.as_view(),
    ),
    path(
    "analytics/jobs/",
    RecruiterJobAnalyticsView.as_view(),
    ),
    path(
    "analytics/time/",
    RecruiterTimeAnalyticsView.as_view(),
    ),
    # ----------------------------
    # Razorpay Payment Verification API
    # ----------------------------

    path(
        "payments/razorpay/verify/",
        VerifyRazorpayPaymentView.as_view(),
        name="verify-razorpay-payment",
    ),
    path(
    "payments/razorpay/fail/",
    FailRazorpayPaymentView.as_view(),
    name="fail-razorpay-payment",
    ),
    # ----------------------------
    # Razorpay Order Creation API
    # ----------------------------

    path(
        "payments/razorpay/create-order/",
        CreateRazorpayOrderView.as_view(),
        name="create-razorpay-order",
    ),
    # ----------------------------
    # Razorpay Payment Page
    # ----------------------------

    path(
        "payments/razorpay/<int:plan_id>/",
        RazorpayPaymentView.as_view(),
        name="razorpay-payment",
    ),
    path(
    "billing/refund-requests/",
    CreateRefundRequestView.as_view(),
    name="create-refund-request",
    ),
    path(
    "payments/razorpay/webhook/",
    RazorpayWebhookView.as_view(),
    name="razorpay-webhook",
    ),
    path(
    "interviews/<int:session_id>/answer/",
    SubmitScheduledInterviewAnswerView.as_view(),
    name="submit-scheduled-interview-answer",
    ),
]