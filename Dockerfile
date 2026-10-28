# Grovii backend: one image for the API, the worker and one-off tasks.
#   docker run IMAGE api        # HTTP API (uvicorn)
#   docker run IMAGE worker     # RQ worker (+ stuck-job reaper and alerts)
#   docker run IMAGE migrate    # alembic upgrade head (deploy step)
# Base pinned by digest; dependencies pinned in requirements.txt.

FROM python:3.14.7-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.14.7-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_FORMAT=json
# Unprivileged user; the code is read-only to it.
RUN groupadd --system --gid 10001 grovii && useradd --system --uid 10001 --gid grovii --no-create-home grovii
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts/docker-entrypoint.sh /usr/local/bin/grovii
RUN chmod 0555 /usr/local/bin/grovii && python -m compileall -q src migrations
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; sys.exit(0 if os.environ.get('GROVII_ROLE','api')!='api' or urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health', timeout=4).status==200 else 1)"]
ENTRYPOINT ["grovii"]
CMD ["api"]
