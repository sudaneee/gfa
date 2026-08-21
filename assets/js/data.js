/* ==========================================================================
   GLITTERING FIELD ACADEMY — DUMMY DATA GENERATOR
   Produces the full seed dataset used by storage.js on first run (or after
   "Reset Demo Data"). Everything here is fictional.
   ========================================================================== */

const SCHOOL = {
  name: 'Glittering Field Academy',
  tagline: 'Academics and Morality',
  slogan: 'Raising Leaders, Building Future',
  address: 'No. 5 Yarima Dalhatu Crescent, Suleja, Niger State',
  session: '2026/2027',
  approvals: ['WAEC APPROVED', 'NECO APPROVED', 'NBAIS APPROVED'],
  phones: ['08117436216', '08102969721', '08164348041', '08070378565'],
  email: 'info@glitteringfieldacademy.edu.ng'
};

const LEVELS = ['Creche', 'Pre-Nursery', 'Nursery', 'Primary', 'Secondary'];

const CLASS_LIST = [
  { name: 'Creche', level: 'Creche', sections: ['A'] },
  { name: 'Pre-Nursery', level: 'Pre-Nursery', sections: ['A'] },
  { name: 'Nursery 1', level: 'Nursery', sections: ['A'] },
  { name: 'Nursery 2', level: 'Nursery', sections: ['A'] },
  { name: 'Primary 1', level: 'Primary', sections: ['A', 'B'] },
  { name: 'Primary 2', level: 'Primary', sections: ['A', 'B'] },
  { name: 'Primary 3', level: 'Primary', sections: ['A', 'B'] },
  { name: 'Primary 4', level: 'Primary', sections: ['A', 'B'] },
  { name: 'Primary 5', level: 'Primary', sections: ['A', 'B'] },
  { name: 'Primary 6', level: 'Primary', sections: ['A', 'B'] },
  { name: 'JSS 1', level: 'Secondary', sections: ['A', 'B'] },
  { name: 'JSS 2', level: 'Secondary', sections: ['A', 'B'] },
  { name: 'JSS 3', level: 'Secondary', sections: ['A', 'B'] },
  { name: 'SSS 1', level: 'Secondary', sections: ['A', 'B'] },
  { name: 'SSS 2', level: 'Secondary', sections: ['A', 'B'] },
  { name: 'SSS 3', level: 'Secondary', sections: ['A', 'B'] }
];

const SUBJECTS_BY_LEVEL = {
  'Creche': ['Numeracy', 'Literacy', 'Rhymes & Music', 'Creative Arts'],
  'Pre-Nursery': ['Numeracy', 'Literacy', 'Phonics', 'Creative Arts', 'Social Habits'],
  'Nursery': ['Numeracy', 'Literacy', 'Phonics', 'Creative Arts', 'Social Habits', 'Physical Education'],
  'Primary': ['English Studies', 'Mathematics', 'Basic Science', 'Social Studies', 'Civic Education', 'Computer Studies', 'Agricultural Science', 'Home Economics', 'Physical & Health Education', 'CRS', 'Fine Arts'],
  'Secondary': ['English Language', 'Mathematics', 'Basic Science', 'Basic Technology', 'Business Studies', 'Social Studies', 'Civic Education', 'Computer Studies', 'French', 'Agricultural Science', 'CRS', 'Physical & Health Education']
};

const TERMS = ['First Term', 'Second Term', 'Third Term'];
const CURRENT_SESSION = '2026/2027';
const CURRENT_TERM = 'First Term';

const GRADE_BOUNDARIES = [
  { grade: 'A', min: 70, max: 100, point: 5, remark: 'Excellent' },
  { grade: 'B', min: 60, max: 69, point: 4, remark: 'Very Good' },
  { grade: 'C', min: 50, max: 59, point: 3, remark: 'Good' },
  { grade: 'D', min: 45, max: 49, point: 2, remark: 'Fair' },
  { grade: 'E', min: 40, max: 44, point: 1, remark: 'Pass' },
  { grade: 'F', min: 0, max: 39, point: 0, remark: 'Fail' }
];

