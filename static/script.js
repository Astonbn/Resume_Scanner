let currentJobId = null;
let candidates = [];
let currentScheduleResumeId = null;

// Helper: Show selected section
function showSection(sectionId) {
    document.querySelectorAll('.content section').forEach(section => section.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
}

// Escape HTML
function escapeHtml(str) {
    if (!str) return '';
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
                select.innerHTML += `<option value="${job.id}">${escapeHtml(job.title)}</option>`;
            });
        }
    } catch (err) {
        console.error('Error loading jobs:', err);
        select.innerHTML = '<option value="">Error loading jobs</option>';
    }
}

// Load jobs list for display
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

// Edit job
async function editJob(jobId) {
    try {
        const response = await axios.get(`/job/${jobId}`);
        const job = response.data;
        document.getElementById('jobTitle').value = job.title;
        document.getElementById('jobEducation').value = job.education || '';
        document.getElementById('jobSkills').value = job.skills || '';
        document.getElementById('jobExperience').value = job.experience || '';
        document.getElementById('jobLicences').value = job.licences || '';
        document.getElementById('jobOther').value = job.other || '';
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
        loadJobsList();
        loadJobs();
        if (currentJobId == jobId) {
            currentJobId = null;
            document.getElementById('jobSelect').value = '';
        }
    } catch (err) {
        console.error('Error deleting job:', err);
        alert('Failed to delete job.');
    }
}

// Job form submit
document.getElementById('jobForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('jobTitle').value;
    const education = document.getElementById('jobEducation').value;
    const skills = document.getElementById('jobSkills').value;
    const experience = document.getElementById('jobExperience').value;
    const licences = document.getElementById('jobLicences').value;
    const other = document.getElementById('jobOther').value;
    const editId = document.getElementById('editJobId').value;

    const formData = new FormData();
    formData.append('job_title', title);
    formData.append('job_education', education);
    formData.append('job_skills', skills);
    formData.append('job_experience', experience);
    formData.append('job_licences', licences);
    formData.append('job_other', other);

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
        document.getElementById('jobEducation').value = '';
        document.getElementById('jobSkills').value = '';
        document.getElementById('jobExperience').value = '';
        document.getElementById('jobLicences').value = '';
        document.getElementById('jobOther').value = '';
        loadJobsList();
        loadJobs();
    } catch (err) {
        console.error('Error saving job:', err);
        alert('Error saving job');
    }
});

// File upload
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => uploadFiles(fileInput.files));

async function uploadFiles(files) {
    const jobId = document.getElementById('jobSelect').value;
    if (!jobId) {
        alert('Please select a job first.');
        return;
    }
    const formData = new FormData();
    for (let file of files) formData.append('resumes', file);
    formData.append('job_id', jobId);
    try {
        const response = await axios.post('/upload_resumes', formData);
        const uploaded = response.data.resumes;
        let message = `${uploaded.length} resumes uploaded.`;
        const duplicates = uploaded.filter(r => r.is_duplicate);
        if (duplicates.length) message += ` Warning: ${duplicates.length} duplicate(s) detected.`;
        document.getElementById('uploadStatus').innerHTML = `<p>${message}</p>`;
    } catch (err) {
        alert('Upload failed: ' + (err.response?.data?.error || err.message));
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
        alert('Analysis failed: ' + (err.response?.data?.error || err.message));
    }
});

// Fetch results
async function fetchResults(jobId) {
    const response = await axios.get(`/results/${jobId}`);
    candidates = response.data;
    renderResultsTable(candidates);
    fetchAnalytics(jobId);
}

