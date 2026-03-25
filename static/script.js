let currentJobId = null;
let candidates = [];

// Helper: Show selected section
function showSection(sectionId) {
    document.querySelectorAll('.content section').forEach(section => section.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
}

// Escape HTML to prevent XSS
function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Load jobs dropdown
async function loadJobs() {
    const select = document.getElementById('jobSelect');
    select.innerHTML = '<option value="">Loading jobs...</option>';
    try {
        const response = await axios.get('/jobs');
        const jobs = response.data;
        if (jobs.length === 0) {
            select.innerHTML = '<option value="">No jobs available. Create one first.</option>';
        } else {
            select.innerHTML = '<option value="">Select a job</option>';
            jobs.forEach(job => {
                select.innerHTML += `<option value="${job.id}">${job.title}</option>`;
            });
        }
    } catch (err) {
        console.error('Error loading jobs:', err);
        select.innerHTML = '<option value="">Error loading jobs</option>';
    }
}

// Load jobs list for display (separate from dropdown)
async function loadJobsList() {
    try {
        const response = await axios.get('/jobs');
        const jobs = response.data;
        const container = document.getElementById('jobsList');
        if (!container) return;

        if (jobs.length === 0) {
            container.innerHTML = '<p>No jobs saved yet.</p>';
            return;
        }

        let html = '<ul class="job-list">';
        jobs.forEach(job => {
            html += `
                <li data-job-id="${job.id}">
                    <strong>${escapeHtml(job.title)}</strong>
                    <button class="edit-job-btn" data-id="${job.id}">Edit</button>
                    <button class="delete-job-btn" data-id="${job.id}">Delete</button>
                </li>
            `;
        });
        html += '</ul>';
        container.innerHTML = html;
    } catch (err) {
        console.error('Error loading jobs list:', err);
        document.getElementById('jobsList').innerHTML = '<p>Error loading jobs.</p>';
    }
}

// Use event delegation on the container that is always present
document.getElementById('jobsList').addEventListener('click', async (e) => {
    const target = e.target;
    if (target.classList.contains('edit-job-btn')) {
        const jobId = target.getAttribute('data-id');
        await editJob(jobId);
    } else if (target.classList.contains('delete-job-btn')) {
        const jobId = target.getAttribute('data-id');
        await deleteJob(jobId);
    }
});

// Edit job: populate form with job details
async function editJob(jobId) {
    try {
        const response = await axios.get(`/job/${jobId}`);
        const job = response.data;
        document.getElementById('jobTitle').value = job.title;
        document.getElementById('jobDesc').value = job.description;
        document.getElementById('editJobId').value = job.id;
        const saveBtn = document.querySelector('#jobForm button[type="submit"]');
        saveBtn.textContent = 'Update Job';
    } catch (err) {
        console.error('Error fetching job:', err);
        alert('Could not load job details.');
    }
}

// Delete job
async function deleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this job? All associated scores will be removed.')) return;
    try {
        await axios.post(`/delete_job/${jobId}`);
        loadJobsList();    // refresh list
        loadJobs();        // refresh dropdown
        if (currentJobId == jobId) {
            currentJobId = null;
            document.getElementById('jobSelect').value = '';
        }
    } catch (err) {
        console.error('Error deleting job:', err);
        alert('Failed to delete job.');
    }
}

// Handle job form submission (create or update)
document.getElementById('jobForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('jobTitle').value;
    const desc = document.getElementById('jobDesc').value;
    const editId = document.getElementById('editJobId').value;
    const formData = new FormData();
    formData.append('job_title', title);
    formData.append('job_desc', desc);
    try {
        if (editId) {
            await axios.post(`/update_job/${editId}`, formData);
            document.getElementById('jobMessage').innerHTML = '<p>Job updated successfully.</p>';
            document.getElementById('editJobId').value = '';
            document.querySelector('#jobForm button[type="submit"]').textContent = 'Save Job';
        } else {
            const response = await axios.post('/upload_job', formData);
            document.getElementById('jobMessage').innerHTML = `<p>Job saved with ID ${response.data.job_id}</p>`;
        }
        // Reset form
        document.getElementById('jobTitle').value = '';
        document.getElementById('jobDesc').value = '';
        loadJobsList();
        loadJobs();
    } catch (err) {
        console.error('Error saving job:', err);
        alert('Error saving job');
    }
});

// File upload via drag & drop
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    uploadFiles(files);
});
fileInput.addEventListener('change', () => uploadFiles(fileInput.files));

