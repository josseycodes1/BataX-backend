# BataX backend: project map

This guide maps the backend files present when it was written and points to the
right place to investigate or change API behavior. The tree focuses on
project-owned source, configuration, deployment files, documentation, and
migrations. It omits `.git/`, `.venv/`, Python bytecode/cache directories, and
other generated/runtime data; those are not application source.

## Project tree

```text
BataX-backend/
├── accounts/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── oauth.py
│   ├── serializers.py
│   ├── services.py
│   ├── urls.py
│   └── views.py
├── audit/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   └── models.py
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py
│   ├── test_settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── media.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── tasks.py
│   ├── tests.py
│   └── views.py
├── exchanges/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── tasks.py
│   └── views.py
├── listings/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   └── views.py
├── locations/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── matching/
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   └── views.py
├── messaging/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── moderation/
│   ├── migrations/
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   └── views.py
├── notifications/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── reports/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── reviews/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── verification/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── wishlist/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── views.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── notes.md
├── README.md
├── requirements.txt
├── schema.yaml
└── website.md
```

## Request flow and project structure

`config/urls.py` is the main URL dispatcher. It exposes health and API schema
routes, includes the account routes, registers product/admin ViewSets, and maps
matching and verification endpoints. Most feature behavior lives in its
corresponding Django app: `views.py` handles requests and permissions,
`serializers.py` validates/transforms API data where present, `models.py`
defines stored records, and `migrations/` records database schema changes.
`config/settings.py` is the central integration point for apps, security,
PostgreSQL, JWT, CORS/CSRF, Redis, Celery, email, and external services.

## Feature apps and files

### `accounts/` — identity, authentication, and profiles

- `accounts/models.py` — custom email-based user model/manager and related
  profile, email challenge, contact-message, and block records. Account schema
  or account-level stored fields start here.
- `accounts/serializers.py` — public/private user representations and
  validation/creation for registration, profile updates, preferences,
  credentials, email, OTP, and password operations.
- `accounts/views.py` — registration and login flow, email/OTP verification,
  token logout, current/public profile endpoints, password reset/change,
  deactivation, preferences, contact, role metadata, and block management.
- `accounts/oauth.py` — Google OAuth redirect, callback/state validation, and
  exchange of a temporary one-time code for the application login result.
- `accounts/services.py` — account-side service helper for sending email
  verification challenges.
- `accounts/urls.py` — account route names and paths, including auth, profile,
  password, public seller, and block routes.
- `accounts/admin.py` — Django admin configuration for the custom BataX user
  model and restricted user administration.
- `accounts/apps.py` — Django app registration metadata.
- `accounts/__init__.py` — marks `accounts` as a Python package.
- `accounts/migrations/0001_initial.py` — initial database schema for accounts
  and the custom user model; do not edit an applied migration to change the
  live schema.
- `accounts/migrations/__init__.py` — marks the migrations directory as a
  Python package.

### `listings/` — categories and offered items

- `listings/models.py` — category, item listing, and listing media database
  records, including listing state and descriptive fields.
- `listings/serializers.py` — category/listing/media API shapes, category
  validation, and uploaded listing-image validation.
- `listings/views.py` — category and listing endpoints: public/user query
  scoping, create/update/delete, owner checks, image upload, submit for
  moderation, and pause actions.
- `listings/apps.py` — Django app registration metadata.
- `listings/__init__.py` — Python package marker.
- `listings/migrations/0001_initial.py` — initial listing/category/media schema.
- `listings/migrations/__init__.py` — migrations package marker.

### `wishlist/` — items users are looking for

- `wishlist/models.py` — saved wanted-item preferences, optionally associated
  with a listing.
- `wishlist/views.py` — validates and exposes the authenticated user's wanted
  items through CRUD endpoints.
- `wishlist/apps.py` — Django app registration metadata.
- `wishlist/__init__.py` — Python package marker.
- `wishlist/migrations/0001_initial.py` — initial wanted-item schema.
- `wishlist/migrations/__init__.py` — migrations package marker.

### `matching/` — candidate exchange discovery

- `matching/views.py` — calculates compatibility between a user's listing
  wants and other listings/preferences and returns match candidates. Change
  matching/scoring behavior here.
- `matching/apps.py` — Django app registration metadata.
- `matching/__init__.py` — Python package marker.
- `matching/migrations/__init__.py` — migrations package marker; this app
  currently has no initial model migration in the inventory.

### `exchanges/` — proposals and completed exchanges

- `exchanges/models.py` — exchange proposal and resulting exchange records,
  statuses, and proposal expiry timestamps.
- `exchanges/serializers.py` — API representations/validation for proposals and
  exchanges.
- `exchanges/views.py` — sent/received proposal lists, create/accept/decline/
  cancel/counter actions, exchange details, meeting details, and mutual
  completion confirmation.
