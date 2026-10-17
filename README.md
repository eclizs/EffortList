# EffortList

A web app for preparing bulk orders from a reusable item dictionary. Import your catalog, find items with prefix autocomplete, and build a list with quantities to copy or download.

EffortList combines a FastAPI backend with a custom trie written in C, connected through Python's `ctypes`. The frontend uses HTML, CSS, and JavaScript modules.

## Features

- **Prefix autocomplete:** Search without matching capitalization and keep each item's original spelling.
- **Order preparation:** Add optional quantities and a header, edit your list, copy it to the clipboard, or download it as text.
- **CSV imports:** Choose a column, review a paginated preview, and inspect duplicate, invalid, and failed entries after importing.
- **Dictionary management:** Add individual items, delete entries, or clear the dictionary with confirmation.
- **Guest sessions and accounts:** Try the dictionary as a guest, then register to save entries to your account.
- **Account recovery:** Reset passwords using expiring email links. Passwords are hashed with Argon2, and sessions use signed cookies.

## How to use it

1. Open **Add** to enter items individually or upload a CSV file.
2. Open **Search**, enter an optional quantity, and type an item prefix. Click a suggestion or select it with the arrow keys and Enter.
3. Edit the assembled list and optionally add a header.
4. Use **Copy to clipboard**, or press **Save** to append a snapshot to the temporary buffer. **Preview** shows the buffer; **Download** exports it and clears the buffer.
5. Register an account to persist your dictionary. Guest entries are transferred during registration, subject to the limit below.

The dictionary and the order list have different lifetimes: account dictionary entries are stored in the database, while the order list and Save buffer exist only in the current page. Reloading the page loses the order list and buffer. Guest dictionaries exist only in server memory and are lost when the server restarts or the guest logs out.

### CSV format

For regular accounts and guests, CSV files should include a header row:

```csv
name,category
Rice 5kg,Pantry
Cooking Oil 1L,Pantry
Dish Soap,Cleaning
```

Enter `name` in **Column to parse**, or leave it blank to use the first column. Previewing a file does not insert entries; confirm the preview to import them. Imports report success or failure for each entry, so some entries can succeed while others fail.

Admin accounts use a specialized importer that reads the third column without a header row and removes quoted word tokens. The column selector does not apply to this format.

### Keyboard shortcuts

| Key | Action |
| --- | --- |
| Up / Down | Move through search suggestions |
| Enter in search | Add the highlighted suggestion, the first result, or the typed text if there are no results |
| Space / Enter in quantity | Move to the search field |
| Backspace in an empty search field | Move back to quantity when enabled |
| Alt+C | Toggle **Clear after adding** |

## Architecture

| Component | Technology and role |
| --- | --- |
| Frontend | HTML, CSS, and JavaScript modules for search, imports, order lists, and account forms |
| API | FastAPI for dictionary operations, authentication, and static file serving |
| Search | C trie loaded as `libtrie.so` through `ctypes` |
| Persistence | Async SQLAlchemy with PostgreSQL; Alembic for schema migrations |
| CSV parsing | Pandas with separate regular and admin import formats |
| Authentication | Argon2 password hashes, signed session cookies, and signed password reset tokens |
| Email | Asynchronous SMTP delivery through `aiosmtplib` |

Each guest or account has a separate trie and an asynchronous lock to serialize access within the server process. Account tries are populated from the database on first use. For signed-in accounts, dictionary changes update both the database and the in-memory trie.

## Local setup

### Requirements

- Python 3.12 or newer
- GCC and Make in a Linux environment, or another environment supporting the current `.so` build
- A running PostgreSQL database and credentials with permission to create tables
- An SMTP service for password reset emails

Run the following commands from the repository root; the app resolves frontend assets relative to that directory.

