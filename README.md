# ReqRes QA Automation

[![CI](https://github.com/YOUR_USERNAME/reqres-qa-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/reqres-qa-automation/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Playwright](https://img.shields.io/badge/playwright-1.44%2B-green)
![Tests](https://img.shields.io/badge/tests-208-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A professional QA automation suite for the [ReqRes](https://reqres.in) REST API,
built with **Playwright**, **Pytest**, and **Python 3.12**.

Covers full CRUD operations, schema validation, response-time SLAs,
negative cases, and error mocking — structured as a 7-day learning project.

---

## Stack

| Tool           | Role                            |
| -------------- | ------------------------------- |
| Python 3.12+   | Language                        |
| Playwright     | HTTP client + route() mocking   |
| Pytest 8       | Test runner + parametrize       |
| Pydantic v2    | Response schema validation      |
| python-dotenv  | Environment variable management |
| pytest-html    | HTML test reports               |
| allure-pytest  | Allure report integration       |
| pytest-xdist   | Parallel test execution         |
| GitHub Actions | CI/CD pipeline                  |

---

## Project structure

```
reqres-qa-automation/
├── .env.example                 # Template — copy to .env and fill in values
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI pipeline
├── Makefile                     # Developer shortcuts
├── pyproject.toml               # Dependencies + pytest configuration
│
├── config/
│   └── settings.py              # Typed settings loaded from .env
│
├── clients/
│   └── api_client.py            # HTTP client wrapping Playwright + timing
│
├── models/
│   ├── user.py                  # Pydantic schemas for user endpoints
│   └── auth.py                  # Pydantic schemas for auth endpoints
│
├── utils/
│   └── assertions.py            # Reusable assertion helpers
│
└── tests/
    ├── conftest.py              # Global fixtures (Playwright session)
    ├── test_smoke.py            # Day 1 — Setup validation (5 tests)
    ├── test_get_users.py        # Day 2 — GET /users (39 tests)
    ├── test_post_users.py       # Day 3 — POST /users /login /register (39 tests)
    ├── test_put_patch_users.py  # Day 4 — PUT + PATCH /users (45 tests)
    ├── test_delete_users.py     # Day 5 — DELETE /users (34 tests)
    ├── test_negative.py         # Day 6 — Negative + edge cases (31 tests)
    └── test_mock_errors.py      # Day 6 — Error mocking (14 tests)
```

---

## Quick start

### 1. Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/reqres-qa-automation.git
cd reqres-qa-automation

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# .env is already pre-filled with working ReqRes defaults.
# No changes needed to run the suite against the public API.
```

### 3. Run the tests

```bash
# Full suite (208 tests)
pytest tests/

# Quick smoke check
make smoke

# Specific day
make test-get
make test-post
make test-crud

# Offline-only (no internet required)
make test-mock
```

### 4. View the report

After any `pytest` run, open `reports/report.html` in your browser:

```bash
make report    # opens automatically
# or open manually: open reports/report.html
```

---

## Makefile targets

```
make setup           Full setup from scratch (install + browsers)
make smoke           Smoke tests only (fast)
make test            Full test suite
make test-get        GET /users tests
make test-post       POST /users, /login, /register
make test-put        PUT and PATCH /users
make test-delete     DELETE /users
make test-crud       Full CRUD (GET + POST + PUT + DELETE)
make test-negative   Negative and edge case tests
make test-mock       Mock/mocking tests (no internet)
make test-parallel   Full suite with 4 parallel workers
make report          Open HTML report in browser
make allure-serve    Generate and serve Allure report
make clean           Remove generated files
make lint            Check syntax across all Python files
```

---

## Test coverage overview

| Day       | File                      | Tests   | What it covers                                     |
| --------- | ------------------------- | ------- | -------------------------------------------------- |
| 1         | `test_smoke.py`           | 5       | Project setup, connectivity, settings              |
| 2         | `test_get_users.py`       | 39      | GET list, GET single, pagination, 404              |
| 3         | `test_post_users.py`      | 39      | Create user, login, register, auth errors          |
| 4         | `test_put_patch_users.py` | 45      | Full replace, partial update, PUT vs PATCH         |
| 5         | `test_delete_users.py`    | 34      | Delete, empty body, idempotency, POST→DELETE chain |
| 6         | `test_negative.py`        | 31      | 404s, bad ids, invalid creds, edge cases           |
| 6         | `test_mock_errors.py`     | 14      | 5xx, 4xx, malformed JSON, route mocking            |
| **Total** |                           | **207** |                                                    |

Every test validates at least one of:

- **Status code** — exact HTTP response code
- **Response schema** — Pydantic v2 model validation
- **Response time** — within `MAX_RESPONSE_TIME_MS` SLA
- **Body content** — specific field values and structure

---

## Environment variables

| Variable               | Default              | Description                                |
| ---------------------- | -------------------- | ------------------------------------------ |
| `BASE_URL`             | `https://reqres.in`  | API base URL                               |
| `API_PREFIX`           | `/api`               | URL prefix for all endpoints               |
| `REQUEST_TIMEOUT_MS`   | `10000`              | Per-request timeout in milliseconds        |
| `MAX_RESPONSE_TIME_MS` | `3000`               | SLA threshold for response time assertions |
| `TEST_EMAIL`           | `eve.holt@reqres.in` | Email used in auth endpoint tests          |
| `TEST_PASSWORD`        | `cityslicka`         | Password used in auth endpoint tests       |
| `ALLURE_RESULTS_DIR`   | `allure-results`     | Directory for Allure report data           |

---

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every
push to `main` or `develop` and on all pull requests.

**Pipeline steps:**

1. Checkout + Python setup
2. Install dependencies (`pip install -e ".[dev]"`)
3. Cache and install Playwright Chromium
4. Generate `.env` from GitHub Secrets / repository variables
5. Run smoke tests (fast gate — fails early if API unreachable)
6. Run mock tests (offline — always passes)
7. Run full suite
8. Upload HTML report as workflow artifact (14-day retention)
9. Upload Allure results as workflow artifact

**Setting up secrets in GitHub:**

Go to `Settings → Secrets and variables → Actions` and add:

| Secret          | Value                |
| --------------- | -------------------- |
| `TEST_EMAIL`    | `eve.holt@reqres.in` |
| `TEST_PASSWORD` | `cityslicka`         |

The `BASE_URL` can be set as a repository **variable** (not secret)
under `Settings → Secrets and variables → Actions → Variables`.

---

## Design principles

**No hardcoding** — all configuration lives in `.env`. No credentials,
URLs, or thresholds inside test files.

**No arbitrary waits** — `time.sleep()` is never used. Playwright's
`REQUEST_TIMEOUT_MS` handles connection-level timeouts.

**Clean, readable code** — each file has a module docstring explaining
its purpose, a coverage matrix, and design decisions. Test names are
sentences that describe the expected behaviour.

**Schema-first validation** — every response that should have a body is
validated against a Pydantic v2 model. If the API changes its response
shape, the relevant test fails immediately at the schema assertion.

**Helpers over repetition** — `utils/assertions.py` provides `assert_status`,
`assert_schema`, `assert_response_time`, and others. Test bodies stay
focused on intent, not mechanics.

**Documented surprises** — non-obvious API behaviours (ReqRes returning
204 for non-existent ids, 200 with empty `data` for out-of-range pages)
are explicitly documented in the test docstrings.

---

## Running in parallel

```bash
# 4 workers — good for local machines with 4+ cores
pytest tests/ -n 4

# Auto-detect CPU count
pytest tests/ -n auto
```

> **Note:** mock tests and smoke tests are safe to run in parallel.
> If you add stateful tests in the future, mark them with `@pytest.mark.xdist_group`
> to keep them on the same worker.

---

## License

MIT — see [LICENSE](LICENSE) for details.
