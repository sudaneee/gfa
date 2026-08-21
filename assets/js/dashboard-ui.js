/* ==========================================================================
   DASHBOARD-UI.JS — generates the sidebar + topbar shell for every console
   (admin, teacher, parent, student) so navigation stays consistent without
   duplicating markup on every page.
   ========================================================================== */

const NAV_BY_ROLE = {
  admin: [
    { items: [{ label: 'Dashboard', icon: 'fa-gauge-high', href: 'index.html' }] },
    { section: 'Admissions', items: [{ label: 'Applications', icon: 'fa-file-signature', href: 'applications.html' }] },
    { section: 'Students', items: [
      { label: 'All Students', icon: 'fa-user-graduate', href: 'students.html' },
      { label: 'Classes & Sections', icon: 'fa-people-roof', href: 'academics.html#classes' }
    ]},
    { section: 'Academics', items: [
      { label: 'Sessions & Terms', icon: 'fa-calendar-days', href: 'academics.html#sessions' },
      { label: 'Subjects', icon: 'fa-book', href: 'academics.html#subjects' },
      { label: 'Timetable', icon: 'fa-table-cells', href: 'academics.html#timetable' }
    ]},
    { section: 'Examinations', items: [
      { label: 'CBT Exams', icon: 'fa-laptop', href: 'examinations.html#cbt' },
      { label: 'Questions Bank', icon: 'fa-list-check', href: 'examinations.html#questions' }
    ]},
    { section: 'Attendance', items: [
      { label: 'Mark Attendance', icon: 'fa-clipboard-check', href: 'attendance.html#mark' },
      { label: 'Attendance Records', icon: 'fa-calendar-check', href: 'attendance.html#records' }
    ]},
    { section: 'Results', items: [{ label: 'Enter & Manage Results', icon: 'fa-pen-to-square', href: 'results.html' }] },
    { section: 'Fees & Payments', items: [
      { label: 'Fee Structure', icon: 'fa-sack-dollar', href: 'fees.html#structure' },
      { label: 'Invoices', icon: 'fa-file-invoice-dollar', href: 'fees.html#invoices' },
      { label: 'Payments', icon: 'fa-credit-card', href: 'payments.html' }
    ]},
    { section: 'Staff', items: [{ label: 'Teachers & Staff', icon: 'fa-chalkboard-user', href: 'teachers.html' }] },
    { section: 'Communication', items: [
      { label: 'Announcements', icon: 'fa-bullhorn', href: 'announcements.html#announcements' },
      { label: 'Events', icon: 'fa-calendar-star', href: 'announcements.html#events' }
    ]},
    { section: 'Insights', items: [{ label: 'Reports', icon: 'fa-chart-column', href: 'reports.html' }] },
    { items: [{ label: 'Settings', icon: 'fa-gear', href: 'settings.html' }] }
  ],
  teacher: [
    { items: [{ label: 'Dashboard', icon: 'fa-gauge-high', href: 'dashboard.html' }] },
    { section: 'My Work', items: [
      { label: 'My Students', icon: 'fa-user-graduate', href: 'dashboard.html#students' },
      { label: 'Attendance', icon: 'fa-clipboard-check', href: 'dashboard.html#attendance' },
      { label: 'Results', icon: 'fa-pen-to-square', href: 'dashboard.html#results' },
      { label: 'Examinations', icon: 'fa-laptop', href: 'dashboard.html#exams' },
      { label: 'Timetable', icon: 'fa-table-cells', href: 'dashboard.html#timetable' }
    ]},
    { section: 'Communication', items: [{ label: 'Announcements', icon: 'fa-bullhorn', href: 'dashboard.html#announcements' }] }
  ],
  parent: [
    { items: [{ label: 'Dashboard', icon: 'fa-gauge-high', href: 'dashboard.html' }] },
    { section: 'My Children', items: [
      { label: 'Children', icon: 'fa-children', href: 'dashboard.html#children' },
      { label: 'Results', icon: 'fa-file-lines', href: 'dashboard.html#results' },
      { label: 'Attendance', icon: 'fa-calendar-check', href: 'dashboard.html#attendance' },
      { label: 'Fees & Payments', icon: 'fa-sack-dollar', href: 'dashboard.html#fees' }
    ]},
    { section: 'Communication', items: [{ label: 'Announcements', icon: 'fa-bullhorn', href: 'dashboard.html#announcements' }] }
  ],
  student: [
    { items: [{ label: 'Dashboard', icon: 'fa-gauge-high', href: 'dashboard.html' }] },
    { section: 'My Academics', items: [
      { label: 'Subjects & Results', icon: 'fa-file-lines', href: 'dashboard.html#results' },
      { label: 'Attendance', icon: 'fa-calendar-check', href: 'dashboard.html#attendance' },
      { label: 'Examinations', icon: 'fa-laptop', href: 'dashboard.html#exams' },
      { label: 'Timetable', icon: 'fa-table-cells', href: 'dashboard.html#timetable' },
      { label: 'Fees', icon: 'fa-sack-dollar', href: 'dashboard.html#fees' }
    ]},
    { section: 'Communication', items: [{ label: 'Announcements', icon: 'fa-bullhorn', href: 'dashboard.html#announcements' }] }
  ]
};

