import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def build_database_uri():
    """DATABASE_URL > MySQL from DB_* vars > local SQLite fallback."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    host = os.getenv("DB_HOST")
    if host and not host.startswith("your-"):
        user = quote_plus(os.getenv("DB_USER", ""))
        password = quote_plus(os.getenv("DB_PASSWORD", ""))
        port = os.getenv("DB_PORT", "3306")
        name = os.getenv("DB_NAME", "landingpage")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

    return "sqlite:///" + os.path.join(BASE_DIR, "instance", "app.db")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
