const el = id => document.getElementById(id);
const labels = {late: "Late", on_time: "On time", review: "Manual review"};
let report = null;
let revision = 0;
let selected = "NQ-103";
let searchRevision = 0;

// All API-provided strings are inserted as text, never as executable HTML.
function node(tag, text = "", className = "") {
  const item = document.createElement(tag);
  item.textContent = text;
  if (className) item.className = className;
  return item;
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed.");
  return result;
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function statusBadge(status) {
  return node("span", labels[status] || status, "status " + status);
}

function clauseCard(ref, quote) {
  const card = node("div", "", "clause");
  card.append(node("div", ref, "clause-ref"), node("p", quote));
  return card;
}

function showOrder(row) {
  selected = row.order_id;
  const detail = el("detail");
  const heading = node("div", "", "detail-heading");
  heading.append(node("h3", row.order_id), statusBadge(row.status));
  const meta = node("p", (row.edition || "No matching policy edition") + " · " + row.item_type, "detail-meta");
  const timeline = node("dl", "", "timeline");
  for (const [label, value, extra] of [
    ["Purchased", row.purchased], ["Delivered", row.delivered],
    ["Return requested", row.requested], ["Deadline", row.deadline, "deadline"],
    ["Refund posted", row.refunded], ["Days late", row.days_late]
  ]) {
    const cell = node("div", "", "date-cell" + (extra ? " " + extra : ""));
    cell.append(node("dt", label), node("dd", valueOrDash(value)));
    timeline.append(cell);
  }
  detail.replaceChildren(heading, meta, timeline, node("p", row.reason, "reason"));
  if (row.false_alarm) {
    const note = node("div", "", "callout");
    note.append(node("strong", "Refund-date false alarm"), node("p", "The request was on time. Using the refund date would incorrectly flag it as late."));
    detail.append(note);
  }
  detail.append(node("h4", "Policy evidence", "evidence-label"));
  if (!row.evidence.length) detail.append(node("p", "No matching policy evidence for this order.", "empty-hint"));
  for (const ref of row.evidence) {
    const source = report.sources[ref];
    detail.append(clauseCard(ref, source ? source.quote : "Policy excerpt unavailable."));
  }
  // Reflect selection for mouse and keyboard users without replacing their focused button.
  for (const tr of el("rows").children) {
    const active = tr.dataset.order === selected;
    tr.classList.toggle("selected", active);
    const button = tr.querySelector("button");
    if (button) button.setAttribute("aria-pressed", String(active));
  }
}

function setFilter(value) {
  el("filter").value = value;
  render();
}

function render() {
  if (!report) return;
  const filter = el("filter").value;
  const rows = report.rows.filter(row => filter === "all" || row.status === filter || (filter === "false" && row.false_alarm));
  el("rows").replaceChildren();
  el("row-count").textContent = `${rows.length} of ${report.rows.length} orders · Select an order to inspect its evidence.`;
  el("reset-filter").hidden = filter === "all";
  for (const card of el("stats").children) card.setAttribute("aria-pressed", String(card.dataset.filter === filter));
  for (const row of rows) {
    const tr = node("tr"), first = node("td");
    tr.dataset.order = row.order_id;
    const button = node("button", row.order_id, "order-button");
    button.type = "button";
    button.setAttribute("aria-label", "Inspect order " + row.order_id);
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => showOrder(row));
    first.append(button);
    tr.append(first);
    for (const value of [row.requested, row.refunded, row.deadline]) tr.append(node("td", valueOrDash(value)));
    const finding = node("td");
    finding.append(statusBadge(row.status));
    if (row.false_alarm) {
      const marker = node("span", "*", "false-marker");
      marker.title = "Refund-date false alarm";
      marker.setAttribute("aria-label", "Refund-date false alarm");
      finding.append(marker);
    }
    tr.append(finding, node("td", valueOrDash(row.days_late), "number"));
    el("rows").append(tr);
  }
  if (rows.length) showOrder(rows.find(row => row.order_id === selected) || rows[0]);
  else {
    const row = node("tr"), cell = node("td", "No matching refunds.", "empty-hint");
    cell.colSpan = 6;
    row.append(cell);
    el("rows").append(row);
    el("detail").replaceChildren(node("p", "No matching refunds to inspect.", "empty-hint"));
  }
}

function showImportWarnings(warnings) {
  const list = el("warning-list");
  list.replaceChildren();
  for (const warning of warnings) {
    list.append(node("li", `${warning.order_id} · ${warning.field} = ${JSON.stringify(warning.raw_value)}. ${warning.reason}`));
  }
  el("import-warnings").hidden = warnings.length === 0;
}

function resetAnswer() {
  el("answer").replaceChildren(node("p", "Ask a question to see an evidence-based explanation.", "empty-hint"));
  el("tool-trace").replaceChildren();
  el("tool-trace").hidden = true;
}

