from django.test import TestCase
from django.urls import reverse
from django.test import override_settings
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)

from rest_framework.test import APIClient

from accounts.models import (
    CustomUser,
    CandidateProfile,
)


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": "test_media",
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class ResumeFileSecurityTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        # --------------------------------
        # Candidate User
        # --------------------------------

        self.candidate_user = (
            CustomUser.objects.create_user(
                username="candidate1",
                email="candidate@test.com",
                password="TestPassword123!",
                role=CustomUser.CANDIDATE,
            )
        )

        self.client.force_authenticate(
            user=self.candidate_user
        )

    # ====================================
    # Invalid file extension should fail
    # ====================================

    def test_invalid_resume_extension_rejected(
        self
    ):

        url = reverse(
            "candidate-profile-create"
        )

        resume = SimpleUploadedFile(
            "malicious.exe",
            b"fake executable content",
            content_type=(
                "application/octet-stream"
            ),
        )

        data = {
            "skills": "Python, Django",
            "education": "B.Sc Computer Science",
            "experience": 1,
            "expected_salary": 50000,
            "resume": resume,
        }

        response = self.client.post(
            url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "errors",
            response.data,
        )

        self.assertIn(
            "resume",
            response.data["errors"],
        )

        self.assertFalse(
            CandidateProfile.objects.filter(
                user=self.candidate_user
            ).exists()
        )

    # ====================================
    # Oversized resume should fail
    # ====================================

    def test_oversized_resume_rejected(
        self
    ):

        url = reverse(
            "candidate-profile-create"
        )

        # More than 5 MB
        large_file = (
            b"a" * (5 * 1024 * 1024 + 1)
        )

        resume = SimpleUploadedFile(
            "large_resume.pdf",
            large_file,
            content_type="application/pdf",
        )

        data = {
            "skills": "Python, Django",
            "education": "B.Sc Computer Science",
            "experience": 1,
            "expected_salary": 50000,
            "resume": resume,
        }

        response = self.client.post(
            url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "errors",
            response.data,
        )

        self.assertIn(
            "resume",
            response.data["errors"],
        )

        self.assertFalse(
            CandidateProfile.objects.filter(
                user=self.candidate_user
            ).exists()
        )

    # ====================================
    # Valid PDF resume should succeed
    # ====================================

    def test_valid_pdf_resume_allowed(
        self
    ):

        url = reverse(
            "candidate-profile-create"
        )

        resume = SimpleUploadedFile(
            "resume.pdf",
            b"Sample resume content",
            content_type="application/pdf",
        )

        data = {
            "skills": "Python, Django",
            "education": "B.Sc Computer Science",
            "experience": 1,
            "expected_salary": 50000,
            "resume": resume,
        }

        response = self.client.post(
            url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        profile = CandidateProfile.objects.get(
            user=self.candidate_user
        )

        self.assertTrue(
            profile.resume
        )

    # ====================================
    # Anonymous user cannot upload resume
    # ====================================

    def test_anonymous_user_cannot_upload_resume(
        self
    ):

        self.client.force_authenticate(
            user=None
        )

        url = reverse(
            "candidate-profile-create"
        )

        resume = SimpleUploadedFile(
            "resume.pdf",
            b"Sample resume content",
            content_type="application/pdf",
        )

        data = {
            "skills": "Python",
            "education": "B.Sc Computer Science",
            "experience": 1,
            "expected_salary": 50000,
            "resume": resume,
        }

        response = self.client.post(
            url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            401,
        )