### 1. Install dependencies and build the trie

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make
```

`make` builds `backend/src/libtrie.so`, which must exist before importing or starting the application.

### 2. Configure the environment

Create a `.env` file in the repository root, replacing the example credentials and secret:

```dotenv
DATABASE_URL=postgresql+psycopg://effortlist:your-password@localhost:5432/effortlist
SECRET_KEY=replace-with-a-random-secret
FRONTEND_URL=http://localhost:8000
SESSION_COOKIE_SECURE=false
```

Generate a secret with:

```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

The PostgreSQL role and database must already exist. For password reset emails, also configure:

```dotenv
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
MAIL_FROM=noreply@example.com
MAIL_USE_TLS=true
MAIL_TIMEOUT_SECONDS=10
RESET_TOKEN_EXPIRE_MINUTES=60
```

`FRONTEND_URL` determines the destination of password reset links. Set `SESSION_COOKIE_SECURE=true` when serving the application over HTTPS.

### 3. Initialize the database

**Current setup blocker:** [alembic/env.py](alembic/env.py) imports `Base` from `backend.src.database`, but it is defined in `backend.src.models`. Before running migrations, change that import to:

```python
from backend.src.models import Base
```

Then apply the schema:

```bash
alembic upgrade head
```

### 4. Start the app

```bash
uvicorn backend.src.main:app --reload
```

Open [localhost:8000](http://localhost:8000). Interactive API documentation is available at [/docs](http://localhost:8000/docs); CSV preview and import endpoints are excluded from that documentation.

Use a single server worker: guest dictionaries, account trie caches, and their locks are local to each process. Multiple workers do not share or synchronize this state. Development reloads also reset guest dictionaries.

## Development

Install the additional dependency used by FastAPI's test client:

```bash
python -m pip install httpx
```

| Command | Purpose |
| --- | --- |
| `make` | Build the C shared library |
| `make test-c` | Build and run the C trie tests |
| `make test-python` | Build the library and run the Python suite |
| `make test` | Run both suites |
| `make clean` | Remove the compiled library and C test binary |
| `make clean && make DEBUG=1` | Rebuild the library with debug symbols and logging |

Python integration tests require PostgreSQL and a role with permission to create and drop schemas. Each integration test creates an isolated schema and removes it afterward. Set `TEST_DATABASE_URL` to select a separate test database; otherwise the suite uses `DATABASE_URL`.

```bash
export TEST_DATABASE_URL='postgresql+psycopg://effortlist:your-password@localhost:5432/effortlist_test'
make test
```

The application configuration still requires `DATABASE_URL` when `TEST_DATABASE_URL` is set.

### Project structure

```text
backend/
  include/trie.h       C trie interface
  src/
    main.py            App entry point and dictionary routes
    routers/users.py   Registration, login, logout, and password recovery
    trie.c             Trie implementation
    init.py            ctypes bindings and shared library loading
    parser.py          C header parser for binding signatures
    trie_state.py      Per-identity roots, locks, and database loading
    models.py          SQLAlchemy user and dictionary models
    crud.py            Database helpers and CSV parsing
    auth.py            Password hashing and reset tokens
    config.py          Environment settings
    database.py        Async database engine and sessions
    email_utils.py     SMTP delivery and reset email content
  tests/
    c/                 Native trie tests
    python/            Unit and API integration tests
frontend/
  js/core/             API client and shared UI helpers
  js/features/         Search, imports, dictionary actions, and accounts
  js/pages/            Page entry points
  *.html               App and account pages
  style.css            Shared styles
alembic/               Database migration configuration and revisions
Makefile               Native build and test commands
pyproject.toml         Python package and dependencies
```

## Current limitations

- Searches return at most **1,000 entries**. Guest registration uses the same enumeration function, so entries beyond that limit are not transferred and are lost when the guest trie is discarded.
- The API declares a 100-character limit for individual entries and prefixes, but the C search buffer cannot safely handle that boundary. CSV imports also bypass the per-entry query validation. Long entries can cause memory corruption.
- Deleting an entry that is a prefix of another, such as `Car` when `Cart` exists, leaves a freed pointer in the trie. Subsequent cleanup, including logout or clearing the dictionary, can trigger a double free and crash the server.

