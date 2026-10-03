import re

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from config import Config
from models import Lead, db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    db.init_app(app)

    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:  # DB unreachable: the site still loads
            app.logger.warning("Could not create tables: %s", exc)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/contact", methods=["POST"])
    def contact():
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not EMAIL_RE.match(email):
            flash("Please enter your name and a valid email.", "error")
            return redirect(url_for("index") + "#contact")

        try:
            db.session.add(Lead(name=name, email=email, message=message))
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            app.logger.error("Saving lead failed: %s", exc)
            flash("Something went wrong. Please try again later.", "error")
            return redirect(url_for("index") + "#contact")

        flash("Thanks! We'll be in touch soon.", "success")
        return redirect(url_for("index") + "#contact")

    @app.route("/health")
    def health():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify(status="ok", database="up")
        except Exception:
            return jsonify(status="degraded", database="down"), 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
