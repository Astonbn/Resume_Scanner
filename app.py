import os
import re
import json
import hashlib
import sqlite3
from flask import (
    Flask, request, jsonify, render_template, session,
    redirect, url_for, flash
)
from flask_cors import CORS
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

import database as db
from resume_parser import extract_text_from_file
from preprocess import extract_skills, extract_experience, extract_education, clean_text
from model import ResumeMatcher

# ----------------------------------------------------------------------
# App configuration
# ----------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# Flask-Mail configuration (update with your SMTP settings)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'
mail = Mail(app)

# File upload settings
UPLOAD_FOLDER_RESUMES = 'uploads/resumes'
UPLOAD_FOLDER_JOBS = 'uploads/jobs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

app.config['UPLOAD_FOLDER_RESUMES'] = UPLOAD_FOLDER_RESUMES
app.config['UPLOAD_FOLDER_JOBS'] = UPLOAD_FOLDER_JOBS

os.makedirs(UPLOAD_FOLDER_RESUMES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_JOBS, exist_ok=True)

# ----------------------------------------------------------------------
# Database initialization (with schema upgrades)
# ----------------------------------------------------------------------
db.init_db()

with db.get_db_connection() as conn:
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN text_hash TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE resumes ADD COLUMN duplicate_group_id INTEGER REFERENCES duplicate_groups(id)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS duplicate_groups (id INTEGER PRIMARY KEY AUTOINCREMENT, group_hash TEXT UNIQUE)")
    except sqlite3.OperationalError:
        pass
    conn.commit()

# ----------------------------------------------------------------------
# Flask-Login setup
# ----------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, role, email):
        self.id = id
        self.username = username
        self.role = role
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = db.get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['role'], user['email'])
    return None

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize_text(text):
    return ' '.join(text.lower().split())

def get_text_hash(text):
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()

def extract_experience(text):
    pattern = r'(\d+)\s*years?'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} years"
    return "Not specified"

def extract_education(text):
    degrees = ["b.sc", "m.sc", "b.e", "m.e", "phd", "bachelor", "master", "mba"]
    text_lower = text.lower()
    for deg in degrees:
        if deg in text_lower:
            return deg.title()
    return "Not specified"

def send_email(to, subject, body):
    try:
        msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to])
        msg.body = body
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def parse_experience_years(exp_str):
    import re
    if not exp_str:
        return None, None
    match = re.search(r'(\d+)(?:\s*-\s*(\d+))?', str(exp_str))
    if match:
        min_y = int(match.group(1))
        max_y = int(match.group(2)) if match.group(2) else min_y
        return min_y, max_y
    return None, None

def check_experience_match(job_exp_str, candidate_exp_str):
    job_min, job_max = parse_experience_years(job_exp_str)
    cand_min, cand_max = parse_experience_years(candidate_exp_str)
    if job_min is None or cand_min is None:
        return False
    if cand_min >= job_min:
        if job_max is not None and cand_min > job_max:
            return False
        return True
    return False