function gradeFor(total) {
  return GRADE_BOUNDARIES.find(g => total >= g.min && total <= g.max) || GRADE_BOUNDARIES[GRADE_BOUNDARIES.length - 1];
}

const FEE_STRUCTURE = {
  'Creche': [['Tuition', 45000], ['Registration', 10000], ['ICT', 3000], ['Feeding', 15000], ['Other Charges', 4000]],
  'Pre-Nursery': [['Tuition', 48000], ['Registration', 10000], ['ICT', 3000], ['Feeding', 15000], ['Other Charges', 4000]],
  'Nursery': [['Tuition', 52000], ['Registration', 10000], ['ICT', 4000], ['Books', 8000], ['Other Charges', 4000]],
  'Primary': [['Tuition', 65000], ['Registration', 8000], ['Examination', 5000], ['ICT', 5000], ['Transport', 12000], ['Uniform', 9000], ['Books', 10000], ['Other Charges', 4000]],
  'Secondary': [['Tuition', 85000], ['Registration', 8000], ['Examination', 8000], ['ICT', 6000], ['Transport', 14000], ['Uniform', 10000], ['Books', 12000], ['Other Charges', 5000]]
};

/* ---------------------------------------------------------------------
   Name pools (fictional)
   --------------------------------------------------------------------- */
const MALE_NAMES = ['Muhammad', 'Ibrahim', 'Abdullahi', 'Yusuf', 'Suleiman', 'Aliyu', 'Emmanuel', 'Chinedu', 'Samuel', 'David', 'Daniel', 'Joseph', 'Peter', 'Musa', 'Umar', 'Bashir', 'Sani', 'Kabiru', 'Victor', 'Ahmad', 'Tunde', 'Segun', 'Femi', 'Chukwuemeka', 'Godwin'];
const FEMALE_NAMES = ['Aisha', 'Fatima', 'Zainab', 'Hauwa', 'Amina', 'Blessing', 'Grace', 'Mary', 'Ruth', 'Esther', 'Comfort', 'Faith', 'Chioma', 'Ngozi', 'Halima', 'Rahma', 'Success', 'Precious', 'Deborah', 'Sarah', 'Maryam', 'Bilkisu', 'Toyin', 'Funmilayo', 'Patience'];
const SURNAMES = ['Ibrahim', 'Musa', 'Abdullahi', 'Yakubu', 'Suleiman', 'Bello', 'Garba', 'Sani', 'Aliyu', 'Umar', 'Danjuma', 'Okafor', 'Eze', 'Nwosu', 'Chukwu', 'Okoro', 'Adeyemi', 'Balogun', 'Ojo', 'Afolabi', 'Etim', 'Okon', 'Yusuf', 'Mohammed', 'Hassan', 'Oladipo', 'Onyema', 'Attah', 'Idris', 'Danladi'];
const STATES = ['Niger', 'Kaduna', 'Kano', 'FCT Abuja', 'Kogi', 'Nasarawa', 'Plateau', 'Katsina', 'Lagos', 'Ogun'];
const LGAS = ['Suleja', 'Tafa', 'Gurara', 'Chanchaga', 'Bosso', 'Shiroro', 'Minna', 'Rafi', 'Wushishi'];
const OCCUPATIONS = ['Civil Servant', 'Trader', 'Engineer', 'Nurse', 'Teacher', 'Business Owner', 'Banker', 'Accountant', 'Farmer', 'Driver', 'Tailor', 'Contractor', 'Lawyer', 'Pharmacist'];
const DEPARTMENTS = ['Mathematics', 'English Language', 'Sciences', 'Social Studies', 'ICT', 'Early Years', 'Languages', 'Vocational Studies'];

function pick(arr, seed) { return arr[seed % arr.length]; }
function initials(first, last) { return (first[0] + last[0]).toUpperCase(); }
function pad(n, len) { return String(n).padStart(len, '0'); }

/* ---------------------------------------------------------------------
   Demo anchor records — kept stable so the four demo logins always have
   coherent, cross-linked data (results, attendance, fees, exams...).
   --------------------------------------------------------------------- */