// Render table
function renderResultsTable(data) {
    const minScore = parseInt(document.getElementById('minScore').value);
    const skillFilter = document.getElementById('skillFilter').value.toLowerCase();
    const filtered = data.filter(c => c.score >= minScore && (skillFilter === '' || c.matched_skills.some(s => s.toLowerCase().includes(skillFilter))));
    const tbody = document.querySelector('#resultsTable tbody');
    tbody.innerHTML = '';
    filtered.forEach(c => {
        const row = tbody.insertRow();

        // Checkbox (col 0)
        const cbCell = row.insertCell(0);
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.className = 'candidate-checkbox';
        cb.dataset.id = c.resume_id;
        cbCell.appendChild(cb);

        // Candidate name (col 1)
        row.insertCell(1).innerText = c.filename;

        // Score (col 2)
        row.insertCell(2).innerText = c.score;

        // Matched skills (col 3)
        const matchedCell = row.insertCell(3);
        const matchedSkills = c.matched_skills || [];
        matchedCell.innerHTML = matchedSkills.map(s => `<span class="skill-tag">${escapeHtml(s)}</span>`).join(' ') || '—';

        // Missing skills (col 4)
        const missingCell = row.insertCell(4);
        const missingSkills = c.missing_skills || [];
        missingCell.innerHTML = missingSkills.map(s => `<span class="skill-tag missing">${escapeHtml(s)}</span>`).join(' ') || '—';

        // Experience match (col 5)
        const expCell = row.insertCell(5);
        expCell.innerHTML = c.experience_match ? '✅ Yes' : '❌ No';

        // Education match (col 6)
        const eduCell = row.insertCell(6);
        eduCell.innerHTML = c.education_match ? '✅ Yes' : '❌ No';

        // Licence match (col 7)
        const licCell = row.insertCell(7);
        licCell.innerHTML = c.licence_match ? '✅ Yes' : '❌ No';

        // Status dropdown (col 8)
        const statusCell = row.insertCell(8);
        const statusSelect = document.createElement('select');
        statusSelect.className = 'status-select';
        statusSelect.dataset.id = c.resume_id;
        ['pending', 'shortlisted', 'rejected', 'interview'].forEach(s => {
            const option = document.createElement('option');
            option.value = s;
            option.text = s.charAt(0).toUpperCase() + s.slice(1);
            if (c.status === s) option.selected = true;
            statusSelect.appendChild(option);
        });
        statusSelect.addEventListener('change', async () => {
            await updateCandidateStatus(c.resume_id, statusSelect.value, null);
        });
        statusCell.appendChild(statusSelect);

        // Notes (col 9)
        const notesCell = row.insertCell(9);
        const notesDiv = document.createElement('div');
        notesDiv.className = 'notes-display';
        notesDiv.textContent = c.notes || '';
        const editNotesBtn = document.createElement('button');
        editNotesBtn.textContent = 'Edit';
        editNotesBtn.className = 'edit-notes-btn';
        editNotesBtn.dataset.id = c.resume_id;
        editNotesBtn.addEventListener('click', () => {
            const newNotes = prompt('Edit notes:', c.notes || '');
            if (newNotes !== null) updateCandidateStatus(c.resume_id, c.status, newNotes);
        });
        notesCell.appendChild(notesDiv);
        notesCell.appendChild(editNotesBtn);

        // Actions (col 10)
        const actionsCell = row.insertCell(10);
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.className = 'delete-candidate-btn';
        deleteBtn.dataset.id = c.resume_id;
        deleteBtn.addEventListener('click', async () => {
            console.log("Deleting resume_id:", c.resume_id); // Debug log
            if (confirm(`Delete candidate "${c.filename}"?`)) await deleteCandidate(c.resume_id);
        });
        actionsCell.appendChild(deleteBtn);
        const scheduleBtn = document.createElement('button');
        scheduleBtn.textContent = 'Schedule Interview';
        scheduleBtn.className = 'schedule-interview-btn';
        scheduleBtn.dataset.id = c.resume_id;
        scheduleBtn.addEventListener('click', () => openScheduleModal(c.resume_id, c.filename));
        actionsCell.appendChild(scheduleBtn);
    });
    document.getElementById('scoreValue').innerText = minScore;
}

// Update candidate status
async function updateCandidateStatus(resumeId, status, notes) {
    try {
        await axios.post('/candidate_status', { resume_id: resumeId, job_id: currentJobId, status, notes });
        if (currentJobId) await fetchResults(currentJobId);
    } catch (err) {
        console.error('Error updating status:', err);
        alert('Failed to update status.');
    }
}

// Delete single candidate
async function deleteCandidate(resumeId) {
    try {
        await axios.delete(`/delete_candidate/${resumeId}`);
        if (currentJobId) {
            await fetchResults(currentJobId);
            await fetchAnalytics(currentJobId);
        }
    } catch (err) {
        console.error('Error deleting candidate:', err);
        alert('Failed to delete candidate.');
    }
}