async function load() {
  const ticket = ++revision;
  report = null;
  el("error").hidden = true;
  el("error").textContent = "";
  el("stats").replaceChildren();
  el("rows").replaceChildren();
  el("detail").replaceChildren(node("p", "Loading report…", "empty-hint"));
  el("row-count").textContent = "Loading orders…";
  el("report-caption").textContent = "Loading report…";
  el("download").removeAttribute("href");
  el("download").setAttribute("aria-disabled", "true");
  el("filter").disabled = true;
  el("reset-filter").hidden = true;
  resetAnswer();
  showImportWarnings([]);
  try {
    const url = "/api/audit?month=" + encodeURIComponent(el("month").value);
    const fresh = await getJson(url);
    if (revision !== ticket) return;
    report = fresh;
    el("download").href = url;
    el("download").setAttribute("aria-disabled", "false");
    el("filter").disabled = false;
    el("report-caption").textContent = `${report.rows.length} orders in ${report.month} · False alarms are a subset of on-time orders`;
    showImportWarnings(report.import_warnings);
    for (const [key, label, count, note] of [
      ["late", "Late requests", report.counts.late, "Requested after deadline"],
      ["on_time", "On time", report.counts.on_time, "Requested by deadline"],
      ["review", "Manual review", report.counts.review, "Needs human assessment"],
      ["false", "Refund-date false alarms", report.false_alarms, "On-time orders at risk of misclassification"]
    ]) {
      const card = node("button", "", "stat-card " + key);
      card.type = "button";
      card.dataset.filter = key;
      card.setAttribute("aria-pressed", "false");
      card.append(node("span", label, "stat-label"), node("span", count, "stat-value"), node("span", note, "stat-note"));
      card.addEventListener("click", () => setFilter(el("filter").value === key ? "all" : key));
      el("stats").append(card);
    }
    render();
  } catch (e) {
    if (revision !== ticket) return;
    el("error").textContent = e.message;
    el("error").hidden = false;
    el("report-caption").textContent = "Report could not be loaded.";
    el("row-count").textContent = "No report available.";
    el("detail").replaceChildren(node("p", "Select a valid refund month and try again.", "empty-hint"));
  }
}

el("month").addEventListener("change", load);
el("filter").addEventListener("change", render);
el("reset-filter").addEventListener("click", () => setFilter("all"));

el("search").addEventListener("submit", async event => {
  event.preventDefault();
  const ticket = ++searchRevision;
  const submit = el("search").querySelector("button[type=submit]");
  submit.disabled = true;
  el("hits").replaceChildren(node("p", "Finding matching clauses…", "empty-hint"));
  try {
    const params = new URLSearchParams({q:el("terms").value, edition:el("edition").value});
    const hits = Object.entries(await getJson("/api/search?" + params));
    if (ticket !== searchRevision) return;
    el("hits").replaceChildren(...hits.map(([ref, quote]) => clauseCard(ref, quote)));
    if (!hits.length) el("hits").append(node("p", "No matching clauses.", "empty-hint"));
  } catch (e) {
    if (ticket === searchRevision) el("hits").replaceChildren(node("p", e.message, "inline-error"));
  } finally {
    if (ticket === searchRevision) submit.disabled = false;
  }
});

function updateQuestionCount() {
  el("question-count").textContent = `${el("question").value.length}/600 characters`;
}
el("question").addEventListener("input", updateQuestionCount);
for (const button of document.querySelectorAll("[data-question]")) {
  button.addEventListener("click", () => {
    el("question").value = button.dataset.question;
    updateQuestionCount();
    el("question").focus();
  });
}

el("chat").addEventListener("submit", async event => {
  event.preventDefault();
  const ticket = revision, submit = el("chat").querySelector("button[type=submit]");
  submit.disabled = true;
  submit.textContent = "Reading evidence…";
  el("answer").replaceChildren(node("p", "Reading evidence…", "empty-hint"));
  el("tool-trace").replaceChildren();
  el("tool-trace").hidden = true;
  try {
    const result = await getJson("/api/ask?month=" + encodeURIComponent(el("month").value), {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify({question: el("question").value})
    });
    if (ticket !== revision) return;
    el("answer").textContent = result.answer;
    const trace = el("tool-trace");
    if (result.tools.length) {
      trace.append(node("span", "Tools used:"));
      for (const tool of result.tools) trace.append(node("span", tool.name, "tool-chip"));
    } else {
      trace.append(node("span", "Direct validation · no LLM tools called"));
    }
    trace.hidden = false;
  } catch (e) {
    if (ticket === revision) el("answer").replaceChildren(node("p", e.message, "inline-error"));
  } finally {
    submit.disabled = false;
    submit.textContent = "Ask assistant →";
  }
});

updateQuestionCount();
load();
