import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename
import database as db
from resume_parser import extract_text_from_file
from preprocess import extract_skills, extract_experience, extract_education  # we'll define these
from model import ResumeMatcher, clean_text

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# Configuration
UPLOAD_FOLDER_RESUMES = 'uploads/resumes'
UPLOAD_FOLDER_JOBS = 'uploads/jobs'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

app.config['UPLOAD_FOLDER_RESUMES'] = UPLOAD_FOLDER_RESUMES
app.config['UPLOAD_FOLDER_JOBS'] = UPLOAD_FOLDER_JOBS

os.makedirs(UPLOAD_FOLDER_RESUMES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_JOBS, exist_ok=True)

db.init_db()  # Ensure database tables exist

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper functions for skill/experience/education extraction (simplified)
def extract_experience(text):
    # Very basic: look for "years" or "experience"
    import re
    pattern = r'(\d+)\s*years?'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return f"{match.group(1)} years"
    return "Not specified"

def extract_education(text):
    # Look for degree keywords
    degrees = ["b.sc", "m.sc", "b.e", "m.e", "phd", "bachelor", "master", "mba"]
    text_lower = text.lower()
    for deg in degrees:
        if deg in text_lower:
            return deg.title()
    return "Not specified"

@app.route('/')
def index():
    return render_template('index.html')

# Upload job description
@app.route('/upload_job', methods=['POST'])
def upload_job():
    if 'job_title' not in request.form or 'job_desc' not in request.form:
        return jsonify({'error': 'Missing job title or description'}), 400
    title = request.form['job_title']
    description = request.form['job_desc']
    job_id = db.add_job(title, description)
    return jsonify({'job_id': job_id, 'message': 'Job added successfully'})

# Upload multiple resumes
@app.route('/upload_resumes', methods=['POST'])
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
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER_RESUMES'], filename)
            file.save(filepath)
            try:
                text = extract_text_from_file(filepath)
                skills = extract_skills(text)
                experience = extract_experience(text)
                education = extract_education(text)
                resume_id = db.add_resume(filename, text, skills, experience, education)
                uploaded_resumes.append({
                    'id': resume_id,
                    'filename': filename,
                    'skills': skills,
                    'experience': experience,
                    'education': education
                })
            except Exception as e:
                return jsonify({'error': f'Error processing {filename}: {str(e)}'}), 500
        else:
            return jsonify({'error': f'Invalid file type: {file.filename}'}), 400

    return jsonify({'resumes': uploaded_resumes, 'message': 'Resumes uploaded successfully'})

# Run AI analysis for a specific job
@app.route('/analyze/<int:job_id>', methods=['POST'])
def analyze(job_id):
    # Retrieve job description from database
    conn = db.get_db_connection()
    job = conn.execute("SELECT description FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    job_desc = job['description']
    matcher = ResumeMatcher()
    matcher.fit_job(job_desc)

    # Get all resumes from database
    conn = db.get_db_connection()
    resumes = conn.execute("SELECT id, text, skills FROM resumes").fetchall()
    conn.close()

    results = []
    for resume in resumes:
        score = matcher.score_resume(resume['text'])
        # Compute matched skills (skills that appear in job description)
        job_desc_lower = job_desc.lower()
        skills_list = eval(resume['skills']) if isinstance(resume['skills'], str) else resume['skills']
        matched = [skill for skill in skills_list if skill.lower() in job_desc_lower]
        db.add_score(job_id, resume['id'], score, matched)
        results.append({
            'resume_id': resume['id'],
            'score': score,
            'matched_skills': matched
        })

    return jsonify({'results': results, 'message': 'Analysis complete'})

# Get ranked candidates for a job
@app.route('/results/<int:job_id>', methods=['GET'])
def get_results(job_id):
    candidates = db.get_ranked_candidates(job_id)
    return jsonify(candidates)

# Analytics endpoint: top skills, average score, etc.
@app.route('/analytics/<int:job_id>', methods=['GET'])
def analytics(job_id):
    conn = db.get_db_connection()
    scores = conn.execute("SELECT score FROM scores WHERE job_id = ?", (job_id,)).fetchall()
    conn.close()
    if not scores:
        return jsonify({'error': 'No scores for this job'}), 404
    avg_score = sum(s['score'] for s in scores) / len(scores)
    # Top skills: we need to aggregate skills from resumes
    conn = db.get_db_connection()
    skills_rows = conn.execute('''
        SELECT resumes.skills, scores.score
        FROM resumes
        JOIN scores ON resumes.id = scores.resume_id
        WHERE scores.job_id = ?
    ''', (job_id,)).fetchall()
    conn.close()

    skill_counter = {}
    for row in skills_rows:
        skills = eval(row['skills']) if isinstance(row['skills'], str) else row['skills']
        for skill in skills:
            skill_counter[skill] = skill_counter.get(skill, 0) + 1
    top_skills = sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    return jsonify({
        'average_score': avg_score,
        'top_skills': [{'name': s, 'count': c} for s, c in top_skills],
        'total_candidates': len(scores)
    })

@app.route('/jobs', methods=['GET'])
def list_jobs():
    conn = db.get_db_connection()
    jobs = conn.execute("SELECT id, title FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([{'id': j['id'], 'title': j['title']} for j in jobs])

@app.route('/job/<int:job_id>', methods=['GET'])
def get_job(job_id):
    conn = db.get_db_connection()
    job = conn.execute("SELECT id, title, description FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify({'id': job['id'], 'title': job['title'], 'description': job['description']})

@app.route('/update_job/<int:job_id>', methods=['POST'])
def update_job(job_id):
    title = request.form.get('job_title')
    description = request.form.get('job_desc')
    if not title or not description:
        return jsonify({'error': 'Missing title or description'}), 400
    conn = db.get_db_connection()
    conn.execute("UPDATE jobs SET title = ?, description = ? WHERE id = ?", (title, description, job_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job updated successfully'})

@app.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    conn = db.get_db_connection()
    # Delete associated scores automatically due to cascade
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Job deleted successfully'})

@app.route('/delete_candidate/<int:resume_id>', methods=['DELETE'])
def delete_candidate(resume_id):
    try:
        conn = db.get_db_connection()
        # Delete scores first (if no cascade)
        conn.execute("DELETE FROM scores WHERE resume_id = ?", (resume_id,))
        # Then delete resume
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Candidate deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)