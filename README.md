# BataX backend

Django REST API for the item-for-item exchange product defined in `notes.md`.
Email is the case-insensitive, database-enforced unique login identifier. The
public signup role is `user`; moderator and administrator accounts are created
by authorized staff. Only super administrators can create other administrators.

## Run with Docker

1. Copy `.env.example` to `.env` and set fresh secrets and service credentials.
2. Run `docker compose up --build -d`.
3. Run `docker compose exec web python manage.py createsuperuser`.
4. Open `http://localhost:8002/api/docs/` for the interactive API reference.

Compose runs PostgreSQL, authenticated Redis, a one-shot migration service,
Gunicorn, a Celery worker and one Celery Beat scheduler. Database and Redis ports
are private to the Docker network. Database, Redis and scheduler data persist
in named volumes. Web binds to the host loopback interface for a reverse proxy.

The example configuration is for local development. For deployment set
`DEBUG=false`, use your actual `ALLOWED_HOSTS` (also retain `127.0.0.1` for the
container health check), HTTPS frontend/API URLs and explicit CORS/CSRF origins.
Terminate TLS at your reverse proxy. Set `TRUST_PROXY=true` only when that proxy
strips client-supplied `X-Forwarded-Proto` and supplies its own trusted value.
Configure SMTP rather than console email. Use URL-safe alphanumeric Redis
credentials, or percent-encode the Redis URL if configuring it separately.
Back up PostgreSQL volumes independently of container deployments.

## Local development and verification

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
# Configure .env for reachable PostgreSQL and Redis services.
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver

