import pytest

from app import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_admin(client):
    """Log in with the default seeded admin account."""
    return client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def _make_student(db, roll_number="R001"):
    return models.create_student(db, "Asha Rao", roll_number, "CSE", 2)


def _make_course(db, code="CS101", credits=4):
    return models.create_course(db, code, "Intro to Programming", credits, "CSE")


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

def test_enroll_student_in_course(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    enrollment_id = models.enroll_student(db, student_id, course_id, "2026-Fall")

    enrollments = models.list_enrollments_for_student(db, student_id)
    assert len(enrollments) == 1
    assert enrollments[0]["enrollment_id"] == enrollment_id
    assert enrollments[0]["course_code"] == "CS101"


def test_duplicate_enrollment_rejected(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    models.enroll_student(db, student_id, course_id, "2026-Fall")

    with pytest.raises(models.ValidationError):
        models.enroll_student(db, student_id, course_id, "2026-Fall")

    # still only one enrollment on record
    assert len(models.list_enrollments_for_student(db, student_id)) == 1


def test_enroll_student_rejects_nonexistent_student_or_course(db):
    course_id = _make_course(db)
    student_id = _make_student(db)

    with pytest.raises(models.ValidationError):
        models.enroll_student(db, student_id=999999, course_id=course_id, semester="2026-Fall")

    with pytest.raises(models.ValidationError):
        models.enroll_student(db, student_id=student_id, course_id=999999, semester="2026-Fall")

    # neither bad call should have created an enrollment row
    assert models.list_enrollments_for_student(db, student_id) == []


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def test_record_attendance_and_percentage(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    models.record_attendance(db, student_id, course_id, "2026-01-01", True)
    models.record_attendance(db, student_id, course_id, "2026-01-02", True)
    models.record_attendance(db, student_id, course_id, "2026-01-03", True)
    models.record_attendance(db, student_id, course_id, "2026-01-04", False)

    pct = models.compute_attendance_percentage(db, student_id, course_id)
    assert pct == 75.0


def test_low_attendance_flagged_below_threshold(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    models.record_attendance(db, student_id, course_id, "2026-01-01", True)
    models.record_attendance(db, student_id, course_id, "2026-01-02", False)
    models.record_attendance(db, student_id, course_id, "2026-01-03", False)
    models.record_attendance(db, student_id, course_id, "2026-01-04", False)

    pct = models.compute_attendance_percentage(db, student_id, course_id)
    assert pct == 25.0
    assert models.is_attendance_low(pct, threshold=75.0) is True

    summary = models.attendance_summary_for_student(db, student_id, threshold=75.0)
    assert summary[0]["low"] is True
    assert summary[0]["percentage"] == 25.0


def test_attendance_percentage_none_without_records(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    pct = models.compute_attendance_percentage(db, student_id, course_id)
    assert pct is None
    # is_attendance_low must treat "no data" as "not low", not a false positive
    assert models.is_attendance_low(pct) is False


def test_attendance_at_or_above_threshold_not_flagged(db):
    student_id = _make_student(db)
    course_id = _make_course(db)

    for day in range(1, 5):
        models.record_attendance(db, student_id, course_id, f"2026-01-0{day}", True)

    pct = models.compute_attendance_percentage(db, student_id, course_id)
    assert pct == 100.0
    assert models.is_attendance_low(pct, threshold=75.0) is False


# ---------------------------------------------------------------------------
# Grades / GPA
# ---------------------------------------------------------------------------

def test_record_grade_sets_letter_and_points(db):
    student_id = _make_student(db)
    course_id = _make_course(db, code="CS101", credits=4)
    enrollment_id = models.enroll_student(db, student_id, course_id, "2026-Fall")

    letter, points = models.record_grade(db, enrollment_id, 85)

    assert letter == "A+"
    assert points == 9.0


def test_gpa_weighted_by_credits_matches_hand_calculation(db):
    student_id = _make_student(db)

    course_a = _make_course(db, code="CS101", credits=4)  # 85 -> A+ -> 9.0
    course_b = _make_course(db, code="CS102", credits=3)  # 72 -> A  -> 8.0
    course_c = _make_course(db, code="CS103", credits=2)  # 55 -> B  -> 6.0

    enroll_a = models.enroll_student(db, student_id, course_a, "2026-Fall")
    enroll_b = models.enroll_student(db, student_id, course_b, "2026-Fall")
    enroll_c = models.enroll_student(db, student_id, course_c, "2026-Fall")

    models.record_grade(db, enroll_a, 85)
    models.record_grade(db, enroll_b, 72)
    models.record_grade(db, enroll_c, 55)

    # Hand calculation: (4*9.0 + 3*8.0 + 2*6.0) / (4+3+2) = 72 / 9 = 8.0
    expected_gpa = (4 * 9.0 + 3 * 8.0 + 2 * 6.0) / (4 + 3 + 2)
    assert expected_gpa == 8.0
    assert models.compute_gpa(db, student_id) == 8.0


def test_gpa_ignores_ungraded_enrollments(db):
    student_id = _make_student(db)
    course_a = _make_course(db, code="CS101", credits=4)
    course_b = _make_course(db, code="CS102", credits=5)

    enroll_a = models.enroll_student(db, student_id, course_a, "2026-Fall")
    models.enroll_student(db, student_id, course_b, "2026-Fall")  # ungraded

    models.record_grade(db, enroll_a, 90)  # O -> 10.0

    # Only the graded course counts toward GPA.
    assert models.compute_gpa(db, student_id) == 10.0


def test_invalid_grade_marks_rejected(db):
    student_id = _make_student(db)
    course_id = _make_course(db)
    enrollment_id = models.enroll_student(db, student_id, course_id, "2026-Fall")

    with pytest.raises(models.ValidationError):
        models.record_grade(db, enrollment_id, 150)

    with pytest.raises(models.ValidationError):
        models.record_grade(db, enrollment_id, -5)

    with pytest.raises(models.ValidationError):
        models.record_grade(db, enrollment_id, "not-a-number")


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------

def test_transcript_aggregates_all_courses_correctly(db):
    student_id = _make_student(db)
    course_a = _make_course(db, code="CS101", credits=4)
    course_b = _make_course(db, code="CS102", credits=3)

    enroll_a = models.enroll_student(db, student_id, course_a, "2026-Fall")
    enroll_b = models.enroll_student(db, student_id, course_b, "2026-Spring")

    models.record_grade(db, enroll_a, 85)
    models.record_grade(db, enroll_b, 60)

    transcript = models.get_transcript(db, student_id)

    codes = {row["course_code"] for row in transcript["rows"]}
    assert codes == {"CS101", "CS102"}
    assert len(transcript["rows"]) == 2

    expected_gpa = round((4 * 9.0 + 3 * 7.0) / 7, 2)
    assert transcript["gpa"] == expected_gpa


# ---------------------------------------------------------------------------
# HTTP layer: views, admin auth
# ---------------------------------------------------------------------------

def test_index_page_lists_students(client, db):
    _make_student(db, roll_number="R042")

    response = client.get("/")
    assert response.status_code == 200
    assert b"R042" in response.data


def test_admin_dashboard_requires_login(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_admin_login_grants_access_to_dashboard(client):
    login_admin(client)
    response = client.get("/admin/")
    assert response.status_code == 200
    assert b"Admin dashboard" in response.data


def test_admin_login_rejects_bad_credentials(client):
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_transcript_view_via_http(client, db):
    student_id = _make_student(db, roll_number="R777")
    course_id = _make_course(db, code="CS201", credits=3)
    enrollment_id = models.enroll_student(db, student_id, course_id, "2026-Fall")
    models.record_grade(db, enrollment_id, 95)

    response = client.get(f"/students/{student_id}/transcript")
    assert response.status_code == 200
    assert b"CS201" in response.data
    assert b"10.0" in response.data  # grade point for 95 marks


def test_invalid_grade_marks_rejected_via_admin_route(client, db):
    student_id = _make_student(db, roll_number="R999")
    course_id = _make_course(db, code="CS301", credits=3)
    enrollment_id = models.enroll_student(db, student_id, course_id, "2026-Fall")

    login_admin(client)
    response = client.post(
        "/admin/grades",
        data={"enrollment_id": str(enrollment_id), "marks": "150"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Could not record grade" in response.data

    # No grade should have been persisted.
    transcript = models.get_transcript(db, student_id)
    assert transcript["rows"][0]["letter_grade"] is None
