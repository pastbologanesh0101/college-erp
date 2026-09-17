"""Simple session-based admin authentication (no RBAC, single admin role)."""
import functools

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from app.db import get_db
from app.models import get_admin_user_by_username

bp = Blueprint("auth", __name__, url_prefix="/admin")


@bp.before_app_request
def load_logged_in_admin():
    username = session.get("admin_username")
    g.admin = username


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.get("admin") is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)

    return wrapped_view


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        db = get_db()
        error = None
        admin_user = get_admin_user_by_username(db, username)

        if admin_user is None or not check_password_hash(
            admin_user["password_hash"], password
        ):
            error = "Invalid username or password."

        if error is None:
            session.clear()
            session["admin_username"] = admin_user["username"]
            next_url = request.args.get("next") or url_for("admin.dashboard")
            return redirect(next_url)

        flash(error)

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
