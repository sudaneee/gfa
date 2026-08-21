/* ==========================================================================
   EXAMINATIONS.JS — CBT exam-taking engine (countdown timer, navigation,
   auto-marking) used by student/exam.html
   ========================================================================== */

let examState = {
  exam: null, currentQ: 0, answers: {}, secondsLeft: 0, timerId: null, started: false
};

function initExam() {
  const params = new URLSearchParams(window.location.search);
  const examId = params.get('id');
  const db = DB.load();
  const exam = db.exams.find(e => e.id === examId);
  if (!exam) { document.getElementById('examRoot').innerHTML = '<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h4>Examination not found</h4></div>'; return; }
  examState.exam = exam;
  examState.secondsLeft = exam.durationMinutes * 60;
  renderInstructions();
}

function renderInstructions() {
  const exam = examState.exam;
  document.getElementById('examRoot').innerHTML = `
    <div class="card" style="max-width:700px;margin:0 auto;">
      <div class="card-header"><h3>${exam.title}</h3><span class="badge badge-purple">${exam.subject}</span></div>
      <div class="card-body">
        <div class="review-grid mb-24">
          <div class="item"><span class="k">Class</span><span class="v">${exam.class}</span></div>
          <div class="item"><span class="k">Questions</span><span class="v">${exam.questions.length}</span></div>
          <div class="item"><span class="k">Duration</span><span class="v">${exam.durationMinutes} minutes</span></div>
          <div class="item"><span class="k">Question Type</span><span class="v">Multiple Choice</span></div>
        </div>
        <div class="alert alert-info"><i class="fa-solid fa-circle-info"></i> ${exam.instructions}</div>
        <ul class="text-muted text-sm">
          <li>The timer starts as soon as you click "Start Examination" and cannot be paused.</li>
          <li>You can navigate between questions using Next/Previous or the question grid.</li>
          <li>Your exam will auto-submit when the timer reaches zero.</li>
        </ul>
        <button class="btn btn-primary btn-lg btn-block mt-16" id="startExamBtn"><i class="fa-solid fa-play"></i> Start Examination</button>
        <a href="dashboard.html#exams" class="btn btn-secondary btn-block mt-8">Cancel</a>
      </div>
    </div>`;
  document.getElementById('startExamBtn').addEventListener('click', startExam);
}

function startExam() {
  examState.started = true;
  examState.currentQ = 0;
  examState.answers = {};
  renderExamShell();
  startTimer();
}

function startTimer() {
  updateTimerDisplay();
  examState.timerId = setInterval(() => {
    examState.secondsLeft--;
    updateTimerDisplay();
    if (examState.secondsLeft <= 0) {
      clearInterval(examState.timerId);
      toast('Time is up! Submitting your examination automatically.', 'info');
      submitExam(true);
    }
  }, 1000);
}

function updateTimerDisplay() {
  const el = document.getElementById('examTimer');
  if (!el) return;
  const m = Math.floor(examState.secondsLeft / 60);
  const s = examState.secondsLeft % 60;
  el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  el.parentElement.classList.toggle('low', examState.secondsLeft <= 60);
}

function renderExamShell() {
  const exam = examState.exam;
  document.getElementById('examRoot').innerHTML = `
    <div class="flex-between mb-24 flex-wrap gap-12">
      <div><h2 class="mb-0">${exam.title}</h2><p class="text-muted mb-0">${exam.subject} &middot; ${exam.class}</p></div>
      <div class="exam-timer"><i class="fa-regular fa-clock"></i> <span id="examTimer">00:00</span></div>
    </div>
    <div class="exam-shell">
      <div class="card question-card"><div class="card-body" id="questionContainer"></div>
        <div class="card-footer flex-between">
          <button class="btn btn-secondary" id="prevQBtn"><i class="fa-solid fa-arrow-left"></i> Previous</button>
          <button class="btn btn-primary" id="nextQBtn">Next <i class="fa-solid fa-arrow-right"></i></button>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3>Questions</h3></div>
        <div class="card-body">
          <div class="q-nav-grid" id="qNavGrid"></div>
          <button class="btn btn-primary btn-block mt-24" id="submitExamBtn"><i class="fa-solid fa-paper-plane"></i> Submit Examination</button>
        </div>
      </div>
    </div>`;
  document.getElementById('prevQBtn').addEventListener('click', () => { if (examState.currentQ > 0) { examState.currentQ--; renderQuestion(); } });
  document.getElementById('nextQBtn').addEventListener('click', () => { if (examState.currentQ < exam.questions.length - 1) { examState.currentQ++; renderQuestion(); } });
  document.getElementById('submitExamBtn').addEventListener('click', () => {
    if (confirm('Are you sure you want to submit the examination? You cannot change your answers after submitting.')) submitExam(false);
  });
  renderQuestion();
}

