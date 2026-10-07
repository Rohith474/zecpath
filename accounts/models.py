from django.contrib.auth.models import AbstractUser
from django.db import models
from accounts.services.encrypted_field import EncryptedTextField

# ----------------------------
# Custom User Model
# ----------------------------

class CustomUser(AbstractUser):

    ADMIN = "Admin"
    EMPLOYER = "Employer"
    CANDIDATE = "Candidate"

    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (EMPLOYER, "Employer"),
        (CANDIDATE, "Candidate"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=CANDIDATE,
    )

    is_flagged = models.BooleanField(
        default=False,
    )
    phone_number = EncryptedTextField(
    blank=True,
    null=True,
    )

    def __str__(self):
        return self.username


# ----------------------------
# Candidate Profile Model
# ----------------------------

class CandidateProfile(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )

    skills = models.TextField()

    education = models.CharField(
        max_length=255,
    )

    experience = models.IntegerField()

    expected_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    resume = models.FileField(
        upload_to="resumes/",
        null=True,
        blank=True,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return self.user.username

# ----------------------------
# Resume Parse Model
# ----------------------------

class ResumeParse(models.Model):

    candidate = models.OneToOneField(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="resume_parse",
    )

    raw_text = models.TextField(
        blank=True,
    )

    cleaned_text = models.TextField(
        blank=True,
    )

    parsed_data = models.JSONField(
        default=dict,
        blank=True,
    )

    parsed_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Resume Parse - {self.candidate.user.username}"
# ----------------------------
# Employer Profile Model
# ----------------------------

class EmployerProfile(models.Model):

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="employer_profile",
    )

    company_name = models.CharField(
        max_length=255,
    )

    domain = models.CharField(
        max_length=255,
    )

    company_size = models.IntegerField()

    is_verified = models.BooleanField(
        default=False,
    )

    is_deleted = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return self.company_name


# ----------------------------
# Job Model
# ----------------------------

class Job(models.Model):

    FULL_TIME = "Full Time"
    PART_TIME = "Part Time"
    INTERNSHIP = "Internship"

    JOB_TYPE_CHOICES = [
        (FULL_TIME, "Full Time"),
        (PART_TIME, "Part Time"),
        (INTERNSHIP, "Internship"),
    ]

    ACTIVE = "Active"
    CLOSED = "Closed"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (CLOSED, "Closed"),
    ]

    employer = models.ForeignKey(
        EmployerProfile,
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    skills = models.TextField()

    experience = models.IntegerField()

    salary_min = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    salary_max = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    location = models.CharField(
        max_length=255,
    )

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES,
        default=FULL_TIME,
    )
    ai_interview_duration = models.PositiveIntegerField(
    choices=[
        (15, "15 minutes"),
        (30, "30 minutes"),
        (45, "45 minutes"),
        (60, "60 minutes"),
    ],
    default=30,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.title


# ----------------------------
# Application Model
# ----------------------------

class Application(models.Model):

    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview Scheduled"
    REJECTED = "Rejected"
    SELECTED = "Selected"

    STATUS_CHOICES = [
        (APPLIED, "Applied"),
        (SHORTLISTED, "Shortlisted"),
        (INTERVIEW, "Interview Scheduled"),
        (REJECTED, "Rejected"),
        (SELECTED, "Selected"),
    ]

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    resume_snapshot = models.FileField(
        upload_to="application_resumes/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=APPLIED,
    )
    is_manual_override = models.BooleanField(
    default=False
    )

    status_updated_at = models.DateTimeField(
        auto_now=True,
    )

    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_candidate_job_application",
            )
        ]

    def __str__(self):
        return (
            f"{self.candidate.user.username} "
            f"-> {self.job.title}"
        )
# ----------------------------
# Application Resume Parse Model
# ----------------------------

