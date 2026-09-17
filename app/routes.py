"""Public-facing views: home page, student detail, transcript."""
from flask import Blueprint, abort, render_template

from app.db import get_db
from app.models import (
    DEFAULT_ATTENDANCE_THRESHOLD,
    attendance_summary_for_student,
    get_student,
    get_transcript,
    list_courses,
    list_students,
)

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    db = get_db()
    students = list_students(db)
    courses = list_courses(db)
    return render_template("index.html", students=students, courses=courses)


@bp.route("/students/<int:student_id>")
def student_detail(student_id):
    db = get_db()
    student = get_student(db, student_id)
    if student is None:
        abort(404)

    transcript = get_transcript(db, student_id)
    attendance = attendance_summary_for_student(
        db, student_id, DEFAULT_ATTENDANCE_THRESHOLD
    )

    return render_template(
        "student/detail.html",
        student=student,
        transcript=transcript,
        attendance=attendance,
        threshold=DEFAULT_ATTENDANCE_THRESHOLD,
    )


@bp.route("/students/<int:student_id>/transcript")
def transcript(student_id):
    db = get_db()
    student = get_student(db, student_id)
    if student is None:
        abort(404)

    transcript_data = get_transcript(db, student_id)

    return render_template(
        "student/transcript.html", student=student, transcript=transcript_data
    )
