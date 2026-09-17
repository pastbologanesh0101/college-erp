"""Admin-only views for managing students, courses, enrollment, attendance
and grades. Protected by the session-based login in app.auth.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_required
from app.db import get_db
from app.models import (
    ValidationError,
    create_course,
    create_student,
    enroll_student,
    list_courses,
    list_students,
    record_attendance,
    record_grade,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
def dashboard():
    db = get_db()
    return render_template(
        "admin/dashboard.html",
        students=list_students(db),
        courses=list_courses(db),
    )


@bp.route("/students/new", methods=("GET", "POST"))
@login_required
def new_student():
    if request.method == "POST":
        db = get_db()
        try:
            create_student(
                db,
                name=request.form["name"],
                roll_number=request.form["roll_number"],
                department=request.form["department"],
                year=int(request.form["year"]),
            )
            flash("Student added.")
            return redirect(url_for("admin.dashboard"))
        except Exception as exc:
            flash(f"Could not add student: {exc}")

    return render_template("admin/new_student.html")


@bp.route("/courses/new", methods=("GET", "POST"))
@login_required
def new_course():
    if request.method == "POST":
        db = get_db()
        try:
            create_course(
                db,
                code=request.form["code"],
                title=request.form["title"],
                credits=int(request.form["credits"]),
                department=request.form["department"],
            )
            flash("Course added.")
            return redirect(url_for("admin.dashboard"))
        except Exception as exc:
            flash(f"Could not add course: {exc}")

    return render_template("admin/new_course.html")


@bp.route("/enroll", methods=("GET", "POST"))
@login_required
def enroll():
    db = get_db()
    if request.method == "POST":
        try:
            enroll_student(
                db,
                student_id=int(request.form["student_id"]),
                course_id=int(request.form["course_id"]),
                semester=request.form["semester"],
            )
            flash("Student enrolled.")
            return redirect(url_for("admin.dashboard"))
        except ValidationError as exc:
            flash(str(exc))

    return render_template(
        "admin/enroll.html",
        students=list_students(db),
        courses=list_courses(db),
    )


@bp.route("/attendance", methods=("GET", "POST"))
@login_required
def attendance():
    db = get_db()
    if request.method == "POST":
        try:
            record_attendance(
                db,
                student_id=int(request.form["student_id"]),
                course_id=int(request.form["course_id"]),
                date=request.form["date"],
                present=request.form.get("present") == "on",
            )
            flash("Attendance recorded.")
            return redirect(url_for("admin.attendance"))
        except ValidationError as exc:
            flash(str(exc))

    return render_template(
        "admin/attendance.html",
        students=list_students(db),
        courses=list_courses(db),
    )


@bp.route("/grades", methods=("GET", "POST"))
@login_required
def grades():
    db = get_db()
    if request.method == "POST":
        try:
            record_grade(
                db,
                enrollment_id=int(request.form["enrollment_id"]),
                marks=float(request.form["marks"]),
            )
            flash("Grade recorded.")
            return redirect(url_for("admin.grades"))
        except (ValidationError, ValueError) as exc:
            flash(f"Could not record grade: {exc}")

    enrollments = db.execute(
        """
        SELECT enrollment.id AS enrollment_id, student.name AS student_name,
               course.code AS course_code, enrollment.semester AS semester
        FROM enrollment
        JOIN student ON student.id = enrollment.student_id
        JOIN course ON course.id = enrollment.course_id
        ORDER BY enrollment.id DESC
        """
    ).fetchall()

    return render_template("admin/grades.html", enrollments=enrollments)
