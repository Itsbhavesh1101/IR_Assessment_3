const state = {
  authToken: "",
  conversationId: null,
  loginType: "teacher",
  theme: "ocean",
  busy: false,
  user: null,
  students: [],
  history: [],
};

const loginView = document.querySelector("#loginView");
const dashboardView = document.querySelector("#dashboardView");
const loginForm = document.querySelector("#loginForm");
const loginUserId = document.querySelector("#loginUserId");
const loginPassword = document.querySelector("#loginPassword");
const loginError = document.querySelector("#loginError");
const loginButton = document.querySelector("#loginButton");
const logoutButton = document.querySelector("#logoutButton");
const chatPanel = document.querySelector("#chatPanel");
const chatForm = document.querySelector("#chatForm");
const messageInput = document.querySelector("#messageInput");
const userId = document.querySelector("#userId");
const authToken = document.querySelector("#authToken");
const studentId = document.querySelector("#studentId");
const historyList = document.querySelector("#historyList");
const healthStatus = document.querySelector("#healthStatus");
const newChatButton = document.querySelector("#newChatButton");
const downloadChatButton = document.querySelector("#downloadChatButton");
const loadHistoryButton = document.querySelector("#loadHistoryButton");
const profileAvatar = document.querySelector("#profileAvatar");
const profileName = document.querySelector("#profileName");
const profileRole = document.querySelector("#profileRole");
const dashboardTitle = document.querySelector("#dashboardTitle");
const workspaceLabel = document.querySelector("#workspaceLabel");
const metricAttendance = document.querySelector("#metricAttendance");
const metricAttendanceDetail = document.querySelector("#metricAttendanceDetail");
const metricMarks = document.querySelector("#metricMarks");
const metricMarksDetail = document.querySelector("#metricMarksDetail");
const metricFees = document.querySelector("#metricFees");
const metricFeesDetail = document.querySelector("#metricFeesDetail");
const metricHomework = document.querySelector("#metricHomework");
const metricHomeworkDetail = document.querySelector("#metricHomeworkDetail");
const metricClasses = document.querySelector("#metricClasses");
const attendanceRing = document.querySelector("#attendanceRing");
const attendanceRingValue = document.querySelector("#attendanceRingValue");
const marksBars = document.querySelector("#marksBars");
const marksCaption = document.querySelector("#marksCaption");
const todayList = document.querySelector("#todayList");
const focusCaption = document.querySelector("#focusCaption");
const focusList = document.querySelector("#focusList");
const feeCaption = document.querySelector("#feeCaption");
const feeBars = document.querySelector("#feeBars");

const roleThemes = {
  teacher: "ocean",
  parent: "forest",
  student: "sunset",
};

function appendMessage(kind, text) {
  return appendMessageContent(kind, text);
}

