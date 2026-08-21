/* ==========================================================================
   ADMISSIONS.JS — multi-step online application workflow
   ========================================================================== */

let currentStep = 1;
const totalSteps = 6;
const uploadedDocs = {};
let lastApplicationNo = null;

function initApplicationForm() {
  const form = document.getElementById('applicationForm');
  if (!form) return;

  // Populate State of Origin
  const stateSelect = form.querySelector('select[name="state"]');
  stateSelect.innerHTML = '<option value="">Select state</option>' + STATES.map(s => `<option>${s}</option>`).join('');

  // Populate "Applying For" grouped by level
  const applyingFor = document.getElementById('applyingForSelect');
  let optionsHtml = '<option value="">Select level / class</option>';
  LEVELS.forEach(level => {
    const classesForLevel = CLASS_LIST.filter(c => c.level === level);
    optionsHtml += `<optgroup label="${level}">` + classesForLevel.map(c => `<option value="${c.name}" data-level="${level}">${c.name}</option>`).join('') + '</optgroup>';
  });
  applyingFor.innerHTML = optionsHtml;

  // File upload handlers
  document.querySelectorAll('input[type="file"][data-doc]').forEach(input => {
    input.addEventListener('change', () => {
      const doc = input.dataset.doc;
      const nameEl = document.getElementById('name-' + doc);
      if (input.files && input.files[0]) {
        uploadedDocs[doc] = input.files[0].name;
        nameEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${input.files[0].name}`;
      } else {
        uploadedDocs[doc] = '';
        nameEl.textContent = '';
      }
    });
  });

  document.getElementById('nextBtn').addEventListener('click', handleNext);
  document.getElementById('prevBtn').addEventListener('click', handlePrev);

  updateStepUI();
}

function currentStepEl() { return document.querySelector(`.form-step[data-step="${currentStep}"]`); }

function validateStep(step) {
  const stepEl = document.querySelector(`.form-step[data-step="${step}"]`);
  if (!stepEl) return true;
  let valid = true;
  stepEl.querySelectorAll('[required]').forEach(field => {
    const group = field.closest('.form-group') || field.parentElement;
    let fieldValid = true;
    if (field.type === 'file') {
      fieldValid = !!uploadedDocs[field.dataset.doc];
    } else {
      fieldValid = field.value.trim() !== '';
    }
    if (field.type === 'email' && field.value) {
      fieldValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value);
    }
    if (field.name === 'phone' && field.value) {
      fieldValid = /^[0-9+\s-]{10,15}$/.test(field.value);
    }
    if (!fieldValid) {
      valid = false;
      if (group) group.classList.add('has-error');
    } else if (group) {
      group.classList.remove('has-error');
    }
  });
  if (!valid) toast('Please complete all required fields correctly.', 'error');
  return valid;
}

function handleNext() {
  if (currentStep === 5) {
    submitApplication();
    return;
  }
  if (!validateStep(currentStep)) return;
  if (currentStep === totalSteps) return;

  if (currentStep === 4) buildReview();

  currentStep++;
  updateStepUI();
}

function handlePrev() {
  if (currentStep > 1) {
    currentStep--;
    updateStepUI();
  }
}

function updateStepUI() {
  document.querySelectorAll('.form-step').forEach(s => s.classList.toggle('active', Number(s.dataset.step) === currentStep));
  document.querySelectorAll('.app-step-item').forEach(item => {
    const n = Number(item.dataset.step);
    item.classList.toggle('active', n === currentStep);
    item.classList.toggle('done', n < currentStep);
  });
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  prevBtn.disabled = currentStep === 1;
  prevBtn.style.visibility = currentStep === 6 ? 'hidden' : 'visible';

  if (currentStep === 5) {
    nextBtn.innerHTML = 'Submit Application <i class="fa-solid fa-paper-plane"></i>';
  } else if (currentStep === 6) {
    nextBtn.style.display = 'none';
    prevBtn.style.display = 'none';
  } else {
    nextBtn.innerHTML = 'Continue <i class="fa-solid fa-arrow-right"></i>';
  }
  window.scrollTo({ top: document.querySelector('.card').offsetTop - 100, behavior: 'smooth' });
}

function getFormData() {
  const form = document.getElementById('applicationForm');
  const data = {};
  new FormData(form).forEach((val, key) => data[key] = val);
  const levelOpt = document.querySelector(`#applyingForSelect option[value="${data.applyingFor}"]`);
  data.level = levelOpt ? levelOpt.dataset.level : '';
  return data;
}

function buildReview() {
  const d = getFormData();
  const html = `
    <div class="review-block">
      <h5>Applicant Information</h5>
      <div class="review-grid">
        <div class="item"><span class="k">Full Name</span><span class="v">${escapeHtml([d.firstName, d.middleName, d.lastName].filter(Boolean).join(' '))}</span></div>
        <div class="item"><span class="k">Date of Birth</span><span class="v">${formatDate(d.dob)}</span></div>
        <div class="item"><span class="k">Gender</span><span class="v">${escapeHtml(d.gender)}</span></div>
        <div class="item"><span class="k">Nationality</span><span class="v">${escapeHtml(d.nationality)}</span></div>
        <div class="item"><span class="k">State of Origin</span><span class="v">${escapeHtml(d.state)}</span></div>
        <div class="item"><span class="k">LGA</span><span class="v">${escapeHtml(d.lga)}</span></div>
      </div>
    </div>
    <div class="review-block">
      <h5>Parent / Guardian Information</h5>
      <div class="review-grid">
        <div class="item"><span class="k">Name</span><span class="v">${escapeHtml(d.parentName)}</span></div>
        <div class="item"><span class="k">Relationship</span><span class="v">${escapeHtml(d.relationship)}</span></div>
        <div class="item"><span class="k">Phone</span><span class="v">${escapeHtml(d.phone)}</span></div>
        <div class="item"><span class="k">Email</span><span class="v">${escapeHtml(d.email)}</span></div>
        <div class="item"><span class="k">Address</span><span class="v">${escapeHtml(d.address)}</span></div>
        <div class="item"><span class="k">Occupation</span><span class="v">${escapeHtml(d.occupation || '-')}</span></div>
      </div>
    </div>
    <div class="review-block">
      <h5>Academic Information</h5>
      <div class="review-grid">
        <div class="item"><span class="k">Applying For</span><span class="v">${escapeHtml(d.applyingFor)}</span></div>
        <div class="item"><span class="k">Previous School</span><span class="v">${escapeHtml(d.previousSchool || 'First time in school')}</span></div>
        <div class="item"><span class="k">Previous Class</span><span class="v">${escapeHtml(d.previousClass || '-')}</span></div>
        <div class="item"><span class="k">Previous Performance</span><span class="v">${escapeHtml(d.previousPerformance || '-')}</span></div>
      </div>
    </div>
    <div class="review-block">
      <h5>Uploaded Documents</h5>
      <div class="review-grid">
        <div class="item"><span class="k">Passport Photograph</span><span class="v">${escapeHtml(uploadedDocs.passport || 'Not uploaded')}</span></div>
        <div class="item"><span class="k">Birth Certificate</span><span class="v">${escapeHtml(uploadedDocs.birthCert || 'Not uploaded')}</span></div>
        <div class="item"><span class="k">Previous Result</span><span class="v">${escapeHtml(uploadedDocs.previousResult || 'Not uploaded')}</span></div>
        <div class="item"><span class="k">Other Document</span><span class="v">${escapeHtml(uploadedDocs.other || 'Not uploaded')}</span></div>
      </div>
    </div>`;
  document.getElementById('reviewContainer').innerHTML = html;
}

function generateApplicationNo(db) {
  const year = '2026';
  const existingNums = db.applications
    .filter(a => a.applicationNo.startsWith(`GFA-${year}-`))
    .map(a => parseInt(a.applicationNo.split('-')[2], 10));
  const next = (existingNums.length ? Math.max(...existingNums) : 100) + 1;
  return `GFA-${year}-${String(next).padStart(6, '0')}`;
}

function submitApplication() {
  if (!validateStep(4)) { currentStep = 4; updateStepUI(); return; }
  const d = getFormData();
  const today = new Date().toISOString().slice(0, 10);

  const db = DB.load();
  const applicationNo = generateApplicationNo(db);
  const application = {
    applicationNo, firstName: d.firstName, middleName: d.middleName, lastName: d.lastName, dob: d.dob,
    gender: d.gender, nationality: d.nationality, state: d.state, lga: d.lga,
    previousSchool: d.previousSchool, previousClass: d.previousClass,
    parentName: d.parentName, relationship: d.relationship, phone: d.phone, email: d.email,
    address: d.address, occupation: d.occupation, applyingFor: d.applyingFor, level: d.level,
    previousPerformance: d.previousPerformance,
    documents: { passport: uploadedDocs.passport || '', birthCert: uploadedDocs.birthCert || '', previousResult: uploadedDocs.previousResult || '', other: uploadedDocs.other || '' },
    status: 'Pending', applicationDate: today,
    timeline: [{ stage: 'Submitted', date: today }]
  };
  db.applications.unshift(application);
  DB.save(db);
  lastApplicationNo = applicationNo;

  renderSuccess(application);
  currentStep = 6;
  updateStepUI();
}

function renderSuccess(app) {
  document.getElementById('successPanel').innerHTML = `
    <div class="check-circle"><i class="fa-solid fa-check"></i></div>
    <h2>Application Submitted Successfully!</h2>
    <p class="text-muted">Thank you, ${escapeHtml(app.parentName)}. Your application for <strong>${escapeHtml([app.firstName, app.lastName].join(' '))}</strong> has been received.</p>
    <div class="ref-number">${app.applicationNo}</div>
    <div class="review-grid" style="max-width:460px;margin:0 auto 24px;text-align:left;">
      <div class="item"><span class="k">Applicant Name</span><span class="v">${escapeHtml([app.firstName, app.lastName].join(' '))}</span></div>
      <div class="item"><span class="k">Programme/Level</span><span class="v">${escapeHtml(app.applyingFor)}</span></div>
      <div class="item"><span class="k">Application Date</span><span class="v">${formatDate(app.applicationDate)}</span></div>
      <div class="item"><span class="k">Current Status</span><span class="v"><span class="badge badge-warning">Pending Review</span></span></div>
    </div>
    <div class="flex gap-12 flex-wrap flex-center no-print">
      <button class="btn btn-secondary" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Application</button>
      <button class="btn btn-secondary" id="downloadSummaryBtn"><i class="fa-solid fa-download"></i> Save Summary</button>
      <a class="btn btn-primary" href="application-tracking.html?ref=${app.applicationNo}">Track Application <i class="fa-solid fa-arrow-right"></i></a>
    </div>`;
  document.getElementById('downloadSummaryBtn').addEventListener('click', () => downloadSummary(app));
}

function downloadSummary(app) {
  const lines = [
    'GLITTERING FIELD ACADEMY - APPLICATION SUMMARY', '================================================',
    `Application No: ${app.applicationNo}`, `Applicant Name: ${app.firstName} ${app.middleName || ''} ${app.lastName}`,
    `Date of Birth: ${app.dob}`, `Gender: ${app.gender}`, `Applying For: ${app.applyingFor}`,
    `Parent/Guardian: ${app.parentName} (${app.relationship})`, `Phone: ${app.phone}`, `Email: ${app.email}`,
    `Application Date: ${app.applicationDate}`, `Status: Pending Review`, '', 'Thank you for applying to Glittering Field Academy.'
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `${app.applicationNo}-summary.txt`;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
  toast('Application summary saved.', 'success');
}

document.addEventListener('DOMContentLoaded', initApplicationForm);
