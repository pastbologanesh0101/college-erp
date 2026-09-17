"""App factory for the College ERP Clone."""
import os
import tempfile

from flask import Flask
from werkzeug.security import generate_password_hash


def create_app(test_config=None, testing=False):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "college_erp.sqlite"),
    )

    if testing:
        # A real (temp-file) SQLite database is used instead of ":memory:"
        # because ":memory:" databases are private to a single sqlite3
        # connection, and Flask opens a fresh connection per request
        # context -- which would make every request see an empty DB.
        temp_fd, temp_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(temp_fd)
        app.config.update(
            TESTING=True,
            DATABASE=temp_path,
        )

    if test_config is not None:
        app.config.update(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from app import db

    db.init_app(app)

    from app import auth

    app.register_blueprint(auth.bp)

    from app import admin

    app.register_blueprint(admin.bp)

    from app import routes

    app.register_blueprint(routes.bp)

    if app.config.get("TESTING") or not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            db.init_db()
            _seed_default_admin(app)

    return app


def _seed_default_admin(app):
    """Create a default admin/admin123 account if none exists yet."""
    from app.db import get_db
    from app.models import create_admin_user, get_admin_user_by_username

    conn = get_db()
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")
    if get_admin_user_by_username(conn, username) is None:
        create_admin_user(conn, username, generate_password_hash(password))
