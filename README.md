# Mayo-Mix API

Mayo-Mix is a backend for a music-review and social app inspired by Letterboxd, built around albums, songs, and personal music taste.

The API lets users create profiles, build curated taste lists, review albums, discover users, connect with other users, and view a review activity feed from accepted connections. Music metadata is provided by MusicBrainz, while album artwork is sourced from the Cover Art Archive.

The project is intentionally designed as a learning-oriented backend: it demonstrates authentication, database modeling, validation, migrations, testing, external API integration, caching, and request pacing in a single application.

> This repository contains the backend API. The frontend is a separate project.

## Features

- JWT authentication with Argon2 password hashing.
- User registration, profile editing, public profiles, username search, and account deletion.
- User profiles with favorite genres and profile metadata.
- Curated taste lists for top songs, albums, artists, and genres, plus rotating songs and albums.
- Album reviews with a 1–10 rating and up to 400 characters of review text.
- One review per user per album.
- Connection requests, acceptance/decline, removal, connection lists, and connection-status lookup.
- Activity feed containing reviews from the current user and accepted connections.
- MusicBrainz-backed search for albums, artists, and songs.
- Album detail lookup with Cover Art Archive artwork lookup.
- SQLite-backed caching for album metadata.
- A shared MusicBrainz request gate that serializes and spaces outbound requests by roughly one second.
- Alembic migrations and a pytest suite using isolated in-memory SQLite.

## Tech stack

