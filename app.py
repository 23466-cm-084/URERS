import os
import random
import sqlite3
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, send_from_directory
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production-secret-key")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max upload

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

DATABASE = "recruitment.db"


# ─── Database ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            department TEXT NOT NULL,
            qualification TEXT NOT NULL,
            certificate_path TEXT,
            score INTEGER,
            total_questions INTEGER DEFAULT 15,
            passed INTEGER DEFAULT 0,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            quiz_questions TEXT,
            quiz_answers TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL
        )
    """)

    conn.commit()

    count = cur.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
    if count == 0:
        seed_questions(conn)

    conn.close()


def seed_questions(conn):
    from questions import QUESTIONS
    cur = conn.cursor()
    for dept, questions in QUESTIONS.items():
        for q in questions:
            cur.execute("""
                INSERT INTO quiz_questions
                    (department, question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dept, q["question"], q["a"], q["b"], q["c"], q["d"], q["correct"]))
    conn.commit()
    print(f"Seeded quiz questions for all departments.")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def send_email(to_email, applicant_name, department, score, total, passed):
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP credentials not configured. Skipping email.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"🎉 Congratulations! You're Shortlisted – {department} Dept"
            if passed else
            f"Your Recruitment Test Result – {department} Dept"
        )
        msg["From"] = SMTP_USER
        msg["To"] = to_email

        if passed:
            html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
    <div style="background:linear-gradient(135deg,#16a34a,#15803d);padding:40px;text-align:center;">
      <div style="font-size:60px;">🎉</div>
      <h1 style="color:#fff;margin:10px 0;">Congratulations!</h1>
      <p style="color:#bbf7d0;font-size:16px;">You have been shortlisted!</p>
    </div>
    <div style="padding:40px;">
      <p style="font-size:16px;color:#374151;">Dear <strong>{applicant_name}</strong>,</p>
      <p style="color:#6b7280;line-height:1.7;">
        We are thrilled to inform you that you have <strong>successfully passed</strong> the
        online recruitment test for the <strong>{department} Department</strong> at our college.
      </p>
      <div style="background:#f0fdf4;border:2px solid #86efac;border-radius:12px;padding:24px;margin:24px 0;text-align:center;">
        <p style="margin:0;font-size:14px;color:#16a34a;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">Your Score</p>
        <p style="margin:8px 0 0;font-size:48px;font-weight:900;color:#15803d;">{score}/{total}</p>
        <p style="margin:4px 0 0;font-size:14px;color:#166534;">PASS ✓</p>
      </div>
      <div style="background:#fefce8;border-left:4px solid #facc15;padding:16px;border-radius:8px;margin:20px 0;">
        <p style="margin:0;font-weight:bold;color:#854d0e;">📅 Next Step: Campus Interview</p>
        <p style="margin:8px 0 0;color:#713f12;">
          Our HR team will contact you shortly with the campus interview schedule.
          Please keep your phone and email active.
        </p>
      </div>
      <p style="color:#6b7280;">Best regards,<br><strong>HR & Recruitment Team</strong><br>College Recruitment Cell</p>
    </div>
  </div>
