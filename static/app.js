const homeView = document.querySelector("#home-view");
const expensesView = document.querySelector("#expenses-view");
const transfersView = document.querySelector("#transfers-view");
const homeButton = document.querySelector("#home-button");
const moduleButtons = document.querySelectorAll(".module-button");

const form = document.querySelector("#expense-form");
const pdfForm = document.querySelector("#pdf-form");
const message = document.querySelector("#message");
const pdfMessage = document.querySelector("#pdf-message");
const expensesBody = document.querySelector("#expenses-body");
const emptyState = document.querySelector("#empty-state");
const total = document.querySelector("#total");
const filterMonth = document.querySelector("#filter-month");
const filterDate = document.querySelector("#filter-date");
const filterSearch = document.querySelector("#filter-search");
const clearFilters = document.querySelector("#clear-filters");
const defaultExpenses = document.querySelector("#default-expenses");
const monthlySummary = document.querySelector("#monthly-summary");
const saveButton = document.querySelector("#save-button");
const cancelEdit = document.querySelector("#cancel-edit");

const transferForm = document.querySelector("#transfer-form");
const transferMessage = document.querySelector("#transfer-message");
const transferFilterMonth = document.querySelector("#transfer-filter-month");
const transferFilterDate = document.querySelector("#transfer-filter-date");
const clearTransferFilters = document.querySelector("#clear-transfer-filters");
const transfersBody = document.querySelector("#transfers-body");
const transfersEmptyState = document.querySelector("#transfers-empty-state");
const transferBalance = document.querySelector("#transfer-balance");
const transferBalanceInline = document.querySelector("#transfer-balance-inline");
const transferExpensesTotal = document.querySelector("#transfer-expenses-total");
const transfersTotal = document.querySelector("#transfers-total");

const money = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
});

let currentExpenses = [];

function today() {
  return new Date().toISOString().slice(0, 10);
}

function currentMonth() {
  return today().slice(0, 7);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showView(view) {
  homeView.hidden = view !== "home";
  expensesView.hidden = view !== "expenses";
  transfersView.hidden = view !== "transfers";
  homeButton.hidden = view === "home";

  if (view === "expenses") loadExpenses();
  if (view === "transfers") loadTransfers();
}

function currentFilters() {
  const params = new URLSearchParams();

  if (filterMonth.value) params.set("month", filterMonth.value);
  if (filterDate.value) params.set("date", filterDate.value);
  if (filterSearch.value.trim()) params.set("q", filterSearch.value.trim());

  return params;
}

function currentTransferFilters() {
  const params = new URLSearchParams();

  params.set("month", transferFilterMonth.value || currentMonth());
  if (transferFilterDate.value) params.set("date", transferFilterDate.value);

  return params;
}

function renderDefaults(defaults) {
  defaultExpenses.innerHTML = "";
  defaults.forEach((description) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "preset-button";
    button.textContent = description;
    button.addEventListener("click", () => {
      form.elements.description.value = description;
      form.elements.amount.focus();
    });
    defaultExpenses.appendChild(button);
  });
}

function renderExpenses(expenses) {
  currentExpenses = expenses;
  expensesBody.innerHTML = "";
  emptyState.hidden = expenses.length > 0;

  expenses.forEach((expense) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(expense.month)}</td>
      <td>${escapeHtml(expense.date)}</td>
      <td>${escapeHtml(expense.description)}</td>
      <td class="amount">${money.format(expense.amount)}</td>
      <td class="actions">
        <button class="edit-button" type="button" data-id="${expense.id}" title="Editar">Editar</button>
        <button class="delete-button" type="button" data-id="${expense.id}" title="Eliminar">X</button>
      </td>
    `;
    expensesBody.appendChild(row);
  });
}

function renderTransfers(transfers) {
  transfersBody.innerHTML = "";
  transfersEmptyState.hidden = transfers.length > 0;

  transfers.forEach((transfer) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(transfer.month)}</td>
      <td>${escapeHtml(transfer.date)}</td>
      <td>${escapeHtml(transfer.destination)}</td>
      <td class="amount">${money.format(transfer.amount)}</td>
      <td class="actions">
        <button class="delete-button" type="button" data-id="${transfer.id}" title="Eliminar">X</button>
      </td>
    `;
    transfersBody.appendChild(row);
  });
}

