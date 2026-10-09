from decimal import Decimal

from accounts.models import (
    ApplicationResumeParse,
    ATSScore,
)

# ============================================================
# ATS WEIGHTS
# ============================================================

SKILL_WEIGHT = Decimal("0.60")
EXPERIENCE_WEIGHT = Decimal("0.25")
EDUCATION_WEIGHT = Decimal("0.15")

# ============================================================
# SKILL MATCHING
# ============================================================

def get_matched_skills(job, parsed_data):
    """
    Return the required job skills that are matched
    by the candidate's parsed resume.
    """

    job_skills = {
        skill.strip().lower()
        for skill in job.skills.split(",")
        if skill.strip()
    }

    resume_skills = parsed_data.get(
        "skills",
        []
    )

    resume_skills = {
        str(skill).strip().lower()
        for skill in resume_skills
        if str(skill).strip()
    }

    return job_skills & resume_skills


def calculate_skill_score(job, parsed_data):
    """
    Calculate the percentage of required job skills
    matched by the candidate.
    """

    job_skills = {
        skill.strip().lower()
        for skill in job.skills.split(",")
        if skill.strip()
    }

    if not job_skills:
        return Decimal(0)

    matched_skills = get_matched_skills(
        job,
        parsed_data,
    )

    score = (
        Decimal(len(matched_skills))
        / Decimal(len(job_skills))
    ) * Decimal(100)

    return min(
        score,
        Decimal(100)
    )

# ============================================================
# EXPERIENCE MATCHING
# ============================================================

def calculate_experience_score(job, candidate):
    """
    Compare required job experience with
    candidate experience.
    """

    required_experience = job.experience or 0

    candidate_experience = (
        candidate.experience or 0
    )

    if required_experience <= 0:
        return Decimal(100)

    if candidate_experience >= required_experience:
        return Decimal(100)

    score = (
        Decimal(candidate_experience)
        / Decimal(required_experience)
    ) * Decimal(100)

    return min(
        score,
        Decimal(100)
    )

# ============================================================
# EDUCATION MATCHING
# ============================================================

def calculate_education_score(
    job,
    parsed_data,
):
    """
    Compare candidate education with the job
    description.

    The current Job model does not have a dedicated
    education field, so we look for education-related
    keywords inside the job description.
    """

    education = parsed_data.get(
        "education",
        []
    )

    if not education:
        return Decimal(0)

    job_text = (
        f"{job.title} {job.description}"
    ).lower()

    education_keywords = [
        "b.sc",
        "bsc",
        "b.tech",
        "btech",
        "b.e",
        "be ",
        "bachelor",
        "m.sc",
        "msc",
        "m.tech",
        "mtech",
        "m.e",
        "me ",
        "master",
        "mba",
        "phd",
        "degree",
    ]

    education_required = any(
        keyword in job_text
        for keyword in education_keywords
    )

    # If the job does not mention an education
    # requirement, don't penalize the candidate.
    if not education_required:
        return Decimal(100)

    candidate_education_text = " ".join(
        [
            str(item.get("qualification", ""))
            for item in education
        ]
    ).lower()

    if not candidate_education_text:
        return Decimal(0)

    for keyword in education_keywords:

        if keyword in job_text:

            if keyword in candidate_education_text:
                return Decimal(100)

    return Decimal(50)

# ============================================================
# FINAL ATS SCORE
# ============================================================

def calculate_ats_score(
    job,
    application,
):
    """
    Calculate the complete ATS score for one application.

    IMPORTANT:
    ATS scoring uses the resume submitted with this application,
    not the candidate's current profile resume.
    """

    candidate = application.candidate

    try:
        application_resume_parse = application.resume_parse

    except ApplicationResumeParse.DoesNotExist:

        return {
            "skill_score": Decimal(0),
            "matched_skill_count": 0,
            "experience_score": Decimal(0),
            "education_score": Decimal(0),
            "match_percentage": Decimal(0),
        }

    parsed_data = (
        application_resume_parse.parsed_data
        or {}
    )

    # ----------------------------------------
    # Matched skills
    # ----------------------------------------

    matched_skills = get_matched_skills(
        job,
        parsed_data,
    )

    matched_skill_count = len(
        matched_skills
    )

    # ----------------------------------------
    # Individual scores
    # ----------------------------------------

    skill_score = calculate_skill_score(
        job,
        parsed_data,
    )

    experience_score = calculate_experience_score(
        job,
        candidate,
    )

    education_score = calculate_education_score(
        job,
        parsed_data,
    )

    # ----------------------------------------
    # Weighted final score
    # ----------------------------------------

    match_percentage = (
        skill_score * SKILL_WEIGHT
        + experience_score * EXPERIENCE_WEIGHT
        + education_score * EDUCATION_WEIGHT
    )

    match_percentage = min(
        match_percentage,
        Decimal(100),
    )

    return {
        "skill_score": skill_score.quantize(
            Decimal("0.01")
        ),

        "matched_skill_count": matched_skill_count,

        "experience_score": experience_score.quantize(
            Decimal("0.01")
        ),

        "education_score": education_score.quantize(
            Decimal("0.01")
        ),

        "match_percentage": match_percentage.quantize(
            Decimal("0.01")
        ),
    }


# ============================================================
# SAVE ATS SCORE
# ============================================================

def calculate_and_save_ats_score(
    job,
    application,
):
    """
    Calculate and store/update the ATS score
    using the resume submitted for this application.
    """

    scores = calculate_ats_score(
        job,
        application,
    )

    ats_score, _created = ATSScore.objects.update_or_create(
        candidate=application.candidate,
        job=job,
        defaults=scores,
    )

    return ats_score