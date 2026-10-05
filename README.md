# Student Management System

Flask app with two roles.

- **Admin**: sees all students, searches them, adds new students (this also creates the student's login), and opens any student's documents.
- **Student**: logs in with their roll number, uploads documents, and views their own.

Files go to a **private S3 bucket**. Each upload's details (title, filename, S3 key, size, owner) are saved in **MySQL**. "View" hands out a 5-minute signed S3 link, so the bucket never needs to be public.

## Project layout

```
app.py            routes, login, upload/view logic, CLI commands
config.py         settings read from .env
models.py         User, Student, Document tables
s3_utils.py       S3 upload / delete / signed links
database.sql      optional: create the schema by hand
templates/ static/
```

## Run locally (Windows PowerShell)

```powershell
cd student_management_system
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then edit .env with your DB and S3 details
```

Create the database and tables, using one of these:

```powershell
mysql -h <host> -u <user> -p < database.sql            # creates database + tables
# or: create an empty database named student_management, then
flask --app app init-db
```

Create the admin login, then start the app:

```powershell
flask --app app create-admin
python app.py                    # http://localhost:5000
```

There are two ways to create a student:

- **Admin adds them**: log in as admin, choose **Add student**, and set a roll number and initial password.
- **Student signs up**: the login page links to **Create an account**, where a student enters their own details and password. They are logged in straight away.

Self-signup is on by default. Set `ALLOW_SELF_REGISTRATION=false` in `.env` to turn it off so only the admin can create students. Admin accounts are only created with `flask --app app create-admin`.

## S3 setup

1. Create a bucket and keep **Block all public access** on.
2. Put its name in `S3_BUCKET` and its region in `AWS_REGION`.
3. Give the app an IAM user (or an EC2 role) with this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
    "Resource": "arn:aws:s3:::YOUR-BUCKET/*"
  }]
}
```

Locally, put the IAM user's keys in `.env`. On EC2, attach the policy to an instance role and leave both key fields blank.

## AWS RDS (MySQL) and EC2

- Set `DB_HOST` to the RDS endpoint. In the RDS security group, allow port 3306 from the EC2 instance's security group.
- On the EC2 instance:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn
cp .env.example .env && nano .env
flask --app app init-db
flask --app app create-admin
gunicorn -w 3 -b 0.0.0.0:8000 app:app
```

- Set a long random `SECRET_KEY` before going live, and put the app behind HTTPS (for example nginx or a load balancer).

## Notes

- Allowed uploads: PDF, PNG, JPG, JPEG, DOC, DOCX, up to 10 MB each. Change `ALLOWED_EXTENSIONS` and `MAX_CONTENT_LENGTH` in `config.py`.
- Forms are CSRF-protected and passwords are stored hashed.
