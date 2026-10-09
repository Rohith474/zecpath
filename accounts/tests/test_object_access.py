from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    Application,
    CandidateProfile,
    CustomUser,
    EmployerProfile,
    Job,
    Notification,
    SavedJob,
)


class ObjectLevelAccessTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # ====================================
        # Candidate 1
        # ====================================

        self.candidate1_user = (
            CustomUser.objects.create_user(
                username="candidate1",
                email="candidate1@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

        self.candidate1 = (
            CandidateProfile.objects.create(
                user=self.candidate1_user,
                skills="Python, Django",
                education="B.Sc Computer Science",
                experience=1,
                expected_salary=50000,
            )
        )

        # ====================================
        # Candidate 2
        # ====================================

        self.candidate2_user = (
            CustomUser.objects.create_user(
                username="candidate2",
                email="candidate2@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

        self.candidate2 = (
            CandidateProfile.objects.create(
                user=self.candidate2_user,
                skills="Java, Spring Boot",
                education="B.Sc Computer Science",
                experience=2,
                expected_salary=60000,
            )
        )

        # ====================================
        # Employer 1
        # ====================================

        self.employer1_user = (
            CustomUser.objects.create_user(
                username="employer1",
                email="employer1@test.com",
                password="TestPassword123!",
                role=CustomUser.EMPLOYER,
            )
        )

        self.employer1 = (
            EmployerProfile.objects.create(
                user=self.employer1_user,
                company_name="Company One",
                domain="Technology",
                company_size=100,
                is_verified=True,
            )
        )

        # ====================================
        # Employer 2
        # ====================================

        self.employer2_user = (
            CustomUser.objects.create_user(
                username="employer2",
                email="employer2@test.com",
                password="TestPassword123!",
                role=CustomUser.EMPLOYER,
            )
        )

        self.employer2 = (
            EmployerProfile.objects.create(
                user=self.employer2_user,
                company_name="Company Two",
                domain="Software",
                company_size=50,
                is_verified=True,
            )
        )

        # ====================================
        # Job 1 - Employer 1
        # ====================================

        self.job1 = Job.objects.create(
            employer=self.employer1,
            title="Python Developer",
            description="Python backend development",
            skills="Python, Django",
            experience=1,
            salary_min=30000,
            salary_max=60000,
            location="Chennai",
            job_type=Job.FULL_TIME,
            status=Job.ACTIVE,
        )

        # ====================================
        # Job 2 - Employer 2
        # ====================================

        self.job2 = Job.objects.create(
            employer=self.employer2,
            title="Java Developer",
            description="Java backend development",
            skills="Java, Spring Boot",
            experience=2,
            salary_min=40000,
            salary_max=70000,
            location="Bangalore",
            job_type=Job.FULL_TIME,
            status=Job.ACTIVE,
        )

        # ====================================
        # Application - Candidate 1 → Job 1
        # ====================================

        self.application1 = (
            Application.objects.create(
                candidate=self.candidate1,
                job=self.job1,
                status=Application.APPLIED,
            )
        )

        # ====================================
        # Application - Candidate 2 → Job 2
        # ====================================

        self.application2 = (
            Application.objects.create(
                candidate=self.candidate2,
                job=self.job2,
                status=Application.APPLIED,
            )
        )

        # ====================================
        # Notification - Candidate 1
        # ====================================

        self.notification1 = (
            Notification.objects.create(
                candidate=self.candidate1,
                application=self.application1,
                message="Your application was received.",
            )
        )

        # ====================================
        # Saved Job - Candidate 1
        # ====================================

        self.saved_job1 = (
            SavedJob.objects.create(
                candidate=self.candidate1,
                job=self.job1,
            )
        )

    # ====================================
    # Test 1
    # Candidate cannot access another
    # candidate's application
    # ====================================

    def test_candidate_cannot_access_another_candidates_application(
        self
    ):

        self.client.force_authenticate(
            user=self.candidate2_user
        )

        url = reverse(
            "application-detail",
            kwargs={
                "pk": self.application1.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    # ====================================
    # Test 2
    # Employer cannot view applicants
    # for another employer's job
    # ====================================

    def test_employer_cannot_view_another_employers_applicants(
        self
    ):

        self.client.force_authenticate(
            user=self.employer2_user
        )

        url = reverse(
            "dashboard-job-applicants",
            kwargs={
                "job_id": self.job1.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    # ====================================
    # Test 3
    # Employer cannot update an application
    # belonging to another employer's job
    # ====================================

    def test_employer_cannot_update_another_employers_application(
        self
    ):

        self.client.force_authenticate(
            user=self.employer2_user
        )

        url = reverse(
            "application-status-update",
            kwargs={
                "pk": self.application1.id
            },
        )

        data = {
            "status": Application.SHORTLISTED,
        }

        response = self.client.patch(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.application1.refresh_from_db()

        self.assertEqual(
            self.application1.status,
            Application.APPLIED,
        )

    # ====================================
    # Test 4
    # Candidate cannot mark another
    # candidate's notification as read
    # ====================================

    def test_candidate_cannot_mark_another_candidates_notification_as_read(
        self
    ):

        self.client.force_authenticate(
            user=self.candidate2_user
        )

        url = reverse(
            "mark-notification-read",
            kwargs={
                "pk": self.notification1.id
            },
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            404,
        )

        self.notification1.refresh_from_db()

        self.assertFalse(
            self.notification1.is_read
        )

    # ====================================
    # Test 5
    # Candidate cannot remove another
    # candidate's saved job
    # ====================================

    def test_candidate_cannot_remove_another_candidates_saved_job(
        self
    ):

        self.client.force_authenticate(
            user=self.candidate2_user
        )

        url = reverse(
            "unsave-job",
            kwargs={
                "job_id": self.job1.id
            },
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertTrue(
            SavedJob.objects.filter(
                id=self.saved_job1.id
            ).exists()
        )