const DEMO_PARENT_ID = 'PAR-DEMO-01';
const DEMO_STUDENT_1_ID = 'STU-DEMO-01'; // Aisha Ibrahim - Primary 5
const DEMO_STUDENT_2_ID = 'STU-DEMO-02'; // Muhammad Ibrahim - JSS 2
const DEMO_TEACHER_ID = 'TCH-DEMO-01';   // Mrs. Grace Adeyemi

function buildStudents() {
  const students = [];

  students.push({
    id: DEMO_STUDENT_1_ID, admissionNo: 'GFA/PRY/2023/014', firstName: 'Aisha', lastName: 'Ibrahim',
    gender: 'Female', dob: '2016-03-11', class: 'Primary 5', section: 'A', level: 'Primary',
    guardianId: DEMO_PARENT_ID, status: 'Active', admissionDate: '2023-09-04'
  });
  students.push({
    id: DEMO_STUDENT_2_ID, admissionNo: 'GFA/JSS/2022/031', firstName: 'Muhammad', lastName: 'Ibrahim',
    gender: 'Male', dob: '2013-07-22', class: 'JSS 2', section: 'A', level: 'Secondary',
    guardianId: DEMO_PARENT_ID, status: 'Active', admissionDate: '2022-09-05'
  });

  const eligibleClasses = CLASS_LIST; // spread across all levels
  let counter = 1;
  for (let i = 0; i < 43; i++) {
    const gender = i % 2 === 0 ? 'Male' : 'Female';
    const first = gender === 'Male' ? pick(MALE_NAMES, i * 3 + 1) : pick(FEMALE_NAMES, i * 3 + 1);
    const last = pick(SURNAMES, i * 5 + 2);
    const cls = eligibleClasses[i % eligibleClasses.length];
    const section = cls.sections[i % cls.sections.length];
    const yearCode = cls.level === 'Secondary' ? '20' + (22 + (i % 4)) : '20' + (23 + (i % 3));
    const admissionNo = `GFA/${cls.level.slice(0, 3).toUpperCase()}/${yearCode}/${pad(counter, 3)}`;
    counter++;
    students.push({
      id: `STU-${pad(i + 1, 3)}`, admissionNo, firstName: first, lastName: last, gender,
      dob: `${2010 + (i % 12)}-0${(i % 9) + 1}-1${i % 9}`, class: cls.name, section, level: cls.level,
      guardianId: null, status: i % 17 === 0 ? 'Inactive' : 'Active', admissionDate: `${yearCode}-09-0${(i % 8) + 1}`
    });
  }
  return students;
}

function buildParents(students) {
  const parents = [];
  parents.push({
    id: DEMO_PARENT_ID, name: 'Ibrahim Musa', relationship: 'Father', phone: '08117436216',
    email: 'parent@gfa.edu.ng', address: 'No. 12 Almara Street, Suleja, Niger State', occupation: 'Civil Servant',
    childrenIds: [DEMO_STUDENT_1_ID, DEMO_STUDENT_2_ID]
  });

  // Pair up remaining students (skip demo ones) into households of 1-2 children
  const remaining = students.filter(s => !s.guardianId);
  let i = 0, pIndex = 1;
  while (i < remaining.length) {
    const takeTwo = i + 1 < remaining.length && (i % 3 === 0);
    const kids = takeTwo ? [remaining[i], remaining[i + 1]] : [remaining[i]];
    const gender = pIndex % 2 === 0 ? 'Male' : 'Female';
    const first = gender === 'Male' ? pick(MALE_NAMES, pIndex * 2) : pick(FEMALE_NAMES, pIndex * 2);
    const last = pick(SURNAMES, pIndex * 4 + 1);
    const parentId = `PAR-${pad(pIndex, 3)}`;
    kids.forEach(k => k.guardianId = parentId);
    parents.push({
      id: parentId, name: `${first} ${last}`, relationship: pick(['Father', 'Mother', 'Guardian'], pIndex),
      phone: `081${pad((pIndex * 7919) % 100000000, 8)}`, email: `${first.toLowerCase()}.${last.toLowerCase()}${pIndex}@example.com`,
      address: `No. ${pIndex + 3} ${pick(['Almara', 'Dalhatu', 'Kuchi', 'Zuma', 'Gwari'], pIndex)} Street, Suleja, Niger State`,
      occupation: pick(OCCUPATIONS, pIndex), childrenIds: kids.map(k => k.id)
    });
    i += takeTwo ? 2 : 1;
    pIndex++;
  }
  return parents;
}