# Isolated tests need neither PostgreSQL nor Redis:
.\.venv\Scripts\python manage.py test --settings=config.test_settings
.\.venv\Scripts\python manage.py makemigrations --check --dry-run --settings=config.test_settings
.\.venv\Scripts\python manage.py spectacular --settings=config.test_settings --file schema.yaml --validate
```

Tests use SQLite, in-memory cache and captured email. PostgreSQL row-lock
contention and live provider integrations must additionally be tested in the
deployment environment. Runtime dependencies are bounded in `requirements.txt`.

## Account API

These routes retain Declutter's `/api/accounts/` paths. JSON request bodies are
used unless uploading images. Login returns `{access, refresh, user}`. Send
`Authorization: Bearer <access>` for protected routes. Refresh tokens are
submitted in JSON, rotated and blacklisted; this backend does not rely on an
authentication cookie. Password changes invalidate existing JWTs.

| Method | Path under `/api/accounts/` | Purpose / payload |
| --- | --- | --- |
| POST | `register/` | `email`, `password`, `first_name`, `last_name`, `accept_terms: true`; optional `phone_number`, `state`, `city` |
| POST | `verify-otp/` | `email`, six-digit `otp` |
| GET | `verify-email/{token}/` | Single-use email verification link |
| POST | `resend-otp/` | `email` |
| POST | `login/` | `email`, `password`; verified email required |
| POST | `logout/` | `refresh` belonging to the current user |
| POST | `token/refresh/` | `refresh` |
| POST | `token/verify/` | `token` |
| GET | `auth/google/login/` | Browser redirect to Google |
| GET | `auth/google/callback/` | Google callback, validated against browser session state |
| POST | `auth/google/exchange/` | Single-use `code`; `accept_terms: true` for new accounts |
| GET | `me/` | Private account details |
| GET, PATCH | `profile/` | Profile fields, bio and multipart `profile_image` |
| POST | `password-reset/` | `email`; always returns a generic response |
| POST | `password-reset/confirm/` | `uid`, `token`, `new_password` |
| POST | `password-change/` | `old_password`, `new_password` |
| POST | `deactivate/` | `password`; active exchanges must be resolved first |
| GET, PATCH | `notification-preferences/` | Preference booleans |
| POST | `contact/` | `name`, `email`, `message` |
| GET | `sellers/{public_id}/` | Public profile; also available as `users/{public_id}/` |
| GET | `user-types/` | Roles and self-registration eligibility |
| GET, POST | `blocks/` | List blocks or create with `blocked_user` UUID |
| DELETE | `blocks/{id}/` | Remove own block |
| GET, POST | `verify-nin/` | Compatibility route for identity review requests |

Differences from Declutter are intentional: registration requires terms
acceptance, profile images use Cloudinary uploads, and `verify-nin/` accepts
`provider` and `reference`, **not a raw NIN**. A reference creates a pending
request; it does not automatically verify the account. A moderator checks the
reference with the provider before approving it. No identity-provider-specific
API is connected yet.

## Product API

Collections are paginated with `count`, `next`, `previous`, `results`.
IDs are UUIDs. Status values are lowercase.

| Route | Operations |
| --- | --- |
| `/api/categories/` | Public read; administrator create/update/delete |
| `/api/locations/` | Public read, country/state filters; administrator writes |
| `/api/listings/` | Browse/search and create draft; owner detail/update/soft-delete |
| `/api/listings/mine/` | Current user's listings in every state |
| `/api/listings/{id}/images/` | POST multipart `image`, optional `caption` |
| `/api/listings/{id}/submit/` | POST to moderation after verification requirements |
| `/api/listings/{id}/pause/` | POST; cancels pending proposals |
| `/api/wishlist/` | Own CRUD: `listing` (optional), `title` and/or `category`, optional `brand`, `model` |
| `/api/matches/` | GET; optional own `listing` and candidate `city` filters |
| `/api/proposals/` | Own sent/received proposals; POST `offered_item`, `requested_item`, optional `message` |
| `/api/proposals/{id}/accept/` | Recipient POST creates and returns an exchange |
| `/api/proposals/{id}/decline/` | Recipient POST |
| `/api/proposals/{id}/cancel/` | Sender POST |
| `/api/proposals/{id}/counter/` | Recipient POST reversed offered/requested items and optional message |
| `/api/exchanges/` | Participant-only list/detail |
| `/api/exchanges/{id}/meeting/` | PATCH private `meeting_details` |
| `/api/exchanges/{id}/confirm/` | POST; completes only after both parties confirm |
| `/api/messages/` | Participant-only list/detail/create; filter `proposal`; `body` and/or multipart `image` |
| `/api/messages/{id}/read/` | Recipient POST marks read |
| `/api/reviews/` | Public list/detail; completed-exchange participant POST `exchange`, `rating`, `comment` |
| `/api/reports/` | Own list/detail/create: `target_type`, `target_id`, `reason`, `description` |
| `/api/disputes/` | Participant list/detail; POST `exchange`, `reason`, `description`, optional multipart `image` |
| `/api/notifications/` | Own list/detail |
| `/api/notifications/{id}/read/` | POST mark one read |
| `/api/notifications/read-all/` | POST mark all read |
| `/api/dashboard/` | Own listing/offer/exchange/notification counts |
| `/api/verification/phone/send/` | POST sends SMS to profile phone (E.164 format) |
| `/api/verification/phone/verify/` | POST `otp`; changing profile phone clears verification |
| `/api/verification/identity/` | GET/POST provider reference review requests |
| `/api/verification/possession/{listing_id}/` | POST creates timed photo challenge; PATCH multipart `image` submits evidence |

Listing filters include category, condition, state, city, brand and possession
verification, with `search` across title/description/brand/model. Publishing
requires verified email, phone and identity; two images; approved possession
evidence; and wanted items or openness to offers. Material edits return the
listing to draft and invalidate possession approval.

Matching compares listing-specific wants in both directions, using title,
category, brand/model and openness to offers. Standalone wishlist entries are
saved preferences; attach them to a listing to power reciprocal matching.
Results identify exact reciprocal, flexible reciprocal and one-way
opportunities. Pagination is over candidates before pairing, so `count` counts
candidates rather than generated pairs. This is a deterministic MVP matcher,
not semantic AI or a multi-person exchange engine.

Acceptance locks both listing rows in PostgreSQL, reserves both items and
cancels conflicting pending proposals. Suspended or blocked participants
cannot proceed with trading. Counter-offers substitute one item per side;
multi-item bundles and cash top-ups are not implemented. Expiry runs every five
minutes through Celery, and acceptance rejects expired offers immediately.

## Staff API

Moderators and administrators access `/api/admin/listings/`, `identity/`,
`possession/`, `reports/`, and `disputes/`. Review actions at `{id}/review/`
accept `decision: approve|reject` and `reason`. Reports use `{id}/resolve/`
with `resolution`; disputes additionally require `outcome: completed|cancelled`.
Cancelled disputes leave items paused for owner review. Listing removal uses
`/api/admin/listings/{id}/remove/`.

Administrators access `/api/admin/users/`, `{id}/suspend/`,
`/api/admin/users/create-account/` and `/api/admin/audit/`. Account creation
requires `email`, `password`, `first_name`, `last_name`, `role`. New staff still
verify their email using the resend/verification flow. Audit records capture
review decisions and critical exchange actions. Django `/admin/` also supports
superuser account management; use the staff API for moderated workflows.

## Media and external services

All uploaded images use Cloudinary, not local media storage. Avatars and listing
photos are public. Chat attachments, possession and dispute evidence are
authenticated assets, exposed through short-lived signed download URLs only
to permitted viewers. Uploads validate image contents and restrict format to
JPEG, PNG or WebP, at most 10 MB. No raw identity documents are collected.
See [Cloudinary upload parameters](https://cloudinary.com/documentation/upload_parameters)
for authenticated asset behavior.

Set Cloudinary credentials, SMTP settings, Twilio SMS credentials and Google
OAuth credentials to exercise the live integrations. Missing SMS or Google
configuration fails explicitly. Identity review is manual using provider
references. Messaging is REST/polling; WebSockets are not included. Notifications
are stored in-app; email preferences are saved for future notification delivery
workers. Automated fraud detection, administrator MFA enrollment, logistics and
multi-party exchanges remain outside this implementation.

## Git

`.env`, environment variants, `.venv/`, `venv/`, caches and generated runtime
files are ignored. `.env.example` is intentionally tracked and contains no
real credentials. Never put real credentials into it. If credentials were
previously pushed, rotate them even after rewriting repository history.
