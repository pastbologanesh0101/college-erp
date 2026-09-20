"""Data-access helpers and domain calculations for the College ERP Clone.

Everything here operates on a plain sqlite3 connection (see app.db.get_db)
so it can be exercised directly from unit tests without going through the
HTTP layer.
"""

# Marks -> (letter grade, grade point on a 10-point scale).
GRADE_SCALE = (
    (90, "O", 10.0),
    (80, "A+", 9.0),
    (70, "A", 8.0),
    (60, "B+", 7.0),
    (50, "B", 6.0),
    (40, "C", 5.0),
    (0, "F", 0.0),
)

DEFAULT_ATTENDANCE_THRESHOLD = 75.0


class ValidationError(Exception):
    """Raised when caller-supplied data fails a domain rule."""


def marks_to_grade(marks):
    """Convert numeric marks (0-100) into (letter_grade, grade_point)."""
    if marks is None:
        raise ValidationError("Marks are required.")
    try:
        marks = float(marks)
    except (TypeError, ValueError):
        raise ValidationError("Marks must be a number.")
    if marks < 0 or marks > 100:
        raise ValidationError("Marks must be between 0 and 100.")

    for cutoff, letter, points in GRADE_SCALE:
        if marks >= cutoff:
            return letter, points
    return "F", 0.0  # pragma: no cover - unreachable, GRADE_SCALE ends at 0


# ---------------------------------------------------------------------------
# Students / Courses
# ---------------------------------------------------------------------------

def create_student(db, name, roll_number, department, year):
    """Create a student.

    Raises ValidationError if roll_number is already taken -- surfacing a
    clear message instead of letting the underlying UNIQUE constraint
    raise a raw sqlite3.IntegrityError.
    """
    if get_student_by_roll_number(db, roll_number) is not None:
        raise ValidationError(
            f"A student with roll number '{roll_number}' already exists."
        )

    cur = db.execute(
        "INSERT INTO student (name, roll_number, department, year) "
        "VALUES (?, ?, ?, ?)",
        (name, roll_number, department, year),
    )
    db.commit()
    return cur.lastrowid


def get_student(db, student_id):
    return db.execute(
        "SELECT * FROM student WHERE id = ?", (student_id,)
    ).fetchone()


def get_student_by_roll_number(db, roll_number):
    return db.execute(
        "SELECT * FROM student WHERE roll_number = ?", (roll_number,)
    ).fetchone()


def list_students(db):
    return db.execute("SELECT * FROM student ORDER BY name").fetchall()


def create_course(db, code, title, credits, department):
    cur = db.execute(
        "INSERT INTO course (code, title, credits, department) "
        "VALUES (?, ?, ?, ?)",
        (code, title, credits, department),
    )
    db.commit()
    return cur.lastrowid


def get_course(db, course_id):
    return db.execute(
        "SELECT * FROM course WHERE id = ?", (course_id,)
    ).fetchone()


def list_courses(db):
    return db.execute("SELECT * FROM course ORDER BY code").fetchall()


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

def enroll_student(db, student_id, course_id, semester):
    """Enroll a student in a course for a given semester.

    Raises ValidationError if the (student, course, semester) combination
    already exists, or if the student/course do not exist.
    """
    if get_student(db, student_id) is None:
        raise ValidationError("Student does not exist.")
    if get_course(db, course_id) is None:
        raise ValidationError("Course does not exist.")

    existing = db.execute(
        "SELECT id FROM enrollment "
        "WHERE student_id = ? AND course_id = ? AND semester = ?",
        (student_id, course_id, semester),
    ).fetchone()
    if existing is not None:
        raise ValidationError(
            "Student is already enrolled in this course for this semester."
        )

    cur = db.execute(
        "INSERT INTO enrollment (student_id, course_id, semester) "
        "VALUES (?, ?, ?)",
        (student_id, course_id, semester),
    )
    db.commit()
    return cur.lastrowid