function buildTeachers() {
  const teachers = [];
  teachers.push({
    id: DEMO_TEACHER_ID, staffId: 'GFA/STAFF/014', name: 'Grace Adeyemi', gender: 'Female',
    department: 'Mathematics', subjects: ['Mathematics', 'Basic Science'], classes: ['JSS 2A', 'JSS 2B', 'Primary 5A'],
    phone: '08102969721', email: 'teacher@gfa.edu.ng', qualification: 'B.Sc. Ed. Mathematics', employmentDate: '2020-01-12', status: 'Active'
  });
  const names = [
    ['Male', 'Yusuf', 'Bello'], ['Female', 'Comfort', 'Nwosu'], ['Male', 'Emmanuel', 'Okoro'],
    ['Female', 'Halima', 'Garba'], ['Male', 'Peter', 'Etim'], ['Female', 'Faith', 'Balogun'],
    ['Male', 'Suleiman', 'Danjuma'], ['Female', 'Ngozi', 'Chukwu'], ['Male', 'Victor', 'Afolabi'],
    ['Female', 'Zainab', 'Sani'], ['Male', 'Daniel', 'Oladipo'], ['Female', 'Success', 'Idris']
  ];
  names.forEach((n, i) => {
    const [gender, first, last] = n;
    const dept = pick(DEPARTMENTS, i);
    const level = pick(['Creche', 'Nursery', 'Primary', 'Secondary'], i);
    const classesPool = CLASS_LIST.filter(c => c.level === level || (level === 'Nursery' && c.level === 'Pre-Nursery'));
    const assigned = classesPool.slice(0, 2).flatMap(c => c.sections.map(s => `${c.name}${s}`));
    teachers.push({
      id: `TCH-${pad(i + 1, 3)}`, staffId: `GFA/STAFF/${pad(i + 20, 3)}`, name: `${first} ${last}`, gender,
      department: dept, subjects: (SUBJECTS_BY_LEVEL[level] || SUBJECTS_BY_LEVEL['Primary']).slice(0, 3),
      classes: assigned.slice(0, 3), phone: `080${pad((i * 991) % 100000000, 8)}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}@gfa.edu.ng`,
      qualification: pick(['B.Sc. Ed.', 'B.A. Ed.', 'NCE', 'B.Ed.', 'M.Ed.'], i), employmentDate: `20${18 + (i % 6)}-0${(i % 8) + 1}-1${i % 9}`,
      status: 'Active'
    });
  });
  return teachers;
}

const APP_STATUSES = ['Pending', 'Under Review', 'Shortlisted', 'Interview', 'Approved', 'Rejected', 'Admitted'];
const STATUS_FLOW = ['Submitted', 'Under Review', 'Shortlisted', 'Interview', 'Approved', 'Admitted'];

