# Contributing to College ERP Clone

Thanks for taking a look at this project. It's a small, scoped-down Flask +
SQLite app, so the workflow below is deliberately lightweight.

## Setting up

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
```

## Running the app locally

```bash
python run.py
```

This starts the dev server at `http://127.0.0.1:5000/` and creates
`instance/college_erp.sqlite` on first run, seeded with the default admin
account (`admin` / `admin123`, overridable via `ADMIN_USERNAME` /
`ADMIN_PASSWORD`). Delete `instance/college_erp.sqlite` (or run
`flask --app run init-db`) if you change `app/schema.sql` and need the
tables recreated.

## Running the tests

```bash
pytest -v
```

Configuration lives in `pytest.ini` (`testpaths = tests`, `pythonpath = .`),
so `pytest` from the repo root picks up `tests/test_app.py` automatically.
Tests build a fresh `create_app(testing=True)` app per test (see
`tests/conftest.py`), which points at a temporary SQLite file instead of
`instance/college_erp.sqlite` — the real database is never touched by the
test suite.

**Run the full suite before opening a PR, and make sure it's green.** If you
add a route, a model function, or a validation rule, add a test for it in
`tests/test_app.py` (unit-level for `app/models.py` functions using the `db`
fixture, HTTP-level via the `client` fixture for routes).

## Code style

- Match the existing style: small, single-purpose functions in
  `app/models.py` doing the actual data access/domain logic; routes in
  `app/routes.py` / `app/admin.py` stay thin and delegate to `models.py`.
- Raise `app.models.ValidationError` for domain-rule violations (duplicate
  enrollment, out-of-range marks, missing student/course, etc.) instead of
  letting a raw `sqlite3` or `ValueError` exception surface to the user —
  routes already know how to catch and flash `ValidationError` messages.
- Keep SQL as parameterized queries (`?` placeholders); never interpolate
  user input into a query string.
- Docstrings on public functions in `app/models.py` are expected, matching
  the existing one-line-summary style.
- No particular formatter is enforced, but keep lines under ~88 columns and
  follow the naming/import conventions already used in the module you're
  editing.

## Submitting changes

1. Fork/branch, make a focused change (one logical change per commit where
   possible).
2. Run `pytest -v` and confirm everything passes.
3. Open a pull request describing what changed and why. Mention any new
   environment variables, schema changes, or manual migration steps a
   reviewer would need to know about.
