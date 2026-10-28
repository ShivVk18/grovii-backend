# Grovii runbook

For whoever is on call. Production = Render (API, worker, Postgres, Key Value)
+ Vercel (frontend and the `/api` proxy). Every command assumes you are in the
`grovii-backend` repo unless it says otherwise. Configuration: `docs/ENV.md`.

**Where to look first**
- API health: `GET https://<api>/health/deep` (database, Redis, migrations, workers, queue).
- Logs: Render → service → Logs. Lines are JSON. Useful searches:
  `"event": "job_finished"`, `"level": "ERROR"`, `ALERT`, `"request_id": "<id from X-Request-ID>"`.
- Metrics: `GET /metrics` with `Authorization: Bearer $METRICS_TOKEN` (Prometheus format).
- Errors: Sentry project (if `SENTRY_DSN` is set).
- Alerts arrive as CRITICAL `ALERT ...` log lines and in the `ALERT_WEBHOOK_URL` channel.

---

## 1. Deploy

**Staging** (automatic): merge to `main` → GitHub Actions runs `tests-and-security`
→ on success `deploy.yml` triggers the Render staging deploy hooks → Render builds
the image, runs `grovii migrate` (pre-deploy) and switches traffic only when
`/ready` passes → the workflow waits until `/health` reports the new release.
The frontend: Vercel deploys `main` as the staging (preview) environment.

**Production** (manual, approved):
1. Check staging: `/health/deep` OK, try one generation on staging.
2. GitHub → Actions → `deploy` → Run workflow → target `production`. A reviewer approves the `production` environment.
3. It deploys exactly the commit staging is running and waits for `/ready`.
4. Frontend: promote the same commit in Vercel (or merge `main` into the Vercel production branch).
5. Watch `/health/deep`, error rate and `ALERT` lines for 15 minutes.

**Migrations** run before the new version gets traffic. Rules for writing them
(so app-only rollbacks stay possible):
- Additive first: add columns/tables as nullable or with defaults; never rename
  or drop in the same release that stops using something. Drop in a later release.
- Test on a copy of real data: `scripts/restore_db.sh` into a `*_restore` DB,
  then `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head`, `alembic check`.

## 2. Roll back

Decide first: **did the bad release include a migration?** (`git diff <good>..<bad> -- migrations/`)

**A. No migration, or an additive one (normal case): app-only rollback**
1. Render → `grovii-api-<env>` → Events → pick the last good deploy → **Rollback**. Same for `grovii-worker-<env>`.
2. Vercel → Deployments → last good → **Promote to Production** (if the frontend changed).
3. Check `/health` shows the old release and `/ready` is OK. Older code accepts a
   newer database (`/ready` says "database is newer than this release").
4. Revert the bad commit on `main` so the next deploy doesn't bring it back.

**B. The migration itself is the problem: schema rollback, then app rollback**
1. Stop new generations from piling up: scale the worker to 0 only if jobs fail
   on the new schema (queued jobs wait; credits are refunded by the reaper after 30 min).
2. Take a backup first (section 5).
3. Run the downgrade **with the new release's image** (it has the migration script):
   Render → API service → Shell: `alembic downgrade <previous revision>`.
4. Then do A.
5. Never downgrade past a migration that dropped data; restore a backup instead (section 5).

**Tested locally** with the compose stack (`fix/evidence/phase_g/08_rollback_drill.txt`): v2 → v1 app-only rollback with the schema still at v2, then schema downgrade + v1, then roll forward.

## 3. Scale workers

- One worker processes one generation at a time (about 1-2 minutes each with a
  paid Gemini tier). Queue backlog alert = more workers needed (or workers down).
- Render → `grovii-worker-<env>` → Scaling → instances. Or `numInstances` in `render.yaml`.
- Check: `/health/deep` → `workers.count`, `/metrics` → `grovii_queue_length`.
- Limits to keep in mind: Gemini requests per minute (set `LLM_REQUESTS_PER_MINUTE`
  per worker if you hit 429s), Postgres connections (each worker uses up to 3).
- API: scale instances, or `WEB_CONCURRENCY` (processes per instance).