class ApplicationResumeParse(models.Model):

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="resume_parse",
    )

    raw_text = models.TextField(
        blank=True,
    )

    cleaned_text = models.TextField(
        blank=True,
    )

    parsed_data = models.JSONField(
        default=dict,
        blank=True,
    )

    parsed_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"Application Resume Parse - "
            f"{self.application.candidate.user.username} - "
            f"{self.application.job.title}"
        )

# ----------------------------
# Saved Job Model
# ----------------------------

class SavedJob(models.Model):

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="saved_jobs",
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="saved_by",
    )

    saved_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = ["-saved_at"]

        indexes = [
            models.Index(
                fields=["candidate", "-saved_at"],
                name="savedjob_candidate_saved_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_saved_job",
            )
        ]

    def __str__(self):

        return (
            f"{self.candidate.user.username} "
            f"saved {self.job.title}"
        )
# ----------------------------
# Audit Log Model
# ----------------------------

class AuditLog(models.Model):

    ACTOR_TYPE_CHOICES = [
        ("USER", "User"),
        ("ADMIN", "Admin"),
        ("AI", "AI"),
        ("SYSTEM", "System"),
        ("SECURITY", "Security"),
    ]

    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )

    actor_type = models.CharField(
        max_length=20,
        choices=ACTOR_TYPE_CHOICES,
        default="ADMIN",
    )

    action = models.CharField(
        max_length=100,
    )

    target_type = models.CharField(
        max_length=50,
    )

    target_id = models.IntegerField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.admin.username if self.admin else 'System'} "
            f"- {self.action}"
        )
# ----------------------------
# ATS Score Model
# ----------------------------

class ATSScore(models.Model):

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="ats_scores",
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name="ats_scores",
    )

    skill_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    matched_skill_count = models.IntegerField(
    default=0,
    )

    experience_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    education_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    match_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["candidate", "job"],
                name="unique_candidate_job_ats_score",
            )
        ]

        ordering = [
            "-match_percentage"
        ]

    def __str__(self):
        return (
            f"{self.candidate.user.username} "
            f"- {self.job.title} "
            f"- {self.match_percentage}%"
        )
# ----------------------------
# Notification Model
# ----------------------------

class Notification(models.Model):

    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["candidate", "-created_at"],
                name="notif_candidate_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Notification for "
            f"{self.candidate.user.username}"
        )
# ----------------------------
# Email Log Model
# ----------------------------

class EmailLog(models.Model):

    PENDING = "Pending"
    SENT = "Sent"
    FAILED = "Failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SENT, "Sent"),
        (FAILED, "Failed"),
    ]

    recipient_email = models.EmailField()

    subject = models.CharField(
        max_length=255,
    )

    template_name = models.CharField(
        max_length=255,
    )

    context = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    attempts = models.PositiveIntegerField(
        default=0,
    )

    error_message = models.TextField(
        blank=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"{self.subject} → "
            f"{self.recipient_email} "
            f"({self.status})"
        )

# ----------------------------
# AI Interview Configuration Model
# ----------------------------

class AIInterviewConfig(models.Model):

    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="ai_interview_config",
    )

    # ----------------------------------------
    # Call Window Configuration
    # ----------------------------------------

    call_start_time = models.TimeField()

    call_end_time = models.TimeField()

    # ----------------------------------------
    # Retry Configuration
    # ----------------------------------------

    max_call_attempts = models.PositiveIntegerField(
        default=3,
    )

    retry_interval_minutes = models.PositiveIntegerField(
        default=60,
    )

    # ----------------------------------------
    # Voice Configuration
    # ----------------------------------------

    MALE = "Male"
    FEMALE = "Female"

    VOICE_CHOICES = [
        (MALE, "Male"),
        (FEMALE, "Female"),
    ]

    voice_type = models.CharField(
        max_length=10,
        choices=VOICE_CHOICES,
        default=FEMALE,
    )

    # ----------------------------------------
    # Language Configuration
    # ----------------------------------------

    ENGLISH = "English"
    HINDI = "Hindi"
    MALAYALAM = "Malayalam"
    TAMIL = "Tamil"

    LANGUAGE_CHOICES = [
        (ENGLISH, "English"),
        (HINDI, "Hindi"),
        (MALAYALAM, "Malayalam"),
        (TAMIL, "Tamil"),
    ]

    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default=ENGLISH,
    )

    # ----------------------------------------
    # Future Voice Settings
    # ----------------------------------------

    speaking_speed = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.00,
    )

    tone = models.CharField(
        max_length=50,
        default="Professional",
    )

    # ----------------------------------------
    # AI Screening Configuration
    # ----------------------------------------

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"AI Interview Config - "
            f"{self.job.title}"
        )


