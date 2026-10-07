from decimal import Decimal


# ============================================================
# DEFAULT THRESHOLD
# ============================================================

DEFAULT_SHORTLIST_THRESHOLD = Decimal("70")


# ============================================================
# ROLE / JOB TYPE THRESHOLDS
# ============================================================

JOB_TYPE_THRESHOLDS = {
    "Internship": Decimal("55"),
    "Part Time": Decimal("65"),
    "Full Time": Decimal("70"),
}


# ============================================================
# GET THRESHOLD
# ============================================================

def get_shortlist_threshold(job):
    """
    Return the minimum ATS score required
    for automatic shortlisting.

    Threshold is determined by job type.
    """

    return JOB_TYPE_THRESHOLDS.get(
        job.job_type,
        DEFAULT_SHORTLIST_THRESHOLD,
    )


# ============================================================
# ELIGIBILITY CHECK
# ============================================================

def is_eligible_for_shortlisting(ats_score):
    """
    Check whether the candidate meets the
    minimum ATS score required for the job.
    """

    threshold = get_shortlist_threshold(
        ats_score.job
    )

    return (
        ats_score.match_percentage
        >= threshold
    )
# AI CALL ELIGIBILITY

def is_eligible_for_ai_call(application):
    """
    Check whether an application is eligible
    for an AI screening call.
    """

    # Application must be shortlisted
    if application.status != application.SHORTLISTED:
        return False, "Application is not shortlisted."

    # Job must be active
    if application.job.status != "Active":
        return False, "Job is not active."

    # Candidate profile must exist
    try:
        candidate = application.candidate
    except Exception:
        return False, "Candidate profile not found."

    # Candidate must not be deleted
    if candidate.is_deleted:
        return False, "Candidate profile is deleted."

    # Candidate must have a resume
    if not candidate.resume:
        return False, "Candidate does not have a resume."

    return True, "Application is eligible for AI call."