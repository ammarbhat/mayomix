# Mayo-Mix API

Mayo-Mix is a backend for a music review and social app inspired by Letterboxd, built around albums, songs, and personal music taste.

The API lets users create profiles, build curated taste lists, review albums, connect with other users, and view a review activity feed from their accepted connections. Music metadata is provided by MusicBrainz, while album artwork is sourced from the Cover Art Archive.

The project is intentionally designed as a learning-oriented backend: it demonstrates authentication, database modeling, validation, migrations, testing, external API integration, caching, and request pacing in a single application.

> This repository contains the backend API. The frontend is a separate project.

## Features

- JWT authentication with Argon2 password hashing.
- User profiles with favorite genres and profile metadata.
- Curated taste lists for top songs, albums, artists, genres, plus rotating songs and albums.
- Album reviews with a 1–10 rating and up to 400 characters of review text.
- One review per user per album.
- Mutual connection requests with pending, accepted, and removable states.
- Activity feed containing reviews from the current user and accepted connections.
- MusicBrainz-backed search for albums, artists, and songs.
- Album detail lookup with Cover Art Archive cover lookup.
- SQLite-backed caching for album metadata.
- A shared MusicBrainz request gate that spaces outbound requests by roughly one second.
- Alembic migrations and a pytest suite using isolated in-memory SQLite.

## Tech stack

| Area | Technology |
| --- | --- |
| API framework | FastAPI |
| ORM / database access | SQLAlchemy 2.0 |
| Database | SQLite |
| Migrations | Alembic |
| Validation | Pydantic |
| Authentication | JWT / PyJWT |
| Password hashing | pwdlib + Argon2 |
| HTTP client | httpx |
| Testing | pytest + FastAPI TestClient |
| Package / environment management | uv |
| Configuration | pydantic-settings / `.env` |

## Project structure

```text
mayomix/
├── alembic/             # database migrations
├── src/
│   ├── routers/         # API resource areas
│   ├── config.py        # environment-backed application settings
│   ├── database.py      # engine, session, and DB dependency
│   ├── dependencies.py  # authentication and shared helpers
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic request/response models
│   └── main.py          # FastAPI app, middleware, handlers, router registration
├── tests/               # API tests
├── pyproject.toml
└── uv.lock
```

## Getting started

### Prerequisites

- Python 3.14+
- uv

### 1. Clone

```bash
git clone https://github.com/ammarbhat/mayomix.git
cd mayomix
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

No `.env.example` file is currently committed. Create a `.env` file in the project root.

The application expects:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection URL |
| `SECRET_KEY` | Secret used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime |
| `ALGORITHM` | JWT signing algorithm |
| `ORIGINS` | Allowed CORS origins |
| `MUSICBRAINZ_USER_AGENT` | Identifying User-Agent sent to MusicBrainz |

Example shape:

```dotenv
DATABASE_URL=sqlite:///./mayomix.db
SECRET_KEY=replace-me
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
ORIGINS=["http://localhost:3000"]
MUSICBRAINZ_USER_AGENT=Mayo-Mix/0.1 (your-contact@example.com)
```

Use your own values. Never commit real secrets.

### 4. Run the development server

```bash
uv run fastapi dev
```

By default, the API is available at:

```text
http://127.0.0.1:8000
```

Interactive documentation:

- Swagger UI: `/docs`
- ReDoc: `/redoc`

The generated OpenAPI documentation is the authoritative API reference.

### 5. Run tests

```bash
uv run pytest
```

Tests use an in-memory SQLite database and FastAPI dependency overrides, so the test database is isolated from the development database.

### 6. Run migrations

```bash
uv run alembic upgrade head
```

When changing database models, create and review an Alembic migration before applying it to another environment.

> **Current migration note:** the repository currently contains migrations for the original application tables and later indexes, but there is not yet a migration creating the `cached_album` table represented by the current `CachedEntity` model.

## API overview

| Area | Purpose |
| --- | --- |
| Authentication | Login and JWT issuance |
| Users | Registration, own profile, public profiles, editing, account deletion |
| Taste | Curated top lists and rotation lists |
| Reviews | Create, read, edit, delete, and list album/user reviews |
| Connections | Send, accept, remove requests and list connection-state collections |
| Activity | Review feed from the current user and accepted connections |
| Music | MusicBrainz search and album lookup |
| Health | Database connectivity check |

See `/docs` for the complete endpoint contract, request schemas, query parameters, and response shapes.

## Architecture and design decisions

### Store MusicBrainz IDs rather than duplicating music metadata

The application keeps user-owned music references as MusicBrainz IDs instead of maintaining local album, artist, and song records. This keeps the database focused on application-owned state while MusicBrainz remains the external source of music metadata.

The trade-off is dependence on an external service, so the API uses caching for album lookups and defensive upstream handling.

### Derive ownership from authentication

For "my" resources, the current user is obtained from the JWT. The client does not provide a user ID that the server trusts for ownership decisions.

### Use database constraints as a correctness backstop

Important invariants are checked at the API layer for user-friendly errors and enforced in the database. Examples include unique usernames and emails, unique taste ranks within a user/category, unique MBIDs within a user/category, and one review per user/album.

### Use async where the work is I/O-bound

Endpoints that call MusicBrainz use `async def` so network I/O can be awaited. Database-only endpoints remain regular `def` handlers.

### Pace MusicBrainz requests

Outbound MusicBrainz calls pass through a shared asyncio semaphore/timing helper. Only one MusicBrainz request is allowed through the gate at a time, and calls are spaced by roughly one second.

### Cache album metadata

Album lookups use a SQLite-backed cache keyed by MBID. Cached values are intended to be reused during the cache TTL.

### Centralize database conflict handling

The FastAPI app registers a global `IntegrityError` handler that maps database integrity failures to HTTP 409 responses. Unexpected exceptions are mapped to a generic HTTP 500 response.

Some router functions also catch `IntegrityError` locally and roll back; those caught exceptions do not reach the global handler.

### Keep the activity feed derived

The activity feed is built from reviews and accepted connections at request time instead of stored separately. Reviews and connections remain the sources of truth.

## Current scope and limitations

- No frontend is included in this repository.
- No production deployment configuration is included yet.
- Pagination is implemented for reviews and activity but is not standardized across every collection endpoint.
- MusicBrainz search responses are returned in the upstream JSON shape rather than a custom normalized schema.
- The connection relationship is intentionally represented with two user IDs rather than ORM foreign-key relationships to the user table.
- Search results are not currently cached.
- There is no dedicated connection-status endpoint; profile UIs need to derive status from accepted, pending, and sent connection collections.

## Roadmap

1. Build and integrate the frontend.
2. Add the missing cache migration and stabilize the album-cache contract.
3. Fix the rotation-song validation path.
4. Standardize pagination and collection-response behavior.
5. Add broader integration/edge-case tests for caching and external API failures.
6. Add production deployment and observability.
7. Introduce stable normalized response schemas where they improve frontend integration.
8. Continue moving remaining database queries to SQLAlchemy 2.0-style `select()` usage.

## Credits

Music metadata: MusicBrainz

Album artwork: Cover Art Archive

## License

No license file is currently included in the repository.