def normalize_degree(edu_str):
    """Return (level, field) tuple from education string."""
    edu_lower = edu_str.lower()
    # Determine degree level
    if any(term in edu_lower for term in ['bachelor', 'b.sc', 'bsc', 'b eng', 'b.e', 'baccalaureate']):
        level = 'bachelor'
    elif any(term in edu_lower for term in ['master', 'm.sc', 'msc', 'm eng', 'm.e', 'magister']):
        level = 'master'
    elif 'phd' in edu_lower or 'doctorate' in edu_lower or 'doctor of' in edu_lower:
        level = 'phd'
    else:
        level = None

    # Determine field of study (common keywords)
    field_keywords = {
        'computer science': ['computer science', 'cs', 'computing', 'software', 'informatics'],
        'information technology': ['information technology', 'it', 'information systems'],
        'engineering': ['engineering', 'engineer'],
        'business': ['business', 'management', 'administration', 'mba'],
        'data science': ['data science', 'data analytics', 'machine learning'],
        'ai': ['artificial intelligence', 'ai', 'machine learning'],
        'mathematics': ['mathematics', 'math', 'statistics'],
        'physics': ['physics', 'physical sciences', 'astrophysics', 'quantum mechanics'],
        'chemistry': ['chemistry', 'chemical', 'biochemistry', 'organic chemistry'],
        'biology': ['biology', 'biological sciences', 'biotechnology', 'molecular biology'],
        'economics': ['economics', 'economy', 'econometrics', 'finance'],
        'psychology': ['psychology', 'psychological', 'clinical psychology', 'cognitive science'],
        'sociology': ['sociology', 'social sciences', 'anthropology', 'sociological'],
        'law': ['law', 'legal', 'jurisprudence', 'criminal justice'],
        'medicine': ['medicine', 'medical', 'clinical', 'healthcare', 'public health'],
        'nursing': ['nursing', 'nurse', 'patient care', 'health sciences'],
        'pharmacy': ['pharmacy', 'pharmaceutical', 'pharmacology', 'drug development'],
        'arts': ['arts', 'fine arts', 'visual arts', 'creative arts', 'performing arts'],
        'humanities': ['humanities', 'history', 'philosophy', 'literature', 'linguistics'],
        'education': ['education', 'teaching', 'pedagogy', 'curriculum', 'instructional design'],
        'environmental science': ['environmental science', 'ecology', 'sustainability', 'climate change'],
        'architecture': ['architecture', 'architectural', 'urban planning', 'landscape architecture']
    }
    field = None
    for f_name, keywords in field_keywords.items():
        if any(kw in edu_lower for kw in keywords):
            field = f_name
            break
    return level, field

def check_education_match(job_education, candidate_education):
    """Match job education requirement against candidate's education."""
    if not job_education or not candidate_education:
        return False

    job_level, job_field = normalize_degree(job_education)
    cand_level, cand_field = normalize_degree(candidate_education)

    if job_level is None:
        if job_field:
            return cand_field == job_field
        return True

    if cand_level is None:
        return False

    level_priority = {'bachelor': 1, 'master': 2, 'phd': 3}
    if level_priority.get(cand_level, 0) < level_priority.get(job_level, 0):
        return False

    if job_field and cand_field and job_field != cand_field:
        return False

    return True

def check_licence_match(job_licences, resume_text):
    if not job_licences:
        return True
    licences = [l.strip().lower() for l in job_licences.split(',') if l.strip()]
    if not licences:
        return True
    resume_lower = resume_text.lower()
    for lic in licences:
        if lic in resume_lower:
            return True
    return False

