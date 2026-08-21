/* ==========================================================================
   APP.JS — shared UI utilities used across every page (public + dashboards)
   ========================================================================== */

/* ---------------- Toast notifications ---------------- */
function ensureToastContainer() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}
function toast(message, type = 'info') {
  const container = ensureToastContainer();
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  const icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info';
  el.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('hide');
    setTimeout(() => el.remove(), 220);
  }, 3400);
}

/* ---------------- Modal helpers ---------------- */
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}
document.addEventListener('click', (e) => {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

/* ---------------- Formatting helpers ---------------- */
function formatCurrency(amount) {
  return '₦' + Number(amount || 0).toLocaleString('en-NG');
}
function formatDate(dateStr, opts) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString('en-GB', opts || { day: '2-digit', month: 'short', year: 'numeric' });
}
function timeAgo(dateStr) {
  const d = new Date(dateStr);
  const diff = Math.floor((Date.now() - d.getTime()) / 60000);
  if (diff < 1) return 'just now';
  if (diff < 60) return diff + 'm ago';
  if (diff < 1440) return Math.floor(diff / 60) + 'h ago';
  return Math.floor(diff / 1440) + 'd ago';
}
function fullName(person) {
  return [person.firstName, person.lastName].filter(Boolean).join(' ') || person.name || '';
}
function studentClassLabel(s) { return `${s.class}${s.section || ''}`; }
function genId(prefix) { return `${prefix}-${Date.now().toString(36).toUpperCase()}${Math.floor(Math.random() * 900 + 100)}`; }
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
}
function debounce(fn, delay = 250) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

/* Badge helper for common status values */
function statusBadgeClass(status) {
  const map = {
    'Active': 'success', 'Present': 'success', 'Paid': 'success', 'Approved': 'success', 'Admitted': 'success', 'Published': 'success', 'Successful': 'success',
    'Pending': 'warning', 'Partial': 'warning', 'Under Review': 'warning', 'Late': 'warning', 'Interview': 'warning',
    'Absent': 'danger', 'Unpaid': 'danger', 'Rejected': 'danger', 'Inactive': 'danger',
    'Shortlisted': 'info', 'Draft': 'gray'
  };
  return map[status] || 'gray';
}

/* ---------------- Public site: navbar + mobile menu ---------------- */
function initMobileNav() {
  const hamburger = document.querySelector('.hamburger');
  const mobileNav = document.querySelector('.mobile-nav');
  if (!hamburger || !mobileNav) return;
  hamburger.addEventListener('click', () => mobileNav.classList.add('open'));
  const closeBtn = mobileNav.querySelector('.mobile-nav-close');
  if (closeBtn) closeBtn.addEventListener('click', () => mobileNav.classList.remove('open'));
  mobileNav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => mobileNav.classList.remove('open')));
}

/* Highlight current nav link based on filename */
function highlightActiveNav() {
  const file = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .mobile-nav a').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (href.split('/').pop() === file) a.classList.add('active');
  });
}

/* ---------------- FAQ accordion (admissions page) ---------------- */
function initFaqAccordion() {
  document.querySelectorAll('.faq-q').forEach(q => {
    q.addEventListener('click', () => {
      const item = q.closest('.faq-item');
      const wasOpen = item.classList.contains('open');
      item.parentElement.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
      if (!wasOpen) item.classList.add('open');
    });
  });
}

/* ---------------- Dashboard shell: sidebar + topbar dropdowns ---------------- */
function initDashboardShell() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const toggle = document.querySelector('.sidebar-toggle');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      sidebar.classList.add('open');
      if (overlay) overlay.classList.add('open');
    });
  }
  if (overlay && sidebar) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
  }
  // Highlight active sidebar link
  const file = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.sidebar-nav a').forEach(a => {
    const href = (a.getAttribute('href') || '').split('/').pop();
    if (href === file) a.classList.add('active');
  });

  // Dropdowns (profile / notifications)
  document.querySelectorAll('[data-dropdown-toggle]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const target = document.getElementById(btn.getAttribute('data-dropdown-toggle'));
      document.querySelectorAll('.dropdown-menu.open').forEach(dd => { if (dd !== target) dd.classList.remove('open'); });
      if (target) target.classList.toggle('open');
    });
  });
  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-menu.open').forEach(dd => dd.classList.remove('open'));
  });

  // Logout buttons
  document.querySelectorAll('[data-logout]').forEach(btn => btn.addEventListener('click', Auth.logout));

  // Populate profile name/role if session bound elements exist
  const session = Auth.current();
  if (session) {
    document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = session.name);
    document.querySelectorAll('[data-user-role]').forEach(el => el.textContent = session.role.charAt(0).toUpperCase() + session.role.slice(1));
    document.querySelectorAll('[data-user-initials]').forEach(el => el.textContent = session.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase());
  }
}

/* ---------------- Simple client-side table search/filter helper ---------------- */
function filterTableRows(inputEl, tableSelector, rowMatcher) {
  inputEl.addEventListener('input', debounce(() => {
    const term = inputEl.value.trim().toLowerCase();
    document.querySelectorAll(`${tableSelector} tbody tr`).forEach(row => {
      row.style.display = rowMatcher(row, term) ? '' : 'none';
    });
  }, 150));
}

document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  highlightActiveNav();
  initFaqAccordion();
});