function buildApplications() {
  const apps = [];
  const statuses = ['Pending', 'Under Review', 'Under Review', 'Shortlisted', 'Interview', 'Approved', 'Approved', 'Rejected', 'Admitted', 'Admitted', 'Pending', 'Under Review', 'Shortlisted', 'Approved', 'Pending', 'Rejected', 'Under Review', 'Admitted'];
  statuses.forEach((status, i) => {
    const gender = i % 2 === 0 ? 'Male' : 'Female';
    const first = gender === 'Male' ? pick(MALE_NAMES, i * 7 + 3) : pick(FEMALE_NAMES, i * 7 + 3);
    const middle = gender === 'Male' ? pick(MALE_NAMES, i * 11 + 5) : pick(FEMALE_NAMES, i * 11 + 5);
    const last = pick(SURNAMES, i * 9 + 4);
    const level = pick(['Creche', 'Pre-Nursery', 'Nursery', 'Primary', 'Secondary'], i);
    const classesForLevel = CLASS_LIST.filter(c => c.level === level);
    const appliedClass = pick(classesForLevel, i).name;
    const parentGender = i % 2 === 0 ? 'Female' : 'Male';
    const pFirst = parentGender === 'Male' ? pick(MALE_NAMES, i * 3) : pick(FEMALE_NAMES, i * 3);
    const day = pad((i % 27) + 1, 2);
    const appDate = `2026-0${(i % 7) + 1}-${day}`;
    const applicationNo = `GFA-2026-${pad(100 + i, 6)}`;
    const submitted = new Date(appDate);
    const timeline = STATUS_FLOW.slice(0, STATUS_FLOW.indexOf(status === 'Pending' ? 'Submitted' : status === 'Rejected' ? 'Under Review' : status) + 1)
      .map((stage, si) => ({ stage, date: new Date(submitted.getTime() + si * 86400000 * 3).toISOString().slice(0, 10) }));
    apps.push({
      applicationNo, firstName: first, middleName: middle, lastName: last, dob: `${2015 + (i % 10)}-0${(i % 9) + 1}-1${i % 8}`,
      gender, nationality: 'Nigerian', state: pick(STATES, i), lga: pick(LGAS, i),
      previousSchool: i % 4 === 0 ? '' : `${pick(['Bright Start', 'Sunshine', 'Kings', 'Hilltop', 'Noble'], i)} School`,
      previousClass: i % 4 === 0 ? '' : appliedClass,
      parentName: `${pFirst} ${last}`, relationship: pick(['Father', 'Mother', 'Guardian'], i), phone: `081${pad((i * 3331) % 100000000, 8)}`,
      email: `${pFirst.toLowerCase()}.${last.toLowerCase()}@example.com`, address: `No. ${i + 5} ${pick(['Yarima', 'Dalhatu', 'Zuma', 'Kuchi'], i)} Crescent, Suleja`,
      occupation: pick(OCCUPATIONS, i), applyingFor: appliedClass, level,
      previousPerformance: i % 4 === 0 ? 'First time in school' : pick(['Excellent', 'Very Good', 'Good'], i),
      documents: { passport: 'passport_photo.jpg', birthCert: 'birth_certificate.pdf', previousResult: i % 4 === 0 ? '' : 'last_result.pdf', other: '' },
      status: status === 'Pending' ? 'Pending' : status, applicationDate: appDate, timeline
    });
  });
  return apps;
}

function buildFeesAndPayments(students) {
  const invoices = [];
  const payments = [];
  let invCounter = 1, payCounter = 1;
  students.filter(s => s.status === 'Active').forEach((s, i) => {
    const items = FEE_STRUCTURE[s.level] || FEE_STRUCTURE['Primary'];
    const total = items.reduce((sum, it) => sum + it[1], 0);
    const scenario = i % 4; // 0 fully paid, 1 partial, 2 unpaid, 3 fully paid
    const paid = scenario === 0 || scenario === 3 ? total : scenario === 1 ? Math.round(total * 0.5) : 0;
    const invoiceId = `INV-${CURRENT_SESSION.slice(0, 4)}-${pad(invCounter++, 4)}`;
    invoices.push({
      id: invoiceId, studentId: s.id, session: CURRENT_SESSION, term: CURRENT_TERM,
      items: items.map(it => ({ category: it[0], amount: it[1] })), total, paid,
      balance: total - paid, status: paid === 0 ? 'Unpaid' : paid >= total ? 'Paid' : 'Partial',
      dueDate: '2026-09-30', issueDate: '2026-09-01'
    });
    if (paid > 0) {
      payments.push({
        id: `PAY-${pad(payCounter, 4)}`, invoiceId, studentId: s.id, amount: paid,
        method: pick(['Card', 'Bank Transfer', 'USSD'], i), date: `2026-09-${pad((i % 20) + 5, 2)}`,
        receiptNo: `RCT-${pad(1000 + payCounter, 5)}`, status: 'Successful'
      });
      payCounter++;
    }
  });
  return { invoices, payments };
}

