# College ERP Clone

A scoped-down academic-records core of a College ERP (Enterprise Resource
Planning) system, built with **Flask** and **SQLite**. It covers the
essentials of enrollment, attendance, and grading that a real college ERP's
academic module would handle, without the surrounding bureaucracy (fees,
hostel, library, etc.).

## Modules covered

- **Students** — roll number, name, department, year.
- **Courses** — code, title, credit weight, department.
- **Enrollment** — enroll a student into a course for a given semester;
  duplicate enrollments (same student + course + semester) are rejected.
- **Attendance** — record per-session attendance (present/absent) for a
  student in a course; computes attendance percentage per course and flags
  it when it falls below a configurable threshold (default **75%**).
- **Grades** — record/update marks (0–100) for an enrollment; marks are
  converted to a letter grade and grade point on a 10-point scale:

  | Marks   | Letter | Grade point |
  |---------|--------|-------------|
  | 90–100  | O      | 10.0        |
  | 80–89   | A+     | 9.0         |
  | 70–79   | A      | 8.0         |
  | 60–69   | B+     | 7.0         |
  | 50–59   | B      | 6.0         |
  | 40–49   | C      | 5.0         |
  | 0–39    | F      | 0.0         |

- **GPA / CGPA** — computed as the credit-weighted average of grade points
  across all of a student's graded enrollments:
  `GPA = sum(credits * grade_point) / sum(credits)`.
- **Transcript** — a per-student view listing every enrollment with its
  course, credits, marks, letter grade, and the overall CGPA.
- **Admin area** — a simple session-based login (`/admin/login`, no RBAC,
  a single admin role) gates the pages for adding students/courses,
  enrolling students, recording attendance, and recording grades.

## Project layout

```
app/
  __init__.py       app factory (create_app)
  db.py             SQLite connection handling
  models.py         domain logic: enrollment, attendance %, GPA, transcript
  auth.py           session-based admin login/logout
  routes.py         public views (home, student detail, transcript)
  admin.py          admin-only management views
  schema.sql        table definitions
  templates/        Jinja2 templates
  static/style.css  plain CSS
tests/
  test_app.py       unit tests (Flask test client + direct model calls)
.github/workflows/tests.yml   CI: runs the test suite on Python 3.11 & 3.12
```

## Running it locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app starts at `http://127.0.0.1:5000/` and creates an on-disk SQLite
database at `instance/college_erp.sqlite` on first run, seeded with a
default admin account:

- **username:** `admin`
- **password:** `admin123`

(Override with the `ADMIN_USERNAME` / `ADMIN_PASSWORD` environment
variables before the first run if you want different credentials.)

## Example usage

1. Go to `/admin/login` and log in with the default admin account.
2. Add a course at `/admin/courses/new` (e.g. `CS101`, "Intro to
   Programming", 4 credits, CSE).
3. Add a student at `/admin/students/new`.
4. Enroll the student in the course at `/admin/enroll`.
5. Record attendance sessions at `/admin/attendance`.
6. Record a grade (marks 0–100) at `/admin/grades`.
7. View the student's transcript and computed CGPA at
   `/students/<id>/transcript`, and their per-course attendance percentage
   (with low-attendance flag) at `/students/<id>`.

## Running the tests

```bash
pip install -r requirements.txt pytest
pytest -v
```

Tests use `create_app(testing=True)`, which points the app at a fresh
temporary SQLite database per test (auto-initialized and torn down), so
they never touch the real `instance/` database. Coverage includes:
enrollment (and duplicate-enrollment rejection), attendance percentage
calculation and low-attendance flagging, grade recording and GPA
computation (checked against hand-calculated expected values), transcript
aggregation across multiple courses, admin-login gating of the admin
views, and rejection of invalid grade input.

## CI

`.github/workflows/tests.yml` runs the full test suite on every push and
pull request against Python 3.11 and 3.12.

## License

MIT — see [LICENSE](LICENSE).
