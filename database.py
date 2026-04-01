import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect('resumes.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'recruiter',
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Jobs table with new columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            education TEXT,
            skills TEXT,
            experience TEXT,
            licences TEXT,
            other TEXT
        )
    ''')
    # Add missing columns if they don't exist (for existing databases)
    for col in ['education', 'skills', 'experience', 'licences', 'other']:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    # Resumes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            text TEXT,
            skills TEXT,
            experience TEXT,
            education TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            text_hash TEXT,
            duplicate_group_id INTEGER
        )
    ''')
    try:
        cursor.execute("ALTER TABLE resumes ADD COLUMN text_hash TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE resumes ADD COLUMN duplicate_group_id INTEGER")
    except sqlite3.OperationalError:
        pass

    # Scores table (create with all required columns)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            resume_id INTEGER,
            score REAL,
            matched_skills TEXT,
            missing_skills TEXT,
            experience_match INTEGER DEFAULT 0,
            education_match INTEGER DEFAULT 0,
            licence_match INTEGER DEFAULT 0,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        )
    ''')
    # Add any missing columns if needed (safe for existing databases)
    for col in ['explanation', 'missing_skills', 'experience_match', 'education_match', 'licence_match']:
        try:
            if col in ['experience_match', 'education_match', 'licence_match']:
                cursor.execute(f"ALTER TABLE scores ADD COLUMN {col} INTEGER DEFAULT 0")
            else:
                cursor.execute(f"ALTER TABLE scores ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    # Candidate status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(resume_id, job_id)
        )
    ''')

    # Duplicate groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_hash TEXT UNIQUE NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# CRUD functions
# ----------------------------------------------------------------------
def add_job(title, description, education, skills, experience, licences, other):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO jobs (title, description, education, skills, experience, licences, other)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, description, education, skills, experience, licences, other))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def update_job(job_id, title, description, education, skills, experience, licences, other):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE jobs SET title=?, description=?, education=?, skills=?, experience=?, licences=?, other=?
        WHERE id=?
    ''', (title, description, education, skills, experience, licences, other, job_id))
    conn.commit()
    conn.close()

def add_resume(filename, text, skills, experience, education):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO resumes (filename, text, skills, experience, education)
        VALUES (?, ?, ?, ?, ?)
    ''', (filename, text, json.dumps(skills), experience, education))
    resume_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return resume_id

def add_score(job_id, resume_id, score, matched_skills, explanation, missing_skills,
              experience_match, education_match, licence_match):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO scores
        (job_id, resume_id, score, matched_skills, explanation, missing_skills,
         experience_match, education_match, licence_match)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (job_id, resume_id, score,
          json.dumps(matched_skills), explanation, json.dumps(missing_skills),
          experience_match, education_match, licence_match))
    conn.commit()
    conn.close()

def get_ranked_candidates(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            r.id AS resume_id,
            r.filename,
            r.skills,
            s.score,
            s.matched_skills,
            s.missing_skills,
            s.experience_match,
            s.education_match,
            s.licence_match,
            COALESCE(cs.status, 'pending') AS status,
            cs.notes
        FROM scores s
        JOIN resumes r ON s.resume_id = r.id
        LEFT JOIN candidate_status cs ON cs.resume_id = r.id AND cs.job_id = s.job_id
        WHERE s.job_id = ?
        ORDER BY s.score DESC
    ''', (job_id,))
    rows = cursor.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        # Load JSON fields safely
        try:
            skills = json.loads(row['skills'])
        except (json.JSONDecodeError, TypeError):
            skills = []
        try:
            matched_skills = json.loads(row['matched_skills'])
        except (json.JSONDecodeError, TypeError):
            matched_skills = []
        try:
            missing_skills = json.loads(row['missing_skills'])
        except (json.JSONDecodeError, TypeError):
            missing_skills = []

        candidates.append({
            'resume_id': row['resume_id'],
            'filename': row['filename'],
            'skills': skills,
            'score': row['score'],
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'experience_match': bool(row['experience_match']),
            'education_match': bool(row['education_match']),
            'licence_match': bool(row['licence_match']),
            'status': row['status'],
            'notes': row['notes'] or ''
        })
    return candidates

def update_candidate_status(resume_id, job_id, status, notes=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO candidate_status (resume_id, job_id, status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(resume_id, job_id) DO UPDATE SET
            status = excluded.status,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
    ''', (resume_id, job_id, status, notes))
    conn.commit()
    conn.close()