import os

from rest_framework import serializers

from .models import (
    AIInterviewConfig,
    Application,
    ApplicationResumeParse,
    CandidateProfile,
    CustomUser,
    EmployerProfile,
    InterviewSchedule,
    Job,
    SavedJob,
)


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password",
            "role",
            "phone_number",
        ]

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=validated_data["role"],
            phone_number=validated_data.get("phone_number"),
        )
        return user

class CandidateProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = CandidateProfile
        fields = [
            "id",
            "user",
            "skills",
            "education",
            "experience",
            "expected_salary",
            "resume",
            "is_deleted",
        ]
        read_only_fields = ["user"]

    def validate_experience(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Experience cannot be negative."
            )
        return value

    def validate_expected_salary(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Expected salary must be greater than zero."
            )
        return value

    def validate_skills(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Skills cannot be empty."
            )
        return value

    def validate_education(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Education cannot be empty."
            )
        return value

    def validate_resume(self, value):
        if value is None:
            return value

        allowed_extensions = [".pdf", ".doc", ".docx"]

        extension = os.path.splitext(value.name)[1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only PDF, DOC and DOCX files are allowed."
            )

        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Resume size must not exceed 5 MB."
            )

        return value
# ----------------------------
# Public Candidate Profile Serializer
# ----------------------------

class PublicCandidateProfileSerializer(
    serializers.ModelSerializer
):

    username = serializers.CharField(
        source="user.username",
        read_only=True,
    )

    class Meta:

        model = CandidateProfile

        fields = [
            "id",
            "username",
            "skills",
            "education",
            "experience",
        ]
class EmployerProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "user",
            "company_name",
            "domain",
            "company_size",
            "is_verified",
            "is_deleted",
        ]
        read_only_fields = [
            "user",
            "is_verified",
            "is_deleted",
        ]

    def validate_company_name(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Company name cannot be empty."
            )
        return value

    def validate_domain(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Domain cannot be empty."
            )
        return value

    def validate_company_size(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Company size must be greater than zero."
            )
        return value
# ----------------------------
# Public Employer Profile Serializer
# ----------------------------

class PublicEmployerProfileSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = EmployerProfile

        fields = [
            "id",
            "company_name",
            "domain",
            "company_size",
            "is_verified",
        ]

# ------------- jobserializer -----------------
class JobSerializer(serializers.ModelSerializer):

    class Meta:

        model = Job

        fields = [
            "id",
            "employer",
            "title",
            "description",
            "skills",
            "experience",
            "salary_min",
            "salary_max",
            "location",
            "job_type",
            "ai_interview_duration",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "employer",
            "created_at",
            "updated_at",
        ]

    # ----------------------------
    # Title Validation
    # ----------------------------

    def validate_title(self, value):

        if not value.strip():

            raise serializers.ValidationError(
                "Job title cannot be empty."
            )

        return value

    # ----------------------------
    # Description Validation
    # ----------------------------

    def validate_description(self, value):

        if not value.strip():

            raise serializers.ValidationError(
                "Description cannot be empty."
            )

        return value

    # ----------------------------
    # Skills Validation
    # ----------------------------

    def validate_skills(self, value):

        if not value.strip():

            raise serializers.ValidationError(
                "Skills cannot be empty."
            )

        return value

    # ----------------------------
    # Experience Validation
    # ----------------------------

    def validate_experience(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "Experience cannot be negative."
            )

        return value

    # ----------------------------
    # Minimum Salary Validation
    # ----------------------------

    def validate_salary_min(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "Minimum salary cannot be negative."
            )

        return value

    # ----------------------------
    # Maximum Salary Validation
    # ----------------------------

    def validate_salary_max(self, value):

        if value < 0:

            raise serializers.ValidationError(
                "Maximum salary cannot be negative."
            )

        return value
    # ----------------------------
    # Location Validation
    # ----------------------------

    def validate_location(self, value):

        if not value.strip():

            raise serializers.ValidationError(
                "Location cannot be empty."
            )

        return value
    # ----------------------------
    # Salary Range Validation
    # ----------------------------

    def validate(self, data):

        salary_min = data.get(
            "salary_min",
            self.instance.salary_min
            if self.instance
            else None,
        )

        salary_max = data.get(
            "salary_max",
            self.instance.salary_max
            if self.instance
            else None,
        )

        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise serializers.ValidationError(
                {
                    "salary_max":
                    "Maximum salary must be greater than or equal to minimum salary."
                }
            )

        return data
