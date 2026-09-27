// =========================================================================
//  Infosys HR Onboarding System — Frontend Orchestrator & Client Engine
// =========================================================================

const API = '/api';
let currentUser = null;
let allEmployeesCache = [];
let allAssetsCache = [];
let parsedCandidatesCache = [];
let activeUploadTarget = null; // { empId, docType }
window.charts = {};

document.addEventListener('DOMContentLoaded', () => {
    initDefaultDates();
    checkAuth();
    startClock();
    setInterval(checkServerStatus, 15000);

    // Form Submissions
    document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
    document.getElementById('logoutBtn')?.addEventListener('click', logout);
    document.getElementById('registerForm')?.addEventListener('submit', handleRegistration);

    // Global File Upload input listener
    document.getElementById('globalFileInput')?.addEventListener('change', handleFileSelected);

    // Sidebar Navigation
    document.querySelectorAll('.sidebar-nav li').forEach(item => {
        item.addEventListener('click', (e) => {
            const targetLi = e.target.closest('li');
            if (!targetLi) return;
            document.querySelectorAll('.sidebar-nav li').forEach(i => i.classList.remove('active'));
            targetLi.classList.add('active');
            const section = targetLi.dataset.section;
            showSection(section);
        });
    });

    // Filters for Employees table
    document.getElementById('empSearch')?.addEventListener('input', filterEmployeesTable);
    document.getElementById('empDeptFilter')?.addEventListener('change', filterEmployeesTable);

    // Filters for Assets table
    document.getElementById('assetTypeFilter')?.addEventListener('change', filterAssetsTable);
    document.getElementById('assetStatusFilter')?.addEventListener('change', filterAssetsTable);
});

function initDefaultDates() {
    // Set default DOJ to 14 days from today
    const dojInput = document.getElementById('regDOJ');
    if (dojInput && !dojInput.value) {
        const nextTwoWeeks = new Date();
        nextTwoWeeks.setDate(nextTwoWeeks.getDate() + 14);
        dojInput.value = nextTwoWeeks.toISOString().split('T')[0];
    }
}

// ═══════════════════════════════════════════════════════════════
//  AUTHENTICATION & SESSION (WITH QUICK LOGIN & RBAC)
// ═══════════════════════════════════════════════════════════════

async function checkAuth() {
    try {
        const res = await fetch(`${API}/me`);
        const data = await res.json();
        if (data.logged_in) {
            currentUser = data;
            applyUserSession(data);
            showDashboard();
        } else {
            showLogin();
        }
    } catch (e) {
        showLogin();
    }
}

function quickLogin(user, pass) {
    const userInput = document.getElementById('username');
    const passInput = document.getElementById('password');
    if (userInput) userInput.value = user;
    if (passInput) passInput.value = pass;
    doLogin(user, pass);
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    doLogin(username, password);
}

