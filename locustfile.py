from locust import HttpUser, task, between


class JobPortalUser(HttpUser):

    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({
            "Authorization": "Bearer YOUR_ACCESS_TOKEN"
        })

    @task
    def recommended_jobs(self):

        self.client.get(
            "/api/jobs/recommended/",
            name="Recommended Jobs API",
        )