# College Recruitment System — Python Flask

A full-featured web-based employee recruitment system built with Python (Flask) as the backend, SQLite3 as the database, and plain HTML/CSS/JavaScript for the frontend.

## Features

- **Phase 1 — Application Form**: Name, email, phone, department, qualification, certificate upload
- **Phase 2 — Online Test**: 50 department-specific questions, 15 randomly selected, 15-minute timer, auto-submit on timeout
- **Phase 3 — Result**: Instant result display + professional HTML email notification (pass/fail)
- **Admin Panel**: Login-protected dashboard with stats, filters by department/status, and full applicant table

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask |
| Database | SQLite3 (built into Python) |
| Email | Python smtplib + Gmail SMTP |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Templates | Jinja2 (built into Flask) |

---

## Project Structure

```
recruitment-flask/
├── app.py               ← Main Flask app (routes, logic, email)
├── questions.py         ← 50 quiz questions per department
├── requirements.txt     ← Python dependencies
├── .env.example         ← Environment variable template
├── .env                 ← Your local config (create from .env.example)
├── recruitment.db       ← SQLite3 database (auto-created on first run)
├── uploads/             ← Uploaded certificate files
├── static/
│   └── css/
│       └── style.css    ← All styling
└── templates/
    ├── base.html        ← Navbar, footer layout
    ├── index.html       ← Application form (Phase 1)
    ├── quiz.html        ← Quiz page (Phase 2)
    ├── result.html      ← Result page (Phase 3)
    └── admin.html       ← Admin panel
```

---

## Local Setup (VS Code)

### Step 1 — Prerequisites

Install **Python 3.10+**: https://www.python.org/downloads/
> ✅ Check "Add Python to PATH" during installation on Windows

Verify installation:
```bash
python --version
```

### Step 2 — Open in VS Code

Extract the folder and open it:
```
File → Open Folder → select "recruitment-flask"
```

### Step 3 — Create virtual environment

Open the VS Code terminal (`Ctrl + `` ` ``):

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You'll see `(venv)` appear in your terminal prompt.

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Create .env file

Copy the example:
```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Edit `.env` and fill in your values:
```env
SECRET_KEY=any-random-string-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-16-char-gmail-app-password
```

> **Gmail App Password:**
> 1. Go to https://myaccount.google.com/security
> 2. Enable 2-Step Verification
> 3. Search for "App Passwords" → Create one for "Mail"
> 4. Use the 16-character password as SMTP_PASS

### Step 6 — Run the app

```bash
python app.py
```

### Step 7 — Open in Chrome

Go to: **http://localhost:5000**

- **Admin Panel**: http://localhost:5000/admin (user: `admin`, pass: `admin123`)

---

## How It Works

| Phase | Flow |
|-------|------|
| **Apply** | Applicant fills form → POST /api/apply → Saved to SQLite3 → Redirect to quiz |
| **Quiz** | GET /api/quiz/<id> → 15 random questions served → Timer starts → Submit via POST /api/quiz/submit |
| **Result** | Score calculated → Saved to DB → Email sent → GET /api/result/<id> → Result page shown |
| **Admin** | POST /api/admin/login → Session cookie set → GET /api/admin/applicants with filters |

## Pass Criteria

- **Pass**: Score ≥ 9 out of 15
- **Fail**: Score < 9 out of 15

## Database Tables

**applicants**
```
id, name, email, phone, department, qualification,
certificate_path, score, total_questions, passed,
submitted_at, quiz_questions (JSON), quiz_answers (JSON)
```

**quiz_questions**
```
id, department, question, option_a, option_b,
option_c, option_d, correct_option
```
