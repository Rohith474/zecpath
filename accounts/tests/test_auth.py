from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import CustomUser


class AuthenticationTests(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = CustomUser.objects.create_user(
            username="testcandidate",
            email="candidate@test.com",
            password="TestPassword123!",
            role=CustomUser.CANDIDATE,
        )

    def test_user_registration(self):

        url = reverse("register")

        data = {
            "username": "newcandidate",
            "email": "newcandidate@test.com",
            "password": "NewPassword123!",
            "password2": "NewPassword123!",
            "role": CustomUser.CANDIDATE,
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
            CustomUser.objects.filter(
                username="newcandidate"
            ).exists()
        )

    def test_user_login(self):

        url = reverse("login")

        data = {
            "username": "testcandidate",
            "password": "TestPassword123!",
        }

        response = self.client.post(
            url,
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "access",
            response.data,
        )

        self.assertIn(
            "refresh",
            response.data,
        )

    def test_protected_endpoint_without_token(self):

        url = reverse("candidate")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_candidate_can_access_candidate_endpoint(self):

        self.client.force_authenticate(
            user=self.user
        )

        url = reverse("candidate")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_candidate_cannot_access_employer_endpoint(self):

        self.client.force_authenticate(
            user=self.user
        )

        url = reverse("employer")

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            403,
        )