function buildResults(students, teachers) {
  const results = [];
  students.filter(s => s.status === 'Active').forEach((s, i) => {
    const subjects = (SUBJECTS_BY_LEVEL[s.level] || SUBJECTS_BY_LEVEL['Primary']).slice(0, 6);
    subjects.forEach((subj, si) => {
      const ca = 15 + ((i + si * 3) % 16); // 15-30
      const exam = 35 + ((i * 2 + si * 5) % 41); // 35-75
      const total = Math.min(ca + exam, 100);
      const g = gradeFor(total);
      results.push({
        studentId: s.id, session: CURRENT_SESSION, term: CURRENT_TERM, subject: subj,
        ca, exam, total, grade: g.grade, point: g.point, remark: g.remark,
        teacherId: teachers[(i + si) % teachers.length].id
      });
    });
  });
  return results;
}

function buildAttendance(students) {
  const records = [];
  const activeStudents = students.filter(s => s.status === 'Active');
  // Generate weekdays for the last 4 weeks
  const days = [];
  let d = new Date('2026-08-17');
  while (days.length < 20) {
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) days.push(new Date(d));
    d.setDate(d.getDate() - 1);
  }
  days.reverse();
  activeStudents.forEach((s, si) => {
    days.forEach((day, di) => {
      const roll = (si * 13 + di * 7) % 100;
      const status = roll < 84 ? 'Present' : roll < 94 ? 'Absent' : 'Late';
      records.push({ studentId: s.id, class: s.class + s.section, date: day.toISOString().slice(0, 10), status });
    });
  });
  return records;
}

/* ---------------------------------------------------------------------
   CBT Examinations
   --------------------------------------------------------------------- */