// Bulk actions
async function bulkAction(action, status = null) {
    const checkboxes = document.querySelectorAll('.candidate-checkbox:checked');
    if (checkboxes.length === 0) { alert('Please select at least one candidate.'); return; }
    const resumeIds = Array.from(checkboxes).map(cb => cb.dataset.id);
    if (action === 'delete') {
        if (!confirm(`Delete ${resumeIds.length} candidate(s)?`)) return;
        try {
            await axios.post('/bulk_delete', { resume_ids: resumeIds });
            await fetchResults(currentJobId);
        } catch (err) { alert('Bulk delete failed.'); }
    } else if (action === 'status') {
        if (!status) return;
        try {
            await axios.post('/bulk_status', { resume_ids: resumeIds, job_id: currentJobId, status, notes: '' });
            await fetchResults(currentJobId);
        } catch (err) { alert('Bulk status update failed.'); }
    } else if (action === 'export') {
        const selectedCandidates = candidates.filter(c => resumeIds.includes(String(c.resume_id)));
        exportCandidatesToCSV(selectedCandidates);
    }
}

function exportCandidatesToCSV(candidatesToExport) {
    // CSV header without Explanation column
    let csv = "Candidate,Score,Matched Skills,Missing Skills,Experience Match,Education Match,Licence Match,Status,Notes\n";
    candidatesToExport.forEach(c => {
        csv += `"${c.filename}",${c.score},"${c.matched_skills.join(', ')}","${c.missing_skills.join(', ')}",`;
        csv += `${c.experience_match ? "Yes" : "No"},${c.education_match ? "Yes" : "No"},${c.licence_match ? "Yes" : "No"},`;
        csv += `"${c.status}","${c.notes || ''}"\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'selected_candidates.csv';
    a.click();
    URL.revokeObjectURL(a.href);
}

// Export all visible
document.getElementById('exportBtn').addEventListener('click', () => {
    const minScore = parseInt(document.getElementById('minScore').value);
    const skillFilter = document.getElementById('skillFilter').value.toLowerCase();
    const filtered = candidates.filter(c => c.score >= minScore && (skillFilter === '' || c.matched_skills.some(s => s.toLowerCase().includes(skillFilter))));
    exportCandidatesToCSV(filtered);
});

// Bulk buttons
document.getElementById('bulkShortlist').addEventListener('click', () => bulkAction('status', 'shortlisted'));
document.getElementById('bulkReject').addEventListener('click', () => bulkAction('status', 'rejected'));
document.getElementById('bulkDelete').addEventListener('click', () => bulkAction('delete'));
document.getElementById('bulkExportCSV').addEventListener('click', () => bulkAction('export'));

// Open schedule modal
function openScheduleModal(resumeId, filename) {
    currentScheduleResumeId = resumeId;
    document.getElementById('modalCandidateName').innerText = filename;
    document.getElementById('interviewDate').value = '';
    document.getElementById('interviewTime').value = '';
    document.getElementById('interviewNotes').value = '';
    document.getElementById('scheduleModal').style.display = 'block';
}

// Modal close handlers
document.querySelector('#scheduleModal .close').addEventListener('click', () => {
    document.getElementById('scheduleModal').style.display = 'none';
});
window.addEventListener('click', (event) => {
    const modal = document.getElementById('scheduleModal');
    if (event.target === modal) modal.style.display = 'none';
});

// Submit interview
document.getElementById('submitInterviewBtn').addEventListener('click', async () => {
    const date = document.getElementById('interviewDate').value;
    const time = document.getElementById('interviewTime').value;
    const notes = document.getElementById('interviewNotes').value;

    if (!date || !time) {
        alert('Please select both date and time.');
        return;
    }
    if (!currentJobId) {
        alert('No job selected. Please select a job and run analysis first.');
        return;
    }
    try {
        const response = await axios.post('/schedule_interview', {
            resume_id: currentScheduleResumeId,
            job_id: currentJobId,
            date: date,
            time: time,
            notes: notes
        });
        alert('Interview invitation sent successfully!');
        document.getElementById('scheduleModal').style.display = 'none';
        if (currentJobId) await fetchResults(currentJobId);
    } catch (err) {
        console.error('Error scheduling interview:', err);
        alert('Failed to schedule interview: ' + (err.response?.data?.error || err.message));
    }
});

// Filters
document.getElementById('minScore').addEventListener('input', (e) => {
    document.getElementById('scoreValue').innerText = e.target.value;
    renderResultsTable(candidates);
});
document.getElementById('skillFilter').addEventListener('input', () => renderResultsTable(candidates));
document.getElementById('selectAll').addEventListener('change', (e) => {
    document.querySelectorAll('.candidate-checkbox').forEach(cb => cb.checked = e.target.checked);
});

// Analytics
async function fetchAnalytics(jobId) {
    try {
        const response = await axios.get(`/analytics/${jobId}`);
        const data = response.data;
        document.getElementById('analyticsData').innerHTML = `
            <p>Average Score: ${data.average_score.toFixed(2)}%</p>
            <p>Total Candidates: ${data.total_candidates}</p>
            <p>Shortlisted: ${data.status_counts?.shortlisted || 0}</p>
            <p>Rejected: ${data.status_counts?.rejected || 0}</p>
            <p>Interview Scheduled: ${data.status_counts?.interview || 0}</p>
        `;
        // Top Skills Chart
        const topSkillsCanvas = document.getElementById('topSkillsChart');
        if (topSkillsCanvas && data.top_skills && data.top_skills.length > 0) {
            if (window.topSkillsChart && typeof window.topSkillsChart.destroy === 'function') window.topSkillsChart.destroy();
            const ctx = topSkillsCanvas.getContext('2d');
            window.topSkillsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.top_skills.map(s => s.name),
                    datasets: [{ label: 'Occurrences', data: data.top_skills.map(s => s.count), backgroundColor: '#4caf50' }]
                }
            });
        } else if (topSkillsCanvas) {
            const parent = topSkillsCanvas.parentElement;
            if (parent) parent.innerHTML = '<p class="no-data-message">No skills data available.</p>';
        }
        // Score distribution
        const distCanvas = document.getElementById('scoreDistribution');
        if (distCanvas && data.scores && data.scores.length > 0) {
            if (window.scoreDistChart && typeof window.scoreDistChart.destroy === 'function') window.scoreDistChart.destroy();
            const bins = [0, 20, 40, 60, 80, 100];
            const counts = new Array(bins.length - 1).fill(0);
            data.scores.forEach(score => {
                for (let i = 0; i < bins.length - 1; i++) {
                    if (score >= bins[i] && score < bins[i+1]) { counts[i]++; break; }
                }
            });
            const labels = bins.slice(0, -1).map((b, i) => `${b}-${bins[i+1]}`);
            const ctx = distCanvas.getContext('2d');
            window.scoreDistChart = new Chart(ctx, {
                type: 'bar',
                data: { labels, datasets: [{ label: 'Number of Candidates', data: counts, backgroundColor: '#3b82f6' }] }
            });
        } else if (distCanvas) {
            const parent = distCanvas.parentElement;
            if (parent) parent.innerHTML = '<p class="no-data-message">Score distribution will appear after analysis.</p>';
        }
    } catch (err) {
        console.error('Error fetching analytics:', err);
        document.getElementById('analyticsData').innerHTML = '<p class="error-message">Failed to load analytics.</p>';
    }
}

// Event delegation for job edit/delete
document.getElementById('jobsList').addEventListener('click', async (e) => {
    if (e.target.classList.contains('edit-job-btn')) await editJob(e.target.dataset.id);
    if (e.target.classList.contains('delete-job-btn')) await deleteJob(e.target.dataset.id);
});

// Set currentJobId when job is selected from dropdown (important for scheduling)
document.getElementById('jobSelect').addEventListener('change', (e) => {
    if (e.target.value) {
        currentJobId = e.target.value;
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadJobs();
    loadJobsList();
});

deleteBtn.addEventListener('click', async () => {
    console.log("Deleting resume_id:", c.resume_id);
    if (confirm(`Delete candidate "${c.filename}"?`)) await deleteCandidate(c.resume_id);
});