async function uploadFiles(files) {
    const jobId = document.getElementById('jobSelect').value;
    if (!jobId) {
        alert('Please select a job first.');
        return;
    }
    const formData = new FormData();
    for (let file of files) {
        formData.append('resumes', file);
    }
    formData.append('job_id', jobId);
    try {
        const response = await axios.post('/upload_resumes', formData);
        document.getElementById('uploadStatus').innerHTML = `<p>${response.data.resumes.length} resumes uploaded.</p>`;
    } catch (err) {
        alert('Upload failed: ' + err.response.data.error);
    }
}

// Run analysis
document.getElementById('analyzeBtn').addEventListener('click', async () => {
    const jobId = document.getElementById('jobSelect').value;
    if (!jobId) {
        alert('Select a job first.');
        return;
    }
    currentJobId = jobId;
    try {
        await axios.post(`/analyze/${jobId}`);
        alert('Analysis complete!');
        fetchResults(jobId);
    } catch (err) {
        alert('Analysis failed: ' + err.response.data.error);
    }
});

// Fetch and display results
async function fetchResults(jobId) {
    const response = await axios.get(`/results/${jobId}`);
    candidates = response.data;
    renderResultsTable(candidates);
    fetchAnalytics(jobId);
}

// Render table with filters
function renderResultsTable(data) {
    const minScore = parseInt(document.getElementById('minScore').value);
    const skillFilter = document.getElementById('skillFilter').value.toLowerCase();
    const filtered = data.filter(c => c.score >= minScore && (skillFilter === '' || c.matched_skills.some(s => s.toLowerCase().includes(skillFilter))));
    const tbody = document.querySelector('#resultsTable tbody');
    tbody.innerHTML = '';
    filtered.forEach(c => {
        const row = tbody.insertRow();
        row.insertCell(0).innerText = c.filename;
        row.insertCell(1).innerText = c.score;
        row.insertCell(2).innerHTML = c.matched_skills.join(', ');
        // Actions cell
        const actionsCell = row.insertCell(3);
        const deleteBtn = document.createElement('button');
        deleteBtn.innerText = 'Delete';
        deleteBtn.className = 'delete-candidate-btn';
        deleteBtn.setAttribute('data-id', c.resume_id);
        deleteBtn.addEventListener('click', async () => {
            if (confirm(`Delete candidate "${c.filename}"? This action cannot be undone.`)) {
                await deleteCandidate(c.resume_id);
            }
        });
        actionsCell.appendChild(deleteBtn);
    });
    // Update score filter display
    document.getElementById('scoreValue').innerText = minScore;
}
async function deleteCandidate(resumeId) {
    try {
        await axios.delete(`/delete_candidate/${resumeId}`);
        // After deletion, refresh results and analytics
        if (currentJobId) {
            await fetchResults(currentJobId);
            await fetchAnalytics(currentJobId);
        }
    } catch (err) {
        console.error('Error deleting candidate:', err);
        alert('Failed to delete candidate.');
    }
}

document.getElementById('minScore').addEventListener('input', (e) => {
    document.getElementById('scoreValue').innerText = e.target.value;
    renderResultsTable(candidates);
});
document.getElementById('skillFilter').addEventListener('input', () => renderResultsTable(candidates));

// Export CSV
document.getElementById('exportBtn').addEventListener('click', () => {
    let csv = "Candidate,Score,Matched Skills\n";
    candidates.forEach(c => {
        csv += `"${c.filename}",${c.score},"${c.matched_skills.join(', ')}"\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'candidates.csv';
    a.click();
    URL.revokeObjectURL(a.href);
});

// Fetch and render analytics
async function fetchAnalytics(jobId) {
    const response = await axios.get(`/analytics/${jobId}`);
    const data = response.data;
    document.getElementById('analyticsData').innerHTML = `
        <p>Average Score: ${data.average_score.toFixed(2)}%</p>
        <p>Total Candidates: ${data.total_candidates}</p>
    `;
    // Top skills chart
    const ctx = document.getElementById('topSkillsChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.top_skills.map(s => s.name),
            datasets: [{ label: 'Occurrences', data: data.top_skills.map(s => s.count), backgroundColor: '#4caf50' }]
        }
    });
    // Score distribution (mock; you can compute from scores)
    // For simplicity, we skip distribution; can add later.
}

// Event delegation for edit/delete buttons (handles dynamic buttons)
document.getElementById('jobsList').addEventListener('click', async (e) => {
    const target = e.target;
    if (target.classList.contains('edit-job')) {
        const jobId = target.getAttribute('data-id');
        editJob(jobId);
    } else if (target.classList.contains('delete-job')) {
        const jobId = target.getAttribute('data-id');
        deleteJob(jobId);
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadJobs();
    loadJobsList();
});