function appendMessageContent(kind, content) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${kind}`;

  const roleLabel = document.createElement("div");
  roleLabel.className = "message-role";
  roleLabel.textContent = kind === "user" ? "You" : kind === "error" ? "Error" : "Assistant";

  const body = document.createElement("div");
  body.className = "message-text";
  if (content instanceof Node) {
    body.append(content);
  } else {
    body.textContent = content;
  }

  wrapper.append(roleLabel, body);
  chatPanel.append(wrapper);
  chatPanel.scrollTop = chatPanel.scrollHeight;
  return wrapper;
}

function authHeaders(baseHeaders = {}) {
  const headers = { ...baseHeaders };
  if (state.authToken) {
    headers["X-ERP-Auth-Token"] = state.authToken;
  }
  return headers;
}

function setBusy(nextBusy) {
  state.busy = nextBusy;
  loginButton.disabled = nextBusy;
  chatForm.querySelector("button").disabled = nextBusy;
  messageInput.disabled = nextBusy;
  studentId.disabled = nextBusy;
  newChatButton.disabled = nextBusy;
  downloadChatButton.disabled = nextBusy;
  loadHistoryButton.disabled = nextBusy;
}

function setLoginType(nextType) {
  state.loginType = nextType;
  document.querySelectorAll("[data-login-type]").forEach((button) => {
    button.classList.toggle("active", button.dataset.loginType === nextType);
  });
  loginError.textContent = "";
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  document.querySelectorAll("[data-theme]").forEach((button) => {
    button.classList.toggle("active", button.dataset.theme === theme);
  });
}

function renderStudentOptions(students) {
  studentId.replaceChildren();
  for (const student of students) {
    const option = document.createElement("option");
    option.value = student.student_id;
    option.textContent = `${student.name} - Class ${student.class_name}${student.section}`;
    studentId.append(option);
  }

  if (!studentId.options.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No active students";
    studentId.append(option);
  }
}

function selectedContextParams() {
  const params = new URLSearchParams();
  if (studentId.value) {
    params.set("student_id", studentId.value);
  }
  return params;
}

function resetWorkspace() {
  state.conversationId = null;
  state.history = [];
  chatPanel.replaceChildren();
  historyList.replaceChildren();
  renderHistorySummary([]);
}

function openDashboard(payload) {
  state.authToken = payload.auth_token;
  state.user = payload.user;
  state.students = payload.students || [];
  authToken.value = state.authToken;
  userId.value = state.user.user_id;

  const initials = state.user.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  profileAvatar.textContent = initials || "AI";
  profileName.textContent = state.user.name;
  profileRole.textContent = state.user.role;
  workspaceLabel.textContent = state.user.role;
  applyTheme(roleThemes[state.user.role] || "ocean");

  renderStudentOptions(state.students);
  resetWorkspace();
  appendMessage("assistant", "Ready for ERP questions.");
  loginView.hidden = true;
  dashboardView.hidden = false;
  activateWindow("homeWindow");
  loadDashboard();
}

function closeDashboard() {
  state.authToken = "";
  state.user = null;
  state.students = [];
  applyTheme("ocean");
  authToken.value = "";
  userId.value = "";
  loginPassword.value = "";
  resetWorkspace();
  dashboardView.hidden = true;
  loginView.hidden = false;
  loginUserId.focus();
}

async function login(event) {
  event.preventDefault();
  if (state.busy) {
    return;
  }

  loginError.textContent = "";
  setBusy(true);
  try {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        login_type: state.loginType,
        user_id: loginUserId.value.trim(),
        password: loginPassword.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      loginError.textContent = payload.message || "Login failed.";
      return;
    }
    openDashboard(payload);
  } catch (error) {
    loginError.textContent = error.message || "Login failed.";
  } finally {
    setBusy(false);
  }
}

function appendAssistantResponse(response) {
  const wrapper = appendMessageContent("assistant", createOutputContent(response));
  wrapper.classList.add("has-output");
}

function createOutputContent(response) {
  const output = document.createElement("div");
  output.className = "output-panel chat-output";
  if (!response) {
    const empty = document.createElement("div");
    empty.className = "output-empty";
    empty.textContent = "No output yet.";
    output.append(empty);
    return output;
  }

  const summary = document.createElement("article");
  summary.className = "output-card output-summary";
  const title = document.createElement("strong");
  title.textContent = response.intent || response.status_label || "Assistant Output";
  const message = document.createElement("p");
  message.textContent = response.message || "Completed.";
  summary.append(title, message);
  const llmBadge = createLlmBadge(response);
  if (llmBadge) {
    summary.append(llmBadge);
  }
  if (Array.isArray(response.highlights) && response.highlights.length) {
    summary.append(createHighlightList(response.highlights));
  }
  output.append(summary);

  const sections = response.sections || [];
  if (sections.length) {
    for (const section of sections) {
      output.append(createOutputCard(section.intent, section.message, section.status_label, section.data));
    }
    return output;
  }

  if (response.data) {
    output.append(createOutputFacts(response.data));
    const generatedOutput = createGeneratedOutput(response.intent, response.data);
    if (generatedOutput) {
      output.append(generatedOutput);
    }
  }
  return output;
}

function createOutputCard(titleText, messageText, statusText, data) {
  const card = document.createElement("article");
  card.className = "output-card";

  const title = document.createElement("strong");
  title.textContent = titleText || "Result";
  const message = document.createElement("p");
  message.textContent = messageText || "Completed.";
  card.append(title, message);

  if (statusText) {
    const status = document.createElement("span");
    status.className = "output-status";
    status.textContent = statusText;
    card.append(status);
  }

  if (data) {
    card.append(createOutputFacts(data));
    const generatedOutput = createGeneratedOutput(titleText, data);
    if (generatedOutput) {
      card.append(generatedOutput);
    }
  }
  return card;
}

function createGeneratedOutput(intent, data) {
  const normalizedIntent = String(intent || "").toLowerCase();
  if (
    (normalizedIntent.includes("marks") || Array.isArray(data.subject_summaries)) &&
    Array.isArray(data.subject_summaries)
  ) {
    return createMarksOutput(data);
  }
  if ((normalizedIntent.includes("exam") || data.study_plan) && Array.isArray(data.study_plan)) {
    return createExamPlanOutput(data);
  }
  if (
    (normalizedIntent.includes("parent") || data.subject_wise_marks) &&
    data.attendance_summary &&
    Array.isArray(data.subject_wise_marks)
  ) {
    return createParentReportOutput(data);
  }
  return null;
}

function createLlmBadge(response) {
  if (!response.llm && response.llm_generated === undefined) {
    return null;
  }
  const llm = response.llm || {};
  const provider = llm.provider || "disabled";
  const status = llm.used || response.llm_generated ? "used" : llm.status || "fallback";
  const badge = document.createElement("span");
  badge.className = `llm-badge ${status === "used" || status === "generated" ? "ok" : "fallback"}`;
  badge.textContent =
    status === "used" || status === "generated"
      ? `LLM: ${formatOutputLabel(provider)} used`
      : `LLM: ${formatOutputLabel(provider)} fallback`;
  if (llm.error) {
    badge.title = llm.error;
  }
  return badge;
}

function createHighlightList(highlights) {
  const list = document.createElement("ul");
  list.className = "output-highlight-list";
  for (const highlight of highlights.slice(0, 4)) {
    const item = document.createElement("li");
    item.textContent = highlight;
    list.append(item);
  }
  return list;
}

function createMarksOutput(data) {
  const wrapper = document.createElement("div");
  wrapper.className = "output-generated";

  const subjects = dedupeSubjectSummaries(data.subject_summaries || []);
  const marksBlock = createOutputBlock("Subject Marks");
  const marksList = document.createElement("ul");
  marksList.className = "output-mark-list";

  for (const record of subjects) {
    const item = document.createElement("li");
    const subject = document.createElement("span");
    subject.textContent = record.subject || "Subject";
    const score = document.createElement("strong");
    const examCount = record.record_count ? ` (${record.record_count} exams)` : "";
    score.textContent = `${valueWithPercent(record.percentage)}${examCount}`;
    item.append(subject, score);
    marksList.append(item);
  }

  if (!marksList.children.length) {
    const item = document.createElement("li");
    item.textContent = "No subject marks available.";
    marksList.append(item);
  }

  marksBlock.append(marksList);
  wrapper.append(marksBlock);

  const recordCount = Array.isArray(data.records) ? data.records.length : 0;
  if (recordCount && subjects.length && recordCount !== subjects.length) {
    const note = document.createElement("p");
    note.className = "output-note";
    note.textContent = `${recordCount} exam records are grouped into ${subjects.length} subjects.`;
    wrapper.append(note);
  }

  return wrapper;
}

function dedupeSubjectSummaries(records) {
  const seen = new Set();
  const subjects = [];
  for (const record of records) {
    const key = String(record.subject || "").toLowerCase();
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    subjects.push(record);
  }
  return subjects;
}

function createExamPlanOutput(data) {
  const wrapper = document.createElement("div");
  wrapper.className = "output-generated";

  const focusSubjects = data.focus_subjects || [];
  if (focusSubjects.length) {
    const focusBlock = createOutputBlock("Focus Subjects");
    const chips = document.createElement("div");
    chips.className = "output-chip-row";
    for (const subject of focusSubjects) {
      const chip = document.createElement("span");
      chip.textContent = subject;
      chips.append(chip);
    }
    focusBlock.append(chips);
    wrapper.append(focusBlock);
  }

  const plan = data.study_plan || [];
  const planBlock = createOutputBlock("Study Plan");
  if (!plan.length) {
    const empty = document.createElement("p");
    empty.textContent = "No study-plan items were generated.";
    planBlock.append(empty);
  } else {
    const list = document.createElement("ol");
    list.className = "output-plan-list";
    for (const item of plan) {
      const row = document.createElement("li");
      const day = document.createElement("span");
      day.className = "output-day";
      day.textContent = `Day ${item.day}`;

      const subject = document.createElement("strong");
      subject.textContent = item.subject || "Study";

      const detail = document.createElement("small");
      const priority = item.priority ? `${formatOutputLabel(item.priority)} priority` : "Practice";
      const basis =
        item.basis_percentage === null || item.basis_percentage === undefined
          ? ""
          : ` - current score ${item.basis_percentage}%`;
      detail.textContent = `${priority}${basis}`;

      row.append(day, subject, detail);
      list.append(row);
    }
    planBlock.append(list);
  }
  wrapper.append(planBlock);
  return wrapper;
}

function createParentReportOutput(data) {
  const wrapper = document.createElement("div");
  wrapper.className = "output-generated";

  const student = data.student || {};
  if (student.name) {
    const studentBlock = createOutputBlock("Student");
    studentBlock.append(
      createOutputRows([
        ["Name", student.name],
        ["Class", `${student.class_name || ""}${student.section || ""}`.trim()],
        ["Guardian", student.guardian_name || "Not listed"],
      ]),
    );
    wrapper.append(studentBlock);
  }

  wrapper.append(
    createOutputBlock(
      "Attendance",
      createOutputRows([
        ["Attendance", valueWithPercent(data.attendance_summary?.attendance_percentage)],
        ["Present", data.attendance_summary?.present_classes ?? 0],
        ["Missed", data.attendance_summary?.missed_classes ?? 0],
      ]),
    ),
  );

  const marksBlock = createOutputBlock("Subject Marks");
  const marksList = document.createElement("ul");
  marksList.className = "output-mark-list";
  for (const record of data.subject_wise_marks.slice(0, 8)) {
    const item = document.createElement("li");
    const subject = document.createElement("span");
    subject.textContent = record.subject || "Subject";
    const score = document.createElement("strong");
    score.textContent = valueWithPercent(record.percentage);
    item.append(subject, score);
    marksList.append(item);
  }
  if (!marksList.children.length) {
    const item = document.createElement("li");
    item.textContent = "No subject marks available.";
    marksList.append(item);
  }
  marksBlock.append(marksList);
  wrapper.append(marksBlock);

  wrapper.append(
    createOutputBlock(
      "Homework And Fees",
      createOutputRows([
        ["Pending Homework", data.homework_status?.pending_count ?? 0],
        ["Pending Fees", data.pending_fees?.pending_total ?? 0],
        ["Fee Status", data.pending_fees?.pending_total ? "Pending" : "Clear"],
      ]),
    ),
  );

  const suggestions = data.suggestions || [];
  if (suggestions.length) {
    const suggestionsBlock = createOutputBlock("Suggestions");
    const list = document.createElement("ul");
    list.className = "output-suggestion-list";
    for (const suggestion of suggestions) {
      const item = document.createElement("li");
      item.textContent = suggestion;
      list.append(item);
    }
    suggestionsBlock.append(list);
    wrapper.append(suggestionsBlock);
  }

  return wrapper;
}

function createOutputBlock(titleText, child) {
  const block = document.createElement("section");
  block.className = "output-block";
  const heading = document.createElement("h3");
  heading.textContent = titleText;
  block.append(heading);
  if (child) {
    block.append(child);
  }
  return block;
}

function createOutputRows(rows) {
  const list = document.createElement("dl");
  list.className = "output-mini-facts";
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value === null || value === undefined || value === "" ? "--" : String(value);
    list.append(term, detail);
  }
  return list;
}

function valueWithPercent(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return `${value}%`;
}

function createOutputFacts(data) {
  const facts = document.createElement("dl");
  facts.className = "output-facts";
  for (const [key, value] of outputFacts(data)) {
    const term = document.createElement("dt");
    term.textContent = formatOutputLabel(key);
    const detail = document.createElement("dd");
    detail.textContent = formatOutputValue(value);
    facts.append(term, detail);
  }
  if (!facts.children.length) {
    const term = document.createElement("dt");
    term.textContent = "Status";
    const detail = document.createElement("dd");
    detail.textContent = "Data available";
    facts.append(term, detail);
  }
  return facts;
}

function outputFacts(data) {
  const preferredKeys = [
    "attendance_percentage",
    "present_classes",
    "missed_classes",
    "average_percentage",
    "overall_performance",
    "days_until_exam",
    "focus_subjects",
    "pending_total",
    "paid_total",
    "pending_count",
    "total_classes",
    "highest_subject",
    "lowest_subject",
    "current_month",
    "status",
    "standing",
    "action",
  ];
  const facts = [];
  for (const key of preferredKeys) {
    if (Object.prototype.hasOwnProperty.call(data, key) && data[key] !== null && data[key] !== undefined) {
      facts.push([key, data[key]]);
    }
  }
  if (!facts.length) {
    for (const [key, value] of Object.entries(data)) {
      if (value === null || value === undefined || Array.isArray(value) || typeof value === "object") {
        continue;
      }
      facts.push([key, value]);
      if (facts.length >= 6) {
        break;
      }
    }
  }
  return facts.slice(0, 8);
}

function formatOutputLabel(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatOutputValue(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value && typeof value === "object") {
    if (value.subject && value.percentage !== undefined) {
      return `${value.subject} (${value.percentage}%)`;
    }
    if (value.month && value.status) {
      return `${value.month} - ${value.status}`;
    }
    return Object.entries(value)
      .slice(0, 3)
      .map(([key, item]) => `${formatOutputLabel(key)}: ${item}`)
      .join(", ");
  }
  return String(value);
}

function renderHistorySummary(history) {
  state.history = [...history].sort((left, right) => {
    const leftTime = new Date(left.created_at || 0).getTime();
    const rightTime = new Date(right.created_at || 0).getTime();
    return rightTime - leftTime;
  });
  historyList.replaceChildren();

  if (!state.history.length) {
    const empty = document.createElement("li");
    empty.className = "history-empty";
    empty.textContent = "No chat history for this student yet.";
    historyList.append(empty);
    return;
  }

  state.history.forEach((item, index) => {
    const historyItem = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-item";
    button.dataset.historyIndex = String(index);
    button.addEventListener("click", () => {
      showHistoryItem(index);
    });

    const title = document.createElement("strong");
    title.textContent = item.message;
    const meta = document.createElement("span");
    meta.textContent = `${formatHistoryDate(item.created_at)} - ${item.response?.intent || item.response?.status_label || "chat"}`;

    button.append(title, meta);
    historyItem.append(button);
    historyList.append(historyItem);
  });
}

function showHistoryItem(index) {
  const item = state.history[index];
  if (!item) {
    return;
  }
  state.conversationId = item.conversation_id;
  chatPanel.replaceChildren();
  appendMessage("user", item.message);
  appendAssistantResponse(item.response);
  historyList.querySelectorAll(".history-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.historyIndex === String(index));
  });
}

function prependHistoryItem(item) {
  state.history = [item, ...state.history].slice(0, 50);
  renderHistorySummary(state.history);
}

function formatHistoryDate(value) {
  if (!value) {
    return "Just now";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function downloadChat() {
  const transcript = buildChatTranscript();
  if (!transcript) {
    appendMessage("error", "No chat is available to download yet.");
    return;
  }

  const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${safeFilePart(profileName.textContent || "school-erp")}-chat-${timestampForFile()}.txt`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function buildChatTranscript() {
  const messages = Array.from(chatPanel.querySelectorAll(".message"));
  if (!messages.length) {
    return "";
  }

  const selectedStudent = studentId.options[studentId.selectedIndex]?.textContent || "No student selected";
  const header = [
    "AI School ERP Assistant Chat Transcript",
    `User: ${profileName.textContent || "Unknown"}`,
    `Role: ${profileRole.textContent || "Unknown"}`,
    `Student: ${selectedStudent}`,
    `Downloaded: ${new Date().toLocaleString()}`,
  ];

  const body = messages
    .map((message) => {
      const role = message.querySelector(".message-role")?.textContent?.trim() || "Message";
      const text = message.querySelector(".message-text")?.innerText?.trim() || "";
      return text ? `${role}\n${text}` : "";
    })
    .filter(Boolean);

  return [...header, "", ...body].join("\n\n");
}

