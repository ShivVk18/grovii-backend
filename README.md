# Grovii Backend

Grovii is a powerful backend application built with FastAPI, PostgreSQL, SQLAlchemy, and LangGraph, designed to automate content creation and strategy for social media. It integrates an intelligent graph-based AI pipeline capable of generating scripts, captions, hashtags, storyboards, dynamic scenes, and actionable trends.

## Features

- **User Authentication**: Secure JWT-based authentication.
- **Storyboard Management**: Full CRUD operations for video storyboards.
- **LangGraph AI Pipeline**: An advanced execution graph integrating:
  - **Hook Generation & Regeneration**: Creates viral hooks tailored to different styles.
  - **Scene Generation**: Generates full cinematic scene descriptions and prompts.
  - **Script Writing**: Generates compelling video scripts.
  - **Caption & Hashtag Generation**: SEO-optimized social media copy.
  - **Trend Analysis**: Insights on editing styles, sounds, and content gaps.
  - **Music Suggestion**: Recommends tempo, genre, and mood per scene.
  - **Content Repurposing**: Transforms scripts into LinkedIn posts, Twitter threads, newsletters, and more.
- *(WIP) Image Generation Pipeline*: Database schema support for AI image generation integrations (Flux, Replicate, HuggingFace).

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL / SQLite (for local testing), SQLAlchemy ORM, Alembic Migrations
- **AI/LLM**: LangChain, LangGraph, OpenAI
- **Testing**: Pytest, Mock

## Folder Structure

```
grovii-backend/
├── alembic/                # Database migrations
├── src/
│   ├── ai/                 # LangGraph state, graph, nodes, and prompts
│   ├── api/                # FastAPI routers and endpoints
│   ├── config/             # Database and app configurations
│   ├── models/             # SQLAlchemy ORM models
│   ├── repositories/       # Database query abstraction layer
│   ├── Schemas/            # Pydantic validation schemas
│   └── services/           # Business logic and external service integrations
├── tests/                  # Pytest test suites
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic configuration
└── main.py                 # Application entry point
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd grovii-backend
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

Copy `.env.example` to `.env` and fill in real values. `.env` is git-ignored; never commit it.

```bash
cp .env.example .env
```

`JWT_SECRET_KEY` is required. The API **refuses to start** if it is missing,
shorter than 32 bytes, or a known placeholder. Generate a fresh value for each
environment:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Changing the secret logs every user out, because existing tokens stop verifying.

### Secret scanning

Commits are scanned for secrets with [gitleaks](https://github.com/gitleaks/gitleaks).
Run once per clone:

```bash
brew install gitleaks          # or download a release binary
./scripts/install-git-hooks.sh
```

The hook blocks any commit that contains a secret. CI runs the same scan on
every pull request.

## Database Setup

Initialize the database using Alembic migrations:

```bash
alembic upgrade head
```

## Running the Application Locally

Start the FastAPI development server:

```bash
uvicorn src.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. You can view the interactive Swagger documentation at `http://localhost:8000/docs`.

## API Documentation

Key endpoints available via the API:

### Authentication
- `POST /api/v1/auth/login` - Authenticate and receive JWT.
- `POST /api/v1/auth/register` - Create a new user account.

### Storyboards
- `GET /api/v1/storyboards` - List user storyboards.
- `POST /api/v1/storyboards` - Create a new storyboard.
- `GET /api/v1/storyboards/{id}` - Retrieve storyboard details.
- `PUT /api/v1/storyboards/{id}` - Update a storyboard.
- `DELETE /api/v1/storyboards/{id}` - Delete a storyboard.

### Graph / AI Pipeline
- `POST /api/v1/storyboards/{id}/generate` - Trigger the complete LangGraph pipeline (Hooks, Script, Captions, Trends, etc.) for a specific storyboard.

*For complete details, including request payloads and response structures, please refer to the `/docs` endpoint when running the app.*

## Testing

Tests run against a local Postgres database named `grovii_test` (created once
with `createdb grovii_test`). They never call OpenAI: a fake key is forced.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # runs tests/ only
pytest --cov=src            # with coverage
ruff check src tests        # lint
mypy src                    # type check
```

`tests/test_regressions.py` holds tests for known bugs, marked `xfail` until
fixed. The old root scripts `test_api.py` and `test_graph.py` call a live
server and the real OpenAI API, so they are not part of the suite.

## Deployment Guidelines

1. Provision a PostgreSQL instance and update `DATABASE_URL` in the production environment.
2. Ensure `ENVIRONMENT=production` is set.
3. Deploy the application using Docker, Render, Heroku, or AWS Elastic Beanstalk using `uvicorn` or `gunicorn` with Uvicorn workers.

## Contribution

1. Fork the repository
2. Create a new branch (`git checkout -b feature/awesome-feature`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome-feature`)
5. Open a Pull Request