</body>
</html>"""
        else:
            html = f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1);">
    <div style="background:linear-gradient(135deg,#d97706,#b45309);padding:40px;text-align:center;">
      <div style="font-size:60px;">📋</div>
      <h1 style="color:#fff;margin:10px 0;">Test Result</h1>
      <p style="color:#fde68a;font-size:16px;">{department} Department</p>
    </div>
    <div style="padding:40px;">
      <p style="font-size:16px;color:#374151;">Dear <strong>{applicant_name}</strong>,</p>
      <p style="color:#6b7280;line-height:1.7;">
        Thank you for appearing in our online recruitment test for the
        <strong>{department} Department</strong>. We appreciate the effort you put in.
      </p>
      <div style="background:#fffbeb;border:2px solid #fcd34d;border-radius:12px;padding:24px;margin:24px 0;text-align:center;">
        <p style="margin:0;font-size:14px;color:#d97706;font-weight:bold;text-transform:uppercase;letter-spacing:1px;">Your Score</p>
        <p style="margin:8px 0 0;font-size:48px;font-weight:900;color:#b45309;">{score}/{total}</p>
        <p style="margin:4px 0 0;font-size:14px;color:#92400e;">Minimum required: 9/{total}</p>
      </div>
      <p style="color:#6b7280;line-height:1.7;">
        Unfortunately, you did not meet the minimum score requirement this time.
        We encourage you to keep learning and apply again in future recruitment drives.
      </p>
      <div style="background:#f8fafc;border-radius:8px;padding:16px;margin:20px 0;">
        <p style="margin:0;font-weight:bold;color:#374151;">💡 Tips to improve:</p>
        <ul style="color:#6b7280;margin:8px 0;padding-left:20px;line-height:1.8;">
          <li>Review core {department} subjects and fundamentals</li>
          <li>Practice with previous year question papers</li>
          <li>Join study groups and online courses</li>
        </ul>
      </div>
      <p style="color:#6b7280;">Best regards,<br><strong>HR & Recruitment Team</strong><br>College Recruitment Cell</p>
    </div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


# ─── Page Routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/apply")
def apply_page():
    return render_template("apply.html")


@app.route("/quiz")
def quiz_page():
    applicant_id = request.args.get("applicant_id")
    if not applicant_id:
        return redirect(url_for("index"))
    return render_template("quiz.html", applicant_id=applicant_id)


@app.route("/result")
def result_page():
    applicant_id = request.args.get("applicant_id")
    if not applicant_id:
        return redirect(url_for("index"))
    return render_template("result.html", applicant_id=applicant_id)


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ─── API: Application ─────────────────────────────────────────────────────────

@app.route("/api/apply", methods=["POST"])
def apply():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    department = request.form.get("department", "").strip()
    qualification = request.form.get("qualification", "").strip()

    if not all([name, email, phone, department, qualification]):
        return jsonify({"error": "All fields are required"}), 400

    valid_depts = {"CSE", "ECE", "MECH", "EEE", "CIVIL", "IT"}
    if department not in valid_depts:
        return jsonify({"error": "Invalid department"}), 400

    certificate_path = None
    if "certificate" in request.files:
        file = request.files["certificate"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            certificate_path = filename

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applicants (name, email, phone, department, qualification, certificate_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, email, phone, department, qualification, certificate_path))
    conn.commit()
    applicant_id = cur.lastrowid
    conn.close()

    return jsonify({"applicant_id": applicant_id, "message": "Application submitted successfully"})


# ─── API: Quiz ────────────────────────────────────────────────────────────────

@app.route("/api/quiz/<int:applicant_id>", methods=["GET"])
def get_quiz(applicant_id):
    conn = get_db()
    cur = conn.cursor()

    applicant = cur.execute(
        "SELECT * FROM applicants WHERE id = ?", (applicant_id,)
    ).fetchone()

    if not applicant:
        conn.close()
        return jsonify({"error": "Applicant not found"}), 404

    if applicant["score"] is not None:
        conn.close()
        return jsonify({"error": "Quiz already submitted"}), 400

    if applicant["quiz_questions"]:
        question_ids = json.loads(applicant["quiz_questions"])
        questions = []
        for qid in question_ids:
            q = cur.execute("SELECT * FROM quiz_questions WHERE id = ?", (qid,)).fetchone()
            if q:
                questions.append({
                    "id": q["id"],
                    "question": q["question"],
                    "option_a": q["option_a"],
                    "option_b": q["option_b"],
                    "option_c": q["option_c"],
                    "option_d": q["option_d"],
                })
        conn.close()
        return jsonify({"questions": questions, "duration_minutes": 15})

    all_questions = cur.execute(
        "SELECT * FROM quiz_questions WHERE department = ?", (applicant["department"],)
    ).fetchall()

    if len(all_questions) < 15:
        conn.close()
        return jsonify({"error": "Not enough questions for this department"}), 500

    selected = random.sample(all_questions, 15)
    question_ids = [q["id"] for q in selected]

    cur.execute(
        "UPDATE applicants SET quiz_questions = ? WHERE id = ?",
        (json.dumps(question_ids), applicant_id)
    )
    conn.commit()
    conn.close()

    questions = [{
        "id": q["id"],
        "question": q["question"],
        "option_a": q["option_a"],
        "option_b": q["option_b"],
        "option_c": q["option_c"],
        "option_d": q["option_d"],
    } for q in selected]

    return jsonify({"questions": questions, "duration_minutes": 15})


@app.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    data = request.get_json()
    applicant_id = data.get("applicant_id")
    answers = data.get("answers", {})

    if not applicant_id:
        return jsonify({"error": "Applicant ID required"}), 400

    conn = get_db()
    cur = conn.cursor()

    applicant = cur.execute(
        "SELECT * FROM applicants WHERE id = ?", (applicant_id,)
    ).fetchone()

    if not applicant:
        conn.close()
        return jsonify({"error": "Applicant not found"}), 404

    if applicant["score"] is not None:
        conn.close()
        return jsonify({
            "score": applicant["score"],
            "total": applicant["total_questions"],
            "passed": bool(applicant["passed"])
        })

    question_ids = json.loads(applicant["quiz_questions"] or "[]")
    score = 0

    for qid in question_ids:
        q = cur.execute("SELECT correct_option FROM quiz_questions WHERE id = ?", (qid,)).fetchone()
        if q and answers.get(str(qid), "").upper() == q["correct_option"].upper():
            score += 1

    passed = score >= 9

    cur.execute("""
        UPDATE applicants
        SET score = ?, passed = ?, quiz_answers = ?, submitted_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (score, 1 if passed else 0, json.dumps(answers), applicant_id))
    conn.commit()
    conn.close()

    send_email(
        applicant["email"],
        applicant["name"],
        applicant["department"],
        score, 15, passed
    )

    return jsonify({
        "score": score,
        "total": 15,
        "passed": passed,
        "message": "Quiz submitted successfully"
    })


