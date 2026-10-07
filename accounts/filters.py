import django_filters

from .models import Job


class JobFilter(django_filters.FilterSet):

    min_salary = django_filters.NumberFilter(
        field_name="salary_min",
        lookup_expr="gte",
    )

    max_salary = django_filters.NumberFilter(
        field_name="salary_max",
        lookup_expr="lte",
    )

    experience = django_filters.NumberFilter()

    location = django_filters.CharFilter(
        lookup_expr="icontains",
    )

    job_type = django_filters.CharFilter(
        lookup_expr="iexact",
    )

    class Meta:
        model = Job

        fields = [
            "job_type",
            "location",
            "experience",
            "min_salary",
            "max_salary",
        ]