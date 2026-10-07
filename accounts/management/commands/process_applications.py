from django.core.management.base import BaseCommand

from accounts.services.batch_processing import (
    process_pending_applications,
)


class Command(BaseCommand):

    help = (
        "Automatically process all pending job applications "
        "using ATS eligibility rules."
    )

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING(
                "Starting application batch processing..."
            )
        )

        results = process_pending_applications()

        total_processed = len(results)

        self.stdout.write(
            self.style.SUCCESS(
                f"Batch processing completed. "
                f"Total processed: {total_processed}"
            )
        )

        for item in results:

            application_id = item["application_id"]
            candidate = item["candidate"]
            job = item["job"]
            result = item["result"]

            if result["success"]:

                action = result.get(
                    "action",
                    "processed",
                )

                match_percentage = result.get(
                    "match_percentage",
                    "N/A",
                )

                self.stdout.write(
                    f"Application #{application_id} | "
                    f"Candidate: {candidate} | "
                    f"Job: {job} | "
                    f"Action: {action} | "
                    f"ATS Score: {match_percentage}"
                )

            else:

                self.stdout.write(
                    self.style.ERROR(
                        f"Application #{application_id} | "
                        f"Failed: {result['message']}"
                    )
                )