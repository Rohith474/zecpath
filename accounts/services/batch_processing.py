from accounts.models import Application

from .auto_shortlisting import auto_process_application


def process_pending_applications(job):
    """
    Automatically process all pending applications
    for one specific job.
    """

    applications = (
        Application.objects
        .filter(
            job=job,
            status=Application.APPLIED,
        )
        .select_related(
            "candidate",
            "candidate__user",
            "job",
        )
    )

    results = []

    for application in applications:

        result = auto_process_application(
            application
        )

        results.append({
            "application_id": application.id,
            "candidate": (
                application.candidate.user.username
            ),
            "job": application.job.title,
            "result": result,
        })

    return results