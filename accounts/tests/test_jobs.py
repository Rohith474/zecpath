from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    CandidateProfile,
    CustomUser,
    EmployerProfile,
    Job,
    SubscriptionPlan,
    UserSubscription,
)


class JobFlowTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # --------------------------------
        # Candidate
        # --------------------------------

        self.candidate_user = (
            CustomUser.objects.create_user(
                username="candidate1",
                email="candidate@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

        self.candidate_profile = (
            CandidateProfile.objects.create(
                user=self.candidate_user,
                skills="Python, Django",
                education="B.Sc Computer Science",
                experience=1,
                expected_salary=50000,
            )
        )

        # --------------------------------
        # Employer 1
        # --------------------------------

        self.employer_user = (
            CustomUser.objects.create_user(
                username="employer1",
                email="employer@test.com",
                password="TestPassword123!",
                role=CustomUser.EMPLOYER,
            )
        )

        self.employer_profile = (
            EmployerProfile.objects.create(
                user=self.employer_user,
                company_name="Tech Company",
                domain="Technology",
                company_size=100,
                is_verified=True,
            )
        )
        # --------------------------------
        # Active subscription for Employer 1
        # --------------------------------

        self.subscription_plan = (
            SubscriptionPlan.objects.create(
                name="Test Pro Plan",
                description="Test subscription plan",
                price=999,
                currency="INR",
                billing_interval=SubscriptionPlan.MONTHLY,
                job_post_limit=20,
                ai_call_limit=100,
                analytics_access=True,
                features={
                    "basic_ats": True,
                    "basic_job_posting": True,
                    "ai_interview": True,
                    "advanced_analytics": True,
                },
                is_active=True,
            )
        )

        now = timezone.now()

        self.employer_subscription = (
            UserSubscription.objects.create(
                user=self.employer_user,
                plan=self.subscription_plan,
                status=UserSubscription.ACTIVE,
                started_at=now,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
        )

        # --------------------------------
        # Employer 2
        # --------------------------------

        self.employer2_user = (
            CustomUser.objects.create_user(
                username="employer2",
                email="employer2@test.com",
                password="TestPassword123!",
                role=CustomUser.EMPLOYER,
            )
        )

        self.employer2_profile = (
            EmployerProfile.objects.create(
                user=self.employer2_user,
                company_name="Another Company",
                domain="Software",
                company_size=50,
                is_verified=True,
            )
        )

        # --------------------------------
        # Existing Active Job
        # --------------------------------

        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Python Developer",
            description="Python development job",
            skills="Python, Django",
            experience=1,
            salary_min=30000,
            salary_max=60000,
            location="Chennai",
            job_type=Job.FULL_TIME,
            status=Job.ACTIVE,
        )

    # ====================================
    # Employer creates a job
    # ====================================

    def test_employer_can_create_job(self):

        self.client.force_authenticate(
            user=self.employer_user
        )

        url = reverse("job-create")

        data = {
            "title": "Django Developer",
            "description": "Django backend development",
            "skills": "Python, Django, DRF",
            "experience": 2,
            "salary_min": 40000,
            "salary_max": 80000,
            "location": "Bangalore",
            "job_type": Job.FULL_TIME,
            "status": Job.ACTIVE,
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertTrue(
            Job.objects.filter(
                title="Django Developer",
                employer=self.employer_profile,
            ).exists()
        )

    # ====================================
    # Candidate cannot create job
    # ====================================

    def test_candidate_cannot_create_job(self):

        self.client.force_authenticate(
            user=self.candidate_user
        )

        url = reverse("job-create")

        data = {
            "title": "Unauthorized Job",
            "description": "Should not be created",
            "skills": "Python",
            "experience": 1,
            "salary_min": 30000,
            "salary_max": 50000,
            "location": "Chennai",
            "job_type": Job.FULL_TIME,
            "status": Job.ACTIVE,
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertFalse(
            Job.objects.filter(
                title="Unauthorized Job"
            ).exists()
        )

    # ====================================
    # Candidate can view active jobs
    # ====================================

    def test_candidate_can_view_active_jobs(self):

        self.client.force_authenticate(
            user=self.candidate_user
        )

        url = reverse("job-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        # Paginated response
        self.assertEqual(
            len(response.data["results"]),
            1,
        )

        self.assertEqual(
            response.data["results"][0]["title"],
            "Python Developer",
        )

    # ====================================
    # Employer cannot update another
    # employer's job
    # ====================================

    def test_employer_cannot_update_another_employer_job(
        self
    ):

        self.client.force_authenticate(
            user=self.employer2_user
        )

        url = reverse(
            "job-update",
            kwargs={
                "pk": self.job.id
            },
        )

        data = {
            "title": "Hacked Job",
        }

        response = self.client.patch(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.job.refresh_from_db()

        self.assertEqual(
            self.job.title,
            "Python Developer",
        )

    # ====================================
    # Closed jobs should not appear
    # in public job listing
    # ====================================

    def test_closed_jobs_not_visible_in_job_list(
        self
    ):

        closed_job = Job.objects.create(
            employer=self.employer_profile,
            title="Closed Python Job",
            description="This job is closed",
            skills="Python",
            experience=1,
            salary_min=30000,
            salary_max=50000,
            location="Chennai",
            job_type=Job.FULL_TIME,
            status=Job.CLOSED,
        )

        self.client.force_authenticate(
            user=self.candidate_user
        )

        url = reverse("job-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        # Get jobs from paginated results
        job_ids = [
            job["id"]
            for job in response.data["results"]
        ]

        self.assertNotIn(
            closed_job.id,
            job_ids,
        )