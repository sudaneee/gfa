/* ==========================================================================
   STORAGE LAYER — wraps localStorage and simulates a backend database
   for the Glittering Field Academy demo prototype.
   ========================================================================== */

const DB_KEY = 'gfa_db_v1';
const AUTH_KEY = 'gfa_auth_v1';

const DemoAccounts = [
  { role: 'admin', email: 'admin@gfa.edu.ng', password: 'admin123', name: 'School Administrator' },
  { role: 'teacher', email: 'teacher@gfa.edu.ng', password: 'teacher123', name: 'Grace Adeyemi', refId: 'TCH-DEMO-01' },
  { role: 'parent', email: 'parent@gfa.edu.ng', password: 'parent123', name: 'Ibrahim Musa', refId: 'PAR-DEMO-01' },
  { role: 'student', email: 'student@gfa.edu.ng', password: 'student123', name: 'Muhammad Ibrahim', refId: 'STU-DEMO-02' }
];

const DB = {
  /** Load the whole database, seeding it on first run. */
  load() {
    let raw = localStorage.getItem(DB_KEY);
    if (!raw) {
      const seed = buildSeedData();
      localStorage.setItem(DB_KEY, JSON.stringify(seed));
      return seed;
    }
    try { return JSON.parse(raw); } catch (e) {
      const seed = buildSeedData();
      localStorage.setItem(DB_KEY, JSON.stringify(seed));
      return seed;
    }
  },
  save(db) { localStorage.setItem(DB_KEY, JSON.stringify(db)); },
  reset() {
    const seed = buildSeedData();
    localStorage.setItem(DB_KEY, JSON.stringify(seed));
    return seed;
  },
  /** Convenience: mutate a collection then persist. fn receives the db and should mutate it. */
  update(fn) {
    const db = DB.load();
    fn(db);
    DB.save(db);
    return db;
  }
};

/* ---------------------------------------------------------------------
   Auth (simulated — no real security, for demo purposes only)
   --------------------------------------------------------------------- */
const Auth = {
  login(email, password) {
    const account = DemoAccounts.find(a => a.email.toLowerCase() === String(email).toLowerCase() && a.password === password);
    if (!account) return null;
    const session = { role: account.role, email: account.email, name: account.name, refId: account.refId || null, loginAt: Date.now() };
    sessionStorage.setItem(AUTH_KEY, JSON.stringify(session));
    return session;
  },
  current() {
    const raw = sessionStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  logout() {
    sessionStorage.removeItem(AUTH_KEY);
    window.location.href = getBasePath() + 'login.html';
  },
  /** Redirect to login if not authenticated as one of the allowed roles. Returns the session. */
  requireRole(roles) {
    const session = Auth.current();
    if (!session || !roles.includes(session.role)) {
      window.location.href = getBasePath() + 'login.html';
      return null;
    }
    return session;
  }
};

/** Figures out the relative path back to the project root based on current URL depth. */
function getBasePath() {
  const path = window.location.pathname;
  const marker = '/dashboard/';
  if (path.includes('/dashboard/') || path.includes('/parent/') || path.includes('/teacher/') || path.includes('/student/')) {
    return '../';
  }
  return '';
}