- `exchanges/services.py` — shared proposal/exchange rules, participant and
  eligibility checks, item locking/validation, and exchange notifications.
- `exchanges/tasks.py` — scheduled expiry of proposals that have timed out.
- `exchanges/apps.py` — Django app registration metadata.
- `exchanges/__init__.py` — Python package marker.
- `exchanges/migrations/0001_initial.py` — initial proposal/exchange schema.
- `exchanges/migrations/__init__.py` — migrations package marker.

### `messaging/` — exchange conversations

- `messaging/models.py` — persisted exchange/proposal messages and any attached
  media/read-state fields.
- `messaging/views.py` — participant-scoped message retrieval and creation,
  upload URL serialization, proposal filtering, and marking received messages
  read.
- `messaging/apps.py` — Django app registration metadata.
- `messaging/__init__.py` — Python package marker.
- `messaging/migrations/0001_initial.py` — initial message schema.
- `messaging/migrations/__init__.py` — migrations package marker.

### `verification/` — phone, identity, and possession checks

- `verification/models.py` — identity review requests, phone OTP challenges,
  and listing possession-verification evidence/status records.
- `verification/views.py` — create/list identity verification requests, send
  and verify phone challenges, and create/submit photo evidence for listing
  possession checks.
- `verification/apps.py` — Django app registration metadata.
- `verification/__init__.py` — Python package marker.
- `verification/migrations/0001_initial.py` — initial verification schema.
- `verification/migrations/__init__.py` — migrations package marker.

### `moderation/` — privileged review and administration endpoints

- `moderation/views.py` — staff/admin APIs for user account administration,
  listing decisions/removal, identity and possession review, report/dispute
  resolution, and audit-event inspection. When admin review actions fail or
  return the wrong state, inspect the relevant ViewSet/action here.
- `moderation/apps.py` — Django app registration metadata.
- `moderation/__init__.py` — Python package marker.
- `moderation/migrations/__init__.py` — migrations package marker; no
  moderation-owned models are currently defined in this app.

### `reports/` — user reports and exchange disputes

- `reports/models.py` — user-submitted reports and exchange disputes, including
  status and dispute evidence metadata.
- `reports/views.py` — report/dispute serializers, validation, participant/
  reporter scoping, submission, and read endpoints.
- `reports/apps.py` — Django app registration metadata.
- `reports/__init__.py` — Python package marker.
- `reports/migrations/0001_initial.py` — initial report/dispute schema.
- `reports/migrations/__init__.py` — migrations package marker.

### `reviews/` — post-exchange reputation

- `reviews/models.py` — exchange-linked member ratings/reviews and status.
- `reviews/views.py` — public review reads and guarded creation for eligible
  participants after an exchange.
- `reviews/apps.py` — Django app registration metadata.
- `reviews/__init__.py` — Python package marker.
- `reviews/migrations/0001_initial.py` — initial review schema.
- `reviews/migrations/__init__.py` — migrations package marker.

### `notifications/` — in-product notices

- `notifications/models.py` — notification records and read state.
- `notifications/views.py` — user-private notification list/detail and
  mark-one/mark-all-as-read actions.
- `notifications/apps.py` — Django app registration metadata.
- `notifications/__init__.py` — Python package marker.
- `notifications/migrations/0001_initial.py` — initial notification schema.
- `notifications/migrations/__init__.py` — migrations package marker.

### `locations/` — location reference data

- `locations/models.py` — persisted country/state/city or equivalent location
  reference entries.
- `locations/views.py` — location serialization and read access/filtering,
  with privileged write permissions.
- `locations/apps.py` — Django app registration metadata.
- `locations/__init__.py` — Python package marker.
- `locations/migrations/0001_initial.py` — initial location schema.
- `locations/migrations/__init__.py` — migrations package marker.

### `audit/` — staff action history

- `audit/models.py` — audit event record and helper used to record an actor,
  action, target object, and structured details.
- `audit/apps.py` — Django app registration metadata.
- `audit/__init__.py` — Python package marker.
- `audit/migrations/0001_initial.py` — initial audit-event schema.
- `audit/migrations/__init__.py` — migrations package marker.

### `core/` — shared backend behavior

- `core/models.py` — abstract `BaseModel` with UUID primary key and created/
  updated timestamps inherited by domain models.
- `core/serializers.py` — small shared response/request serializers, including
  detail, logout, deactivation, user-type, OTP, Google exchange, and dashboard
  data shapes.
- `core/permissions.py` — shared moderator/administrator access checks and
  trading/block eligibility guards. Update this when a common authorization
  rule changes, and check the affected views still use it.
- `core/media.py` — validated Cloudinary image uploads and short-lived private
  image URLs. Inspect for image size/type/storage problems.
- `core/tasks.py` — periodic cleanup of expired/revoked token records.
- `core/views.py` — health endpoint (database/cache checks) and the user's
  dashboard counts.