const EXAMS = [
  {
    id: 'EXM-001', title: 'Basic Computer Studies', level: 'Primary', class: 'Primary 6', subject: 'Computer Studies',
    durationMinutes: 15, instructions: 'Answer all 10 questions. Each question carries equal marks. Do not refresh the page during the exam.',
    questions: [
      { q: 'What does CPU stand for?', options: ['Central Process Unit', 'Central Processing Unit', 'Computer Personal Unit', 'Central Processor Utility'], answer: 1 },
      { q: 'Which of these is an input device?', options: ['Monitor', 'Printer', 'Keyboard', 'Speaker'], answer: 2 },
      { q: 'A computer mouse is used to ______.', options: ['Type text', 'Point and click', 'Print documents', 'Play sound'], answer: 1 },
      { q: 'Which device is used to display computer output?', options: ['Monitor', 'Keyboard', 'Mouse', 'Scanner'], answer: 0 },
      { q: 'MS Word is an example of a ______.', options: ['Hardware', 'Operating System', 'Word Processor', 'Printer'], answer: 2 },
      { q: 'The brain of the computer is the ______.', options: ['Monitor', 'CPU', 'Keyboard', 'Mouse'], answer: 1 },
      { q: 'Which of these stores data permanently?', options: ['RAM', 'Hard Disk', 'Cache', 'Monitor'], answer: 1 },
      { q: 'A device that lets you print a document is called a ______.', options: ['Scanner', 'Printer', 'Projector', 'Modem'], answer: 1 },
      { q: 'Which key is used to create a new line in a document?', options: ['Shift', 'Enter', 'Tab', 'Ctrl'], answer: 1 },
      { q: 'The full meaning of ICT is ______.', options: ['Information and Computer Tools', 'Information and Communication Technology', 'Internet Computer Technology', 'Information Coding Technique'], answer: 1 }
    ]
  },
  {
    id: 'EXM-002', title: 'Mathematics Mid-Term Test', level: 'Secondary', class: 'JSS 2', subject: 'Mathematics',
    durationMinutes: 20, instructions: 'Answer all questions. Calculators are not allowed. Submit before the timer runs out.',
    questions: [
      { q: 'Simplify: 7 + 3 × 2', options: ['20', '13', '17', '10'], answer: 1 },
      { q: 'What is the value of x in 2x = 18?', options: ['7', '8', '9', '10'], answer: 2 },
      { q: 'Convert 0.75 to a fraction.', options: ['3/4', '2/3', '4/5', '1/2'], answer: 0 },
      { q: 'The sum of angles in a triangle is ______.', options: ['90°', '180°', '270°', '360°'], answer: 1 },
      { q: 'What is the LCM of 4 and 6?', options: ['10', '12', '18', '24'], answer: 1 },
      { q: '15% of 200 is ______.', options: ['20', '25', '30', '35'], answer: 2 },
      { q: 'Which of these is a prime number?', options: ['9', '15', '17', '21'], answer: 2 },
      { q: 'Solve: 5x - 4 = 16', options: ['4', '5', '6', '3'], answer: 0 },
      { q: 'The perimeter of a square with side 6cm is ______.', options: ['12cm', '18cm', '24cm', '36cm'], answer: 2 },
      { q: 'Express 3/5 as a percentage.', options: ['50%', '60%', '65%', '75%'], answer: 1 }
    ]
  },
  {
    id: 'EXM-003', title: 'English Language Quiz', level: 'Secondary', class: 'SSS 1', subject: 'English Language',
    durationMinutes: 15, instructions: 'Choose the most appropriate option for each question.',
    questions: [
      { q: 'Choose the correct spelling.', options: ['Recieve', 'Receive', 'Receeve', 'Receve'], answer: 1 },
      { q: 'Identify the noun in: "The teacher praised the student."', options: ['Praised', 'The', 'Teacher', 'Quickly'], answer: 2 },
      { q: 'What is the synonym of "Happy"?', options: ['Sad', 'Joyful', 'Angry', 'Tired'], answer: 1 },
      { q: 'Choose the correct form: She ___ to school every day.', options: ['go', 'goes', 'going', 'gone'], answer: 1 },
      { q: 'What is the antonym of "Difficult"?', options: ['Hard', 'Easy', 'Complex', 'Tough'], answer: 1 },
      { q: 'Identify the verb: "They quickly ran to the field."', options: ['Quickly', 'Ran', 'Field', 'They'], answer: 1 },
      { q: 'A group of words with a subject and verb is called a ______.', options: ['Phrase', 'Clause', 'Adjective', 'Preposition'], answer: 1 },
      { q: 'Choose the plural of "Child".', options: ['Childs', 'Childes', 'Children', 'Childern'], answer: 2 },
      { q: 'Which sentence is punctuated correctly?', options: ['i am happy', 'I am happy.', 'I Am happy', 'i Am Happy.'], answer: 1 },
      { q: 'Choose the correct comparative form of "Good".', options: ['Gooder', 'Best', 'Better', 'More good'], answer: 2 }
    ]
  }
];

const ANNOUNCEMENTS = [
  { id: 'ANN-001', title: 'Resumption Date for 2026/2027 First Term', content: 'All students are to resume for the First Term on Monday, 8th September 2026. Parents are to ensure all fees are paid before resumption.', audience: 'All Parents', date: '2026-08-15', status: 'Published' },
  { id: 'ANN-002', title: 'Inter-House Sports Competition', content: 'The annual Inter-House Sports Competition holds on Saturday, 26th September 2026 at the school field. Parents are invited.', audience: 'All Parents', date: '2026-08-10', status: 'Published' },
  { id: 'ANN-003', title: 'Mid-Term Examination Timetable Released', content: 'The Mid-Term examination timetable has been released. Students should check the Examinations section on their portal.', audience: 'Students', date: '2026-08-05', status: 'Published' },
  { id: 'ANN-004', title: 'Staff Development Workshop', content: 'All teaching staff are to attend a mandatory ICT & Digital Learning workshop on Friday, 21st August 2026.', audience: 'Teachers', date: '2026-08-02', status: 'Published' },
  { id: 'ANN-005', title: 'PTA General Meeting', content: 'The first PTA general meeting of the 2026/2027 session will hold on Saturday, 12th September 2026 by 10:00 AM in the school hall.', audience: 'All Parents', date: '2026-07-28', status: 'Published' },
  { id: 'ANN-006', title: 'Debate & Quiz Club Registration Open', content: 'Registration for the Debate Club, Quiz Club and Reading Club is now open. Interested students should see their class teacher.', audience: 'Students', date: '2026-07-20', status: 'Published' }
];

