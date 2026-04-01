# 📄 Smart Resume Screener

An AI‑powered web application for Human Resource managers to automatically analyze, rank, and filter job applicants. It extracts key information from resumes (PDF, DOCX, TXT), matches them against a job description using NLP, and provides a ranked list with skill gap analysis, experience/education/licence matching, shortlisting, notes, interview scheduling, and email notifications.

![Dashboard Screenshot](screenshots/dashboard.png) *(Add your own screenshots)*

---

✨ Features

🧠 AI‑Powered Resume Matching
- **Text extraction** from PDF, DOCX, and TXT files.
- **Skill extraction** using a predefined skill list (easily extendable).
- **TF‑IDF + Cosine Similarity** to score candidates against job descriptions.
- **Skill gap analysis** – shows which skills the candidate has and which are missing.
- **Experience, Education, Licence matching** – intelligent parsing of years and degree levels.
- **Ranking explanation** – e.g., "Strong match: Python, Java. Missing: SQL".

👩‍💼 HR Workflow & Management
- **User authentication** (Flask‑Login) with roles: `admin` and `recruiter`.
- **Structured job creation** – separate fields for education, skills, experience, licences, other requirements.
- **Shortlisting, rejection, interview scheduling** – per‑candidate status with notes.
- **Email notifications** – automated emails when status changes (shortlisted/rejected).
- **Bulk actions** – shortlist, reject, delete, or export multiple candidates at once.
- **Candidate notes** – private notes for each application.

 📊 Analytics & Reporting
- **Top skills chart** – most frequent skills among candidates.
- **Score distribution chart** – how candidates are spread across score ranges.
- **Status counts** – number of pending, shortlisted, rejected, interviewed.
- **Export to CSV** – filtered or selected candidates.

🔍 Duplicate Detection
- Prevents duplicate resume uploads by comparing text hashes.
- Groups duplicates together so they don't clutter the list.

🗓️ Interview Scheduling
- HR can schedule an interview from the candidate row.
- Candidate receives an email with date, time, and notes.
- Status automatically updates to "interview".

---

🛠️ Technology Stack

| Component       | Technology                                                                 |
|-----------------|----------------------------------------------------------------------------|
| **Backend**     | Python 3.11+, Flask, Flask‑Login, Flask‑Mail, SQLite3                      |
| **AI/ML**       | scikit‑learn (TF‑IDF, Cosine Similarity), NLTK                             |
| **Frontend**    | HTML5, CSS3, JavaScript, Chart.js, Axios                                   |
| **File Parsing**| pdfplumber (PDF), python-docx (DOCX), built‑in for TXT                     |

---
 📋 Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (optional, for cloning)

---

 🚀 Installation & Setup

1. **Clone the repository** (or download the source):
   ```bash
   git clone https://github.com/Astonbn/Resume_Scanner.git
   cd smart-resume-screener