function renderQuestion() {
  const exam = examState.exam;
  const q = exam.questions[examState.currentQ];
  document.getElementById('questionContainer').innerHTML = `
    <div class="q-num">Question ${examState.currentQ + 1} of ${exam.questions.length}</div>
    <h3>${q.q}</h3>
    <div id="optionsContainer">${q.options.map((opt, i) => `
      <div class="option-row ${examState.answers[examState.currentQ] === i ? 'selected' : ''}" data-index="${i}">
        <div class="letter">${String.fromCharCode(65 + i)}</div><span>${opt}</span>
      </div>`).join('')}</div>`;
  document.querySelectorAll('#optionsContainer .option-row').forEach(row => {
    row.addEventListener('click', () => {
      examState.answers[examState.currentQ] = Number(row.dataset.index);
      renderQuestion();
      renderQNav();
    });
  });
  document.getElementById('prevQBtn').disabled = examState.currentQ === 0;
  document.getElementById('nextQBtn').textContent = examState.currentQ === exam.questions.length - 1 ? 'Last Question' : 'Next';
  renderQNav();
}

function renderQNav() {
  const exam = examState.exam;
  document.getElementById('qNavGrid').innerHTML = exam.questions.map((_, i) => `
    <button class="q-nav-btn ${examState.answers[i] !== undefined ? 'answered' : ''} ${i === examState.currentQ ? 'current' : ''}" data-goto="${i}">${i + 1}</button>`).join('');
  document.querySelectorAll('#qNavGrid .q-nav-btn').forEach(btn => btn.addEventListener('click', () => { examState.currentQ = Number(btn.dataset.goto); renderQuestion(); }));
}

function submitExam(autoSubmitted) {
  clearInterval(examState.timerId);
  const exam = examState.exam;
  let score = 0;
  exam.questions.forEach((q, i) => { if (examState.answers[i] === q.answer) score++; });
  const session = Auth.current();

  DB.update(db => {
    db.examAttempts = db.examAttempts || [];
    db.examAttempts.push({ examId: exam.id, studentId: session.refId, score, total: exam.questions.length, date: new Date().toISOString().slice(0, 10), autoSubmitted: !!autoSubmitted });
  });

  const pct = Math.round((score / exam.questions.length) * 100);
  document.getElementById('examRoot').innerHTML = `
    <div class="card" style="max-width:600px;margin:0 auto;"><div class="card-body success-panel">
      <div class="check-circle"><i class="fa-solid fa-check"></i></div>
      <h2>Examination Submitted!</h2>
      <p class="text-muted">${autoSubmitted ? 'Time expired — your exam was submitted automatically.' : 'Your examination has been submitted and marked automatically.'}</p>
      <div class="rc-summary" style="max-width:400px;margin:20px auto;">
        <div class="box"><strong>${score}/${exam.questions.length}</strong><span>Score</span></div>
        <div class="box"><strong>${pct}%</strong><span>Percentage</span></div>
      </div>
      <span class="badge badge-${pct>=50?'success':'danger'}" style="font-size:.9rem;padding:8px 18px;">${pct>=50?'Pass':'Needs Improvement'}</span>
      <div class="mt-24"><a href="dashboard.html#exams" class="btn btn-primary">Back to Examinations</a></div>
    </div></div>`;
}

document.addEventListener('DOMContentLoaded', initExam);
