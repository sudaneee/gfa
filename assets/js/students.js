/* ==========================================================================
   STUDENTS.JS — Student Management module (admin dashboard)
   ========================================================================== */

document.getElementById('dashContent').innerHTML = document.getElementById('pageTemplate').innerHTML;

let currentPage = 1;
const perPage = 8;
let editingId = null;

function populateFilterOptions() {
  const db = DB.load();
  const classFilter = document.getElementById('classFilter');
  classFilter.innerHTML += db.classes.map(c => `<option value="${c.name}">${c.name}</option>`).join('');

  const sClass = document.getElementById('sClass');
  sClass.innerHTML = '<option value="">Select class</option>' + db.classes.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
  sClass.addEventListener('change', updateSectionOptions);

  const sGuardian = document.getElementById('sGuardian');
  sGuardian.innerHTML = '<option value="">Select guardian</option>' + db.parents.map(p => `<option value="${p.id}">${p.name} (${p.phone})</option>`).join('');
}

function updateSectionOptions() {
  const db = DB.load();
  const className = document.getElementById('sClass').value;
  const cls = db.classes.find(c => c.name === className);
  const sSection = document.getElementById('sSection');
  sSection.innerHTML = (cls ? cls.sections : []).map(s => `<option value="${s}">${s}</option>`).join('');
}

function getFilteredStudents() {
  const db = DB.load();
  const term = document.getElementById('searchInput').value.trim().toLowerCase();
  const cls = document.getElementById('classFilter').value;
  const status = document.getElementById('statusFilter').value;
  return db.students.filter(s => {
    if (cls && s.class !== cls) return false;
    if (status && s.status !== status) return false;
    if (term) {
      const hay = `${s.firstName} ${s.lastName} ${s.admissionNo}`.toLowerCase();
      if (!hay.includes(term)) return false;
    }
    return true;
  }).sort((a, b) => fullName(a).localeCompare(fullName(b)));
}

function renderTable() {
  const db = DB.load();
  const all = getFilteredStudents();
  const totalPages = Math.max(1, Math.ceil(all.length / perPage));
  currentPage = Math.min(currentPage, totalPages);
  const pageItems = all.slice((currentPage - 1) * perPage, currentPage * perPage);

  document.getElementById('emptyState').style.display = all.length ? 'none' : 'block';
  document.getElementById('studentTableBody').innerHTML = pageItems.map(s => {
    const guardian = db.parents.find(p => p.id === s.guardianId);
    return `<tr>
      <td><div class="avatar">${initials(s.firstName, s.lastName)}</div></td>
      <td><strong>${s.admissionNo}</strong></td>
      <td>${escapeHtml(fullName(s))}</td>
      <td>${s.gender}</td>
      <td>${studentClassLabel(s)}</td>
      <td>${guardian ? escapeHtml(guardian.name) : '<span class="text-muted">Not linked</span>'}</td>
      <td><span class="badge badge-${statusBadgeClass(s.status)}">${s.status}</span></td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="viewStudent('${s.id}')"><i class="fa-solid fa-eye"></i></button>
        <button class="btn btn-sm btn-secondary" onclick="editStudent('${s.id}')"><i class="fa-solid fa-pen"></i></button>
      </td>
    </tr>`;
  }).join('');

  document.getElementById('pagination').innerHTML = Array.from({ length: totalPages }, (_, i) => i + 1)
    .map(p => `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`).join('');
}
function goToPage(p) { currentPage = p; renderTable(); }

function openAddModal() {
  editingId = null;
  document.getElementById('studentModalTitle').textContent = 'Add Student';
  document.getElementById('studentForm').reset();
  updateSectionOptions();
  openModal('studentModal');
}

function editStudent(id) {
  const db = DB.load();
  const s = db.students.find(s => s.id === id);
  if (!s) return;
  editingId = id;
  document.getElementById('studentModalTitle').textContent = 'Edit Student';
  document.getElementById('sFirstName').value = s.firstName;
  document.getElementById('sLastName').value = s.lastName;
  document.getElementById('sGender').value = s.gender;
  document.getElementById('sDob').value = s.dob || '';
  document.getElementById('sClass').value = s.class;
  updateSectionOptions();
  document.getElementById('sSection').value = s.section;
  document.getElementById('sGuardian').value = s.guardianId || '';
  document.getElementById('sStatus').value = s.status;
  openModal('studentModal');
}

