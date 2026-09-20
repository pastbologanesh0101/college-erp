# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - Initial release

The first commit (`c829bb9`, "Initial commit: College ERP Clone")
established the whole app in 28 files / ~1,773 lines:

### Added

- **App factory** (`app/__init__.py`) — `create_app()` sets up config,
  registers blueprints, auto-initializes the SQLite schema on first run,
  and seeds a default admin account (`admin` / `admin123`, overridable via
  `ADMIN_USERNAME` / `ADMIN_PASSWORD`).
- **Database layer** (`app/db.py`, `app/schema.sql`) — request-scoped
  SQLite connection handling, a `flask init-db` CLI command, and the
  `student` / `course` / `enrollment` / `grade` / `attendance` /
  `admin_user` tables with their `UNIQUE` constraints.
- **Domain logic** (`app/models.py`) — student/course creation, enrollment
  with duplicate-(student, course, semester) rejection, marks-to-letter-
  grade conversion on a 10-point scale, credit-weighted GPA/CGPA
  computation, per-student transcript aggregation, attendance recording
  with percentage/low-attendance-flag calculation, and admin-user lookup.
- **Public views** (`app/routes.py`) — home page listing students/courses,
  a per-student detail page (transcript + attendance summary), and a
  dedicated transcript page.
- **Admin views** (`app/admin.py`, `app/auth.py`) — session-based admin
  login/logout (no RBAC, single admin role) gating a dashboard and forms
  to add students/courses, enroll students, record attendance, and record
  grades.
- **Templates & styling** (`app/templates/`, `app/static/style.css`) —
  Jinja2 templates for every view above plus plain CSS.
- **Tests** (`tests/test_app.py`, `tests/conftest.py`) — 16 tests covering
  enrollment, attendance percentage/flagging, grading and GPA computation
  (checked against hand-calculated values), transcript aggregation, admin-
  login gating, and invalid-grade rejection, run against a temporary
  per-test SQLite database via `create_app(testing=True)`.
- **CI** (`.github/workflows/tests.yml`) — runs the test suite on every
  push/PR against Python 3.11 and 3.12.
- **Docs & licensing** — `README.md` and the MIT `LICENSE`.

[0.1.0]: https://github.com/pastbologanesh0101/college-erp/commit/c829bb9