| Area | Technology |
| --- | --- |
| API framework | FastAPI |
| ORM / database access | SQLAlchemy 2.0 |
| Database | SQLite |
| Migrations | Alembic |
| Validation | Pydantic |
| Authentication | PyJWT / JWT |
| Password hashing | pwdlib + Argon2 |
| HTTP client | httpx |
| Testing | pytest + FastAPI TestClient |
| Package / environment management | uv |
| Configuration | pydantic-settings / `.env` |
| Music metadata | MusicBrainz |
| Album artwork | Cover Art Archive |

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
- [uv](https://docs.astral.sh/uv/)

### 1. Clone the repository

```bash
git clone https://github.com/ammarbhat/mayomix.git
cd mayomix
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

There is no committed `.env.example` file at present. Create a `.env` file in the project root.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection URL |
| `SECRET_KEY` | Secret used to sign JWTs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes |
| `ALGORITHM` | JWT signing algorithm |
| `ORIGINS` | Allowed CORS origins |
| `MUSICBRAINZ_USER_AGENT` | Identifying User-Agent sent to MusicBrainz |

Example configuration:

```dotenv
DATABASE_URL=sqlite:///./mayomix.db
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALGORITHM=HS256
ORIGINS=["http://localhost:5173"]
MUSICBRAINZ_USER_AGENT=Mayo-Mix/0.1 (your-contact@example.com)
```

Replace the example values with your own. Use a long, random secret and never commit real secrets. Set `ORIGINS` to the origin(s) used by your frontend.

### 4. Apply database migrations

```bash
uv run alembic upgrade head
```

The migration chain includes the `cached_album` table. When you change database models, generate and review an Alembic migration before applying the change to another environment.

### 5. Run the development server

```bash
uv run fastapi dev
```

By default, the API is available at `http://127.0.0.1:8000`.

Interactive documentation:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

The generated OpenAPI documentation is the authoritative reference for endpoint request and response schemas.

### 6. Run tests

```bash
uv run pytest
```

Tests use an in-memory SQLite database and FastAPI dependency overrides, keeping test data isolated from the development database.

## API overview

| Area | Purpose |
| --- | --- |
| Authentication | Login and JWT issuance |
| Users | Registration, own profile, public profiles, username search, editing, and account deletion |
| Taste | Curated ranked lists, rotation lists, and liked entries |
| Reviews | Create, read, edit, delete, and list album/user reviews |
| Connections | Send, accept, decline, remove, and inspect connection requests and status |
| Activity | Review feed from the current user and accepted connections |
| Music | MusicBrainz search and album metadata/artwork lookup |
| Health | Database connectivity check |

See `/docs` for the complete endpoint contract, request schemas, query parameters, and response shapes.

### Selected endpoint behavior

- `GET /users/search?username=<substring>` searches usernames by substring and returns up to 20 matching users.
- `GET /connections/me/status/{username}` reports the current user's connection state with that username. Possible values include `not_found`, `pending_sent`, `pending_recieved`, and `connected`; an unknown username returns 404. Note that `pending_recieved` is the current spelling in the API response.
- `GET /search/albums` is protected and defaults to 15 results, with a limit range of 1–24.
- `GET /search/artists` is public and defaults to 6 results, with a limit range of 1–24.
- `GET /search/songs` is public and defaults to 10 results, with a limit range of 1–24.
- Album reviews use a rating from 1 to 10 and review text of up to 400 characters.
- Review and activity feeds support `limit` and `offset` pagination. Some empty result pages may return 404 rather than an empty list.

Use `/docs` to confirm exact methods, authentication requirements, payloads, and response schemas.

## Architecture and design decisions

### Store MusicBrainz IDs instead of duplicating music metadata

The application stores MusicBrainz IDs (MBIDs) for user-owned music references instead of maintaining local album, artist, and song catalogs. This keeps the database focused on application-owned state while MusicBrainz remains the external source of music metadata.

The trade-off is dependence on an external service, so the API uses caching for album lookups and defensive handling around upstream requests.

### Derive ownership from authentication

For protected “my” resources, the current user is derived from the JWT bearer token. The client does not supply a user ID that the server trusts for ownership decisions.

### Use database constraints as a correctness backstop

Validation at the API layer can provide user-friendly errors, while database constraints enforce important invariants. These include unique usernames and emails, unique taste ranks within a user/category, unique MBIDs within a user/category, and one review per user/album.

### Use async where the work is I/O-bound

Endpoints that call MusicBrainz use `async def` so network I/O can be awaited. Most database-only endpoints use regular synchronous route handlers.

### Pace MusicBrainz requests

Outbound MusicBrainz calls pass through a shared asynchronous gate. It serializes requests and spaces them by roughly one second, helping the app avoid sending requests too quickly.

### Cache album metadata

Album metadata is stored in a SQLite-backed cache keyed by MBID, with a cache lifetime configured in the implementation. The cache path still has issues described below, so the current behavior should not be treated as fully optimized.

### Centralize database conflict handling

The FastAPI app registers a global `IntegrityError` handler that maps uncaught database integrity failures to HTTP 409 responses. Unexpected exceptions are mapped to a generic HTTP 500 response.

Some router functions also catch `IntegrityError` locally and roll back. Because those exceptions are handled inside the route, they do not reach the global handler; a few paths may still return a success-shaped response after a failed write.

### Keep the activity feed derived

The activity feed is built from reviews and accepted connections at request time instead of storing a separate copy of activity events. Reviews and connections remain the sources of truth.

## Current scope and limitations

- The frontend is not included in this repository.
- Production deployment and observability configuration are not included yet.
- Pagination is implemented for reviews and activity but is not standardized across every collection endpoint.
- Some empty collection or page results return 404 instead of consistently returning an empty list.
- MusicBrainz search results are returned in the upstream JSON shape rather than a custom normalized response schema.
- Search results are not currently cached.
- The album endpoint makes a MusicBrainz request before checking whether cached metadata is fresh, which reduces the benefit of the cache.
- There is no password-reset, email-verification, refresh-token/revocation, password-change, or profile-image-upload flow yet.

## Roadmap

1. Build and integrate the frontend.
2. Standardize the album detail response shape for cache hits and fresh fetches.
3. Ensure failed database writes cannot return success responses.
4. Standardize pagination and empty-collection response behavior.
5. Add broader integration and edge-case tests for caching and external API failures.
6. Add production deployment, configuration, and observability.
7. Introduce normalized response schemas where they improve frontend integration.
8. Continue moving remaining database queries toward SQLAlchemy 2.0-style `select()` usage.

## Credits

- Music metadata: [MusicBrainz](https://musicbrainz.org/)
- Album artwork: [Cover Art Archive](https://coverartarchive.org/)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