- `core/tests.py` — API regression tests covering accounts, listings,
  proposals/exchanges, messaging, matching, reviews, verification, moderation,
  notifications, media, and privacy/access rules. Start here when checking
  behavior-level regressions.
- `core/apps.py` — Django app registration metadata.
- `core/__init__.py` — Python package marker.
- `core/migrations/__init__.py` — migrations package marker; the shared base
  model is abstract and has no table migration of its own.

## Project configuration and operations

- `config/settings.py` — production/default Django settings: installed apps and
  middleware, PostgreSQL, custom user, REST Framework/JWT, API schema, CORS/
  CSRF, Redis/cache, Celery schedules, SMTP, Cloudinary, Twilio/Google OAuth
  variables, and transport/security options. For environment-dependent bugs,
  check the relevant environment variable and this file together.
- `config/test_settings.py` — test-only overrides: in-memory SQLite/cache/email,
  faster password hashing, eager Celery, and test-safe HTTPS behavior.
- `config/urls.py` — top-level route wiring, router registrations, health,
  accounts, product, staff, matching, and verification URLs, plus schema/docs.
  If a route returns 404, start here, then inspect the owning app's `urls.py`
  or ViewSet.
- `config/asgi.py` — ASGI application entry point.
- `config/wsgi.py` — WSGI application entry point used by Gunicorn.
- `config/celery.py` — Celery application setup and automatic task discovery.
- `config/__init__.py` — Python package marker for project configuration.
- `manage.py` — Django command-line entry point for migrations, tests,
  development server, schema generation, and management commands.
- `requirements.txt` — bounded Python runtime dependency versions.
- `.env.example` — names and safe example values for required/optional runtime
  settings. Copy to a local `.env`; do not put real secrets in this tracked
  example file.
- `.gitignore` — files Git excludes, including local environment and Python
  artifacts.
- `.dockerignore` — files excluded from the Docker build context.
- `Dockerfile` — backend container image build, dependency installation,
  non-root runtime user, and Gunicorn startup command.
- `docker-compose.yml` — local/production-style service wiring for PostgreSQL,
  Redis, one-shot migrations, web/Gunicorn, Celery worker, and Celery Beat,
  including health checks and persistent volumes.
- `README.md` — run/deploy/testing instructions and the documented account and
  product API surface. Update it when commands, environment setup, or endpoint
  behavior change.
- `schema.yaml` — checked-in OpenAPI schema snapshot used to inspect documented
  API paths and request/response shapes. Regenerate/validate it with the
  documented `manage.py spectacular` command after API changes; the route and
  serializer source remains authoritative.
- `notes.md` — product requirements/definition document describing the
  exchange product and intended behaviors; use it for product intent, not as
  executable backend configuration.

## Where to start when something breaks

| Symptom | First file(s) to inspect |
| --- | --- |
| Endpoint returns 404 or is missing from the API schema | `config/urls.py`, then the app's `urls.py` (for accounts) or `views.py` |
| Request fields are rejected or response fields are wrong | The feature app's `serializers.py`; if shared, `core/serializers.py` |
| Data is missing, invalid, or has the wrong lifecycle/status | The feature app's `models.py`, `views.py`, and its migrations |
| A database column/table needs to change | Feature app `models.py`, then create and review a new migration; do not rewrite an applied migration |
| Login, registration, profile, password, or Google sign-in fails | `accounts/views.py`, `accounts/oauth.py`, `accounts/serializers.py`, `accounts/services.py`, `accounts/urls.py` |
| Permissions leak data or block a valid operation | The relevant app `views.py`, `core/permissions.py`, and `core/tests.py` |
| Listing image upload/storage fails | `listings/views.py`, `listings/serializers.py`, `core/media.py`, and Cloudinary environment values |
| Match results are inaccurate | `matching/views.py` and the listing/wishlist models and data |
| Proposal acceptance, expiry, or completion is wrong | `exchanges/views.py`, `exchanges/services.py`, `exchanges/models.py`, `exchanges/tasks.py` |
| Messages or notifications are visible to the wrong user | `messaging/views.py` or `notifications/views.py`, their models, and access-control tests |
| Admin review or audit history is wrong | `moderation/views.py`, `audit/models.py`, and `core/permissions.py` |
| Email, SMS, OAuth, database, cache, or deployment behaves differently by environment | `config/settings.py`, `.env.example`, and `docker-compose.yml` |
| Background task is not running | The task module (`exchanges/tasks.py` or `core/tasks.py`), then `config/celery.py`, `config/settings.py`, and Compose worker/beat services |
| An API change is missing from generated docs | `config/urls.py` and the relevant serializer/view, then regenerate `schema.yaml` |

For feature work, follow the vertical slice: route wiring → view/action →
serializer → model/service/task as relevant → migration when the schema changes
→ regression test → OpenAPI schema update. `core/tests.py` contains the current
central API test suite.
