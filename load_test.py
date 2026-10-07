from locust import HttpUser, task, between


EMPLOYER1_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwNjUyMTU1LCJpYXQiOjE3OTA2NDg1NTUsImp0aSI6IjJmYmI3Mjk3NzIyMjRlMTZhM2QxOGViYTk5ZGIwN2NjIiwidXNlcl9pZCI6IjE0In0.-WLjrqWHtu4S1Yd-IIq5srJQvT8KGD464-WTCzkgpU0"
EMPLOYER2_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkwNjUyMTc4LCJpYXQiOjE3OTA2NDg1NzgsImp0aSI6IjFjMjRmZGM1ZTZkMDRkOTQ4MDA2OWU0ZTY5OGQ5Zjc4IiwidXNlcl9pZCI6IjE1In0.8rw9fjQfbO9tlWQipurCcSuxxddELGN-bRldQe9Z6gE"


class Employer1User(HttpUser):
    fixed_count = 1
    wait_time = between(1, 2)

    def on_start(self):
        self.auth_headers = {
            "Authorization": f"Bearer {EMPLOYER1_TOKEN.strip()}"
        }

    @task
    def analytics_jobs(self):
        with self.client.get(
            "/api/analytics/jobs/",
            headers=self.auth_headers,
            name="GET /api/analytics/jobs/",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"HTTP {response.status_code}"
                )


class Employer2User(HttpUser):
    fixed_count = 1
    wait_time = between(1, 2)

    def on_start(self):
        self.auth_headers = {
            "Authorization": f"Bearer {EMPLOYER2_TOKEN.strip()}"
        }

    @task
    def analytics_jobs(self):
        with self.client.get(
            "/api/analytics/jobs/",
            headers=self.auth_headers,
            name="GET /api/analytics/jobs/",
            catch_response=True,
        ) as response:

            if response.status_code != 200:
                response.failure(
                    f"HTTP {response.status_code}"
                )