@app.route("/api/result/<int:applicant_id>", methods=["GET"])
def get_result(applicant_id):
    conn = get_db()
    applicant = conn.execute(
        "SELECT id, name, email, department, score, total_questions, passed, submitted_at FROM applicants WHERE id = ?",
        (applicant_id,)
    ).fetchone()
    conn.close()

    if not applicant:
        return jsonify({"error": "Applicant not found"}), 404

    if applicant["score"] is None:
        return jsonify({"error": "Quiz not yet submitted"}), 400

    return jsonify({
        "id": applicant["id"],
        "name": applicant["name"],
        "email": applicant["email"],
        "department": applicant["department"],
        "score": applicant["score"],
        "total": applicant["total_questions"],
        "passed": bool(applicant["passed"]),
        "submitted_at": applicant["submitted_at"],
    })


# ─── API: Admin ───────────────────────────────────────────────────────────────

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if data.get("username") == ADMIN_USERNAME and data.get("password") == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"message": "Logged out"})


@app.route("/api/admin/applicants", methods=["GET"])
@admin_required
def admin_applicants():
    dept = request.args.get("department", "")
    status = request.args.get("status", "")

    query = "SELECT id, name, email, phone, department, qualification, score, total_questions, passed, submitted_at FROM applicants WHERE 1=1"
    params = []

    if dept:
        query += " AND department = ?"
        params.append(dept)
    if status == "passed":
        query += " AND passed = 1 AND score IS NOT NULL"
    elif status == "failed":
        query += " AND passed = 0 AND score IS NOT NULL"
    elif status == "pending":
        query += " AND score IS NULL"

    query += " ORDER BY submitted_at DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    applicants = []
    for r in rows:
        applicants.append({
            "id": r["id"],
            "name": r["name"],
            "email": r["email"],
            "phone": r["phone"],
            "department": r["department"],
            "qualification": r["qualification"],
            "score": r["score"],
            "total": r["total_questions"],
            "passed": bool(r["passed"]) if r["score"] is not None else None,
            "submitted_at": r["submitted_at"],
        })

    return jsonify({"applicants": applicants})


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    conn = get_db()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
    passed = cur.execute("SELECT COUNT(*) FROM applicants WHERE passed = 1").fetchone()[0]
    failed = cur.execute("SELECT COUNT(*) FROM applicants WHERE passed = 0 AND score IS NOT NULL").fetchone()[0]
    pending = cur.execute("SELECT COUNT(*) FROM applicants WHERE score IS NULL").fetchone()[0]

    dept_stats = cur.execute("""
        SELECT department, COUNT(*) as total,
               SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as passed
        FROM applicants GROUP BY department
    """).fetchall()

    conn.close()

    return jsonify({
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "by_department": [{"department": r["department"], "total": r["total"], "passed": r["passed"]} for r in dept_stats],
    })


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port)
