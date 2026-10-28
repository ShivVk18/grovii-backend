# Grovii configuration: every environment variable

All configuration comes from environment variables. No value below is ever
committed with a real secret. **Secret** means: store it only in the platform's
secret settings (Render env group / Vercel project settings), never in git,
never in a `NEXT_PUBLIC_*` variable.

Defaults are what the code uses when the variable is unset.

## Backend (API and worker: same image, same variables)

### Required

| Variable | Secret | What it is |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string. Render injects it from the database. |
| `REDIS_URL` | yes | Redis connection string (default `redis://localhost:6379/0`). Render injects it from Key Value. |
| `JWT_SECRET_KEY` | yes | Signs session tokens. At least 32 random bytes; the app refuses to start with a weak or placeholder value. Rotating it signs everyone out. |
| `GEMINI_API_KEY` | yes | Gemini API key (`GOOGLE_API_KEY` is accepted as a fallback). Needs a paid tier for real users (BACKLOG #27). |
| `APP_ENV` | no | `production` on every deployed environment (staging too): Secure + `__Host-` cookies, HSTS, JSON logs, `/docs` hidden. Default `development`. |
| `CORS_ORIGINS` | no | Comma-separated frontend origins, e.g. `https://grovii.vercel.app`. Writes from any other Origin are refused. Default `http://localhost:3000`. |
| `PROXY_SHARED_SECRET` | yes | Same value as on the frontend. Lets the API trust the client IP the Next.js proxy forwards (for rate limits). Without it every user shares the proxy's IP. |

### Cost and abuse limits (Phase B)

| Variable | Default | Meaning |
|---|---|---|
| `CREDITS_PER_GENERATION` | 1 | Credits charged per generation. |
| `MAX_ACTIVE_JOBS_PER_USER` | 2 | Generations one user may have waiting/running. |
| `ACTIVE_JOB_WINDOW_MINUTES` | 30 | Older unfinished jobs don't count toward the cap. |
| `RATE_GENERATE_PER_USER` | 10 | Per hour. |
| `RATE_GENERATE_PER_IP` | 30 | Per hour. |
| `RATE_LOGIN_PER_IP` | 10 | Per minute. |
| `RATE_REGISTER_PER_IP` | 5 | Per hour. |
| `RATE_CREATE_PER_USER` | 30 | Manual storyboard creates per minute. |
| `DAILY_SPEND_LIMIT_USD` | 20 | All users combined, per UTC day. Generation pauses (503) at the ceiling. |
| `JOB_TOKEN_BUDGET` | 40000 | Tokens per generation job. |
| `LLM_PRICE_INPUT_PER_M` / `LLM_PRICE_OUTPUT_PER_M` | 0.30 / 2.50 | USD per 1M tokens for cost estimates and the ceiling. **Set to your model's real prices.** |

### LLM

| Variable | Default | Meaning |
|---|---|---|
| `LLM_MODEL` | `gemini-3.6-flash` | Model name. |
| `LLM_THINKING_BUDGET` | 0 | Hidden reasoning tokens (0 = off; they count against output caps). |
| `LLM_TIMEOUT_SECONDS` | 60 | Per call. |
| `LLM_MAX_RETRIES` | 2 | Client retries per call. |
| `LLM_REQUESTS_PER_MINUTE` | 0 (off) | Per-process pacing for low quotas. |
| `LLM_BASE_URL` | (unset) | Override the API endpoint (proxies, testing). |

### Jobs and queue

| Variable | Default | Meaning |
|---|---|---|
| `STORYBOARD_QUEUE_NAME` | `storyboards` | Must match between API and worker. |
| `JOB_TIMEOUT_SECONDS` | 300 | One attempt. |
| `JOB_MAX_RETRIES` | 2 | Queue-level retries. |
| `QUEUED_TIMEOUT_MINUTES` | 30 | Waiting longer: failed and refunded by the reaper. |
| `RUNNING_TIMEOUT_MINUTES` | derived | Running longer: failed and refunded. |
| `REAPER_INTERVAL_SECONDS` | 60 | Reaper + alert check interval (in each worker). |
| `ALLOW_INPROCESS_JOBS` | false | Dev only: run jobs inside the API when no worker exists. Never in production. |

### Database pool

| Variable | Default |
|---|---|
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 10 / 10 (API); the worker sets 2 / 1 |
| `DB_POOL_TIMEOUT` | 10 s |
| `DB_POOL_RECYCLE` | 1800 s |

### Security (Phase F)

| Variable | Default | Meaning |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 (7 days) | Session lifetime (max 30 days). Sessions are revocable regardless. |
| `COOKIE_SECURE` | false | Forces Secure cookies outside production. Production always uses them. |
| `MAX_BODY_BYTES` | 65536 | Larger requests get 413. |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCK_SECONDS` | 5 / 900 | Per-account lockout. |

### Operations (Phase G)

| Variable | Secret | Default | Meaning |
|---|---|---|---|
| `LOG_FORMAT` | no | `json` in production, else `text` | Log line format. |
| `LOG_LEVEL` | no | `INFO` | |
| `METRICS_TOKEN` | yes | (unset: `/metrics` is 404) | Bearer token for Prometheus/Grafana scraping `/metrics`. |
| `ALERT_WEBHOOK_URL` | yes | (unset) | Slack-style incoming webhook; alerts are also CRITICAL log lines. |
| `ALERT_WINDOW_MINUTES` | no | 15 | Window for the failed-job count. |
| `ALERT_FAILED_JOBS` | no | 5 | Failed jobs in the window that trigger an alert. |
| `ALERT_QUEUE_BACKLOG` | no | 20 | Waiting jobs that trigger an alert. |
| `ALERT_SPEND_FRACTION` | no | 0.8 | Fraction of the daily ceiling that triggers an alert. |
| `ALERT_COOLDOWN_SECONDS` | no | 1800 | The same alert is sent at most this often. |
| `SENTRY_DSN` | yes | (unset: off) | Error tracking. Personal data is scrubbed before sending. |
| `SENTRY_TRACES_SAMPLE_RATE` | no | 0 | Performance tracing sample rate. |
| `RELEASE` | no | `RENDER_GIT_COMMIT` (Render sets it) or `dev` | Tags logs and Sentry events with the deployed version. |
| `PORT` | no | 8000 | API listen port (Render sets it). |
| `WEB_CONCURRENCY` | no | 1 | uvicorn worker processes per API container. |

### Optional / unused

| Variable | Meaning |
|---|---|
| `IMAGEKIT_PUBLIC_KEY`, `IMAGEKIT_PRIVATE_KEY`, `IMAGEKIT_URL_ENDPOINT` | Image uploads for the (currently unused) thumbnail/scene-image nodes. |
| `OPENAI_API_KEY` | Only the unused image service reads it. Leave unset. |

### Scripts only

| Variable | Used by |
|---|---|
| `BACKUP_KEEP_DAYS` (14), `BACKUP_S3_URI` | `scripts/backup_db.sh` |
| `TARGET_DATABASE_URL`, `CONFIRM_RESTORE_TO_PRODUCTION` | `scripts/restore_db.sh` |
| `TEST_DATABASE_URL`, `TEST_REDIS_URL` | test suite (database name must end in `_test`, Redis db ≠ 0) |

## Frontend (Vercel project settings)

| Variable | Secret | Meaning |
|---|---|---|
| `API_PROXY_TARGET` | no | API base URL the `/api` proxy forwards to, e.g. `https://grovii-api-staging.onrender.com`. Server-side only. |
| `PROXY_SHARED_SECRET` | yes | Same value as the API's. Server-side only; **never** prefix with `NEXT_PUBLIC_`. |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | no | Shown on error screens and the privacy/terms pages. |
| `NEXT_PUBLIC_API_URL` | no | **Leave unset in deployments.** Only for local experiments calling an API directly. |
| `NODE_ENV` | no | Set by Next.js/Vercel. |

## Per-environment summary

| | local dev | local staging (compose) | Render/Vercel staging | production |
|---|---|---|---|---|
| `APP_ENV` | development | production | production | production |
| Secrets | `.env` (git-ignored) | `deploy/staging.env` (git-ignored) | Render env group `grovii-staging` + Vercel Preview env | Render `grovii-production` + Vercel Production env |
| Database | local Postgres | compose `postgres` | `grovii-db-staging` | `grovii-db-production` |
| LLM key | test/free key | fake (no AI calls) | separate key with a low spend ceiling | production key |
