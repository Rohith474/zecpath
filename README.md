# Zecpath --- Recruitment Platform Backend

A backend system for a recruitment platform that connects candidates and
employers and supports job applications, resume-based candidate
evaluation, AI-assisted screening workflows, interview scheduling,
notifications, and payment-related functionality.

> **Project context:** Developed as part of a backend engineering
> internship.
>
> **Status note:** This README documents the project architecture and
> development workflow. Features and deployment checks should be
> described as verified only when supported by the current code and test
> results. In particular, validate Razorpay webhook delivery end-to-end
> in the relevant Razorpay test environment before describing it as
> fully verified.

## Table of Contents

-   [Overview](#overview)
-   [Core Features](#core-features)
-   [Technology Stack](#technology-stack)
-   [Architecture](#architecture)
-   [Key Workflows](#key-workflows)
-   [ATS Scoring Rules](#ats-scoring-rules)
-   [AI Interview Evaluation](#ai-interview-evaluation)
-   [Repository Structure](#repository-structure)
-   [Local Development Setup](#local-development-setup)
-   [Environment Configuration](#environment-configuration)
-   [Database, Redis, and Celery](#database-redis-and-celery)
-   [Running Tests and Checks](#running-tests-and-checks)
-   [API Documentation and Testing](#api-documentation-and-testing)
-   [Deployment Overview](#deployment-overview)
-   [Security Notes](#security-notes)
-   [Known Validation Notes](#known-validation-notes)
-   [Future Improvements](#future-improvements)

## Overview

Zecpath is a recruitment-platform backend built with Django and Django
REST Framework. It organizes recruitment workflows around candidate,
employer, and administrator roles. The backend includes job and
application management, ATS-style scoring and shortlisting support, AI
interview workflows, scheduled background processing, and supporting
operational features.

The project is structured as a **modular Django application**. Keeping
related functionality in Django apps, services, models, and tasks makes
it easier to develop and test the system without introducing the
operational complexity of microservices prematurely.

## Core Features

-   **Role-based accounts:** Candidate, Employer, and Admin roles.
-   **Job management:** Job postings, job status, job types, and
    employer-related workflows.
-   **Applications:** Candidate applications, application status
    tracking, and duplicate-application prevention through
    model/database constraints.
-   **Candidate profiles:** Skills, education, experience, expected
    salary, and resume information.
-   **ATS-style evaluation:** Skill, experience, and education scoring
    with a combined match percentage.
-   **Shortlisting eligibility:** Job-type-specific thresholds used by
    the eligibility logic.
-   **AI-assisted interview workflow:** Question flow, follow-up
    questions, answer storage, availability collection, and call/session
    status tracking.
-   **AI answer evaluation:** Relevance, completeness, and keyword-match
    scoring.
-   **Interview scheduling support:** Candidate availability, interview
    scheduling, and reminder processing.
-   **Background processing:** Celery tasks with Redis as broker/result
    backend and cache infrastructure.
-   **Authentication and authorization:** JWT-based authentication and
    role/permission checks.
-   **Notifications and audit-related records:** Supporting models for
    notifications, email logs, and audit logs.
-   **Payment integration:** Razorpay-related payment and webhook
    handling code.
-   **Operational support:** Automated tests, Django checks, and
    deployment using Linux services and Nginx.

The exact availability of each endpoint and feature depends on the
current repository version. Use the source code and tests as the final
authority.

## Technology Stack

  -----------------------------------------------------------------------
  Area                                Technology
  ----------------------------------- -----------------------------------
  Language                            Python

  Backend framework                   Django

  API framework                       Django REST Framework

  Database                            PostgreSQL

  Cache / message broker              Redis

  Background jobs                     Celery

  Authentication                      JWT (Simple JWT)

  Payment integration                 Razorpay

  Application server / reverse proxy  Gunicorn and Nginx (deployment
                                      configuration)

  Production environment              Ubuntu on AWS EC2

  Testing                             Django test framework and targeted
                                      application tests

  Version control                     Git and GitHub
  -----------------------------------------------------------------------

## Architecture

``` text
                 ┌────────────────────────────┐
                 │ Client / API Consumer      │
                 │ (e.g. Postman or frontend) │
                 └──────────────┬─────────────┘
                                │ HTTP / REST
                                ▼
                 ┌────────────────────────────┐
                 │ Nginx / Django REST API    │
                 │ Authentication & Permissions│
                 └──────────────┬─────────────┘
                                ▼
                 ┌────────────────────────────┐
                 │ Django Application         │
                 │ Views · Serializers        │
                 │ Models · Service Layer     │
                 └───────┬───────────┬────────┘
                         │           │
              ┌──────────▼───┐   ┌───▼────────────────┐
              │ PostgreSQL   │   │ Redis              │
              │ Persistent   │   │ Cache / Broker     │
              │ Data         │   └─────────┬──────────┘
              └──────────────┘             │
                                           ▼
                                 ┌─────────────────────┐
                                 │ Celery Worker / Beat│
                                 │ Background & Timed  │
                                 │ Tasks               │
                                 └─────────────────────┘
```

### Architectural responsibilities

-   **Views and API classes:** Handle HTTP requests and responses.
-   **Serializers and validation:** Validate and represent API data.
-   **Models and PostgreSQL:** Store persistent application data and
    enforce relational constraints.
-   **Service layer:** Encapsulate business rules that should not be
    duplicated across views.
-   **Redis and Celery:** Support asynchronous and scheduled tasks.
-   **Nginx and application service:** Route production HTTP traffic to
    the Django application.

## Key Workflows

### 1. Job application and ATS workflow

1.  An employer creates and manages a job posting.
2.  A candidate maintains a profile and resume and applies for a job.
3.  The backend evaluates relevant candidate/job attributes through ATS
    scoring logic.
4.  Eligibility logic compares the resulting match percentage with the
    threshold for the job type.
5.  Employer-facing workflows can use the score and application status
    to support shortlisting decisions.

### 2. AI-assisted interview workflow

1.  An eligible application can be considered for an AI interview call.
2.  The call/session state tracks the interview lifecycle.
3.  The question engine selects configured questions and may handle
    follow-up questions.
4.  Answers and relevant flow state are stored.
5.  Availability information may be collected as part of the flow.
6.  Answer evaluation produces scoring information.
7.  The workflow updates completion status and related records.

### 3. Scheduled/background processing

1.  A scheduled or asynchronous task is queued through Celery.
2.  Redis supports broker/result-backend responsibilities configured for
    the project.
3.  A Celery worker processes the task.
4.  Celery Beat can trigger periodic processing, such as scheduled-call
    or reminder checks.
5.  Failures and retries should be monitored through task logs and
    application records.

## ATS Scoring Rules

The documented ATS weighting is:

  Component        Weight
  ------------ ----------
  Skills              60%
  Experience          25%
  Education           15%
  **Total**      **100%**

Documented shortlisting thresholds:

  Job type       Threshold
  ------------ -----------
  Internship           55%
  Part Time            65%
  Full Time            70%

These values describe the project rules recorded during development.
Confirm the current implementation before changing them or using them as
a production policy.

## AI Interview Evaluation

The documented answer-evaluation weighting is:

  Component           Weight
  --------------- ----------
  Relevance              40%
  Completeness           30%
  Keyword match          30%
  **Total**         **100%**

The interview workflow also tracks question progression, follow-ups,
answer storage, availability collection, and call/session completion.
Evaluation scores should be interpreted as application-generated signals
rather than a substitute for a complete human hiring decision.

## Repository Structure

The project has a Django project package and an `accounts` app
containing a substantial part of the recruitment functionality. The
repository also includes migrations, tests, dependency information, and
supporting task/configuration files. A simplified view is shown below;
confirm exact filenames against the current checkout.

``` text
zecpath/
├── manage.py
├── requirements.txt
├── locustfile.py
├── accounts/
│   ├── migrations/
│   ├── tests/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── ...
├── day10project/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── README.md
```

> This is a representative structure, not a complete file listing. Some
> service modules and task files may be nested elsewhere in the
> repository.

## Local Development Setup

### Prerequisites

Install or configure:

-   Python compatible with the project's pinned dependencies.
-   Git.
-   PostgreSQL.
-   Redis.
-   A Windows terminal (the commands below use Windows CMD) or an
    equivalent shell with adjusted activation syntax.

### 1. Clone the repository

``` cmd
git clone https://github.com/Rohith474/zecpath.git
cd zecpath
```

### 2. Create and activate a virtual environment

``` cmd
python -m venv env
env\Scripts\activate
```

### 3. Install dependencies

``` cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If installation fails, check the Python version supported by the
repository's dependencies. Do not assume every dependency supports the
newest Python release.

### 4. Configure environment variables

Create a local `.env` file in the directory expected by
`day10project/settings.py`. Do not commit it. Populate the variables
required by the settings and enabled integrations. See [Environment
Configuration](#environment-configuration).

### 5. Apply migrations

Ensure PostgreSQL is running and the configured database exists, then
run:

``` cmd
python manage.py migrate
```

### 6. Create an administrator account (optional)

``` cmd
python manage.py createsuperuser
```

### 7. Run Django checks

``` cmd
python manage.py check
```

### 8. Start the development server

``` cmd
python manage.py runserver
```

The local development server is normally available at
`http://127.0.0.1:8000/`. Use the actual routes declared in the
project's URL configuration when testing endpoints.

## Environment Configuration

The project uses environment-based configuration. The precise required
variables depend on `day10project/settings.py` and the integrations
enabled for the environment.

Typical configuration categories include:

  ---------------------------------------------------------------------------------
  Category                Example variable names      Notes
  ----------------------- --------------------------- -----------------------------
  Django                  `SECRET_KEY`, `DEBUG`,      Use a private production
                          `ALLOWED_HOSTS`             secret and disable debug mode
                                                      in production.

  PostgreSQL              `DB_NAME`, `DB_USER`,       Use the exact names expected
                          `DB_PASSWORD`, `DB_HOST`,   by the current settings
                          `DB_PORT`                   module.

  Redis / Celery          `CELERY_BROKER_URL`,        Project configuration has
                          `CELERY_RESULT_BACKEND`     used Redis at
                                                      `redis://localhost:6379/0`;
                                                      confirm current settings.

  Razorpay                `RAZORPAY_KEY_ID`,          API credentials and webhook
                          `RAZORPAY_KEY_SECRET`,      secret are different values.
                          `RAZORPAY_WEBHOOK_SECRET`   Keep them private and use
                                                      matching test/live-mode
                                                      configuration.

  Email / storage         Variables for the           Consult settings and
                          configured email provider   deployment configuration for
                          and S3-compatible storage   exact names.
  ---------------------------------------------------------------------------------

**Important:** The table lists configuration categories and known
variable names, not a complete `.env` template. Never publish actual
values. Do not paste API keys, database passwords, `SECRET_KEY`, webhook
secrets, tokens, or private certificates into GitHub issues or README
examples.

## Database, Redis, and Celery

### PostgreSQL

PostgreSQL is the project's active database in the documented
development/deployment setup. It supports relational constraints and
transaction behavior used by concurrency-sensitive workflows.

### Redis

Redis is used for the configured cache and Celery infrastructure.
Confirm the Redis service is running and that the broker/result-backend
URLs match the environment.

### Celery worker

In the documented Windows development environment, Celery was run with
the `solo` pool:

``` cmd
celery -A day10project worker --loglevel=info --pool=solo
```

### Celery Beat

``` cmd
celery -A day10project beat --loglevel=info
```

Run the worker and Beat in separate terminals during local testing when
periodic/background tasks are needed. Production should run them as
supervised services with logs and restart policies.

## Running Tests and Checks

Run the broad Django test suite with:

``` cmd
python manage.py test
```

Run a targeted test module using its actual dotted Python path, for
example:

``` cmd
python manage.py test accounts.tests.test_security
```

Check whether model changes require migrations:

``` cmd
python manage.py makemigrations --check --dry-run
```

Run Django's configuration/system check:

``` cmd
python manage.py check
```

During development, prioritize tests for:

-   Authentication and role-based permissions.
-   Input validation and error responses.
-   Duplicate applications and database constraints.
-   ATS scoring boundaries and job-type thresholds.
-   AI question progression, answer storage, and completion states.
-   Celery scheduling, retries, and failure paths.
-   Payment verification and webhook signature validation.
-   Concurrent requests against PostgreSQL for locking-sensitive
    workflows.

**Test reporting rule:** Record the exact command and result for each
test run. Do not describe a planned test as passed.

## API Documentation and Testing

The backend exposes REST APIs through Django REST Framework. Use the
project's URL configuration and API view classes as the source of truth
for exact endpoint paths and HTTP methods.

Recommended API test record:

  Field                Record
  -------------------- -------------------------------------------------
  Feature / endpoint   Exact path from `urls.py`
  HTTP method          GET, POST, PUT, PATCH, or DELETE as implemented
  Authentication       Required token/role, or public access
  Request              Sanitized example payload
  Expected result      Expected status and response fields
  Actual result        Observed status and response
  Test evidence        Test name, Postman result, or log reference

Do not include real user data, access tokens, payment secrets, or
private resume files in published examples.

## Deployment Overview

The documented deployment setup uses Ubuntu on AWS EC2, Nginx as a
reverse proxy, and supervised services for the Django application and
Celery processes. PostgreSQL and Redis provide persistence and
background-task infrastructure.

A typical deployment checklist:

1.  Pull the intended Git commit.
2.  Activate the deployment virtual environment and install
    dependencies.
3.  Verify production environment variables and secret permissions.
4.  Run migrations after confirming the target database and backup
    status.
5.  Collect static files if required by the current settings.
6.  Restart the Django, Celery worker, and Celery Beat services as
    appropriate.
7.  Check service status and logs.
8.  Run Django checks and safe API smoke tests.
9.  Verify HTTPS, allowed hosts, static/media access, and external
    integrations.
10. Keep a rollback path to the previously deployed commit.

Exact service names and commands are environment-specific. Verify the
deployed systemd unit names and Nginx configuration on the target host
before running operational commands.

## Security Notes

-   Keep `.env`, credentials, private keys, database dumps, uploaded
    resumes, and local virtual environments out of Git.
-   Set `DEBUG=False` in production and configure `ALLOWED_HOSTS`
    deliberately.
-   Use HTTPS for public authentication and payment-related traffic.
-   Validate permissions on every protected endpoint; authentication
    alone does not guarantee authorization.
-   Validate uploaded files by type, size, and content as appropriate;
    do not trust the filename alone.
-   Verify payment webhook signatures using the raw request body and the
    webhook secret configured for the matching Razorpay mode.
-   Avoid exposing internal exception messages or secrets in API
    responses.
-   Use least-privilege credentials and rotate any secret that may have
    been exposed.
-   Back up the database before high-impact schema or data operations.

## Known Validation Notes

-   The project has been checked with Django's system check and targeted
    test suites during development; consult the latest local test output
    for the precise coverage and results.
-   PostgreSQL is the active database in the documented environment,
    including for testing transaction and row-locking behavior.
-   Razorpay webhook configuration requires a reachable public HTTPS URL
    and a webhook secret matching the configured Razorpay environment.
    An unsigned request returning a missing/invalid-signature response
    is not proof of successful webhook delivery.
-   Resume parsing and ATS output should be checked against
    representative test files and expected results; a successful
    response alone does not guarantee every extracted field is accurate.
-   Review the current repository before publishing a feature list or
    declaring a workflow production-ready.

## Future Improvements

-   Expand automated integration and concurrency tests.
-   Improve observability for Celery tasks, retries, and payment webhook
    failures.
-   Add or maintain an API reference with verified endpoints,
    authentication requirements, and example responses.
-   Improve resume-parsing evaluation with a representative test corpus
    and documented accuracy checks.
-   Add CI checks for formatting, tests, dependency/security review, and
    migration consistency.
-   Maintain clear operational runbooks for deployment, backup,
    rollback, and incident handling.

## Author / Project

**Project:** Zecpath Recruitment Platform Backend\
**Repository:**
[github.com/Rohith474/zecpath](https://github.com/Rohith474/zecpath)\
**Focus:** Python backend engineering, REST APIs, database workflows,
asynchronous processing, testing, and deployment.

------------------------------------------------------------------------

*Keep this README synchronized with the current codebase. Update paths,
commands, environment-variable names, API examples, and test claims
whenever the implementation changes.*
