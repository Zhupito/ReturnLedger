const el = id => document.getElementById(id);
const labels = {late: "Late", on_time: "On time", review: "Manual review"};
let report = null;
let revision = 0;
let selected = "NQ-103";

function node(tag, text = "") {
  const item = document.createElement(tag);
  item.textContent = text;
  return item;
}
async function getJson(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed.");
  return result;
}
function showOrder(row) {
  selected = row.order_id;
  const detail = el("detail");
  detail.replaceChildren(node("h3", row.order_id + " · " + labels[row.status]),
    node("p", "Purchased " + row.purchased + " · Delivered " + (row.delivered || "unknown") +
      " · " + (row.edition || "no matching edition") + " · " + row.item_type),
    node("p", row.reason));
  if (row.false_alarm) detail.append(node("p", "Refund-date false alarm. Using the payment date would wrongly flag this request as late."));
  for (const ref of row.evidence) detail.append(node("p", ref + " — " + report.sources[ref].quote));
}
function render() {
  if (!report) return;
  const rows = report.rows.filter(row => el("filter").value === "all" ||
    row.status === el("filter").value || (el("filter").value === "false" && row.false_alarm));
  el("rows").replaceChildren();
  for (const row of rows) {
    const tr = node("tr"), first = node("td"), button = node("button", row.order_id);
    button.onclick = () => showOrder(row);
    first.append(button);
    tr.append(first);
    for (const value of [row.requested, row.refunded, row.deadline, labels[row.status], row.days_late]) {
      const td = node("td", value === null || value === "" ? "—" : value);
      if (value === labels[row.status]) td.className = row.status;
      tr.append(td);
    }
    el("rows").append(tr);
  }
  if (rows.length) showOrder(rows.find(row => row.order_id === selected) || rows[0]);
  else el("detail").replaceChildren(node("p", "No matching refunds."));
}
async function load() {
  const ticket = ++revision;
  report = null;
  for (const id of ["error","stats","rows","detail","answer"]) el(id).replaceChildren();
  el("download").removeAttribute("href");
  try {
    const url = "/api/audit?month=" + encodeURIComponent(el("month").value);
    const fresh = await getJson(url);
    if (revision !== ticket) return;
    report = fresh;
    el("download").href = url;
    for (const [label, count] of [["Late requests",report.counts.late],["On time",report.counts.on_time],
         ["Manual review",report.counts.review],["Refund-date false alarms",report.false_alarms]]) {
      const card = node("div", label);
      card.append(node("b",count));
      el("stats").append(card);
    }
    render();
  } catch (e) { if (revision === ticket) el("error").textContent = e.message; }
}
el("month").onchange = load;
el("filter").onchange = render;
el("search").onsubmit = async event => {
  event.preventDefault();
  try {
    const params = new URLSearchParams({q:el("terms").value, edition:el("edition").value});
    const hits = Object.entries(await getJson("/api/search?" + params));
    el("hits").replaceChildren(...hits.map(([ref, quote]) => node("p", ref + " — " + quote)));
    if (!hits.length) el("hits").textContent = "No matching clauses.";
  } catch (e) { el("hits").textContent = e.message; }
};
el("chat").onsubmit = async event => {
  event.preventDefault();
  const ticket = revision, submit = el("chat").querySelector("button");
  submit.disabled = true;
  el("answer").textContent = "Reading evidence…";
  try {
    const result = await getJson("/api/ask?month=" + encodeURIComponent(el("month").value),
      {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:el("question").value})});
    if (ticket === revision) el("answer").textContent = result.answer + "\nTools used: " +
      result.tools.map(t => t.name).join(", ");
  } catch (e) { if (ticket === revision) el("answer").textContent = e.message; }
  finally { submit.disabled = false; }
};
load();