const EVENTS = [
  { id: 'EVT-001', title: 'Inter-House Sports Competition', date: '2026-09-26', category: 'Sports', description: 'Annual sporting event featuring track and field events across all houses.' },
  { id: 'EVT-002', title: 'Inter-School Debate Championship', date: '2026-10-10', category: 'Debate', description: 'Glittering Field Academy hosts the zonal inter-school debate championship.' },
  { id: 'EVT-003', title: 'Cultural Day & Quiz Competition', date: '2026-11-14', category: 'Cultural', description: 'Celebrating Nigerian culture with a quiz competition and cultural displays.' },
  { id: 'EVT-004', title: 'First Term PTA Meeting', date: '2026-09-12', category: 'Meeting', description: 'General meeting for parents and teachers to review the term progress.' },
  { id: 'EVT-005', title: 'Career Day', date: '2026-11-28', category: 'Academic', description: 'Professionals visit to speak with secondary students about career paths.' },
  { id: 'EVT-006', title: 'End of Term Prize-Giving Day', date: '2026-12-11', category: 'Academic', description: 'Celebrating outstanding students at the end of the First Term.' },
  { id: 'EVT-007', title: 'Reading Club Book Fair', date: '2026-07-15', category: 'Academic', description: 'Students showcased projects from the Reading Club book fair.', past: true }
];

const CALENDAR_EVENTS = {
  '2026-09-08': 'Resumption for First Term',
  '2026-09-12': 'PTA General Meeting',
  '2026-09-26': 'Inter-House Sports',
  '2026-10-10': 'Debate Championship',
  '2026-10-19': 'Mid-Term Break Begins',
  '2026-11-14': 'Cultural Day',
  '2026-11-28': 'Career Day',
  '2026-12-08': 'First Term Examinations Begin',
  '2026-12-11': 'Prize-Giving Day',
  '2026-12-18': 'First Term Ends'
};

function buildTimetable() {
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const periods = ['8:00 - 8:40', '8:40 - 9:20', '9:20 - 10:00', '10:00 - 10:20', '10:20 - 11:00', '11:00 - 11:40', '11:40 - 12:20', '12:20 - 1:00'];
  const timetable = {};
  ['Primary 5A', 'JSS 2A', 'JSS 2B', 'SSS 1A'].forEach((cls, ci) => {
    const level = cls.startsWith('Primary') ? 'Primary' : 'Secondary';
    const subjects = SUBJECTS_BY_LEVEL[level];
    timetable[cls] = {};
    days.forEach((day, di) => {
      timetable[cls][day] = periods.map((p, pi) => {
        if (pi === 3) return { period: p, subject: 'BREAK', teacher: '' };
        const subj = subjects[(ci + di + pi) % subjects.length];
        return { period: p, subject: subj, teacher: pick(['Mrs. Adeyemi', 'Mr. Bello', 'Mrs. Nwosu', 'Mr. Okoro', 'Mrs. Garba', 'Mr. Etim'], ci + di + pi) };
      });
    });
  });
  return timetable;
}

/* ---------------------------------------------------------------------
   Master seed builder
   --------------------------------------------------------------------- */
function buildSeedData() {
  const students = buildStudents();
  const parents = buildParents(students);
  const teachers = buildTeachers();
  const applications = buildApplications();
  const { invoices, payments } = buildFeesAndPayments(students);
  const results = buildResults(students, teachers);
  const attendance = buildAttendance(students);
  const timetable = buildTimetable();

  return {
    school: SCHOOL, students, parents, teachers, applications,
    invoices, payments, results, attendance, exams: EXAMS,
    examAttempts: [], announcements: ANNOUNCEMENTS, events: EVENTS,
    calendarEvents: CALENDAR_EVENTS, timetable,
    classes: CLASS_LIST, subjectsByLevel: SUBJECTS_BY_LEVEL, gradeBoundaries: GRADE_BOUNDARIES,
    feeStructure: FEE_STRUCTURE
  };
}