# ----------------------------
# AI Call Model
# ----------------------------

class AICall(models.Model):

    PENDING = "Pending"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    ANSWERED = "Answered"
    MISSED = "Missed"
    RETRY_SCHEDULED = "Retry Scheduled"
    FAILED = "Failed"
    COMPLETED = "Completed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SCHEDULED, "Scheduled"),
        (IN_PROGRESS, "In Progress"),
        (ANSWERED, "Answered"),
        (MISSED, "Missed"),
        (RETRY_SCHEDULED, "Retry Scheduled"),
        (FAILED, "Failed"),
        (COMPLETED, "Completed"),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="ai_call",
    )

    config = models.ForeignKey(
        AIInterviewConfig,
        on_delete=models.SET_NULL,
        null=True,
        related_name="calls",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    attempt_count = models.PositiveIntegerField(
        default=0,
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"AI Call - "
            f"{self.application.candidate.user.username} "
            f"- {self.application.job.title}"
        )

# ----------------------------------------
# AI Interview Answer
# ----------------------------------------

class AIInterviewAnswer(models.Model):

    ai_call = models.ForeignKey(
        AICall,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question_order = models.PositiveIntegerField()

    question_text = models.TextField()

    answer_text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "ai_call",
                    "question_order",
                ],
                name="unique_ai_call_question_order",
            )
        ]

        ordering = [
            "question_order",
        ]

    def __str__(self):

        return (
            f"AI Call {self.ai_call.id} - "
            f"Question {self.question_order}"
        )
# ----------------------------------------
# Candidate Interview Availability
# ----------------------------------------

class CandidateInterviewAvailability(models.Model):

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="interview_availability",
    )

    preferred_date = models.DateField()

    preferred_time = models.TimeField()

    timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"{self.application.candidate.user.username} "
            f"- {self.preferred_date} "
            f"{self.preferred_time}"
        )
class AIAnswerEvaluation(models.Model):
    answer = models.OneToOneField(
        AIInterviewAnswer,
        on_delete=models.CASCADE,
        related_name="evaluation"
    )

    relevance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completeness_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    keyword_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    annotations = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Evaluation - Answer {self.answer.id}"
# ----------------------------
# Interview Schedule Model
# ----------------------------

class InterviewSchedule(models.Model):

    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    RESCHEDULED = "Rescheduled"

    STATUS_CHOICES = [
        (SCHEDULED, "Scheduled"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (RESCHEDULED, "Rescheduled"),
    ]

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="interview_schedule",
    )

    scheduled_at = models.DateTimeField()

    meeting_link = models.URLField(
        blank=True,
    )

    meeting_location = models.CharField(
        max_length=255,
        blank=True,
    )

    instructions = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=SCHEDULED,
    )

    reminder_sent = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"Interview - "
            f"{self.application.candidate.user.username} "
            f"- {self.application.job.title}"
        )

# ----------------------------
# Scheduled Interview Session Model
# ----------------------------