def list_enrollments_for_student(db, student_id):
    return db.execute(
        """
        SELECT enrollment.id AS enrollment_id,
               enrollment.semester AS semester,
               course.id AS course_id,
               course.code AS course_code,
               course.title AS course_title,
               course.credits AS credits
        FROM enrollment
        JOIN course ON course.id = enrollment.course_id
        WHERE enrollment.student_id = ?
        ORDER BY enrollment.semester, course.code
        """,
        (student_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------------

def record_grade(db, enrollment_id, marks):
    """Record or update the grade for an enrollment based on numeric marks."""
    enrollment = db.execute(
        "SELECT id FROM enrollment WHERE id = ?", (enrollment_id,)
    ).fetchone()
    if enrollment is None:
        raise ValidationError("Enrollment does not exist.")

    letter_grade, grade_point = marks_to_grade(marks)

    existing = db.execute(
        "SELECT id FROM grade WHERE enrollment_id = ?", (enrollment_id,)
    ).fetchone()
    if existing is not None:
        db.execute(
            "UPDATE grade SET marks = ?, letter_grade = ?, grade_point = ? "
            "WHERE enrollment_id = ?",
            (marks, letter_grade, grade_point, enrollment_id),
        )
    else:
        db.execute(
            "INSERT INTO grade (enrollment_id, marks, letter_grade, grade_point) "
            "VALUES (?, ?, ?, ?)",
            (enrollment_id, marks, letter_grade, grade_point),
        )
    db.commit()
    return letter_grade, grade_point


def compute_gpa(db, student_id):
    """Weighted-by-credits GPA across every graded enrollment for a student.

    Returns 0.0 if the student has no graded enrollments.
    """
    rows = db.execute(
        """
        SELECT course.credits AS credits, grade.grade_point AS grade_point
        FROM enrollment
        JOIN course ON course.id = enrollment.course_id
        JOIN grade ON grade.enrollment_id = enrollment.id
        WHERE enrollment.student_id = ?
        """,
        (student_id,),
    ).fetchall()

    total_credits = sum(row["credits"] for row in rows)
    if total_credits == 0:
        return 0.0

    weighted_sum = sum(row["credits"] * row["grade_point"] for row in rows)
    return round(weighted_sum / total_credits, 2)


def get_transcript(db, student_id):
    """All enrollments (with grade, if any) plus the overall GPA."""
    rows = db.execute(
        """
        SELECT enrollment.id AS enrollment_id,
               enrollment.semester AS semester,
               course.code AS course_code,
               course.title AS course_title,
               course.credits AS credits,
               grade.marks AS marks,
               grade.letter_grade AS letter_grade,
               grade.grade_point AS grade_point
        FROM enrollment
        JOIN course ON course.id = enrollment.course_id
        LEFT JOIN grade ON grade.enrollment_id = enrollment.id
        WHERE enrollment.student_id = ?
        ORDER BY enrollment.semester, course.code
        """,
        (student_id,),
    ).fetchall()

    return {
        "rows": rows,
        "gpa": compute_gpa(db, student_id),
    }


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def record_attendance(db, student_id, course_id, date, present):
    """Record (or update) attendance for a student/course/date."""
    if get_student(db, student_id) is None:
        raise ValidationError("Student does not exist.")
    if get_course(db, course_id) is None:
        raise ValidationError("Course does not exist.")

    existing = db.execute(
        "SELECT id FROM attendance "
        "WHERE student_id = ? AND course_id = ? AND date = ?",
        (student_id, course_id, date),
    ).fetchone()

    present_int = 1 if present else 0

    if existing is not None:
        db.execute(
            "UPDATE attendance SET present = ? WHERE id = ?",
            (present_int, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO attendance (student_id, course_id, date, present) "
            "VALUES (?, ?, ?, ?)",
            (student_id, course_id, date, present_int),
        )
    db.commit()


def compute_attendance_percentage(db, student_id, course_id):
    """Percentage of sessions attended by a student in a course.

    Returns None if no attendance has been recorded for that pairing.
    """
    row = db.execute(
        """
        SELECT COUNT(*) AS total, COALESCE(SUM(present), 0) AS attended
        FROM attendance
        WHERE student_id = ? AND course_id = ?
        """,
        (student_id, course_id),
    ).fetchone()

    if row["total"] == 0:
        return None

    return round((row["attended"] / row["total"]) * 100, 2)


def is_attendance_low(percentage, threshold=DEFAULT_ATTENDANCE_THRESHOLD):
    """True if percentage is below threshold. None percentage -> False."""
    if percentage is None:
        return False
    return percentage < threshold


def attendance_summary_for_student(db, student_id, threshold=DEFAULT_ATTENDANCE_THRESHOLD):
    """Per-course attendance percentage + low-attendance flag for a student."""
    courses = db.execute(
        """
        SELECT DISTINCT course.id AS course_id, course.code AS course_code,
               course.title AS course_title
        FROM attendance
        JOIN course ON course.id = attendance.course_id
        WHERE attendance.student_id = ?
        ORDER BY course.code
        """,
        (student_id,),
    ).fetchall()

    summary = []
    for course in courses:
        pct = compute_attendance_percentage(db, student_id, course["course_id"])
        summary.append(
            {
                "course_id": course["course_id"],
                "course_code": course["course_code"],
                "course_title": course["course_title"],
                "percentage": pct,
                "low": is_attendance_low(pct, threshold),
            }
        )
    return summary


# ---------------------------------------------------------------------------
# Admin users
# ---------------------------------------------------------------------------

def create_admin_user(db, username, password_hash):
    db.execute(
        "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    db.commit()


def get_admin_user_by_username(db, username):
    return db.execute(
        "SELECT * FROM admin_user WHERE username = ?", (username,)
    ).fetchone()