const ROLE_LABEL = { admin: 'Administrator', teacher: 'Teacher', parent: 'Parent', student: 'Student' };

function renderSidebarHtml(role) {
  const groups = NAV_BY_ROLE[role] || [];
  const currentFile = window.location.pathname.split('/').pop() || 'index.html';
  const currentHash = window.location.hash;
  const navHtml = groups.map(g => `
    <div class="nav-section">
      ${g.section ? `<div class="nav-section-title">${g.section}</div>` : ''}
      ${g.items.map(it => {
        const [file, hash] = it.href.split('#');
        const isActive = file === currentFile && (hash ? ('#' + hash) === currentHash : !currentHash);
        return `<a href="${it.href}" class="${isActive ? 'active' : ''}"><i class="fa-solid ${it.icon}"></i> ${it.label}</a>`;
      }).join('')}
    </div>`).join('');

  return `
    <div class="sidebar-brand">
      <div class="brand-mark">GFA</div>
      <div>
        <div class="name">Glittering Field<br>Academy</div>
        <div class="role-tag">${ROLE_LABEL[role]} Console</div>
      </div>
    </div>
    <nav class="sidebar-nav">${navHtml}</nav>`;
}

function renderTopbarHtml(title, subtitle) {
  const db = DB.load();
  const recentAnnouncements = (db.announcements || []).slice(0, 4);
  return `
    <div class="left">
      <button class="sidebar-toggle"><i class="fa-solid fa-bars"></i></button>
      <div>
        <h1 style="font-size:1.25rem;margin:0;">${title}</h1>
        ${subtitle ? `<div class="sub text-sm text-muted">${subtitle}</div>` : ''}
      </div>
    </div>
    <div class="right">
      <button class="topbar-icon-btn" data-dropdown-toggle="notifDropdown"><i class="fa-solid fa-bell"></i><span class="dot"></span></button>
      <div class="topbar-profile" data-dropdown-toggle="profileDropdown">
        <div class="avatar" data-user-initials>U</div>
        <div class="info"><strong data-user-name>User</strong><span data-user-role>Role</span></div>
        <i class="fa-solid fa-chevron-down chev"></i>
      </div>
    </div>
    <div class="dropdown-menu" id="notifDropdown" style="width:320px;">
      <div class="dd-header">Recent Announcements</div>
      ${recentAnnouncements.map(a => `<div class="notif-item"><i class="fa-solid fa-bullhorn"></i><div><p>${a.title}</p><span>${formatDate(a.date)}</span></div></div>`).join('')}
    </div>
    <div class="dropdown-menu" id="profileDropdown">
      <div class="dd-header">Signed in as <strong data-user-name>User</strong></div>
      <a href="#" onclick="toast('Profile settings coming soon.','info');return false;"><i class="fa-solid fa-user"></i> My Profile</a>
      <a href="../dashboard/settings.html" class="admin-only-link" style="display:none;"><i class="fa-solid fa-gear"></i> Settings</a>
      <button data-logout><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</button>
    </div>`;
}

/**
 * Builds the full dashboard shell for a page.
 * opts: { role, roles (array allowed to view this page), title, subtitle }
 */
function initDashLayout(opts) {
  const session = Auth.requireRole(opts.roles || [opts.role]);
  if (!session) return null;

  document.body.classList.add('dash-body');
  const shell = document.createElement('div');
  shell.className = 'dash-shell';
  shell.innerHTML = `
    <div class="sidebar-overlay"></div>
    <aside class="sidebar">${renderSidebarHtml(opts.role)}</aside>
    <div class="dash-main">
      <header class="dash-topbar">${renderTopbarHtml(opts.title, opts.subtitle)}</header>
      <main class="dash-content" id="dashContent"></main>
    </div>`;
  document.body.appendChild(shell);
  initDashboardShell();
  return session;
}

/** Simple tab-switch helper reused by every dashboard page with #hash tabs. */
function initHashTabs(defaultTab) {
  function activate(tab) {
    document.querySelectorAll('[data-tabkey]').forEach(btn => btn.classList.toggle('active', btn.dataset.tabkey === tab));
    document.querySelectorAll('[data-tabpanel]').forEach(p => p.classList.toggle('active', p.dataset.tabpanel === tab));
    document.querySelectorAll('[data-tabpanel]').forEach(p => p.style.display = p.dataset.tabpanel === tab ? 'block' : 'none');
    // Keep the sidebar link for this tab highlighted too, since it lives outside this panel.
    document.querySelectorAll('.sidebar-nav a').forEach(a => {
      const hash = (a.getAttribute('href') || '').split('#')[1];
      if (hash) a.classList.toggle('active', hash === tab);
    });
  }
  document.querySelectorAll('[data-tabkey]').forEach(btn => {
    btn.addEventListener('click', () => { window.location.hash = btn.dataset.tabkey; });
  });
  // Sidebar links (and any other in-page links) that point to "#tab" change the hash without
  // reloading the page, so listen for hashchange to keep the visible panel in sync.
  window.addEventListener('hashchange', () => activate(window.location.hash.replace('#', '') || defaultTab));
  activate(window.location.hash.replace('#', '') || defaultTab);
}
