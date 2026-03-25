import sqlite3
import json

def get_db_connection():
    conn = sqlite3.connect('resumes.db')
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Job descriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Resumes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            text TEXT,
            skills TEXT,
            experience TEXT,
            education TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Scores table (links jobs and resumes) with CASCADE delete
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            resume_id INTEGER,
            score REAL,
            matched_skills TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

# The rest of your functions remain unchanged, but ensure they use the updated get_db_connection
def add_job(title, description):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (title, description) VALUES (?, ?)", (title, description))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

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

def add_score(job_id, resume_id, score, matched_skills):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO scores (job_id, resume_id, score, matched_skills)
        VALUES (?, ?, ?, ?)
    ''', (job_id, resume_id, score, json.dumps(matched_skills)))
    conn.commit()
    conn.close()

def get_ranked_candidates(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT resumes.id, resumes.filename, resumes.skills, scores.score, scores.matched_skills
        FROM scores
        JOIN resumes ON scores.resume_id = resumes.id
        WHERE scores.job_id = ?
        ORDER BY scores.score DESC
    ''', (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{
        'resume_id': row['id'],
        'filename': row['filename'],
        'skills': json.loads(row['skills']),
        'score': row['score'],
        'matched_skills': json.loads(row['matched_skills'])
    } for row in rows]