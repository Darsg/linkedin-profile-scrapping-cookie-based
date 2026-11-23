# LinkedIn Profile Scraper

Paste a LinkedIn profile URL → the profile's name, headline, contact info, work
experience, education and recent activity are collected by a background worker,
stored in PostgreSQL, and shown in a Next.js UI.

```
Next.js UI ──HTTP──> FastAPI (stateless) ──enqueue──> Redis ──> Worker(s)
                          │                                        │
                          └──────────── PostgreSQL <───────────────┘
                                                     Worker → ProfileProvider
                                                       ├─ mock        (sample data, offline)
                                                       ├─ playwright  (your own logged-in session)
                                                       └─ api         (third-party data API, Apify)
```

## Run it

Requires Docker, [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
cp .env.example .env
make infra      # Postgres :5433 + Redis :6380 (offset so they don't clash with local ones)
make install
make migrate
make api        # terminal 1 → http://localhost:8001/docs
make worker     # terminal 2
make web        # terminal 3 → http://localhost:3000
```

Out of the box `PROVIDER=mock`, which returns clearly-labelled sample data so the
whole pipeline can be tried without touching LinkedIn.

## Data sources

Set `PROVIDER` in `.env` and restart the API and worker.

| Provider | What it does | Setup |
|---|---|---|
| `mock` | Generated sample data. Slugs `not-found` and `flaky` simulate failures. | none |
| `playwright` | Reads profiles through **your own** LinkedIn session in a real browser. | `make login`, sign in by hand once |
| `api` | Calls an Apify LinkedIn-profile actor. | `APIFY_TOKEN`, `APIFY_ACTOR_ID` (and `APIFY_INPUT_FIELD` if the actor's input isn't `profileUrls`) |

**About the `playwright` provider.** LinkedIn's User Agreement prohibits automated
scraping, and accounts that do it can be restricted. This provider is therefore
deliberately conservative: it never handles your password (you log in yourself in
the window `make login` opens; cookies stay in the git-ignored
`backend/.linkedin-session/`), it fetches one profile at a time with a minimum gap
(`PLAYWRIGHT_MIN_DELAY_SECONDS`) and a daily cap (`PLAYWRIGHT_DAILY_CAP`), and if
LinkedIn shows a login wall or verification it stops and marks the job
`needs_attention` instead of trying to get around it. Use the `api` provider for volume.

Its HTML selectors live in one file, `backend/app/providers/linkedin/parsers.py`,
and are tested against fixtures in `backend/tests/fixtures/`. LinkedIn changes its
markup often: if a field comes back empty, save the page as a fixture, fix the
selector, add a test.

Checked against three live profiles (the account owner's own and two public
figures') in November 2026:

- It runs in a **visible** browser window (`PLAYWRIGHT_HEADLESS=false`). When the
  saved session was used from a headless browser, LinkedIn sent it to the sign-in
  wall and the session cookie was gone afterwards.
- LinkedIn's current pages have hashed class names, so the parsers rely on
  `data-testid`, `componentkey` prefixes, headings and line order. The older
  class-based selectors are kept as a fallback.
- Several roles under one company are split into one experience each, sharing the
  company name and, when the role has none, the company-level location.
- Post times are exact: they are decoded from the id LinkedIn embeds next to each
  post rather than from the "4d" label.
- Known gaps: a post's permalink is only stored when the markup contains one
  (4 of 10 posts on one profile checked, none on another); the rest have an empty
  `url`. Contact info is only available where LinkedIn shows it to your account:
  for one public figure the contact page redirected back to the profile, and for
  both nothing was stored.

Scraped profiles are personal data. Only collect what you have a legitimate reason
to hold; `DELETE /api/v1/profiles/{id}` (or the Delete button) removes a profile
and everything stored about it.

## How it scales

- **Stateless API** — any number of instances behind a load balancer.
- **Queue + workers** — the API only enqueues; start more `make worker` processes to add capacity.
- **One queue per provider** (`scrape:<provider>`) — the slow browser queue runs one job at a time and never blocks API-provider jobs.
- **Idempotent writes** — `INSERT … ON CONFLICT (public_id)` plus child-row replacement in one transaction, so concurrent or repeated scrapes of the same profile leave exactly one consistent row set.
- **Freshness cache** — a profile newer than `PROFILE_TTL_HOURS` is returned without scraping unless `force` is set.
- **Retries** — transient failures retry with exponential backoff; permanent ones (`not found`, `needs_attention`) do not.
- **Raw payload kept** (`profiles.raw` JSONB) — parsing can be fixed without re-scraping.

## Layout

```
backend/app/
  api/v1/        routers (HTTP only)
  services/      use cases — submit a job, execute a job
  repositories/  all database access
  providers/     data sources behind one ProfileProvider protocol
  workers/       arq worker entry point
  models/ schemas/ core/ utils/
frontend/src/
  app/           routes
  features/      scrape/, profiles/ — components + data hooks per feature
  components/ui/ shared primitives
  lib/api/       fetch client + types generated from the backend OpenAPI schema
```

Rule: routers → services → repositories / providers. Providers never touch the
database; they only return a normalized `ScrapedProfile`.

## API

| Method | Path | |
|---|---|---|
| POST | `/api/v1/scrape-jobs` | `{url, force?}` → 202 + job |
| GET | `/api/v1/scrape-jobs/{id}` | job status |
| GET | `/api/v1/scrape-jobs?status=&limit=&offset=` | job history |
| GET | `/api/v1/profiles?q=&limit=&offset=` | search stored profiles |
| GET | `/api/v1/profiles/{id}` | full profile |
| POST | `/api/v1/profiles/{id}/refresh` | forced re-scrape |
| DELETE | `/api/v1/profiles/{id}` | delete profile and its data |
| GET | `/api/v1/health` | database + queue check |

## Development

```bash
make test      # backend tests (uses a separate linkedin_test database)
make lint      # ruff + mypy + eslint
make gen-api   # regenerate frontend types after changing backend schemas (API must be running)
```
