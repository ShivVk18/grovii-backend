# First-time setup: staging and production (Render + Vercel)

Do these once, in order. Nothing here was run by the fix work (it was not
allowed to deploy); every step is for the owner. Staging first, production only
after staging has worked for a while. Day-to-day operations: `docs/RUNBOOK.md`.

## 0. Before you start

- [ ] Phases A-G merged into `main` in both repos (backend `grovii-backend`, frontend `frontend`).
- [ ] Old leaked credentials rotated (Phase A owner actions).
- [ ] A **paid** Gemini key for production, and a separate key for staging with a low limit.
- [ ] Decide `DAILY_SPEND_LIMIT_USD` and the real `LLM_PRICE_*` values for your model.
- [ ] Optional: a Sentry project (two DSNs: staging, production) and a Slack incoming webhook for alerts.
- [ ] Generate one `PROXY_SHARED_SECRET` per environment: `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`.

## 1. Backend on Render (staging)

1. Render dashboard → **New → Blueprint** → connect the `grovii-backend` GitHub repo → blueprint file `render.yaml`.
2. Render shows the resources it will create: `grovii-api-staging`, `grovii-worker-staging`,
   `grovii-redis-staging` (Key Value, `noeviction`), `grovii-db-staging` (Postgres 18), env group
   `grovii-staging`. Check plan names and region in the preview (field names were written from
   Render's Blueprint spec but not applied by us: **UNVERIFIED**).
3. Fill the `sync: false` values in the env group:
   - `CORS_ORIGINS` = your Vercel staging URL (step 2), e.g. `https://grovii-git-main-<team>.vercel.app`
     (you can set it after step 2 and redeploy).
   - `PROXY_SHARED_SECRET` = the staging value from step 0.
   - `GEMINI_API_KEY`, `LLM_PRICE_INPUT_PER_M`, `LLM_PRICE_OUTPUT_PER_M`, optional `ALERT_WEBHOOK_URL`, `SENTRY_DSN`.
4. Apply. The first API deploy runs `grovii migrate` (pre-deploy) on the empty database, then
   starts; Render waits for `/ready`.
5. Check: `https://grovii-api-staging.onrender.com/health/deep` → all `ok`, `workers.count` ≥ 1.

## 2. Frontend on Vercel (staging)

1. Vercel → **Add New → Project** → import the `frontend` repo. Framework: Next.js (auto).
2. Settings → Git → Production Branch: **`production`** (so `main` deploys are staging/preview, and
   production only changes when you promote).
3. Settings → Environment Variables, scope **Preview**:
   - `API_PROXY_TARGET` = `https://grovii-api-staging.onrender.com`
   - `PROXY_SHARED_SECRET` = the staging value (same as Render)
   - `NEXT_PUBLIC_SUPPORT_EMAIL` = your support address
   - Do **not** set `NEXT_PUBLIC_API_URL`.
4. Deploy `main`. Copy its URL into the backend's `CORS_ORIGINS` (step 1.3) and redeploy the API.
5. Check in a browser: sign up, sign in, create a shoot plan, open it, Settings → Download my data.

## 3. CI/CD wiring (GitHub)

Backend repo → Settings:
- **Secrets → Actions:** `RENDER_DEPLOY_HOOK_STAGING_API`, `RENDER_DEPLOY_HOOK_STAGING_WORKER`
  (Render → service → Settings → Deploy Hook), later the `..._PRODUCTION_...` pair.
- **Variables → Actions:** `STAGING_API_URL`, `PRODUCTION_API_URL`.
- **Environments:** create `staging` and `production`; on `production` add **required reviewers**.
- In Render, set **Auto-Deploy: No** on the staging services if you want deploys only from
  the workflow (after tests pass). `render.yaml` sets `autoDeploy: true` for staging; change it to
  `false` once the workflow is wired.
- **Branch protection** on `main` (both repos): require the `tests-and-security` / `frontend-ci`
  checks and the `secret-scan` check before merging.

The deploy workflow passes `&ref=<commit>` to the deploy hook so the deployed commit is the
tested one. Render documents deploy hooks; whether `ref` is honoured for your service type is
**UNVERIFIED**: if it isn't, the hook deploys the branch head, which is the same commit when
deploys run right after the merge.

## 4. Production

Repeat 1-2 with `render.production.yaml` (resources named `...-production`) and the Vercel
**Production** environment scope, with production values (paid Gemini key, production
`PROXY_SHARED_SECRET`, production Sentry DSN). Then promote with the `deploy` workflow
(RUNBOOK section 1).

Before real users:
- [ ] Privacy policy and terms reviewed by a lawyer (pages are marked as drafts).
- [ ] `NEXT_PUBLIC_SUPPORT_EMAIL` is a monitored inbox.
- [ ] Backups: confirm Render's backup retention for your plan; schedule `scripts/backup_db.sh`
      to off-site storage (RUNBOOK section 5) and do one restore drill on production data.
- [ ] Alerts reach a human (send a test: temporarily set `ALERT_QUEUE_BACKLOG=-1` on staging).
- [ ] Metrics scraped (Grafana Cloud / any Prometheus: scrape `/metrics` with the bearer token),
      or rely on the JSON `job_finished` log lines in Render's log search.
- [ ] No paid plans or prices shown anywhere (there is no payment system).
