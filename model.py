import re
import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Download stopwords if not already
nltk.download('stopwords')
from nltk.corpus import stopwords

stop_words = set(stopwords.words('english'))

def clean_text(text):
    """Basic text cleaning: lower, remove punctuation, remove stopwords."""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    tokens = text.split()
    tokens = [word for word in tokens if word not in stop_words]
    return ' '.join(tokens)

def extract_skills(text):
    """Simple skill extraction using a predefined list (can be enhanced)."""
    skills_pool = ["python", "java", "sql", "machine learning", "data analysis",
                   "project management", "communication", "leadership", "aws", "docker",
                   "react", "javascript", "html/css", "c++", "tensorflow"]
    text_lower = text.lower()
    found = [skill for skill in skills_pool if skill in text_lower]
    return found

class ResumeMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.jd_vector = None

    def fit_job(self, job_description):
        """Fit vectorizer on job description and compute its TF-IDF vector."""
        cleaned_jd = clean_text(job_description)
        self.jd_vector = self.vectorizer.fit_transform([cleaned_jd])

    def score_resume(self, resume_text):
        """Score a single resume against the job description."""
        cleaned_resume = clean_text(resume_text)
        resume_vector = self.vectorizer.transform([cleaned_resume])
        similarity = cosine_similarity(resume_vector, self.jd_vector)[0][0]
        return round(similarity * 100, 2)   # percentage score