## 4. Rotate a secret

| Secret | How | Effect |
|---|---|---|
| `JWT_SECRET_KEY` | Render env group → new value from `python -c "import secrets;print(secrets.token_urlsafe(64))"` → redeploy API | **Everyone is signed out.** Do it if the key may have leaked. |
| `PROXY_SHARED_SECRET` | Set the new value in Vercel and Render together, redeploy both | Until both match, rate limits see the proxy IP (shared limits). |
| `GEMINI_API_KEY` | Create a new key in Google AI Studio → Render env group → redeploy API **and worker** → delete the old key | Running jobs on the old key may fail and be refunded. |
| Database password | Render → database → rotate credentials; `DATABASE_URL` updates automatically → redeploy | Brief connection errors during the switch. |
| `METRICS_TOKEN`, `ALERT_WEBHOOK_URL`, `SENTRY_DSN` | Update value → redeploy | Update the scraper / channel too. |

After a suspected leak also: search logs for unusual sign-ins, check `/metrics` spend, run
`gitleaks detect` on the repos.

## 5. Backups and restore

- **Automatic:** Render Postgres takes daily backups (retention depends on plan).
- **Off-site copy:** run `scripts/backup_db.sh` on a schedule (e.g. a Render cron job or GitHub Actions)
  with `BACKUP_S3_URI` set. It writes a checksummed, compressed dump.
- **Restore (tested: `fix/evidence/phase_g/02_backup_restore.txt`, 265 storyboards in about 1 s; expect minutes for large databases):**
  1. Restore into a NEW database first: `TARGET_DATABASE_URL=postgresql://.../grovii_restore scripts/restore_db.sh grovii-<stamp>.dump`
  2. Check the printed row counts and `alembic_version`.
  3. If it's correct and production must be replaced: put the API in maintenance (scale API and worker to 0),
     restore into production with `CONFIRM_RESTORE_TO_PRODUCTION=yes`, run `alembic upgrade head`, scale back up.
  4. Data created after the backup is lost; tell affected users.

## 6. The AI provider (Gemini) is down or slow

Symptoms: `ALERT failed_jobs`, many `job_finished` lines with `"status": "failed"`, logs with
`503 UNAVAILABLE`, `429`, `timed out`. Creators see: "Our AI provider is having trouble right
now… Your credit has been refunded."

1. Check https://status.cloud.google.com and https://aistudio.google.com/status.
2. **429 / quota:** check the key's quota and billing in Google AI Studio. Lower `LLM_REQUESTS_PER_MINUTE`
   or the number of workers so jobs stop failing; raise the quota.
3. **Outage:** nothing to fix on our side. Failed jobs are refunded automatically. Optionally scale workers to 0
   to stop burning retries; queued jobs wait (and are refunded by the reaper after `QUEUED_TIMEOUT_MINUTES`).
4. **Model retired / 404:** set `LLM_MODEL` to a supported model, redeploy API and worker.
5. When it recovers: scale workers back, watch `grovii_job_failure_ratio` drop.

## 7. Other alerts

- **queue_backlog:** workers down or too few → `/health/deep` workers count; restart/scale the worker (section 3).
- **spend:** today's estimated spend is near `DAILY_SPEND_LIMIT_USD`. At 100 % generation pauses with a clear
  message until midnight UTC. Check for abuse (one user/IP with many jobs: search logs by `job_id`/`request_id`),
  then decide whether to raise the limit.
- **Redis down:** `/ready` 503, generation returns 503 `queue_unavailable` (credit refunded), login rate limits
  fail open. Queued jobs survive a Redis restart (append-only file; drill: `fix/evidence/phase_g/06_redis_restart_drill.txt`).
  A job that was *running* when Redis restarted may lose its worker connection; the reaper fails and refunds it
  after `RUNNING_TIMEOUT_MINUTES`.
- **Postgres down:** `/ready` 503; the platform stops routing traffic to the API. Check Render's database status.

## 8. Payments

There is **no payment system** (no checkout, webhooks, top-ups or refunds of money). Do not
launch paid plans or show prices until it is built as its own project (BACKLOG).
