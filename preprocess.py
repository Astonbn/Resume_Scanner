import re
import nltk
from nltk.corpus import stopwords

# Download stopwords if not already done
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Predefined skill list (can be expanded or loaded from a file)
SKILLS_LIST = [
    "python", "java", "sql", "machine learning", "data analysis",
    "project management", "communication", "leadership", "aws", "docker",
    "react", "javascript", "html/css", "c++", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "excel", "power bi", "tableau"
]

def clean_text(text):
    """
    Basic text cleaning: lowercase, remove punctuation, remove stopwords.
    """
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # keep only letters and spaces
    tokens = text.split()
    tokens = [word for word in tokens if word not in stop_words]
    return ' '.join(tokens)

def extract_skills(text):
    """
    Extract skills from resume text using a predefined list.
    Returns a list of matched skills.
    """
    text_lower = text.lower()
    found = [skill for skill in SKILLS_LIST if skill in text_lower]
    return list(set(found))  # remove duplicates

def extract_experience(text):
    """
    Extract years of experience using regex.
    Returns a string like "5 years" or "Not specified".
    """
    # Look for patterns like "5 years", "3+ years", "5-7 years", etc.
    pattern = r'(\d+)\s*(?:-|\+)?\s*years?'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        # Take the first numeric value found
        return f"{matches[0]} years"
    return "Not specified"

def extract_education(text):
    """
    Extract education degree from text using a list of common degree keywords.
    Returns the degree title or "Not specified".
    """
    degrees = [
        "b.sc", "m.sc", "b.e", "m.e", "phd", "bachelor", "master", "mba",
        "b.tech", "m.tech", "bca", "mca", "b.com", "m.com", "b.a", "m.a"
    ]
    text_lower = text.lower()
    for deg in degrees:
        if deg in text_lower:
            return deg.upper()  # return in uppercase for consistency
    return "Not specified"