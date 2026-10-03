# Flower Project

A small Flask landing page with a contact form that stores leads in MySQL (AWS RDS) or SQLite.

## Structure

```
flower_project/
├── app.py            # Flask app, routes (/, /contact, /health)
├── config.py         # Loads .env and builds the database URL
├── models.py         # SQLAlchemy models (Lead)
├── check.py          # Config + database connection check
├── database.sql      # MySQL schema
├── flower_project/    # package folder for extra modules
├── templates/        # base.html, index.html
├── instance/         # Local SQLite file goes here
├── requirements.txt
└── .env              # Secrets (not committed)
```

## Run locally (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python check.py
python app.py
```

Open http://127.0.0.1:5000. With no DB settings in `.env`, the app uses SQLite automatically.

## Use AWS RDS (MySQL)

1. Put `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `.env`.
2. Allow inbound port 3306 from your EC2/security group in the RDS security group.
3. Run `python check.py`. Tables are created automatically, or import `database.sql`.

## Deploy on EC2

```bash
pip install -r requirements.txt
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```
