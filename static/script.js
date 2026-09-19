const state = { deadlines: [], filter: "all", editingId: null };
const $ = (selector) => document.querySelector(selector);

const formatDate = (value) => {
  if (!value) return "No date set";
  return new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
};

const startOfToday = () => { const date = new Date(); date.setHours(0, 0, 0, 0); return date; };
const isToday = (deadline) => deadline && new Date(deadline).toDateString() === new Date().toDateString();
const isOverdue = (item) => item.deadline && new Date(item.deadline) < new Date() && !item.completed;
const isUpcoming = (item) => item.deadline && new Date(item.deadline) > new Date() && !isToday(item.deadline) && !item.completed;

function setMessage(text = "") { $("#form-message").textContent = text; }
function setLoading(loading) { $("#button-label").textContent = loading ? "Analyzing..." : "Add deadline"; $("#analyze-form button").disabled = loading; }

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

async function loadDeadlines() {
  $("#loading-state").classList.remove("hidden"); $("#error-state").classList.add("hidden");
  try { state.deadlines = await api("/api/deadlines"); render(); } catch (error) { $("#error-text").textContent = error.message; $("#error-state").classList.remove("hidden"); } finally { $("#loading-state").classList.add("hidden"); }
}

function updateStats() {
  const values = { all: state.deadlines.length, today: state.deadlines.filter((item) => isToday(item.deadline) && !item.completed).length, upcoming: state.deadlines.filter(isUpcoming).length, overdue: state.deadlines.filter(isOverdue).length, completed: state.deadlines.filter((item) => item.completed).length };
  Object.entries(values).forEach(([key, value]) => { $(`#stat-${key}`).textContent = value; });
}

function filteredDeadlines() {
  return state.deadlines.filter((item) => {
    if (state.filter === "today") return isToday(item.deadline) && !item.completed;
    if (state.filter === "upcoming") return isUpcoming(item);
    if (state.filter === "overdue") return isOverdue(item);
    if (state.filter === "completed") return item.completed;
    return true;
  });
}

function render() {
  updateStats();
  document.querySelectorAll("[data-filter]").forEach((button) => button.classList.toggle("active", button.dataset.filter === state.filter));
  const list = $("#deadline-list"); const items = filteredDeadlines(); list.innerHTML = "";
  $("#empty-state").classList.toggle("hidden", items.length > 0); $("#empty-title").textContent = state.deadlines.length ? "Nothing in this view" : "Nothing here yet"; $("#empty-text").textContent = state.deadlines.length ? "Try another filter to see more deadlines." : "Add your first deadline above and get it out of your head.";
  items.forEach((item) => list.appendChild(createCard(item)));
}

function createCard(item) {
  const card = document.createElement("article"); card.className = `deadline-card ${item.completed ? "is-completed" : ""}`;
  const overdue = isOverdue(item); const priorityClass = item.priority.toLowerCase();
  card.innerHTML = `<div><div class="task-meta"><span class="category">${item.category}</span><span class="priority ${priorityClass}">${item.priority} priority</span></div><h3 class="task-title"></h3><p class="task-description"></p></div><div class="task-date ${overdue ? "overdue" : ""}"><span>${overdue ? "Past due" : item.completed ? "Completed" : "Due"}</span><strong>${formatDate(item.deadline)}</strong></div><div class="task-actions"><button class="task-action" data-action="complete">${item.completed ? "Mark active" : "Mark complete"}</button><button class="task-action" data-action="edit">Edit</button><button class="task-action" data-action="delete">Delete</button></div>`;
  card.querySelector(".task-title").textContent = item.title; card.querySelector(".task-description").textContent = item.description;
  card.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => handleAction(button.dataset.action, item)));
  return card;
}

function isoToLocal(value) { if (!value) return ""; const date = new Date(value); const offset = date.getTimezoneOffset(); return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16); }
function localToIso(value) { return value ? new Date(value).toISOString() : null; }

function openPreview(data, editingId = null) {
  state.editingId = editingId; $("#preview-title-input").value = data.title; $("#preview-category").value = data.category; $("#preview-priority").value = data.priority; $("#preview-deadline").value = isoToLocal(data.deadline); $("#preview-description").value = data.description; $("#preview-title").textContent = editingId ? "Edit your deadline" : "Review your deadline"; $("#preview-message").textContent = ""; $("#preview-modal").classList.remove("hidden"); $("#preview-title-input").focus();
}
function closePreview() { $("#preview-modal").classList.add("hidden"); state.editingId = null; }

async function handleAction(action, item) {
  try {
    if (action === "delete") { if (!window.confirm(`Delete “${item.title}”?`)) return; await api(`/api/deadlines/${item.id}`, { method: "DELETE" }); }
    if (action === "complete") await api(`/api/deadlines/${item.id}/complete`, { method: "PATCH", body: JSON.stringify({ completed: !item.completed }) });
    if (action === "edit") { openPreview(item, item.id); return; }
    await loadDeadlines();
  } catch (error) { window.alert(error.message); }
}

$("#analyze-form").addEventListener("submit", async (event) => { event.preventDefault(); const input = $("#reminder-input"); setMessage(""); setLoading(true); try { const data = await api("/api/deadlines/analyze", { method: "POST", body: JSON.stringify({ text: input.value.trim() }) }); openPreview(data); } catch (error) { setMessage(error.message); } finally { setLoading(false); } });
$("#preview-form").addEventListener("submit", async (event) => { event.preventDefault(); const data = { title: $("#preview-title-input").value.trim(), category: $("#preview-category").value, priority: $("#preview-priority").value, deadline: localToIso($("#preview-deadline").value), description: $("#preview-description").value.trim() }; try { await api(state.editingId ? `/api/deadlines/${state.editingId}` : "/api/deadlines", { method: state.editingId ? "PUT" : "POST", body: JSON.stringify(data) }); closePreview(); $("#reminder-input").value = ""; await loadDeadlines(); } catch (error) { $("#preview-message").textContent = error.message; } });

document.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { state.filter = button.dataset.filter; render(); }));
$("#close-modal").addEventListener("click", closePreview); $("#cancel-preview").addEventListener("click", closePreview); $("#refresh-button").addEventListener("click", loadDeadlines); $("#retry-button").addEventListener("click", loadDeadlines); $("#preview-modal").addEventListener("click", (event) => { if (event.target.id === "preview-modal") closePreview(); });
loadDeadlines();
