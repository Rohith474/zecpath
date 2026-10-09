from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    CandidateProfile,
    CustomUser,
    EmployerProfile,
    Job,
)


class ATSRankingSecurityTests(TestCase):

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
        # Employer 1 - Owns the job
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
        # Employer 2 - Does not own job
        # --------------------------------

        self.other_employer_user = (
            CustomUser.objects.create_user(
                username="employer2",
                email="employer2@test.com",
                password="TestPassword123!",
                role=CustomUser.EMPLOYER,
            )
        )

        self.other_employer_profile = (
            EmployerProfile.objects.create(
                user=self.other_employer_user,
                company_name="Another Company",
                domain="Software",
                company_size=50,
                is_verified=True,
            )
        )

        # --------------------------------
        # Job
        # --------------------------------

        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Python Developer",
            description="Python backend developer",
            skills="Python, Django",
            experience=1,
            salary_min=30000,
            salary_max=60000,
            location="Chennai",
            job_type=Job.FULL_TIME,
            status=Job.ACTIVE,
        )

    # ====================================
    # Anonymous user cannot access ATS
    # rankings
    # ====================================

    def test_anonymous_user_cannot_access_rankings(
        self
    ):

        url = reverse(
            "ranked-candidates",
            kwargs={
                "job_id": self.job.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            401,
        )

    # ====================================
    # Candidate cannot access ATS rankings
    # ====================================

    def test_candidate_cannot_access_rankings(
        self
    ):

        self.client.force_authenticate(
            user=self.candidate_user
        )

        url = reverse(
            "ranked-candidates",
            kwargs={
                "job_id": self.job.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            403,
        )

    # ====================================
    # Different employer cannot access
    # another employer's ATS rankings
    # ====================================

    def test_other_employer_cannot_access_rankings(
        self
    ):

        self.client.force_authenticate(
            user=self.other_employer_user
        )

        url = reverse(
            "ranked-candidates",
            kwargs={
                "job_id": self.job.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            404,
        )

    # ====================================
    # Job owner can access ATS rankings
    # ====================================

    def test_job_owner_can_access_rankings(
        self
    ):

        self.client.force_authenticate(
            user=self.employer_user
        )

        url = reverse(
            "ranked-candidates",
            kwargs={
                "job_id": self.job.id
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )
class EmployerProfileSecurityTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # --------------------------------
        # Employer User
        # --------------------------------

        self.employer_user = (
            CustomUser.objects.create_user(
                username="employer1",
                email="employer1@test.com",
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
        # Another Authenticated User
        # --------------------------------

        self.candidate_user = (
            CustomUser.objects.create_user(
                username="candidate1",
                email="candidate1@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

    # ====================================
    # Public employer list must not expose
    # internal fields
    # ====================================

    def test_employer_list_hides_internal_fields(self):

        self.client.force_authenticate(
            user=self.candidate_user
        )

        url = reverse("employer-list")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

        employer = response.data["results"][0]

        # --------------------------------
        # Public fields must be visible
        # --------------------------------

        self.assertIn(
            "id",
            employer,
        )

        self.assertIn(
            "company_name",
            employer,
        )

        self.assertIn(
            "domain",
            employer,
        )

        self.assertIn(
            "company_size",
            employer,
        )

        self.assertIn(
            "is_verified",
            employer,
        )

        # --------------------------------
        # Internal fields must be hidden
        # --------------------------------

        self.assertNotIn(
            "user",
            employer,
        )

        self.assertNotIn(
            "is_deleted",
            employer,
        )
class CandidateProfileSecurityTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # --------------------------------
        # Candidate User
        # --------------------------------

        self.candidate_user = (
            CustomUser.objects.create_user(
                username="candidate1",
                email="candidate1@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

        # --------------------------------
        # Candidate Profile
        # --------------------------------

        self.candidate_profile = (
            CandidateProfile.objects.create(
                user=self.candidate_user,
                skills="Python, Django",
                education="B.Sc Computer Science",
                experience=2,
                expected_salary=75000,
                is_deleted=False,
            )
        )

        # --------------------------------
        # Another authenticated user
        # --------------------------------

        self.other_user = (
            CustomUser.objects.create_user(
                username="candidate2",
                email="candidate2@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

    # ====================================
    # Public candidate list must not expose
    # sensitive candidate fields
    # ====================================

    def test_candidate_list_hides_sensitive_fields(self):

        employer_user = CustomUser.objects.create_user(
            username="employer_security_test",
            email="employer_security_test@test.com",
            password="TestPassword123!",
            role=CustomUser.EMPLOYER,
        )

        self.client.force_authenticate(
            user=employer_user
        )

        url = reverse("candidate-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        candidate = response.data["results"][0]

        # Public fields must be visible
        self.assertIn("id", candidate)
        self.assertIn("username", candidate)
        self.assertIn("skills", candidate)
        self.assertIn("education", candidate)
        self.assertIn("experience", candidate)

        # Sensitive fields must not be exposed
        self.assertNotIn("user", candidate)
        self.assertNotIn("expected_salary", candidate)
        self.assertNotIn("resume", candidate)
        self.assertNotIn("is_deleted", candidate)