async function doLogin(username, password) {
    showLoadingOverlay('Authenticating with Infosys Directory...');
    try {
        const res = await fetch(`${API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (data.success) {
            currentUser = data.user;
            applyUserSession(data.user);
            showToast(`Welcome, ${data.user.name} (${data.user.role})!`, 'success');
            showDashboard();
        } else {
            showToast(data.error || 'Invalid corporate credentials', 'error');
        }
    } catch (err) {
        hideLoadingOverlay();
        showToast('Authentication server unreachable. Ensure python main.py is running.', 'error');
    }
}

async function logout() {
    try {
        await fetch(`${API}/logout`, { method: 'POST' });
    } catch (e) {}
    currentUser = null;
    showToast('Signed out successfully.', 'info');
    showLogin();
}

function applyUserSession(user) {
    const name = user.name || user.username || 'HR User';
    const role = user.role || 'HR Staff';
    const perms = user.permissions || {};

    const headerName = document.getElementById('headerUserName');
    const userDisp = document.getElementById('userDisplayName');
    const roleBadge = document.getElementById('userRoleBadge');
    if (headerName) headerName.innerText = name;
    if (userDisp) userDisp.innerText = name;
    if (roleBadge) roleBadge.innerText = role;

    // Enforce RBAC on navigation and action buttons
    const navRegister = document.getElementById('navRegister');
    const btnBatchImport = document.getElementById('btnBatchImport');
    const thSalary = document.getElementById('thSalary');

    if (navRegister) {
        navRegister.style.display = perms.can_register ? 'flex' : 'none';
    }
    if (btnBatchImport) {
        btnBatchImport.style.display = perms.can_register ? 'inline-flex' : 'none';
    }
    if (thSalary) {
        thSalary.style.display = perms.can_view_salary ? '' : 'none';
    }
}

function showLogin() {
    document.getElementById('loginSection')?.classList.remove('hidden');
    document.getElementById('mainSection')?.classList.add('hidden');
}

function showDashboard() {
    document.getElementById('loginSection')?.classList.add('hidden');
    document.getElementById('mainSection')?.classList.remove('hidden');
    showSection('dashboard');
}

// ═══════════════════════════════════════════════════════════════
//  NAVIGATION & SECTIONS
// ═══════════════════════════════════════════════════════════════

function showSection(name) {
    document.querySelectorAll('.content-section').forEach(sec => sec.classList.add('hidden'));
    const target = document.getElementById(name);
    if (target) target.classList.remove('hidden');

    const titles = {
        'dashboard': 'Executive Dashboard & Metrics',
        'register': 'Register New Employee (RPA Pipeline)',
        'excel-hub': 'Excel Data Hub & Bulk Onboarding',
        'employee-list': 'Employee Directory & Records',
        'documents': 'Document Management & Verification',
        'assets': 'IT Asset Tracking & Provisioning',
        'reports': 'Compliance & Audit Reports',
        'audit': 'System Audit Trail Log'
    };
    const titleEl = document.getElementById('sectionTitle');
    if (titleEl) titleEl.innerText = titles[name] || 'HR Portal';

    // Highlight sidebar item
    document.querySelectorAll('.sidebar-nav li').forEach(i => {
        if (i.dataset.section === name) {
            i.classList.add('active');
        } else {
            i.classList.remove('active');
        }
    });

    if (name === 'dashboard') loadStats();
    if (name === 'employee-list') loadEmployees();
    if (name === 'documents') populateDocEmployeeDropdown();
    if (name === 'assets') loadAssets();
    if (name === 'reports') loadReports();
    if (name === 'audit') loadAuditLog();
}

function openExcelHub() {
    showSection('excel-hub');
}

// ═══════════════════════════════════════════════════════════════
//  DASHBOARD & METRICS
// ═══════════════════════════════════════════════════════════════

async function loadStats() {
    try {
        const res = await fetch(`${API}/dashboard-stats`);
        if (res.status === 401) return checkAuth();
        const data = await res.json();

        const kpiTotal = document.getElementById('kpiTotal');
        const kpiComp = document.getElementById('kpiCompleted');
        const kpiProg = document.getElementById('kpiProgress');
        const kpiOffers = document.getElementById('kpiOffers');

        if (kpiTotal) kpiTotal.innerText = data.total ?? 0;
        if (kpiComp) kpiComp.innerText = data.completed ?? 0;
        if (kpiProg) kpiProg.innerText = data.onboarding ?? 0;
        if (kpiOffers) kpiOffers.innerText = data.offer_letters_sent ?? (data.completed ?? 0);

        renderCharts(data);
    } catch (e) {
        console.error('Failed to load dashboard statistics', e);
    }
}

function renderCharts(stats) {
    if (window.charts.monthly) { window.charts.monthly.destroy(); }
    if (window.charts.dept) { window.charts.dept.destroy(); }

    const monthlyTrend = stats.monthly_trend || { '2026-07': 2, '2026-08': 4, '2026-09': 6 };
    const monthLabels = Object.keys(monthlyTrend);
    const monthValues = Object.values(monthlyTrend);

    const ctxM = document.getElementById('monthlyChart')?.getContext('2d');
    if (ctxM) {
        window.charts.monthly = new Chart(ctxM, {
            type: 'bar',
            data: {
                labels: monthLabels.length ? monthLabels : ['Prior Months', 'Current Month'],
                datasets: [{
                    label: 'Onboarded Headcount',
                    data: monthValues.length ? monthValues : [2, 5],
                    backgroundColor: '#007CC3',
                    borderRadius: 4,
                    barPercentage: 0.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    const depts = stats.departments || { 'IT': 3, 'HR': 1, 'Engineering': 2 };
    const deptLabels = Object.keys(depts);
    const deptValues = Object.values(depts);

    const ctxD = document.getElementById('deptChart')?.getContext('2d');
    if (ctxD) {
        window.charts.dept = new Chart(ctxD, {
            type: 'doughnut',
            data: {
                labels: deptLabels,
                datasets: [{
                    data: deptValues,
                    backgroundColor: ['#007CC3', '#003366', '#FF6600', '#10B981', '#6366F1', '#F59E0B', '#EC4899']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } }
                }
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════
//  REGISTRATION STEPPER & WORKFLOW
// ═══════════════════════════════════════════════════════════════

let currentRegStep = 1;

function nextStep(step) {
    if (step === 2) {
        const fname = document.getElementById('regFName')?.value.trim();
        const lname = document.getElementById('regLName')?.value.trim();
        const email = document.getElementById('regEmail')?.value.trim();
        const phone = document.getElementById('regPhone')?.value.trim();
        const dob = document.getElementById('regDOB')?.value;
        if (!fname || !lname || !email || !phone || !dob) {
            return showToast('Please complete all required personal details marked with *', 'warning');
        }
    } else if (step === 3) {
        const role = document.getElementById('regRole')?.value.trim();
        const ctc = document.getElementById('regCTC')?.value;
        const doj = document.getElementById('regDOJ')?.value;
        if (!role || !ctc || !doj) {
            return showToast('Please complete all required job details marked with *', 'warning');
        }

        const fname = document.getElementById('regFName')?.value.trim();
        const lname = document.getElementById('regLName')?.value.trim();
        const email = document.getElementById('regEmail')?.value.trim();
        const phone = document.getElementById('regPhone')?.value.trim();
        const dob = document.getElementById('regDOB')?.value;
        const gender = document.getElementById('regGender')?.value;
        const dept = document.getElementById('regDept')?.value;
        const location = document.getElementById('regLocation')?.value;
        const manager = document.getElementById('regManager')?.value.trim() || 'HR Manager';
        const empType = document.getElementById('regEmpType')?.value;
        const sendOffer = document.getElementById('regSendOffer')?.checked;

        const rev = document.getElementById('reviewDetails');
        if (rev) {
            rev.innerHTML = `
                <table class="review-table">
                    <tr><td>Candidate Name:</td><td><strong>${fname} ${lname}</strong> (${gender})</td></tr>
                    <tr><td>Date of Birth:</td><td>${dob}</td></tr>
                    <tr><td>Email Address:</td><td><code>${email}</code></td></tr>
                    <tr><td>Contact Phone:</td><td>${phone}</td></tr>
                    <tr><td>Department:</td><td><strong>${dept}</strong></td></tr>
                    <tr><td>Job Role:</td><td>${role}</td></tr>
                    <tr><td>Annual CTC:</td><td><strong>₹ ${Number(ctc).toLocaleString('en-IN')}</strong></td></tr>
                    <tr><td>Date of Joining:</td><td>${doj}</td></tr>
                    <tr><td>Work Location:</td><td>${location}</td></tr>
                    <tr><td>Reporting Manager:</td><td>${manager}</td></tr>
                    <tr><td>Employment Type:</td><td>${empType}</td></tr>
                    <tr><td>Send Offer Email:</td><td>${sendOffer ? '✅ Yes (PDF attachment via automated email)' : '❌ No'}</td></tr>
                </table>
            `;
        }
    }

    document.getElementById(`step${currentRegStep}`)?.classList.add('hidden');
    document.getElementById(`stepIndicator${currentRegStep}`)?.classList.remove('active');

    currentRegStep = step;

    document.getElementById(`step${currentRegStep}`)?.classList.remove('hidden');
    document.getElementById(`stepIndicator${currentRegStep}`)?.classList.add('active');
}

async function handleRegistration(e) {
    e.preventDefault();

    const fname = document.getElementById('regFName').value.trim();
    const lname = document.getElementById('regLName').value.trim();
    const fullName = `${fname} ${lname}`.trim();

    const payload = {
        full_name: fullName,
        date_of_birth: document.getElementById('regDOB').value,
        gender: document.getElementById('regGender').value,
        email: document.getElementById('regEmail').value.trim(),
        phone: document.getElementById('regPhone').value.trim(),
        address: document.getElementById('regAddress').value.trim(),
        department: document.getElementById('regDept').value,
        designation: document.getElementById('regRole').value.trim(),
        salary: String(document.getElementById('regCTC').value),
        date_of_joining: document.getElementById('regDOJ').value,
        location: document.getElementById('regLocation').value,
        manager_name: document.getElementById('regManager').value.trim() || 'HR Manager',
        employment_type: document.getElementById('regEmpType').value,
        engine: document.getElementById('regEngine')?.value || 'uipath',
        send_offer: document.getElementById('regSendOffer').checked
    };

    const engineName = payload.engine === 'uipath' ? 'UiPath (.xaml) Workflow' : 'Python Orchestrator';
    showLoadingOverlay(`🤖 Executing ${engineName} Pipeline: ID Gen, Folders, Letter & Email...`);

    try {
        const res = await fetch(`${API}/onboard`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.status === 'Success') {
            const empId = data.employee_id || 'EMP';
            showToast(`🎉 Onboarding Successful! Assigned ID: ${empId}`, 'success');

            if (data.offer_email_sent) {
                showToast(`📧 Offer Letter PDF emailed to ${payload.email}`, 'info');
            }

            document.getElementById('registerForm')?.reset();
            initDefaultDates();
            nextStep(1);

            showSection('employee-list');
        } else {
            const errMsg = data.error || (data.errors && data.errors.join(', ')) || 'Onboarding failed validation';
            showToast(`❌ Error: ${errMsg}`, 'error');
        }
    } catch (err) {
        hideLoadingOverlay();
        showToast('Network error while executing onboarding workflow.', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
//  EXCEL DATA HUB & BATCH ONBOARDING
// ═══════════════════════════════════════════════════════════════

function downloadExcelTemplate() {
    window.location.href = `${API}/download-template`;
    showToast('📄 Downloading Employee Onboarding Excel Template...', 'info');
}

function exportEmployeesExcel() {
    window.location.href = `${API}/export-employees-excel`;
    showToast('📊 Exporting Master Employee Database to Excel...', 'info');
}

async function handleExcelFileSelected(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    showLoadingOverlay(`Parsing and validating employee records from ${file.name}...`);
    try {
        const res = await fetch(`${API}/upload-excel-preview`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            parsedCandidatesCache = data.candidates || [];
            displayExcelPreview(data);
            showToast(`✅ Successfully parsed ${data.total_rows} candidate rows!`, 'success');
        } else {
            showToast(data.error || 'Failed to parse Excel spreadsheet', 'error');
        }
    } catch (err) {
        hideLoadingOverlay();
        showToast('Network error while uploading Excel spreadsheet.', 'error');
    }
}

function displayExcelPreview(data) {
    const container = document.getElementById('excelPreviewContainer');
    const tbody = document.getElementById('excelPreviewTbody');
    const prevTotal = document.getElementById('prevTotal');
    const prevValid = document.getElementById('prevValid');
    const prevErrors = document.getElementById('prevErrors');
    const badge = document.getElementById('batchCountBadge');
    const btnLaunch = document.getElementById('btnLaunchBatch');

    if (!container || !tbody) return;

    container.classList.remove('hidden');
    prevTotal.innerText = data.total_rows || 0;
    prevValid.innerText = data.valid_count || 0;
    prevErrors.innerText = data.error_count || 0;
    if (badge) badge.innerText = data.valid_count || 0;

    if (btnLaunch) {
        btnLaunch.disabled = data.valid_count === 0;
    }

    const canViewSalary = currentUser?.permissions?.can_view_salary ?? true;

    tbody.innerHTML = (data.candidates || []).map((item, idx) => {
        const c = item.candidate;
        const isValid = item.is_valid;
        const errs = item.errors || [];
        const salaryText = canViewSalary
            ? `₹ ${Number(c.salary || 0).toLocaleString('en-IN')}`
            : 'Confidential';

        return `
            <tr class="${isValid ? '' : 'row-warning'}">
                <td><strong>#${c.row_number || idx + 1}</strong></td>
                <td><strong>${c.full_name || 'N/A'}</strong> <span class="text-muted">(${c.gender})</span></td>
                <td><code>${c.email || 'N/A'}</code></td>
                <td><span class="dept-badge">${c.department}</span></td>
                <td>${c.designation}</td>
                <td>${c.date_of_joining}</td>
                <td>${salaryText}</td>
                <td>
                    ${isValid
                        ? `<span class="badge success">✅ Ready to Onboard</span>`
                        : `<span class="badge danger" title="${errs.join(' | ')}">⚠️ ${errs[0] || 'Error'}</span>`
                    }
                </td>
            </tr>
        `;
    }).join('');

    container.scrollIntoView({ behavior: 'smooth' });
}

function cancelExcelPreview() {
    parsedCandidatesCache = [];
    const container = document.getElementById('excelPreviewContainer');
    const input = document.getElementById('excelFileInput');
    if (container) container.classList.add('hidden');
    if (input) input.value = '';
}

async function launchBatchOnboarding() {
    const validCandidates = parsedCandidatesCache.filter(item => item.is_valid);
    if (!validCandidates.length) {
        return showToast('No valid candidates found to onboard.', 'warning');
    }

    if (!confirm(`Are you sure you want to launch automated RPA onboarding for ${validCandidates.length} candidate(s)?\n\nThis will generate IDs, create folders, generate PDF letters, allocate hardware kits, and send welcome emails.`)) {
        return;
    }

    showLoadingOverlay(`🤖 RPA Robot executing batch onboarding for ${validCandidates.length} candidates...`);

    try {
        const res = await fetch(`${API}/batch-onboard`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidates: validCandidates })
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast(`🎉 Batch RPA Onboarding Complete: ${data.success_count} succeeded, ${data.failed_count} failed`, 'success');
            displayBatchResults(data);
            cancelExcelPreview();
            loadStats();
        } else {
            showToast(data.error || 'Batch onboarding failed.', 'error');
        }
    } catch (err) {
        hideLoadingOverlay();
        showToast('Network error while executing batch onboarding.', 'error');
    }
}

function displayBatchResults(data) {
    const container = document.getElementById('batchResultsContainer');
    const kpiGrid = document.getElementById('batchResultKpis');
    const tbody = document.getElementById('batchResultsTbody');

    if (!container || !kpiGrid || !tbody) return;

    container.classList.remove('hidden');

    kpiGrid.innerHTML = `
        <div class="kpi-card border-blue">
            <h3>Total Processed</h3>
            <p class="kpi-value">${data.total || 0}</p>
        </div>
        <div class="kpi-card border-green">
            <h3>Succeeded</h3>
            <p class="kpi-value">${data.success_count || 0}</p>
        </div>
        <div class="kpi-card border-orange">
            <h3>Failed</h3>
            <p class="kpi-value">${data.failed_count || 0}</p>
        </div>
    `;

    tbody.innerHTML = (data.results || []).map(r => {
        const isSuccess = r.status === 'Success';
        return `
            <tr>
                <td><strong>${r.employee_id || '-'}</strong></td>
                <td>${r.full_name}</td>
                <td><code>${r.email}</code></td>
                <td><span class="dept-badge">${r.department}</span> ${r.designation}</td>
                <td>${r.folder_created ? '✅ Created' : '❌ Failed'}</td>
                <td>${r.offer_letter_generated ? '✅ Generated' : '❌ Failed'}</td>
                <td>${r.assets_allocated ? '✅ Standard Kit' : '❌'}</td>
                <td>
                    <span class="badge ${isSuccess ? 'success' : 'danger'}">
                        ${r.status}
                    </span>
                </td>
            </tr>
        `;
    }).join('');

    container.scrollIntoView({ behavior: 'smooth' });
}

// ═══════════════════════════════════════════════════════════════
//  EMPLOYEE DIRECTORY & DRAWER
// ═══════════════════════════════════════════════════════════════

async function loadEmployees() {
    const tbody = document.querySelector('#empTable tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="8" class="text-center">Loading employee records...</td></tr>`;

    try {
        const res = await fetch(`${API}/employees`);
        if (res.status === 401) return checkAuth();
        const data = await res.json();
        allEmployeesCache = data.employees || [];
        renderEmployeesTable(allEmployeesCache);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Failed to retrieve records.</td></tr>`;
    }
}

function renderEmployeesTable(list) {
    const tbody = document.querySelector('#empTable tbody');
    if (!tbody) return;

    if (!list || !list.length) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No employee records found. Use "Register Employee" or "Excel Data Hub" to add.</td></tr>`;
        return;
    }

    const canViewSalary = currentUser?.permissions?.can_view_salary ?? true;
    const canRegister = currentUser?.permissions?.can_register ?? true;

    tbody.innerHTML = list.map(emp => {
        const id = emp['Employee ID'] || emp.id || '-';
        const name = emp['Full Name'] || emp.name || '-';
        const email = emp['Email'] || '-';
        const dept = emp['Department'] || '-';
        const role = emp['Designation'] || '-';
        const rawSalary = emp['Salary'];
        const salaryText = canViewSalary
            ? (rawSalary && rawSalary !== 'Confidential' ? `₹ ${Number(rawSalary).toLocaleString('en-IN')}` : (rawSalary || '-'))
            : 'Confidential';
        const status = emp['Status'] || 'Completed';
        const isComplete = status.toLowerCase().includes('complete');

        return `
            <tr>
                <td><strong>${id}</strong></td>
                <td>${name}</td>
                <td>${email}</td>
                <td><span class="dept-badge">${dept}</span></td>
                <td>${role}</td>
                <td style="${canViewSalary ? '' : 'display:none;'}">${salaryText}</td>
                <td><span class="badge ${isComplete ? 'success' : 'warning'}">${status}</span></td>
                <td>
                    <button class="btn btn-ghost btn-sm" onclick="openEmployeeDrawer('${id}')">View Details</button>
                    ${canRegister ? `<button class="btn btn-primary btn-sm" onclick="sendOfferEmail('${id}')" title="Dispatch Offer Email">📧 Offer</button>` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function filterEmployeesTable() {
    const q = (document.getElementById('empSearch')?.value || '').toLowerCase();
    const dept = document.getElementById('empDeptFilter')?.value || '';

    const filtered = allEmployeesCache.filter(emp => {
        const matchesQuery = !q ||
            (emp['Employee ID'] || '').toLowerCase().includes(q) ||
            (emp['Full Name'] || '').toLowerCase().includes(q) ||
            (emp['Email'] || '').toLowerCase().includes(q);
        const matchesDept = !dept || (emp['Department'] || '') === dept;
        return matchesQuery && matchesDept;
    });

    renderEmployeesTable(filtered);
}

// ═══════════════════════════════════════════════════════════════
//  EMPLOYEE DETAILS SLIDE-IN DRAWER
// ═══════════════════════════════════════════════════════════════

async function openEmployeeDrawer(empId) {
    const drawer = document.getElementById('employeeDrawer');
    const overlay = document.getElementById('drawerOverlay');
    const content = document.getElementById('drawerContent');

    const emp = allEmployeesCache.find(e => (e['Employee ID'] || e.id) === empId) || {};
    const empName = emp['Full Name'] || empId;

    document.getElementById('drawerEmpName').innerText = empName;
    document.getElementById('drawerEmpIdBadge').innerText = empId;

    overlay.classList.remove('hidden');
    drawer.classList.remove('hidden');
    setTimeout(() => drawer.classList.add('open'), 10);

    content.innerHTML = `<p style="padding:20px;">Fetching candidate assets, documents, and records...</p>`;

    let assets = [];
    let docData = { checklist: [] };
    try {
        const [assetRes, docRes] = await Promise.all([
            fetch(`${API}/employees/${empId}/assets`),
            fetch(`${API}/employees/${empId}/documents`)
        ]);
        if (assetRes.ok) assets = await assetRes.json();
        if (docRes.ok) docData = await docRes.json();
    } catch (e) {
        console.warn('Error loading drawer sub-resources', e);
    }

    const checklist = docData.checklist || [];
    const perms = currentUser?.permissions || {};
    const canViewSalary = perms.can_view_salary ?? true;
    const canUploadDocs = perms.can_upload_docs ?? true;
    const canApprove = perms.can_approve ?? true;
    const canRegister = perms.can_register ?? true;

    const rawSalary = emp['Salary'];
    const salaryDisplay = canViewSalary
        ? (rawSalary && rawSalary !== 'Confidential' ? `₹ ${Number(rawSalary).toLocaleString('en-IN')}` : (rawSalary || '-'))
        : 'Confidential (Restricted)';

    content.innerHTML = `
        <div class="drawer-section">
            <h4>📋 Profile Information</h4>
            <table class="drawer-info-table">
                <tr><td>Department</td><td>${emp['Department'] || '-'}</td></tr>
                <tr><td>Designation</td><td>${emp['Designation'] || '-'}</td></tr>
                <tr><td>Email</td><td>${emp['Email'] || '-'}</td></tr>
                <tr><td>Phone</td><td>${emp['Phone'] || '-'}</td></tr>
                <tr><td>Date of Joining</td><td>${emp['Date of Joining'] || '-'}</td></tr>
                <tr><td>Annual CTC</td><td><strong>${salaryDisplay}</strong></td></tr>
                <tr><td>Reporting Manager</td><td>${emp['Manager Name'] || '-'}</td></tr>
                <tr><td>Status</td><td><span class="badge success">${emp['Status'] || 'Active'}</span></td></tr>
            </table>
        </div>

        <div class="drawer-section">
            <div class="card-header-flex">
                <h4>💻 Provisioned IT Hardware</h4>
            </div>
            ${assets.length ? `
                <table class="drawer-mini-table">
                    <thead><tr><th>Asset</th><th>Serial</th><th>Status</th></tr></thead>
                    <tbody>
                        ${assets.map(a => `
                            <tr>
                                <td>${a.asset_type || '-'}</td>
                                <td><code>${a.serial_number || '-'}</code></td>
                                <td><span class="badge success">${a.status || 'Available'}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : `<p class="text-muted" style="font-size:12px;">No specific hardware registered yet.</p>`}
        </div>

        <div class="drawer-section">
            <div class="card-header-flex">
                <h4>📁 Onboarding Document Checklist</h4>
            </div>
            <div class="drawer-doc-list">
                ${checklist.map(d => {
                    const isUploaded = d.uploaded;
                    const isVerified = d.verified;
                    const docType = d.doc_type;
                    const docId = d.document_id || '';

                    return `
                        <div class="drawer-doc-item">
                            <div class="doc-info">
                                <span class="badge ${isVerified ? 'success' : (isUploaded ? 'primary' : 'warning')}">
                                    ${isVerified ? 'Verified' : (isUploaded ? 'Uploaded' : 'Pending')}
                                </span>
                                <span class="doc-title">${docType}</span>
                            </div>
                            <div class="doc-actions">
                                ${canUploadDocs ? `
                                    <button class="btn btn-ghost btn-sm" onclick="triggerDocumentUpload('${empId}', '${docType}')">Upload</button>
                                ` : ''}
                                ${isUploaded && !isVerified && docId && canApprove ? `
                                    <button class="btn btn-success btn-sm" onclick="verifyDocument('${empId}', '${docId}')">Verify</button>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>

        ${canRegister ? `
            <div class="drawer-footer-actions">
                <button class="btn btn-primary btn-block" onclick="sendOfferEmail('${empId}')">
                    📨 Send / Resend Offer Letter Email
                </button>
            </div>
        ` : ''}
    `;
}

function closeDrawer() {
    const drawer = document.getElementById('employeeDrawer');
    const overlay = document.getElementById('drawerOverlay');
    drawer?.classList.remove('open');
    setTimeout(() => {
        drawer?.classList.add('hidden');
        overlay?.classList.add('hidden');
    }, 280);
}

// ═══════════════════════════════════════════════════════════════
//  DOCUMENT MANAGEMENT & UPLOADS
// ═══════════════════════════════════════════════════════════════

async function populateDocEmployeeDropdown() {
    const select = document.getElementById('docEmployeeSelect');
    if (!select) return;

    if (!allEmployeesCache.length) {
        try {
            const res = await fetch(`${API}/employees`);
            const data = await res.json();
            allEmployeesCache = data.employees || [];
        } catch (e) {}
    }

    select.innerHTML = '<option value="">-- Select Employee --</option>' +
        allEmployeesCache.map(e => {
            const id = e['Employee ID'] || e.id;
            const name = e['Full Name'] || e.name;
            return `<option value="${id}">${id} — ${name}</option>`;
        }).join('');
}

async function loadDocumentChecklistForSelected() {
    const select = document.getElementById('docEmployeeSelect');
    const empId = select?.value;
    if (!empId) return showToast('Please select an employee first.', 'warning');

    const container = document.getElementById('docListContainer');
    const summaryCard = document.getElementById('docSummaryContainer');
    if (container) container.innerHTML = `<p class="empty-state">Loading document verification matrix for ${empId}...</p>`;

    try {
        const res = await fetch(`${API}/employees/${empId}/documents`);
        const data = await res.json();
        const checklist = data.checklist || [];
        const summary = data.summary || {};
        const perms = currentUser?.permissions || {};
        const canUploadDocs = perms.can_upload_docs ?? true;
        const canApprove = perms.can_approve ?? true;

        if (summaryCard) {
            summaryCard.classList.remove('hidden');
            summaryCard.innerHTML = `
                <div class="kpi-card border-blue">
                    <h3>Mandatory Documents</h3>
                    <p class="kpi-value">${summary.total_required || 8}</p>
                </div>
                <div class="kpi-card border-orange">
                    <h3>Uploaded</h3>
                    <p class="kpi-value">${summary.uploaded || 0}</p>
                </div>
                <div class="kpi-card border-green">
                    <h3>HR Verified</h3>
                    <p class="kpi-value">${summary.verified || 0}</p>
                </div>
                <div class="kpi-card border-purple">
                    <h3>Verification Progress</h3>
                    <p class="kpi-value">${summary.percentage || 0}%</p>
                </div>
            `;
        }

        if (!checklist.length) {
            if (container) container.innerHTML = `<p class="empty-state">No checklist found for employee ${empId}.</p>`;
            return;
        }

        if (container) {
            container.innerHTML = `
                <div class="doc-matrix-grid">
                    ${checklist.map(d => {
                        const isUploaded = d.uploaded;
                        const isVerified = d.verified;
                        const docType = d.doc_type;
                        const docId = d.document_id || '';
                        const fileName = d.file_name || 'No file';

                        return `
                            <div class="doc-card card">
                                <div class="doc-card-header">
                                    <h4>${docType}</h4>
                                    <span class="badge ${isVerified ? 'success' : (isUploaded ? 'primary' : 'warning')}">
                                        ${isVerified ? 'Verified' : (isUploaded ? 'Uploaded' : 'Pending')}
                                    </span>
                                </div>
                                <p class="text-muted" style="font-size:12px;margin:8px 0;">${isUploaded ? `File: ${fileName}` : 'Submission pending'}</p>
                                <div class="doc-card-actions">
                                    ${canUploadDocs ? `
                                        <button class="btn btn-ghost btn-sm" onclick="triggerDocumentUpload('${empId}', '${docType}')">
                                            ${isUploaded ? 'Replace' : 'Upload'}
                                        </button>
                                    ` : ''}
                                    ${isUploaded && !isVerified && docId && canApprove ? `
                                        <button class="btn btn-success btn-sm" onclick="verifyDocument('${empId}', '${docId}')">Verify</button>
                                    ` : ''}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
    } catch (e) {
        if (container) container.innerHTML = `<p class="empty-state text-danger">Failed to load document records.</p>`;
    }
}

function triggerDocumentUpload(empId, docType) {
    activeUploadTarget = { empId, docType };
    const input = document.getElementById('globalFileInput');
    if (input) {
        input.value = '';
        input.click();
    }
}

async function handleFileSelected(e) {
    const file = e.target.files[0];
    if (!file || !activeUploadTarget) return;

    const { empId, docType } = activeUploadTarget;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);

    showLoadingOverlay(`Uploading ${docType} for ${empId}...`);
    try {
        const res = await fetch(`${API}/employees/${empId}/documents`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast(`✅ ${docType} uploaded successfully!`, 'success');
            const select = document.getElementById('docEmployeeSelect');
            if (select && select.value === empId) loadDocumentChecklistForSelected();
            openEmployeeDrawer(empId);
        } else {
            showToast(data.error || 'Failed to upload document.', 'error');
        }
    } catch (err) {
        hideLoadingOverlay();
        showToast('Network error during file upload.', 'error');
    }
}

async function verifyDocument(empId, docId) {
    showLoadingOverlay('Signing verification audit...');
    try {
        const res = await fetch(`${API}/employees/${empId}/documents/${docId}/verify`, {
            method: 'POST'
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast('✅ Document marked as verified by HR.', 'success');
            const select = document.getElementById('docEmployeeSelect');
            if (select && select.value === empId) loadDocumentChecklistForSelected();
            openEmployeeDrawer(empId);
        } else {
            showToast(data.error || 'Verification failed.', 'error');
        }
    } catch (e) {
        hideLoadingOverlay();
        showToast('Network error during document verification.', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
//  ASSET TRACKER (FIXED FUNCTION SCOPING & CLOSING BRACE)
// ═══════════════════════════════════════════════════════════════

async function loadAssets() {
    const tbody = document.querySelector('#assetTable tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">Loading asset repository...</td></tr>`;

    try {
        const res = await fetch(`${API}/assets`);
        if (res.status === 401) return checkAuth();
        const data = await res.json();
        allAssetsCache = data.assets || [];
        renderAssetsTable(allAssetsCache);
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Failed to load assets.</td></tr>`;
    }
}

function renderAssetsTable(list) {
    const tbody = document.querySelector('#assetTable tbody');
    if (!tbody) return;

    if (!list || !list.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No assets recorded yet. Assets are auto-allocated during onboarding.</td></tr>`;
        return;
    }

    tbody.innerHTML = list.map(a => {
        const id = a.asset_id || '-';
        const type = a.asset_type || '-';
        const serial = a.serial_number || '-';

        const emp = a.employee_name
            ? `${a.employee_name} (${a.employee_id || '-'})`
            : (a.employee_id || 'Unassigned');

        const date = a.assigned_date || '-';
        const status = a.status || 'Available';

        return `
            <tr>
                <td><strong>${id}</strong></td>
                <td>${type}</td>
                <td><code>${serial}</code></td>
                <td>${emp}</td>
                <td>${date}</td>
                <td>
                    <span class="badge ${status === 'Allocated' ? 'success' : 'primary'}">
                        ${status}
                    </span>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAssetsTable() {
    const typeFilter = document.getElementById('assetTypeFilter')?.value || '';
    const statusFilter = document.getElementById('assetStatusFilter')?.value || '';

    const filtered = allAssetsCache.filter(a => {
        const matchesType = !typeFilter || a.asset_type === typeFilter;
        const matchesStatus = !statusFilter || a.status === statusFilter;
        return matchesType && matchesStatus;
    });

    renderAssetsTable(filtered);
}

// ═══════════════════════════════════════════════════════════════
//  REPORTS (GENERATE & DELETE)
// ═══════════════════════════════════════════════════════════════

async function loadReports() {
    const tbody = document.querySelector('#reportsTable tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4" class="text-center">Loading reports catalog...</td></tr>`;

    try {
        const res = await fetch(`${API}/reports`);
        if (res.status === 401) return checkAuth();
        const data = await res.json();
        const list = data.reports || [];

        if (!list.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No reports generated yet. Click "+ Generate New Excel Report".</td></tr>`;
            return;
        }

        const canDelete = currentUser?.permissions?.can_delete ?? true;

        tbody.innerHTML = list.map(rep => {
            const name = rep.name;
            const created = rep.created;
            const size = `${rep.size_kb} KB`;

            return `
                <tr>
                    <td><strong>📄 ${name}</strong></td>
                    <td>${created}</td>
                    <td>${size}</td>
                    <td>
                        ${canDelete ? `<button class="btn btn-danger btn-sm" onclick="deleteReport('${name}')">🗑️ Delete</button>` : '<span class="text-muted">-</span>'}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Failed to fetch reports list.</td></tr>`;
    }
}

async function generateReport() {
    showLoadingOverlay('Compiling database audit & generating styled Excel report...');
    try {
        const res = await fetch(`${API}/generate-report`, { method: 'POST' });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast('✅ Executive Onboarding Report generated successfully!', 'success');
            const summary = data.summary || {};
            const sumBox = document.getElementById('reportSummary');
            if (sumBox) {
                sumBox.classList.remove('hidden');
                sumBox.innerHTML = `
                    <div class="kpi-card border-blue">
                        <h3>Total Processed</h3>
                        <p class="kpi-value">${summary.total || 0}</p>
                    </div>
                    <div class="kpi-card border-green">
                        <h3>Successful</h3>
                        <p class="kpi-value">${summary.successful || 0}</p>
                    </div>
                    <div class="kpi-card border-orange">
                        <h3>Emails Dispatched</h3>
                        <p class="kpi-value">${summary.emails_sent || 0}</p>
                    </div>
                    <div class="kpi-card border-purple">
                        <h3>Hardware Kits</h3>
                        <p class="kpi-value">${summary.folders_created || 0}</p>
                    </div>
                `;
            }
            loadReports();
        } else {
            showToast(data.error || 'Failed to generate report.', 'error');
        }
    } catch (e) {
        hideLoadingOverlay();
        showToast('Network error while generating report.', 'error');
    }
}

async function deleteReport(filename) {
    if (!confirm(`Are you sure you want to delete the report: "${filename}"?\n\nThis action cannot be undone.`)) {
        return;
    }

    showLoadingOverlay(`Deleting ${filename}...`);
    try {
        const res = await fetch(`${API}/reports/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast(`✅ ${filename} has been deleted.`, 'success');
            loadReports();
        } else {
            showToast(data.error || 'Could not delete report.', 'error');
        }
    } catch (e) {
        hideLoadingOverlay();
        showToast('Server error while deleting report.', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
//  AUDIT TRAIL LOG
// ═══════════════════════════════════════════════════════════════

async function loadAuditLog() {
    const tbody = document.querySelector('#auditTable tbody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4" class="text-center">Loading audit events...</td></tr>`;

    try {
        const res = await fetch(`${API}/audit-log`);
        if (res.status === 401) return checkAuth();
        const data = await res.json();
        const entries = data.entries || [];

        if (!entries.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No audit trail entries recorded yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = entries.map(line => {
            const parts = line.split(' | ');
            const time = (parts[0] || '').replace(/[\[\]]/g, '');
            const emp = parts[1] || 'SYSTEM';
            const action = parts[2] || 'EVENT';
            const details = parts.slice(3).join(' | ') || '';

            let badgeClass = 'primary';
            if (action.includes('SUCCESS') || action.includes('OFFER') || action.includes('START') || action.includes('COMPLETE')) badgeClass = 'success';
            if (action.includes('FAIL') || action.includes('ERROR') || action.includes('DELETE')) badgeClass = 'danger';

            return `
                <tr>
                    <td><code>${time}</code></td>
                    <td><strong>${emp}</strong></td>
                    <td><span class="badge ${badgeClass}">${action}</span></td>
                    <td>${details}</td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Failed to retrieve audit log.</td></tr>`;
    }
}

// ═══════════════════════════════════════════════════════════════
//  OFFER EMAIL DISPATCH (STANDALONE)
// ═══════════════════════════════════════════════════════════════

async function sendOfferEmail(empId) {
    showLoadingOverlay(`Generating branded Offer Letter PDF and dispatching email for ${empId}...`);
    try {
        const res = await fetch(`${API}/send-offer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ employee_id: empId })
        });
        const data = await res.json();
        hideLoadingOverlay();

        if (res.ok && data.success) {
            showToast(`✅ Offer email successfully dispatched for ${data.employee_name || empId} (${data.mode} mode)`, 'success');
        } else {
            showToast(`❌ ${data.error || 'Failed to dispatch offer email'}`, 'error');
        }
    } catch (e) {
        hideLoadingOverlay();
        showToast('Network error while dispatching offer email.', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════
//  UI HELPERS: TOAST, LOADER, CLOCK
// ═══════════════════════════════════════════════════════════════

function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = msg;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

function showLoadingOverlay(msg = 'Processing RPA Workflow...') {
    const overlay = document.getElementById('loadingOverlay');
    const p = document.getElementById('loadingMsg');
    if (p) p.innerText = msg;
    overlay?.classList.remove('hidden');
}

function hideLoadingOverlay() {
    document.getElementById('loadingOverlay')?.classList.add('hidden');
}

function startClock() {
    const update = () => {
        const el = document.getElementById('dateTimeDisplay');
        if (el) el.innerText = new Date().toLocaleString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit', second: '2-digit'
        });
    };
    update();
    setInterval(update, 1000);
}

async function checkServerStatus() {
    try {
        const res = await fetch(`${API}/config`);
        if (res.ok) {
            const cfg = await res.json();
            const mode = cfg.EmailMode || 'mock';
            const modeBadge = document.getElementById('emailMode');
            if (modeBadge) {
                modeBadge.innerText = mode.toUpperCase() === 'SMTP' ? 'Live SMTP Mode' : 'Mock Email Mode';
                modeBadge.className = `badge ${mode.toUpperCase() === 'SMTP' ? 'success' : 'warning'}`;
            }
        }
    } catch (e) {}
}