class ScheduledInterviewSession(models.Model):

    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"

    STATUS_CHOICES = [
        (NOT_STARTED, "Not Started"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    PASSED = "Passed"
    RESULT_FAILED = "Failed"

    RESULT_CHOICES = [
        (PASSED, "Passed"),
        (RESULT_FAILED, "Failed"),
    ]

    interview = models.OneToOneField(
        InterviewSchedule,
        on_delete=models.CASCADE,
        related_name="session",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=NOT_STARTED,
    )

    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        return (
            f"Interview Session - "
            f"{self.interview.application.candidate.user.username} "
            f"- {self.interview.application.job.title}"
        )
# ----------------------------
# Scheduled Interview Question Model
# ----------------------------

class ScheduledInterviewQuestion(models.Model):

    session = models.ForeignKey(
        ScheduledInterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    question_order = models.PositiveIntegerField()

    question_text = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):

        return (
            f"Question {self.question_order} - "
            f"{self.session.interview.application.job.title}"
        )

    class Meta:

        ordering = [
            "question_order",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "session",
                    "question_order",
                ],
                name="unique_scheduled_interview_question_order",
            ),
        ]


# ----------------------------
# Scheduled Interview Answer Model
# ----------------------------

class ScheduledInterviewAnswer(models.Model):

    question = models.OneToOneField(
        ScheduledInterviewQuestion,
        on_delete=models.CASCADE,
        related_name="answer",
    )

    answer_text = models.TextField()

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    evaluation_feedback = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):

        return (
            f"Answer - "
            f"Question {self.question.question_order}"
        )
    
class InterviewReminder(models.Model):

    REMINDER_24_HOURS = "24_HOURS"
    REMINDER_1_HOUR = "1_HOUR"
    REMINDER_AT_TIME = "AT_TIME"

    REMINDER_TYPE_CHOICES = [
        (REMINDER_24_HOURS, "24 Hours Before"),
        (REMINDER_1_HOUR, "1 Hour Before"),
        (REMINDER_AT_TIME, "At Interview Time"),
]

    PENDING = "Pending"
    SENT = "Sent"
    FAILED = "Failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SENT, "Sent"),
        (FAILED, "Failed"),
    ]

    interview = models.ForeignKey(
        InterviewSchedule,
        on_delete=models.CASCADE,
        related_name="reminders",
    )

    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES,
    )

    scheduled_for = models.DateTimeField()

    interview_scheduled_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    email_log = models.OneToOneField(
        EmailLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_reminder",
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "interview",
                    "reminder_type",
                    "interview_scheduled_at",
                ],
                name="unique_interview_reminder",
            )
        ]
# ----------------------------------------
# AI Screening Report
# ----------------------------------------

class AIScreeningReport(models.Model):

    ai_call = models.OneToOneField(
        AICall,
        on_delete=models.CASCADE,
        related_name="screening_report",
    )

    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    summary = models.TextField(
        blank=True,
    )

    recommendation = models.CharField(
        max_length=100,
        blank=True,
    )

    analysis = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"AI Screening Report - "
            f"AI Call {self.ai_call.id}"
        )
# ----------------------------------------
# AI Interview Session
# ----------------------------------------

class AIInterviewSession(models.Model):

    STATUS_CHOICES = [
        ("Started", "Started"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    ai_call = models.OneToOneField(
        AICall,
        on_delete=models.CASCADE,
        related_name="interview_session",
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Started",
    )

    transcript = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"AI Interview Session {self.id}"


# ----------------------------------------
# AI Call Log
# ----------------------------------------

class CallLog(models.Model):

    EVENT_CHOICES = [
        ("CALL_CREATED", "Call Created"),
        ("CALL_STARTED", "Call Started"),
        ("QUESTION_ASKED", "Question Asked"),
        ("ANSWER_RECEIVED", "Answer Received"),
        ("CALL_COMPLETED", "Call Completed"),
        ("CALL_FAILED", "Call Failed"),
    ]

    session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name="call_logs",
    )

    event = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
    )

    message = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"Session {self.session.id} - "
            f"{self.event}"
        )