function saveStudent() {
  const form = document.getElementById('studentForm');
  if (!form.checkValidity()) { form.reportValidity(); return; }

  const db = DB.update(db => {
    const data = {
      firstName: document.getElementById('sFirstName').value.trim(),
      lastName: document.getElementById('sLastName').value.trim(),
      gender: document.getElementById('sGender').value,
      dob: document.getElementById('sDob').value,
      class: document.getElementById('sClass').value,
      section: document.getElementById('sSection').value,
      guardianId: document.getElementById('sGuardian').value,
      status: document.getElementById('sStatus').value
    };
    const cls = db.classes.find(c => c.name === data.class);
    data.level = cls ? cls.level : '';

    if (editingId) {
      const s = db.students.find(s => s.id === editingId);
      Object.assign(s, data);
    } else {
      const count = db.students.length + 1;
      const admissionNo = `GFA/${data.level.slice(0, 3).toUpperCase()}/2026/${String(count).padStart(3, '0')}`;
      db.students.push({ id: `STU-NEW-${Date.now()}`, admissionNo, admissionDate: new Date().toISOString().slice(0, 10), ...data });
    }
  });

  toast(editingId ? 'Student updated successfully.' : 'Student added successfully.', 'success');
  closeModal('studentModal');
  renderTable();
}

function viewStudent(id) {
  const db = DB.load();
  const s = db.students.find(s => s.id === id);
  if (!s) return;
  const guardian = db.parents.find(p => p.id === s.guardianId);
  const results = db.results.filter(r => r.studentId === id);
  const attendance = db.attendance.filter(a => a.studentId === id);
  const present = attendance.filter(a => a.status === 'Present').length;
  const attendanceRate = attendance.length ? Math.round((present / attendance.length) * 100) : 0;
  const invoice = db.invoices.find(i => i.studentId === id);
  const avgScore = results.length ? Math.round(results.reduce((sum, r) => sum + r.total, 0) / results.length) : 0;

  document.getElementById('profileModalBody').innerHTML = `
    <div class="flex gap-16 mb-24" style="align-items:center;">
      <div class="avatar avatar-lg">${initials(s.firstName, s.lastName)}</div>
      <div>
        <h3 class="mb-0">${escapeHtml(fullName(s))}</h3>
        <p class="text-muted mb-0">${s.admissionNo} &middot; ${studentClassLabel(s)} &middot; <span class="badge badge-${statusBadgeClass(s.status)}">${s.status}</span></p>
      </div>
    </div>
    <div class="rc-summary">
      <div class="box"><strong>${avgScore}%</strong><span>Average Score</span></div>
      <div class="box"><strong>${attendanceRate}%</strong><span>Attendance Rate</span></div>
      <div class="box"><strong>${invoice ? formatCurrency(invoice.balance) : '₦0'}</strong><span>Fees Balance</span></div>
      <div class="box"><strong>${results.length}</strong><span>Subjects Recorded</span></div>
    </div>
    <div class="review-block"><h5>Personal Information</h5><div class="review-grid">
      <div class="item"><span class="k">Date of Birth</span><span class="v">${formatDate(s.dob)}</span></div>
      <div class="item"><span class="k">Gender</span><span class="v">${s.gender}</span></div>
      <div class="item"><span class="k">Class / Section</span><span class="v">${studentClassLabel(s)}</span></div>
      <div class="item"><span class="k">Admission Date</span><span class="v">${formatDate(s.admissionDate)}</span></div>
      <div class="item"><span class="k">Guardian</span><span class="v">${guardian ? escapeHtml(guardian.name) : '-'}</span></div>
      <div class="item"><span class="k">Guardian Phone</span><span class="v">${guardian ? escapeHtml(guardian.phone) : '-'}</span></div>
    </div></div>
    <div class="review-block"><h5>Recent Results (${CURRENT_TERM})</h5>
      <div class="table-wrap"><table class="data-table">
        <thead><tr><th>Subject</th><th>CA</th><th>Exam</th><th>Total</th><th>Grade</th></tr></thead>
        <tbody>${results.slice(0, 6).map(r => `<tr><td>${r.subject}</td><td>${r.ca}</td><td>${r.exam}</td><td>${r.total}</td><td><span class="badge badge-${r.grade === 'F' ? 'danger' : r.grade === 'A' ? 'success' : 'gray'}">${r.grade}</span></td></tr>`).join('') || '<tr><td colspan="5" class="text-muted">No results recorded yet.</td></tr>'}</tbody>
      </table></div>
    </div>`;
  openModal('profileModal');
}

document.getElementById('addStudentBtn').addEventListener('click', openAddModal);
document.getElementById('saveStudentBtn').addEventListener('click', saveStudent);
document.getElementById('searchInput').addEventListener('input', debounce(() => { currentPage = 1; renderTable(); }, 150));
document.getElementById('classFilter').addEventListener('change', () => { currentPage = 1; renderTable(); });
document.getElementById('statusFilter').addEventListener('change', () => { currentPage = 1; renderTable(); });

populateFilterOptions();
renderTable();

if (new URLSearchParams(window.location.search).get('add') === '1') openAddModal();