function renderSummary(summary) {
  monthlySummary.innerHTML = "";
  if (!summary.length) {
    monthlySummary.innerHTML = '<p class="empty-summary">Sin gastos para resumir.</p>';
    return;
  }

  summary.forEach((item) => {
    const article = document.createElement("article");
    article.className = "summary-item";
    article.innerHTML = `<span>${escapeHtml(item.month)}</span><strong>${money.format(item.total)}</strong>`;
    monthlySummary.appendChild(article);
  });
}

function renderTransferTotals(data) {
  transferExpensesTotal.textContent = money.format(data.expenses_total);
  transfersTotal.textContent = money.format(data.total);
  transferBalance.textContent = money.format(data.balance);
  transferBalanceInline.textContent = money.format(data.balance);
}

function resetForm() {
  form.reset();
  form.elements.id.value = "";
  form.elements.month.value = currentMonth();
  form.elements.date.value = today();
  saveButton.textContent = "Guardar gasto";
  cancelEdit.hidden = true;
}

function resetTransferForm() {
  transferForm.reset();
  transferForm.elements.date.value = today();
}

async function loadExpenses() {
  const params = currentFilters();
  const response = await fetch(`/api/expenses?${params.toString()}`);
  const data = await response.json();

  renderDefaults(data.defaults);
  renderExpenses(data.expenses);
  renderSummary(data.summary);
  total.textContent = money.format(data.total);
}

async function loadTransfers() {
  const params = currentTransferFilters();
  const response = await fetch(`/api/transfers?${params.toString()}`);
  const data = await response.json();

  transferFilterMonth.value = data.month;
  renderTransfers(data.transfers);
  renderTransferTotals(data);
}

moduleButtons.forEach((button) => {
  button.addEventListener("click", () => showView(button.dataset.view));
});

homeButton.addEventListener("click", () => showView("home"));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";

  const payload = Object.fromEntries(new FormData(form).entries());
  const id = payload.id;
  delete payload.id;

  const response = await fetch(id ? `/api/expenses/${id}` : "/api/expenses", {
    method: id ? "PUT" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json();
    message.textContent = data.error || "No se pudo guardar el gasto.";
    return;
  }

  resetForm();
  await loadExpenses();
});

transferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  transferMessage.textContent = "";

  const payload = Object.fromEntries(new FormData(transferForm).entries());
  const response = await fetch("/api/transfers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json();
    transferMessage.textContent = data.error || "No se pudo guardar la transferencia.";
    return;
  }

  transferFilterMonth.value = payload.date.slice(0, 7);
  resetTransferForm();
  await loadTransfers();
});

expensesBody.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-button");
  const deleteButton = event.target.closest(".delete-button");

  if (editButton) {
    const expense = currentExpenses.find((item) => item.id === Number(editButton.dataset.id));
    if (!expense) return;

    form.elements.id.value = expense.id;
    form.elements.month.value = expense.month;
    form.elements.date.value = expense.date;
    form.elements.description.value = expense.description;
    form.elements.amount.value = expense.amount;
    saveButton.textContent = "Guardar cambios";
    cancelEdit.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }

  if (!deleteButton) return;

  await fetch(`/api/expenses/${deleteButton.dataset.id}`, { method: "DELETE" });
  await loadExpenses();
});

transfersBody.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest(".delete-button");
  if (!deleteButton) return;

  await fetch(`/api/transfers/${deleteButton.dataset.id}`, { method: "DELETE" });
  await loadTransfers();
});

pdfForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  pdfMessage.textContent = "";

  const response = await fetch("/api/import/pdf", {
    method: "POST",
    body: new FormData(pdfForm),
  });
  const data = await response.json();

  if (!response.ok) {
    pdfMessage.textContent = data.error || "No se pudo importar el PDF.";
    return;
  }

  pdfForm.reset();
  pdfMessage.textContent = `Se importaron ${data.imported} gastos.`;
  await loadExpenses();
});

[filterMonth, filterDate].forEach((control) => {
  control.addEventListener("change", loadExpenses);
});

filterSearch.addEventListener("input", loadExpenses);

[transferFilterMonth, transferFilterDate].forEach((control) => {
  control.addEventListener("change", loadTransfers);
});

clearFilters.addEventListener("click", () => {
  filterMonth.value = "";
  filterDate.value = "";
  filterSearch.value = "";
  loadExpenses();
});

clearTransferFilters.addEventListener("click", () => {
  transferFilterMonth.value = currentMonth();
  transferFilterDate.value = "";
  loadTransfers();
});

cancelEdit.addEventListener("click", resetForm);

resetForm();
resetTransferForm();
transferFilterMonth.value = currentMonth();
showView("home");