class AIQuestionTemplate(models.Model):

    CATEGORY_CHOICES = [
        ("Introduction", "Introduction"),
        ("Experience", "Experience"),
        ("Skills", "Skills"),
        ("Availability", "Availability"),
        ("Salary", "Salary"),
    ]

    question_text = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
    )

    order = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "order"]

    def __str__(self):
        return f"{self.category} - {self.question_text}"


class AIQuestionJobMapping(models.Model):

    question = models.ForeignKey(
        AIQuestionTemplate,
        on_delete=models.CASCADE,
        related_name="job_mappings",
    )

    job = models.ForeignKey(
        "Job",
        on_delete=models.CASCADE,
        related_name="ai_question_mappings",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "job"],
                name="unique_ai_question_job_mapping",
            )
        ]

    def __str__(self):
        return f"{self.job} - {self.question}"
class AICandidateReport(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="ai_candidate_report",
    )

    ats_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    ai_call_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    strengths = models.JSONField(
        default=list,
        blank=True,
    )

    risks = models.JSONField(
        default=list,
        blank=True,
    )

    summary = models.TextField(
        blank=True,
    )

    report_data = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AI Candidate Report - Application {self.application_id}"

class SubscriptionPlan(models.Model):

    MONTHLY = "Monthly"
    YEARLY = "Yearly"

    BILLING_INTERVAL_CHOICES = [
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    billing_interval = models.CharField(
        max_length=20,
        choices=BILLING_INTERVAL_CHOICES,
        default=MONTHLY,
    )

    job_post_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum active jobs. Null means unlimited.",
    )

    ai_call_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum AI calls per billing period. Null means unlimited.",
    )
    candidate_access_limit = models.PositiveIntegerField(
    null=True,
    blank=True,
    help_text="Maximum candidates accessible per billing period. Null means unlimited."
    )

    analytics_access = models.BooleanField(
        default=False,
    )
    features = models.JSONField(
    default=dict,
    blank=True,
    help_text="Feature entitlements available for this plan.",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name
    
class UserSubscription(models.Model):

    ACTIVE = "Active"
    TRIALING = "Trialing"
    PAST_DUE = "Past Due"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (TRIALING, "Trialing"),
        (PAST_DUE, "Past Due"),
        (CANCELLED, "Cancelled"),
        (EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
    )

    started_at = models.DateTimeField()

    current_period_start = models.DateTimeField()

    current_period_end = models.DateTimeField()

    grace_period_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
class PaymentTransaction(models.Model):

    PENDING = "Pending"
    SUCCESS = "Success"
    FAILED = "Failed"
    REFUNDED = "Refunded"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    SUBSCRIPTION = "Subscription"
    RENEWAL = "Renewal"
    REFUND = "Refund"

    TRANSACTION_TYPE_CHOICES = [
        (SUBSCRIPTION, "Subscription"),
        (RENEWAL, "Renewal"),
        (REFUND, "Refund"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )
    plan = models.ForeignKey(
    SubscriptionPlan,
    on_delete=models.PROTECT,
    related_name="payment_transactions",
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    payment_gateway = models.CharField(
        max_length=50,
        blank=True,
    )
    gateway_order_id = models.CharField(
    max_length=255,
    blank=True,
    )
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
    )
    razorpay_refund_id = models.CharField(
        max_length=255,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default=SUBSCRIPTION,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency}"

class RefundRequest(models.Model):

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="refund_requests",
    )

    payment_transaction = models.OneToOneField(
        PaymentTransaction,
        on_delete=models.CASCADE,
        related_name="refund_request",
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_refund_requests",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    admin_note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"Refund request #{self.id} - "
            f"{self.user.username} - "
            f"{self.payment_transaction.amount} "
            f"{self.payment_transaction.currency}"
        )
    
class BillingHistory(models.Model):

    PENDING = "Pending"
    PAID = "Paid"
    FAILED = "Failed"
    REFUNDED = "Refunded"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="billing_history",
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_history",
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="billing_history",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=10,
        default="INR",
    )

    billing_period_start = models.DateTimeField()

    billing_period_end = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )

    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_records",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.amount}"
    