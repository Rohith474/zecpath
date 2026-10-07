from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    CustomUser,
    CandidateProfile,
    EmployerProfile,
    Job,
    Application,
    ResumeParse,
    AIInterviewConfig,
    AICall,
    InterviewSchedule,
    AIInterviewAnswer,
    AIScreeningReport,
    AIInterviewSession,
    CallLog,
    AIQuestionTemplate,
    AIQuestionJobMapping,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "id",
        "username",
        "email",
        "role",
        "is_active",
        "is_flagged",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_active",
        "is_flagged",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "is_flagged",
                ),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Information",
            {
                "fields": (
                    "role",
                    "is_flagged",
                ),
            },
        ),
    )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "experience",
        "expected_salary",
        "is_deleted",
    )


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):

    list_display = (
        "company_name",
        "domain",
        "company_size",
        "is_verified",
        "is_deleted",
    )


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "employer",
        "location",
        "job_type",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "job_type",
    )

    search_fields = (
        "title",
        "location",
        "skills",
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "candidate",
        "job",
        "status",
        "applied_at",
    )

    list_filter = (
        "status",
        "applied_at",
    )

    search_fields = (
        "candidate__user__username",
        "job__title",
    )

    ordering = (
        "-applied_at",
    )


@admin.register(ResumeParse)
class ResumeParseAdmin(admin.ModelAdmin):

    list_display = (
        "candidate",
        "parsed_at",
    )

    search_fields = (
        "candidate__user__username",
        "candidate__user__email",
    )

    ordering = (
        "-parsed_at",
    )


# ----------------------------
# AI Interview Configuration
# ----------------------------

@admin.register(AIInterviewConfig)
class AIInterviewConfigAdmin(admin.ModelAdmin):

    list_display = (
        "job",
        "call_start_time",
        "call_end_time",
        "max_call_attempts",
        "retry_interval_minutes",
        "voice_type",
        "language",
        "is_active",
    )

    list_filter = (
        "is_active",
        "voice_type",
        "language",
    )

    search_fields = (
        "job__title",
    )


# ----------------------------
# AI Call
# ----------------------------

@admin.register(AICall)
class AICallAdmin(admin.ModelAdmin):

    list_display = (
        "application",
        "status",
        "attempt_count",
        "scheduled_at",
        "last_attempt_at",
        "next_retry_at",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "application__candidate__user__username",
        "application__job__title",
    )


# ----------------------------
# Interview Schedule
# ----------------------------

@admin.register(InterviewSchedule)
class InterviewScheduleAdmin(admin.ModelAdmin):

    list_display = (
        "application",
        "scheduled_at",
        "status",
        "reminder_sent",
    )

    list_filter = (
        "status",
        "reminder_sent",
    )

    search_fields = (
        "application__candidate__user__username",
        "application__job__title",
    )


# ----------------------------
# AI Interview Answer
# ----------------------------

@admin.register(AIInterviewAnswer)
class AIInterviewAnswerAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ai_call",
        "question_order",
        "question_text",
        "answer_text",
        "created_at",
    )

    list_filter = (
        "question_order",
    )


# ----------------------------
# AI Screening Report
# ----------------------------

@admin.register(AIScreeningReport)
class AIScreeningReportAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ai_call",
        "overall_score",
        "recommendation",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "ai_call__id",
        "recommendation",
        "summary",
    )

    list_filter = (
        "recommendation",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


# ----------------------------
# AI Interview Session
# ----------------------------

@admin.register(AIInterviewSession)
class AIInterviewSessionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "ai_call",
        "status",
        "started_at",
        "ended_at",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "ai_call__id",
    )

    readonly_fields = (
        "started_at",
        "ended_at",
        "created_at",
        "updated_at",
    )


# ----------------------------
# AI Call Log
# ----------------------------

@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "session",
        "event",
        "message",
        "created_at",
    )

    list_filter = (
        "event",
        "created_at",
    )

    search_fields = (
        "session__id",
        "message",
    )

    readonly_fields = (
        "created_at",
    )
@admin.register(AIQuestionTemplate)
class AIQuestionTemplateAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "category",
        "question_text",
        "order",
        "is_active",
    )

    list_filter = (
        "category",
        "is_active",
    )

    search_fields = (
        "question_text",
    )


@admin.register(AIQuestionJobMapping)
class AIQuestionJobMappingAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "job",
        "question",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "question__question_text",
    )