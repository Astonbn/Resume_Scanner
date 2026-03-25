import os
import random
import pandas as pd

# Create folders if they don't exist
os.makedirs("uploads/resumes", exist_ok=True)
os.makedirs("uploads/jobs", exist_ok=True)

# Sample skills, degrees, job titles
skills_pool = [
    "Python", "Java", "SQL", "Machine Learning", "Data Analysis",
    "Project Management", "Communication", "Leadership", "AWS", "Docker",
    "React", "JavaScript", "HTML/CSS", "C++", "TensorFlow"
]
degrees = ["B.Sc. Computer Science", "M.Sc. Data Science", "B.E. Electronics", "MBA", "Ph.D. AI"]
companies = ["Google", "Microsoft", "Amazon", "Facebook", "Tesla", "IBM", "Accenture"]

def generate_resume(i):
    name = f"Candidate_{i}"
    skills = random.sample(skills_pool, k=random.randint(3, 8))
    experience = f"{random.randint(1, 10)} years in {random.choice(skills)}"
    education = random.choice(degrees)
    text = f"""
    Name: {name}
    Skills: {', '.join(skills)}
    Experience: {experience}
    Education: {education}
    Worked at {random.choice(companies)} for {random.randint(1,5)} years.
    Achieved {random.choice(['increased efficiency', 'led team', 'won award'])}.
    """
    # Save as .txt (simulate resume file)
    with open(f"uploads/resumes/resume_{i}.txt", "w") as f:
        f.write(text)

def generate_job_description(i):
    title = f"Job Title: {random.choice(['Data Scientist', 'Software Engineer', 'Project Manager', 'AI Engineer'])}"
    required_skills = random.sample(skills_pool, k=random.randint(4, 6))
    description = f"""
    {title}
    Required Skills: {', '.join(required_skills)}
    Experience: {random.randint(2, 8)} years
    Education: {random.choice(degrees)}
    Responsibilities: Develop and deploy solutions.
    """
    with open(f"uploads/jobs/job_{i}.txt", "w") as f:
        f.write(description)

# Generate 20 resumes
for i in range(1, 21):
    generate_resume(i)

# Generate 5 job descriptions
for i in range(1, 6):
    generate_job_description(i)

print("Synthetic data generated.")