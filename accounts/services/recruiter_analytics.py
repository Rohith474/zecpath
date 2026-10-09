from datetime import date, datetime, time

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from accounts.models import Application


class RecruiterAnalyticsService:

    @staticmethod
    def get_funnel_metrics(employer):
        cache_key = f"recruiter_funnel_{employer.id}"

        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        applications = Application.objects.filter(
            job__employer=employer
        )

        metrics = applications.aggregate(
            total_applied=Count("id"),

            shortlisted=Count(
                "id",
                filter=Q(
                    status__in=[
                        Application.SHORTLISTED,
                        Application.INTERVIEW,
                        Application.SELECTED,
                    ]
                ),
            ),

            interviewed=Count(
                "id",
                filter=Q(
                    ai_call__status="Completed"
                ),
                distinct=True,
            ),

            selected=Count(
                "id",
                filter=Q(
                    status=Application.SELECTED
                ),
            ),
        )

        total_applied = metrics["total_applied"]

        def conversion_rate(value):
            if total_applied == 0:
                return 0

            return round((value / total_applied) * 100, 2)

        result = {
            "total_applications": total_applied,
            "shortlisted": metrics["shortlisted"],
            "interviewed": metrics["interviewed"],
            "selected": metrics["selected"],
            "conversion_rates": {
                "shortlisted": conversion_rate(
                    metrics["shortlisted"]
                ),
                "interviewed": conversion_rate(
                    metrics["interviewed"]
                ),
                "selected": conversion_rate(
                    metrics["selected"]
                ),
            },
        }

        cache.set(cache_key, result, timeout=300)

        return result
    @staticmethod
    def get_job_wise_metrics(employer):
        cache_key = f"recruiter_job_analytics_{employer.id}"

        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        jobs = (
            employer.jobs
            .annotate(
                total_applications=Count(
                    "applications",
                    distinct=True,
                ),
                shortlisted=Count(
                    "applications",
                    filter=Q(
                        applications__status__in=[
                            Application.SHORTLISTED,
                            Application.INTERVIEW,
                            Application.SELECTED,
                        ]
                    ),
                    distinct=True,
                ),
                interviewed=Count(
                    "applications",
                    filter=Q(
                        applications__ai_call__status="Completed"
                    ),
                    distinct=True,
                ),
                selected=Count(
                    "applications",
                    filter=Q(
                        applications__status=Application.SELECTED
                    ),
                    distinct=True,
                ),
            )
            .order_by("-total_applications", "title")
        )

        result = [
            {
                "job_id": job.id,
                "job_title": job.title,
                "total_applications": job.total_applications,
                "shortlisted": job.shortlisted,
                "interviewed": job.interviewed,
                "selected": job.selected,
                "conversion_rates": {
                    "shortlisted": round(
                        (job.shortlisted / job.total_applications) * 100, 2
                    )
                    if job.total_applications
                    else 0.0,
                    "interviewed": round(
                        (job.interviewed / job.total_applications) * 100, 2
                    )
                    if job.total_applications
                    else 0.0,
                    "selected": round(
                        (job.selected / job.total_applications) * 100, 2
                    )
                    if job.total_applications
                    else 0.0,
                },
            }
            for job in jobs
        ]

        cache.set(cache_key, result, timeout=300)

        return result
    @staticmethod
    def get_time_based_metrics(
        employer,
        start_date=None,
        end_date=None,
    ):
        original_start_date = start_date
        original_end_date = end_date
        cache_key = (
            f"recruiter_time_analytics_"
            f"{employer.id}_"
            f"{start_date}_"
            f"{end_date}"
        )

        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        applications = Application.objects.filter(
            job__employer=employer
        )

        if start_date:
            if isinstance(start_date, str):
                start_date = date.fromisoformat(start_date)

            start_datetime = timezone.make_aware(
                datetime.combine(start_date, time.min)
            )

            applications = applications.filter(
                applied_at__gte=start_datetime
            )

        if end_date:
            if isinstance(end_date, str):
                end_date = date.fromisoformat(end_date)

            end_datetime = timezone.make_aware(
                datetime.combine(end_date, time.max)
            )

            applications = applications.filter(
                applied_at__lte=end_datetime
            )
        metrics = applications.aggregate(
            total_applications=Count("id"),

            shortlisted=Count(
                "id",
                filter=Q(
                    status__in=[
                        Application.SHORTLISTED,
                        Application.INTERVIEW,
                        Application.SELECTED,
                    ]
                ),
            ),

            interviewed=Count(
                "id",
                filter=Q(
                    ai_call__status="Completed"
                ),
                distinct=True,
            ),

            selected=Count(
                "id",
                filter=Q(
                    status=Application.SELECTED
                ),
            ),
        )

        result = {
            "start_date": original_start_date,
            "end_date": original_end_date,
            "total_applications": metrics["total_applications"],
            "shortlisted": metrics["shortlisted"],
            "interviewed": metrics["interviewed"],
            "selected": metrics["selected"],
        }

        cache.set(cache_key, result, timeout=300)

        return result