import os
import uuid
from datetime import datetime
from functools import wraps

import click
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

import s3_utils
from config import Config
from models import Document, Student, User, db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


admin_required = role_required("admin")
student_required = role_required("student")


@app.template_filter("filesize")
def filesize(n):
    n = n or 0
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


@app.errorhandler(403)
@app.errorhandler(404)
def http_error(error):
    return render_template("error.html", error=error), error.code


@app.errorhandler(413)
def too_large(error):
    flash("That file is larger than 10 MB. Choose a smaller file.", "error")
    return redirect(url_for("index"))


# ---------------------------------------------------------------- auth

@app.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    return redirect(url_for("admin_dashboard" if current_user.is_admin else "student_dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            return redirect(url_for("index"))
        flash("Wrong username or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- admin

@app.route("/admin")
@admin_required
def admin_dashboard():
    q = request.args.get("q", "").strip()
    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Student.full_name.like(like),
                Student.roll_no.like(like),
                Student.email.like(like),
                Student.course.like(like),
            )
        )
    students = query.order_by(Student.created_at.desc()).all()
    return render_template("admin_dashboard.html", students=students, q=q)


FORM_FIELDS = ("roll_no", "full_name", "email", "phone", "course", "date_of_birth", "address")


def read_student_form():
    return {k: request.form.get(k, "").strip() for k in FORM_FIELDS}


def save_new_student(form, password):
    """Validate the form, then create the student and their login.

    Returns (student, None) on success or (None, error_message) on failure.
    Used by both the admin "Add student" page and public registration.
    """
    if not all(form[k] for k in ("roll_no", "full_name", "email", "course")):
        return None, "Roll number, name, email and course are required."
    if len(password) < 6:
        return None, "The password needs at least 6 characters."

    dob = None
    if form["date_of_birth"]:
        try:
            dob = datetime.strptime(form["date_of_birth"], "%Y-%m-%d").date()
        except ValueError:
            return None, "Enter the date of birth as a valid date."

    exists = (
        User.query.filter_by(username=form["roll_no"]).first()
        or Student.query.filter_by(email=form["email"]).first()
    )
    if exists:
        return None, "A student with this roll number or email already exists."

    user = User(username=form["roll_no"], role="student")
    user.set_password(password)
    student = Student(
        user=user,
        roll_no=form["roll_no"],
        full_name=form["full_name"],
        email=form["email"],
        phone=form["phone"] or None,
        course=form["course"],
        date_of_birth=dob,
        address=form["address"] or None,
    )
    db.session.add(student)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, "A student with this roll number or email already exists."
    return student, None


@app.route("/admin/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    form = {}
    if request.method == "POST":
        form = read_student_form()
        student, error = save_new_student(form, request.form.get("password", ""))
        if error:
            flash(error, "error")
        else:
            flash(f"{student.full_name} added. They log in with roll number {student.roll_no}.", "ok")
            return redirect(url_for("student_detail", student_id=student.id))
    return render_template("student_form.html", form=form, mode="admin")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Public sign-up: a student creates their own account."""
    if not app.config["ALLOW_SELF_REGISTRATION"]:
        abort(404)
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = {}
    if request.method == "POST":
        form = read_student_form()
        password = request.form.get("password", "")
        if password != request.form.get("confirm_password", ""):
            flash("The two passwords do not match.", "error")
        else:
            student, error = save_new_student(form, password)
            if error:
                flash(error, "error")
            else:
                login_user(student.user)
                flash(f"Welcome, {student.full_name}. Your account is ready.", "ok")
                return redirect(url_for("student_dashboard"))
    return render_template("student_form.html", form=form, mode="register")


@app.route("/admin/students/<int:student_id>")
@admin_required
def student_detail(student_id):
    student = db.get_or_404(Student, student_id)
    return render_template("student_detail.html", student=student)


# ---------------------------------------------------------------- student

@app.route("/student")
@student_required
def student_dashboard():
    return render_template("student_dashboard.html", student=current_user.student)


@app.route("/student/upload", methods=["POST"])
@student_required
def upload_document():
    student = current_user.student
    file = request.files.get("file")
    title = request.form.get("title", "").strip()
    allowed = app.config["ALLOWED_EXTENSIONS"]

    if not file or not file.filename:
        flash("Choose a file to upload.", "error")
        return redirect(url_for("student_dashboard"))

    stem, _, ext = file.filename.rpartition(".")
    ext = ext.lower()
    if not stem or ext not in allowed:
        flash(f"Upload one of these file types: {', '.join(sorted(allowed))}.", "error")
        return redirect(url_for("student_dashboard"))

    filename = f"{secure_filename(stem) or 'document'}.{ext}"
    key = f"students/{student.id}/{uuid.uuid4().hex}_{filename}"

    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)

    try:
        s3_utils.upload_fileobj(file.stream, key, file.mimetype)
    except (BotoCoreError, ClientError) as exc:
        app.logger.exception("S3 upload failed: %s", exc)
        flash("The upload to storage failed. Try again in a moment.", "error")
        return redirect(url_for("student_dashboard"))

    document = Document(
        student_id=student.id,
        title=title or stem[:150],
        original_filename=filename,
        s3_key=key,
        content_type=file.mimetype,
        file_size=size,
    )
    db.session.add(document)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:  # don't leave an orphan file in the bucket
            s3_utils.delete_object(key)
        except (BotoCoreError, ClientError):
            pass
        app.logger.exception("Saving document row failed")
        flash("The file uploaded but could not be saved. Try again.", "error")
        return redirect(url_for("student_dashboard"))

    flash(f"Uploaded {filename}.", "ok")
    return redirect(url_for("student_dashboard"))


@app.route("/documents/<int:doc_id>/view")
@login_required
def view_document(doc_id):
    document = db.get_or_404(Document, doc_id)
    owns = current_user.student is not None and document.student_id == current_user.student.id
    if not (current_user.is_admin or owns):
        abort(403)
    try:
        url = s3_utils.presigned_url(
            document.s3_key, document.original_filename, document.content_type
        )
    except (BotoCoreError, ClientError):
        app.logger.exception("Could not sign S3 URL")
        flash("Could not open that document right now.", "error")
        return redirect(url_for("index"))
    return redirect(url)


# ---------------------------------------------------------------- CLI

@app.cli.command("init-db")
def init_db():
    """Create all tables (the database itself must already exist)."""
    db.create_all()
    click.echo("Tables created.")


@app.cli.command("create-admin")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(username, password):
    """Create an admin login."""
    if User.query.filter_by(username=username).first():
        click.echo("That username already exists.")
        return
    user = User(username=username, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin '{username}' created.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
