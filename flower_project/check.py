"""Quick sanity check: python check.py
Verifies config values and that the database is reachable."""
from sqlalchemy import create_engine, text

from config import Config


def main():
    uri = Config.SQLALCHEMY_DATABASE_URI
    safe_uri = uri.split("@")[-1] if "@" in uri else uri
    print(f"Database target: {safe_uri}")

    if Config.SECRET_KEY.startswith(("dev-", "change-me")):
        print("WARNING: SECRET_KEY is still a placeholder.")

    try:
        engine = create_engine(uri, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("OK: connected to the database.")
            try:
                count = conn.execute(text("SELECT COUNT(*) FROM leads")).scalar()
                print(f"OK: 'leads' table found with {count} row(s).")
            except Exception:
                print("NOTE: 'leads' table not found yet. Run the app once or import database.sql.")
    except Exception as exc:
        print(f"FAILED: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