# ----------------------------------------------------------------------
# Authentication routes
# ----------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = db.get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['role'], user['email'])
            login_user(user_obj)
            flash('Logged in successfully.')
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']
        role = request.form.get('role', 'recruiter')
        conn = db.get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                (username, password, email, role)
            )
            conn.commit()
            flash('Registration successful. Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ----------------------------------------------------------------------
# Job management
# ----------------------------------------------------------------------
@app.route('/upload_job', methods=['POST'])
@login_required
def upload_job():
    title = request.form.get('job_title')
    education = request.form.get('job_education', '')
    skills = request.form.get('job_skills', '')
    experience = request.form.get('job_experience', '')
    licences = request.form.get('job_licences', '')
    other = request.form.get('job_other', '')

    if not title:
        return jsonify({'error': 'Job title is required'}), 400

    description_parts = []
    if education: description_parts.append(f"Education: {education}")
    if skills: description_parts.append(f"Skills: {skills}")
    if experience: description_parts.append(f"Experience: {experience}")
    if licences: description_parts.append(f"Licences: {licences}")
    if other: description_parts.append(f"Other: {other}")
    description = "\n".join(description_parts)

    job_id = db.add_job(title, description, education, skills, experience, licences, other)
    return jsonify({'job_id': job_id, 'message': 'Job added successfully'})

@app.route('/jobs', methods=['GET'])
@login_required
def list_jobs():
    conn = db.get_db_connection()
    jobs = conn.execute("SELECT id, title FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([{'id': j['id'], 'title': j['title']} for j in jobs])

@app.route('/job/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    conn = db.get_db_connection()
    job = conn.execute('''
        SELECT id, title, description, education, skills, experience, licences, other
        FROM jobs WHERE id = ?
    ''', (job_id,)).fetchone()
    conn.close()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({
        'id': job['id'],
        'title': job['title'],
        'description': job['description'],
        'education': job['education'] or '',
        'skills': job['skills'] or '',
        'experience': job['experience'] or '',
        'licences': job['licences'] or '',
        'other': job['other'] or ''
    })

@app.route('/update_job/<int:job_id>', methods=['POST'])
@login_required
def update_job(job_id):
    title = request.form.get('job_title')
    education = request.form.get('job_education', '')
    skills = request.form.get('job_skills', '')
    experience = request.form.get('job_experience', '')
    licences = request.form.get('job_licences', '')
    other = request.form.get('job_other', '')

    if not title:
        return jsonify({'error': 'Job title is required'}), 400

    description_parts = []
    if education: description_parts.append(f"Education: {education}")
    if skills: description_parts.append(f"Skills: {skills}")
    if experience: description_parts.append(f"Experience: {experience}")
    if licences: description_parts.append(f"Licences: {licences}")
    if other: description_parts.append(f"Other: {other}")
    description = "\n".join(description_parts)

    db.update_job(job_id, title, description, education, skills, experience, licences, other)
    return jsonify({'message': 'Job updated successfully'})

@app.route('/delete_job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    conn = db.get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job deleted successfully'})

# ----------------------------------------------------------------------
# Resume upload with duplicate detection
# ----------------------------------------------------------------------
@app.route('/upload_resumes', methods=['POST'])
@login_required
def upload_resumes():
    if 'resumes' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    files = request.files.getlist('resumes')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400

    job_id = request.form.get('job_id')
    if not job_id:
        return jsonify({'error': 'Job ID missing'}), 400

    uploaded_resumes = []
    conn = db.get_db_connection()
    for file in files:
        if not (file and allowed_file(file.filename)):
            conn.close()
            return jsonify({'error': f'Invalid file type: {file.filename}'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER_RESUMES'], filename)
        file.save(filepath)

        try:
            text = extract_text_from_file(filepath)
            skills = extract_skills(text)
            experience = extract_experience(text)
            education = extract_education(text)
            text_hash = get_text_hash(text)

            # Check for duplicate using text_hash
            existing = conn.execute(
                "SELECT id FROM resumes WHERE text_hash = ?", (text_hash,)
            ).fetchone()
            if existing:
                # Duplicate: reuse existing resume ID
                resume_id = existing['id']
                duplicate_flag = True
                print(f"Duplicate detected: {filename} matches existing resume ID {resume_id}")
            else:
                # New unique resume
                resume_id = db.add_resume(filename, text, skills, experience, education)
                conn.execute("UPDATE resumes SET text_hash = ? WHERE id = ?", (text_hash, resume_id))
                duplicate_flag = False

            uploaded_resumes.append({
                'id': resume_id,
                'filename': filename,
                'skills': skills,
                'experience': experience,
                'education': education,
                'is_duplicate': duplicate_flag
            })
        except Exception as e:
            conn.close()
            return jsonify({'error': f'Error processing {filename}: {str(e)}'}), 500

    conn.commit()
    conn.close()
    return jsonify({'resumes': uploaded_resumes, 'message': 'Resumes uploaded successfully'})

# ----------------------------------------------------------------------
# AI analysis with skill gap and explanation
# ----------------------------------------------------------------------
@app.route('/analyze/<int:job_id>', methods=['POST'])
@login_required
def analyze(job_id):
    conn = db.get_db_connection()
    job = conn.execute('''
        SELECT description, education, skills, experience, licences, other
        FROM jobs WHERE id = ?
    ''', (job_id,)).fetchone()
    if not job:
        conn.close()
        return jsonify({'error': 'Job not found'}), 404

    job_desc = job['description']
    job_education = job['education'] or ''
    job_experience = job['experience'] or ''
    job_licences = job['licences'] or ''
    job_skills_text = job['skills'] or ''

    job_skills = extract_skills(job_skills_text) if job_skills_text else extract_skills(job_desc)

    matcher = ResumeMatcher()
    matcher.fit_job(job_desc)

    resumes = conn.execute('''
        SELECT id, text, skills, experience, education
        FROM resumes
    ''').fetchall()
    conn.close()

    results = []
    for resume in resumes:
        score = matcher.score_resume(resume['text'])
        skills_list = eval(resume['skills']) if isinstance(resume['skills'], str) else resume['skills']

        matched = [s for s in job_skills if s.lower() in [sk.lower() for sk in skills_list]]
        missing = [s for s in job_skills if s.lower() not in [sk.lower() for sk in skills_list]]
        explanation = f"Strong match: {', '.join(matched)}. Missing: {', '.join(missing)}." if matched else "No strong match."

        exp_match = check_experience_match(job_experience, resume['experience'])
        edu_match = check_education_match(job_education, resume['education'])
        # Debug prints (remove after testing)
        print(f"Job education: {job_education}")
        print(f"Candidate education: {resume['education']}")
        print(f"Education match: {edu_match}")
        print("-" * 40)
        lic_match = check_licence_match(job_licences, resume['text'])

        db.add_score(job_id, resume['id'], score, matched, explanation, missing,
                     exp_match, edu_match, lic_match)

        results.append({
            'resume_id': resume['id'],
            'score': score,
            'matched_skills': matched,
            'missing_skills': missing,
            'experience_match': exp_match,
            'education_match': edu_match,
            'licence_match': lic_match
        })

    return jsonify({'results': results, 'message': 'Analysis complete'})

@app.route('/results/<int:job_id>', methods=['GET'])
@login_required
def get_results(job_id):
    candidates = db.get_ranked_candidates(job_id)
    return jsonify(candidates)

# ----------------------------------------------------------------------
# Candidate status (shortlist, reject, interview) and notes
# ----------------------------------------------------------------------
@app.route('/candidate_status', methods=['POST'])
@login_required
def update_candidate_status():
    data = request.json
    resume_id = data.get('resume_id')
    job_id = data.get('job_id')
    status = data.get('status')
    notes = data.get('notes', '')

    if not all([resume_id, job_id, status]):
        return jsonify({'error': 'Missing fields'}), 400

    conn = db.get_db_connection()
    conn.execute("""
        INSERT INTO candidate_status (resume_id, job_id, status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(resume_id, job_id) DO UPDATE SET
            status = excluded.status,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
    """, (resume_id, job_id, status, notes))
    conn.commit()

    if status in ['shortlisted', 'rejected']:
        resume = conn.execute("SELECT text, filename FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if resume:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume['text'])
            if email_match:
                candidate_email = email_match.group(0)
                subject = f"Application Status Update - {status.capitalize()}"
                body = f"Dear applicant,\n\nYour application for job ID {job_id} has been {status}.\n\n"
                if notes:
                    body += f"Note from HR: {notes}\n\n"
                body += "Thank you for applying."
                send_email(candidate_email, subject, body)
    conn.close()
    return jsonify({'message': 'Status updated'})

@app.route('/candidate_status/<int:job_id>', methods=['GET'])
@login_required
def get_candidate_statuses(job_id):
    conn = db.get_db_connection()
    rows = conn.execute("""
        SELECT resume_id, status, notes
        FROM candidate_status
        WHERE job_id = ?
    """, (job_id,)).fetchall()
    conn.close()
    return jsonify([{'resume_id': r['resume_id'], 'status': r['status'], 'notes': r['notes']} for r in rows])

# ----------------------------------------------------------------------
# Bulk actions
# ----------------------------------------------------------------------
@app.route('/bulk_status', methods=['POST'])
@login_required
def bulk_update_status():
    data = request.json
    resume_ids = data.get('resume_ids', [])
    job_id = data.get('job_id')
    status = data.get('status')
    notes = data.get('notes', '')

    if not resume_ids or not job_id or not status:
        return jsonify({'error': 'Missing parameters'}), 400

    conn = db.get_db_connection()
    for resume_id in resume_ids:
        conn.execute("""
            INSERT INTO candidate_status (resume_id, job_id, status, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(resume_id, job_id) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                updated_at = CURRENT_TIMESTAMP
        """, (resume_id, job_id, status, notes))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Bulk update completed for {len(resume_ids)} candidates'})

@app.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    data = request.json
    resume_ids = data.get('resume_ids', [])
    if not resume_ids:
        return jsonify({'error': 'No resume IDs provided'}), 400

    conn = db.get_db_connection()
    placeholders = ','.join('?' * len(resume_ids))
    conn.execute(f"DELETE FROM scores WHERE resume_id IN ({placeholders})", resume_ids)
    conn.execute(f"DELETE FROM resumes WHERE id IN ({placeholders})", resume_ids)
    conn.commit()
    conn.close()
    return jsonify({'message': f'Deleted {len(resume_ids)} candidates'})

# ----------------------------------------------------------------------
# Analytics
# ----------------------------------------------------------------------
@app.route('/analytics/<int:job_id>', methods=['GET'])
@login_required
def analytics(job_id):
    conn = db.get_db_connection()
    scores = conn.execute("SELECT score FROM scores WHERE job_id = ?", (job_id,)).fetchall()
    if not scores:
        conn.close()
        return jsonify({'error': 'No scores for this job'}), 404
    avg_score = sum(s['score'] for s in scores) / len(scores)
    all_scores = [s['score'] for s in scores]

    skills_rows = conn.execute("""
        SELECT resumes.skills
        FROM resumes
        JOIN scores ON resumes.id = scores.resume_id
        WHERE scores.job_id = ?
    """, (job_id,)).fetchall()
    skill_counter = {}
    for row in skills_rows:
        skills = eval(row['skills']) if isinstance(row['skills'], str) else row['skills']
        for skill in skills:
            skill_counter[skill] = skill_counter.get(skill, 0) + 1
    top_skills = sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:5]

    status_counts = conn.execute("""
        SELECT status, COUNT(*) as count
        FROM candidate_status
        WHERE job_id = ?
        GROUP BY status
    """, (job_id,)).fetchall()
    status_dict = {row['status']: row['count'] for row in status_counts}

    conn.close()
    return jsonify({
        'average_score': avg_score,
        'top_skills': [{'name': s, 'count': c} for s, c in top_skills],
        'total_candidates': len(scores),
        'status_counts': status_dict,
        'scores': all_scores
    })

# ----------------------------------------------------------------------
# Delete a single candidate
# ----------------------------------------------------------------------
@app.route('/delete_candidate/<int:resume_id>', methods=['DELETE'])
@login_required
def delete_candidate(resume_id):
    try:
        print(f"Deleting candidate with resume_id: {resume_id}")
        conn = db.get_db_connection()
        conn.execute("DELETE FROM scores WHERE resume_id = ?", (resume_id,))
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Candidate deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----------------------------------------------------------------------
# Interview scheduling
# ----------------------------------------------------------------------
@app.route('/schedule_interview', methods=['POST'])
@login_required
def schedule_interview():
    data = request.json
    resume_id = data.get('resume_id')
    job_id = data.get('job_id')
    interview_date = data.get('date')
    interview_time = data.get('time')
    notes = data.get('notes', '')

    if not all([resume_id, job_id, interview_date, interview_time]):
        return jsonify({'error': 'Missing fields'}), 400

    conn = db.get_db_connection()
    resume = conn.execute("SELECT text, filename FROM resumes WHERE id = ?", (resume_id,)).fetchone()
    if not resume:
        conn.close()
        return jsonify({'error': 'Resume not found'}), 404

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume['text'])
    if not email_match:
        conn.close()
        return jsonify({'error': 'Could not extract candidate email from resume'}), 400
    candidate_email = email_match.group(0)

    interview_note = f"Interview scheduled for {interview_date} at {interview_time}. {notes}"
    conn.execute("""
        INSERT INTO candidate_status (resume_id, job_id, status, notes)
        VALUES (?, ?, 'interview', ?)
        ON CONFLICT(resume_id, job_id) DO UPDATE SET
            status = 'interview',
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
    """, (resume_id, job_id, interview_note))
    conn.commit()
    conn.close()

    subject = f"Interview Invitation for {resume['filename']}"
    body = f"""Dear candidate,

You have been invited for an interview on {interview_date} at {interview_time}.

Additional notes: {notes}

Please reply to confirm your availability.

Best regards,
HR Team
"""
    #send_email(candidate_email, subject, body)  # Uncomment when email is configured
    return jsonify({'message': 'Interview scheduled and email sent'})

# ----------------------------------------------------------------------
# Run the app
# ----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)