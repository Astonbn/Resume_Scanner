Smart Resume Screener
A full-stack web application that uses Natural Language Processing (NLP) to automatically analyze, rank, and filter job applicants. Built for Human Resource managers to streamline the recruitment process.

🚀 Features
Job Description Management – Create, edit, and delete job postings with bullet‑point requirements.

Resume Upload – Drag & drop multiple resumes (PDF, DOCX, TXT) for batch processing.

AI-Powered Matching – Uses TF‑IDF vectorization and cosine similarity to score candidates against a job description.

Ranked Candidates Table – View candidates sorted by match score, with matched skills highlighted.

Filtering – Filter by minimum score or skill keywords.

Analytics Dashboard – See average score, top skills among candidates, and total applicants.

Export Results – Download candidate list as a CSV file.

Delete Candidates – Remove candidates from the system and associated scores.

Modern UI – Responsive dashboard with glassmorphism effects, charts, and smooth interactions.

🛠️ Tech Stack
Layer	Technologies
Frontend	HTML, CSS (custom), JavaScript, Chart.js, Axios
Backend	Python, Flask
AI/ML	scikit-learn (TF‑IDF, Cosine Similarity), NLTK (stopwords, tokenization)
Database	SQLite (with foreign key cascades)
File Parsing	pdfplumber (PDF), python-docx (DOCX)

🎯 Usage Walkthrough
Add a Job – Go to the Job Description section, enter a title and bullet‑point requirements, and click Save Job.

Upload Resumes – In the Upload Resumes section, select a job from the dropdown, then drag & drop or click to select files (PDF/DOCX/TXT). The system extracts text, skills, experience, and education.

Run Analysis – Click Run Analysis to score all uploaded resumes against the selected job. Scores appear in the Ranked Candidates table.

Filter & Export – Use the sliders and skill filter to narrow results, then click Export CSV to download the list.

Manage Candidates – Delete candidates directly from the table if needed.

Analytics – Switch to the Analytics tab to view average score, top skills among applicants, and total candidates.

🧠 How the AI Matching Works
Text Preprocessing – Lowercasing, punctuation removal, stopword elimination (using NLTK).

TF‑IDF Vectorization – Converts job description and resumes into numerical vectors.

Cosine Similarity – Measures the angle between vectors; higher similarity = higher relevance.

Skill Matching – A simple list of skills is extracted from the resume text and compared with the job description for display purposes.

The model can be extended with BERT or other embeddings for semantic understanding.

🚧 Future Enhancements
Advanced AI: Replace TF‑IDF with BERT or Sentence Transformers.

Shortlisting: Allow HR to mark candidates as shortlisted/interviewed.

Email Integration: Send automated emails to candidates.

Keyword Highlighting: Show matched terms inside a resume preview.

Authentication: Multi‑user support with roles.

Cloud Storage: Store uploaded files in S3.

Background Processing: Use Celery for large batch uploads