# ----------------------------
# Application Serializer
# ----------------------------

class ApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Application

        fields = [
            "id",
            "candidate",
            "job",
            "resume_snapshot",
            "status",
            "applied_at",
        ]

        read_only_fields = [
            "candidate",
            "job",
            "resume_snapshot",
            "status",
            "applied_at",
        ]

class ApplicationStatusSerializer(serializers.Serializer):

    status = serializers.ChoiceField(
        choices=Application.STATUS_CHOICES
    )

    def validate_status(self, value):
        return value
# ----------------------------
# Candidate Dashboard Serializer
# ----------------------------

class CandidateDashboardSerializer(serializers.Serializer):

    total_applications = serializers.IntegerField()

    saved_jobs = serializers.IntegerField()

    applied = serializers.IntegerField()

    shortlisted = serializers.IntegerField()

    interview_scheduled = serializers.IntegerField()

    selected = serializers.IntegerField()

    rejected = serializers.IntegerField()
# ----------------------------
# Saved Job Serializer
# ----------------------------

class SavedJobSerializer(serializers.ModelSerializer):

    class Meta:
        model = SavedJob

        fields = [
            "id",
            "candidate",
            "job",
            "saved_at",
        ]

        read_only_fields = [
            "candidate",
            "job",
            "saved_at",
            ]
# ----------------------------
# Employer Candidate Review Serializer
# ----------------------------

class EmployerCandidateReviewSerializer(
    serializers.ModelSerializer
):

    candidate_username = serializers.CharField(
        source="candidate.user.username",
        read_only=True,
    )

    resume_url = serializers.FileField(
        source="resume_snapshot",
        read_only=True,
    )

    parsed_resume = serializers.SerializerMethodField()

    ats_score = serializers.SerializerMethodField()

    class Meta:

        model = Application

        fields = [
            "id",
            "status",
            "is_manual_override",
            "applied_at",
            "status_updated_at",

            "candidate_username",

            "resume_url",

            "parsed_resume",

            "ats_score",
        ]

    # ----------------------------------------
    # Actual submitted resume data
    # ----------------------------------------

    def get_parsed_resume(self, obj):

        try:

            return obj.resume_parse.parsed_data

        except ApplicationResumeParse.DoesNotExist:

            return None

    # ----------------------------------------
    # ATS score breakdown
    # ----------------------------------------

    def get_ats_score(self, obj):

        ats_score = obj.candidate.ats_scores.filter(
            job=obj.job
        ).first()

        if not ats_score:

            return None

        return {
            "skill_score": float(
                ats_score.skill_score
            ),

            "matched_skill_count":
            ats_score.matched_skill_count,

            "experience_score": float(
                ats_score.experience_score
            ),

            "education_score": float(
                ats_score.education_score
            ),

            "match_percentage": float(
                ats_score.match_percentage
            ),
        }
# ----------------------------
# AI Interview Configuration Serializer
# ----------------------------

class AIInterviewConfigSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = AIInterviewConfig

        fields = [
            "id",
            "job",
            "call_start_time",
            "call_end_time",
            "max_call_attempts",
            "retry_interval_minutes",
            "voice_type",
            "language",
            "speaking_speed",
            "tone",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "job",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):

        call_start_time = data.get(
            "call_start_time"
        )

        call_end_time = data.get(
            "call_end_time"
        )

        if (
            call_start_time
            and call_end_time
            and call_start_time >= call_end_time
        ):

            raise serializers.ValidationError(
                {
                    "call_end_time":
                    "Call end time must be later than call start time."
                }
            )

        return data
# ----------------------------
# Interview Schedule Serializer
# ----------------------------

class InterviewScheduleSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = InterviewSchedule

        fields = [
            "id",
            "application",
            "scheduled_at",
            "meeting_link",
            "meeting_location",
            "instructions",
            "status",
            "reminder_sent",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "application",
            "status",
            "reminder_sent",
            "created_at",
            "updated_at",
        ]