function safeFilePart(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "school-erp";
}

function timestampForFile() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
}

function renderDashboard(payload) {
  const metrics = payload.metrics || {};
  const charts = payload.charts || {};
  const recent = payload.recent || {};
  const attendance = metrics.attendance_percentage;
  const averageMarks = metrics.average_marks;
  const pendingFees = metrics.pending_fees || 0;
  const pendingHomework = metrics.pending_homework || 0;

  dashboardTitle.textContent = `${payload.student.name} dashboard`;
  metricAttendance.textContent = attendance === null || attendance === undefined ? "--" : `${attendance}%`;
  metricAttendanceDetail.textContent = `${metrics.present_classes || 0} present, ${metrics.missed_classes || 0} missed`;
  metricMarks.textContent = averageMarks === null || averageMarks === undefined ? "--" : `${averageMarks}%`;
  metricMarksDetail.textContent = `${(recent.strong_subjects || []).length} strong subjects`;
  metricFees.textContent = formatMoney(pendingFees);
  metricFeesDetail.textContent = pendingFees > 0 ? "Balance pending" : "Cleared";
  metricHomework.textContent = String(pendingHomework);
  metricHomeworkDetail.textContent = pendingHomework === 1 ? "Pending item" : "Pending items";
  metricClasses.textContent = `${metrics.classes_today || 0} classes today`;

  const ringValue = Math.max(0, Math.min(Number(attendance || 0), 100));
  attendanceRing.style.setProperty("--ring-value", `${ringValue}%`);
  attendanceRingValue.textContent = attendance === null || attendance === undefined ? "--" : `${attendance}%`;

  renderMarksBars(charts.marks_by_subject || []);
  renderTodayList(recent);
  renderFocusList(recent.weak_subjects || [], recent.strong_subjects || []);
  renderFeeBars(charts.fee_history || []);
}

