from accounts.models import ATSScore


def get_matched_skill_count(ats_score, application):
    """
    Count how many required job skills
    are matched by the resume submitted
    for this application.
    """

    job_skills = {
        skill.strip().lower()
        for skill in ats_score.job.skills.split(",")
        if skill.strip()
    }

    if not application:
        return 0

    application_resume_parse = getattr(
        application,
        "resume_parse",
        None,
    )

    if not application_resume_parse:
        return 0

    resume_skills = (
        application_resume_parse.parsed_data.get(
            "skills",
            []
        )
    )

    resume_skills = {
        str(skill).strip().lower()
        for skill in resume_skills
        if str(skill).strip()
    }

    return len(
        job_skills & resume_skills
    )


def get_ranked_candidates(job):
    """
    Return ATS-ranked candidates who applied
    for the specified job.

    Ranking priority:
    1. Match percentage
    2. Skill score
    3. Experience score
    4. Education score
    5. Matched skill count
    6. Application time
    """

    # ----------------------------------------
    # Get ATS scores
    # ----------------------------------------

    ats_scores = (
        ATSScore.objects
        .filter(
            job=job,
            candidate__applications__job=job,
            candidate__user__is_flagged=False,
        )
        .select_related(
            "candidate__user",
            "job",
        )
        .order_by(
            "-match_percentage",
            "-skill_score",
            "-experience_score",
            "-education_score",
        )
        .distinct()
    )

    # ----------------------------------------
    # Get all relevant applications at once
    # ----------------------------------------

    applications = (
        job.applications
        .filter(
            candidate__user__is_flagged=False,
        )
        .select_related(
            "candidate",
            "candidate__user",
        )
        .prefetch_related(
            "resume_parse",
        )
        .order_by(
            "candidate_id",
            "applied_at",
        )
    )

    # ----------------------------------------
    # Build application lookup
    # ----------------------------------------

    application_lookup = {}

    for application in applications:

        if application.candidate_id not in application_lookup:

            application_lookup[
                application.candidate_id
            ] = application

    # ----------------------------------------
    # Build ranked candidate list
    # ----------------------------------------

    ranked_candidates = []

    for ats_score in ats_scores:

        application = application_lookup.get(
            ats_score.candidate_id
        )

        matched_skill_count = (
            get_matched_skill_count(
                ats_score,
                application,
            )
        )

        application_time = (
            application.applied_at
            if application
            else None
        )

        ranked_candidates.append({
            "candidate_id": ats_score.candidate.id,

            "candidate": (
                ats_score.candidate.user.username
            ),

            "skill_score": float(
                ats_score.skill_score
            ),

            "experience_score": float(
                ats_score.experience_score
            ),

            "education_score": float(
                ats_score.education_score
            ),

            "matched_skill_count": (
                matched_skill_count
            ),

            "match_percentage": float(
                ats_score.match_percentage
            ),

            "application_time": application_time,
        })

    # ----------------------------------------
    # Final ranking
    # ----------------------------------------

    ranked_candidates.sort(
        key=lambda candidate: (
            -candidate["match_percentage"],
            -candidate["skill_score"],
            -candidate["experience_score"],
            -candidate["education_score"],
            -candidate["matched_skill_count"],
            (
                candidate["application_time"]
                if candidate["application_time"]
                else float("inf")
            ),
        )
    )

    # ----------------------------------------
    # Assign rank
    # ----------------------------------------

    for rank, candidate in enumerate(
        ranked_candidates,
        start=1,
    ):
        candidate["rank"] = rank

    return ranked_candidates