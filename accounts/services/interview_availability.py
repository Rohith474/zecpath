import re
from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import CandidateInterviewAvailability


class InterviewAvailabilityService:
    """
    Extract and store a candidate's preferred
    interview date and time.
    """

    @staticmethod
    def extract_datetime(answer):
        """
        Extract date and time from a candidate's
        natural-language availability answer.

        Supports:
        - September 24, 2026 at 10:30 AM
        - 24/09/2026 at 2:30 PM
        - 2026-09-24 at 10:30 AM
        - Tomorrow at 10:30 AM
        - Next Monday at 2 PM
        """

        if not answer:
            return {
                "success": False,
                "message": "Availability answer is required.",
            }

        answer = answer.strip()

        # ----------------------------------------
        # Extract date
        # ----------------------------------------

        parsed_date = None
        answer_lower = answer.lower()

        # Tomorrow
        if re.search(r"\btomorrow\b", answer_lower):
            parsed_date = (
                timezone.localdate() + timedelta(days=1)
            )

        # Today
        elif re.search(r"\btoday\b", answer_lower):
            parsed_date = timezone.localdate()

        # Next weekday
        if not parsed_date:

            weekday_names = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }

            weekday_match = re.search(
                r"\bnext\s+(monday|tuesday|wednesday|"
                r"thursday|friday|saturday|sunday)\b",
                answer_lower,
            )

            if weekday_match:

                target_weekday = weekday_names[
                    weekday_match.group(1)
                ]

                today = timezone.localdate()

                days_ahead = (
                    target_weekday - today.weekday()
                ) % 7

                # "next Monday" should mean the following
                # Monday, not today.
                if days_ahead == 0:
                    days_ahead = 7

                parsed_date = (
                    today + timedelta(days=days_ahead)
                )

        # ----------------------------------------
        # Explicit numeric date formats
        # ----------------------------------------

        date_patterns = [
            r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b",
            r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        ]

        # DD/MM/YYYY or DD-MM-YYYY
        if not parsed_date:

            match = re.search(
                date_patterns[0],
                answer,
            )

            if match:

                day, month, year = match.groups()

                try:

                    parsed_date = datetime(
                        int(year),
                        int(month),
                        int(day),
                    ).date()

                except ValueError:
                    pass

        # YYYY-MM-DD
        if not parsed_date:

            match = re.search(
                date_patterns[1],
                answer,
            )

            if match:

                year, month, day = match.groups()

                try:

                    parsed_date = datetime(
                        int(year),
                        int(month),
                        int(day),
                    ).date()

                except ValueError:
                    pass

        # ----------------------------------------
        # Month-name formats
        # ----------------------------------------

        month_patterns = [
            "%B %d, %Y",
            "%B %d %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%b %d %Y",
            "%d %b %Y",
        ]

        if not parsed_date:

            for date_format in month_patterns:

                try:

                    parsed_date = datetime.strptime(
                        answer,
                        date_format,
                    ).date()

                    break

                except ValueError:
                    pass

        # Search date inside a sentence
        if not parsed_date:

            date_regex_patterns = [
                r"\b([A-Za-z]+ \d{1,2}, \d{4})\b",
                r"\b(\d{1,2} [A-Za-z]+ \d{4})\b",
                r"\b([A-Za-z]+ \d{1,2} \d{4})\b",
            ]

            for pattern in date_regex_patterns:

                match = re.search(
                    pattern,
                    answer,
                    re.IGNORECASE,
                )

                if not match:
                    continue

                date_text = match.group(1)

                for date_format in month_patterns:

                    try:

                        parsed_date = datetime.strptime(
                            date_text,
                            date_format,
                        ).date()

                        break

                    except ValueError:
                        pass

                if parsed_date:
                    break

        # ----------------------------------------
        # Validate date
        # ----------------------------------------

        if not parsed_date:

            return {
                "success": False,
                "message": (
                    "Could not identify a valid interview date. "
                    "Please provide a date such as "
                    "'September 24, 2026', 'tomorrow', "
                    "or 'next Monday'."
                ),
            }

        # ----------------------------------------
        # Extract time
        # ----------------------------------------

        time_patterns = [
            r"\b(\d{1,2}):(\d{2})\s*(AM|PM)\b",
            r"\b(\d{1,2})\s*(AM|PM)\b",
        ]

        parsed_time = None

        for pattern in time_patterns:

            match = re.search(
                pattern,
                answer,
                re.IGNORECASE,
            )

            if not match:
                continue

            if len(match.groups()) == 3:

                hour = int(match.group(1))
                minute = int(match.group(2))
                meridiem = match.group(3).upper()

                time_text = (
                    f"{hour}:{minute:02d} {meridiem}"
                )

            else:

                hour = int(match.group(1))
                meridiem = match.group(2).upper()

                time_text = (
                    f"{hour}:00 {meridiem}"
                )

            try:

                parsed_time = datetime.strptime(
                    time_text,
                    "%I:%M %p",
                ).time()

                break

            except ValueError:
                continue

        # ----------------------------------------
        # Time is mandatory
        # ----------------------------------------

        if not parsed_time:

            return {
                "success": False,
                "message": (
                    "Could not identify a valid interview time. "
                    "Please provide an exact time such as "
                    "'10:30 AM' or '2 PM'."
                ),
            }

        # ----------------------------------------
        # Return parsed availability
        # ----------------------------------------

        return {
            "success": True,
            "preferred_date": parsed_date,
            "preferred_time": parsed_time,
            "timezone": "Asia/Kolkata",
        }

    @staticmethod
    def save_availability(application, answer):
        """
        Extract and save a candidate's preferred
        interview availability for an application.
        """

        result = InterviewAvailabilityService.extract_datetime(
            answer
        )

        if not result["success"]:
            return result

        availability, created = (
            CandidateInterviewAvailability.objects.update_or_create(
                application=application,
                defaults={
                    "preferred_date": result["preferred_date"],
                    "preferred_time": result["preferred_time"],
                    "timezone": result["timezone"],
                },
            )
        )

        return {
            "success": True,
            "created": created,
            "availability_id": availability.id,
            "preferred_date": availability.preferred_date,
            "preferred_time": availability.preferred_time,
            "timezone": availability.timezone,
        }