function renderMarksBars(records) {
  marksBars.replaceChildren();
  marksCaption.textContent = records.length ? `${records.length} subjects` : "No records";
  if (!records.length) {
    const item = document.createElement("li");
    item.textContent = "No marks records available.";
    marksBars.append(item);
    return;
  }

  for (const record of records) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = record.label;
    const track = document.createElement("span");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(0, Math.min(Number(record.value || 0), 100))}%`;
    const value = document.createElement("span");
    value.textContent = `${record.value}%`;
    track.append(fill);
    item.append(label, track, value);
    marksBars.append(item);
  }
}

function renderTodayList(recent) {
  todayList.replaceChildren();
  const timetable = recent.timetable || [];
  const homework = recent.homework || [];
  const items = [];

  for (const entry of timetable.slice(0, 3)) {
    items.push(`${entry.start_time} ${entry.subject} with ${entry.teacher}`);
  }
  for (const task of homework.slice(0, 2)) {
    items.push(`${task.subject}: ${task.title}`);
  }

  if (!items.length) {
    items.push("No dashboard items for the selected student.");
  }

  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    todayList.append(item);
  }
}

function renderFocusList(weakSubjects, strongSubjects) {
  focusList.replaceChildren();
  const entries = [];
  for (const subject of weakSubjects) {
    entries.push(`Focus: ${subject}`);
  }
  if (!entries.length) {
    for (const subject of strongSubjects.slice(0, 4)) {
      entries.push(`Strong: ${subject}`);
    }
  }
  if (!entries.length) {
    entries.push("No focus areas from current records.");
  }

  focusCaption.textContent = weakSubjects.length ? `${weakSubjects.length} need attention` : "Strengths";
  for (const text of entries) {
    const item = document.createElement("li");
    item.textContent = text;
    focusList.append(item);
  }
}

function renderFeeBars(history) {
  feeBars.replaceChildren();
  feeCaption.textContent = history.length ? `${history.length} fee records` : "No fee records";
  if (!history.length) {
    const item = document.createElement("li");
    item.textContent = "No fee records available.";
    feeBars.append(item);
    return;
  }

  for (const record of history) {
    const paidRatio = record.amount ? (record.paid_amount / record.amount) * 100 : 0;
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = record.month;
    const track = document.createElement("span");
    track.className = "fee-track";
    const fill = document.createElement("span");
    fill.className = "fee-paid";
    fill.style.width = `${Math.max(0, Math.min(Number(paidRatio || 0), 100))}%`;
    const value = document.createElement("span");
    value.textContent = record.status;
    track.append(fill);
    item.append(label, track, value);
    feeBars.append(item);
  }
}

function formatMoney(value) {
  return Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  });
}

async function loadDashboard() {
  if (!state.authToken || !studentId.value) {
    return;
  }

  try {
    const params = selectedContextParams();
    const response = await fetch(`/dashboard?${params.toString()}`, {
      headers: authHeaders(),
    });
    const payload = await response.json();
    if (!response.ok) {
      appendMessage("error", payload.message || "Unable to load dashboard.");
      return;
    }
    renderDashboard(payload);
  } catch (error) {
    appendMessage("error", error.message || "Unable to load dashboard.");
  }
}

async function sendMessage(message) {
  if (!message.trim() || state.busy) {
    return;
  }

  appendMessage("user", message);
  setBusy(true);

  try {
    const requestBody = {
      student_id: studentId.value,
      conversation_id: state.conversationId,
      message,
      return_plan: true,
    };

    const response = await fetch("/chat", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();

    if (!response.ok) {
      appendMessage("error", payload.message || "The request failed.");
      return;
    }

    state.conversationId = payload.conversation_id;
    appendAssistantResponse(payload.response);
    prependHistoryItem({
      conversation_id: payload.conversation_id,
      message,
      response: payload.response,
      created_at: new Date().toISOString(),
    });
    loadDashboard();
  } catch (error) {
    appendMessage("error", error.message || "Network error.");
  } finally {
    setBusy(false);
    messageInput.focus();
  }
}

async function loadHistory({ silent = false } = {}) {
  if (state.busy && !silent) {
    return;
  }

  if (!silent) {
    setBusy(true);
  }
  try {
    const params = selectedContextParams();

    const response = await fetch(`/chat/history?${params.toString()}`, {
      headers: authHeaders(),
    });
    const payload = await response.json();
    if (!response.ok) {
      if (!silent) {
        appendMessage("error", payload.message || "Unable to load history.");
      }
      return;
    }
    renderHistorySummary(payload.history || []);
  } catch (error) {
    if (!silent) {
      appendMessage("error", error.message || "Unable to load history.");
    }
  } finally {
    if (!silent) {
      setBusy(false);
      messageInput.focus();
    }
  }
}

async function loadHealth() {
  try {
    const response = await fetch("/health");
    const payload = await response.json();
    healthStatus.textContent = payload.status === "ok" ? "Ready" : "Issue";
    healthStatus.className = `status-pill ${payload.status === "ok" ? "ok" : "error"}`;
  } catch {
    healthStatus.textContent = "Offline";
    healthStatus.className = "status-pill error";
  }
}

function activateWindow(windowId) {
  document.querySelectorAll("[data-window]").forEach((button) => {
    button.classList.toggle("active", button.dataset.window === windowId);
  });
  document.querySelectorAll(".view-window").forEach((windowElement) => {
    windowElement.hidden = windowElement.id !== windowId;
  });
  if (windowId === "chatWindow") {
    if (state.authToken && !state.history.length) {
      loadHistory({ silent: true });
    }
    messageInput.focus();
  }
}

loginForm.addEventListener("submit", login);

document.querySelectorAll("[data-login-type]").forEach((button) => {
  button.addEventListener("click", () => {
    setLoginType(button.dataset.loginType);
  });
});

chatForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = messageInput.value;
  messageInput.value = "";
  sendMessage(message);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.prompt;
    messageInput.focus();
  });
});

document.querySelectorAll("[data-window]").forEach((button) => {
  button.addEventListener("click", () => {
    activateWindow(button.dataset.window);
  });
});

document.querySelectorAll("[data-theme]").forEach((button) => {
  button.addEventListener("click", () => {
    applyTheme(button.dataset.theme);
  });
});

newChatButton.addEventListener("click", () => {
  state.conversationId = null;
  chatPanel.replaceChildren();
  appendMessage("assistant", "Started a new conversation.");
  activateWindow("chatWindow");
  messageInput.focus();
});

downloadChatButton.addEventListener("click", () => {
  downloadChat();
});

loadHistoryButton.addEventListener("click", () => {
  loadHistory();
});

logoutButton.addEventListener("click", () => {
  closeDashboard();
});

studentId.addEventListener("change", () => {
  resetWorkspace();
  appendMessage("assistant", "Student changed. Started a new conversation.");
  loadDashboard();
});

setLoginType("teacher");
applyTheme("ocean");
loadHealth();
