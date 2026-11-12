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
const filterYear = document.querySelector("#filter-year");
const filterDate = document.querySelector("#filter-date");
const filterFrom = document.querySelector("#filter-from");
const filterTo = document.querySelector("#filter-to");
const filterSearch = document.querySelector("#filter-search");
const clearFilters = document.querySelector("#clear-filters");
const monthlySummary = document.querySelector("#monthly-summary");
const cardSummary = document.querySelector("#card-summary");
const cardDetailPanel = document.querySelector("#card-detail-panel");
const cardDetailTitle = document.querySelector("#card-detail-title");
const cardDetailBody = document.querySelector("#card-detail-body");
const cardDetailEmpty = document.querySelector("#card-detail-empty");
const closeCardDetail = document.querySelector("#close-card-detail");
const saveButton = document.querySelector("#save-button");
const cancelEdit = document.querySelector("#cancel-edit");

const transferForm = document.querySelector("#transfer-form");
const transferMessage = document.querySelector("#transfer-message");
const transferFilterMonth = document.querySelector("#transfer-filter-month");
const transferFilterYear = document.querySelector("#transfer-filter-year");
const transferFilterDate = document.querySelector("#transfer-filter-date");
const transferFilterFrom = document.querySelector("#transfer-filter-from");
const transferFilterTo = document.querySelector("#transfer-filter-to");
const clearTransferFilters = document.querySelector("#clear-transfer-filters");
const transfersBody = document.querySelector("#transfers-body");
const transfersEmptyState = document.querySelector("#transfers-empty-state");
const transferBalance = document.querySelector("#transfer-balance");
const transferBalanceInline = document.querySelector("#transfer-balance-inline");
const transferExpensesTotal = document.querySelector("#transfer-expenses-total");
const transfersTotal = document.querySelector("#transfers-total");
const totalSpent = document.querySelector("#total-spent");
const totalRefunds = document.querySelector("#total-refunds");
const pdfPreview = document.querySelector("#pdf-preview");
const pdfPreviewBody = document.querySelector("#pdf-preview-body");
const confirmPdf = document.querySelector("#confirm-pdf");
const cancelPdf = document.querySelector("#cancel-pdf");

const money = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
});

let currentExpenses = [];
let currentCardExpenses = [];
let previewCardType = "";

function today() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function currentMonth() {
  return today().slice(0, 7);
}

function setMonthYear(monthControl, yearControl, value) {
  const [year, month] = value.split("-");
  monthControl.value = String(Number(month));
  yearControl.value = year;
}

function selectedMonth(monthControl, yearControl) {
  return `${yearControl.value}-${String(monthControl.value).padStart(2, "0")}`;
}

function setExpenseDescription(value) {
  const descriptionControl = form.elements.description;
  const matchingOption = [...descriptionControl.options].find(
    (option) => option.value === value,
  );
  if (!matchingOption && value) {
    const option = new Option(value, value);
    option.dataset.legacy = "true";
    descriptionControl.add(option);
  }
  descriptionControl.value = value;
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

function appendMonthYear(params, monthControl, yearControl) {
  params.set("month", monthControl.value);
  params.set("year", yearControl.value);
}

function currentFilters() {
  const params = new URLSearchParams();

  if (filterDate.value) {
    params.set("date", filterDate.value);
  } else if (filterFrom.value || filterTo.value) {
    if (filterFrom.value) params.set("from", filterFrom.value);
    if (filterTo.value) params.set("to", filterTo.value);
  } else {
    appendMonthYear(params, filterMonth, filterYear);
  }
  if (filterSearch.value.trim()) params.set("q", filterSearch.value.trim());
  return params;
}

function currentTransferFilters() {
  const params = new URLSearchParams();

  if (transferFilterDate.value) {
    params.set("date", transferFilterDate.value);
  } else if (transferFilterFrom.value || transferFilterTo.value) {
    if (transferFilterFrom.value) params.set("from", transferFilterFrom.value);
    if (transferFilterTo.value) params.set("to", transferFilterTo.value);
  } else {
    appendMonthYear(params, transferFilterMonth, transferFilterYear);
  }
  return params;
}

function cardPeriodFilters() {
  const params = new URLSearchParams();
  appendMonthYear(params, filterMonth, filterYear);
  return params;
}

async function readJson(response, fallback) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || fallback);
  return data;
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
      <td class="amount">${expense.movement_type === "refund" ? "−" : ""}${money.format(expense.amount)}</td>
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
    monthlySummary.innerHTML = '<p class="empty-summary">Sin gastos para este periodo.</p>';
    return;
  }

  summary.forEach((item) => {
    const article = document.createElement("article");
    article.className = "summary-item";
    article.innerHTML = `<span>${escapeHtml(item.month)}</span><strong>${money.format(item.total)}</strong>`;
    monthlySummary.appendChild(article);
  });
}

function renderCardSummary(cards) {
  cardSummary.innerHTML = "";
  cards.forEach((card) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "card-summary-button";
    button.dataset.cardType = card.card_type;
    button.innerHTML = `
      <span>${escapeHtml(card.label)}</span>
      <strong>${money.format(card.total)}</strong>
      <small>${card.count} movimientos · ver detalle</small>
    `;
    cardSummary.appendChild(button);
  });
}

function renderCardExpenses(data) {
  currentCardExpenses = data.expenses;
  cardDetailTitle.textContent = `${data.label} · pagos de ${String(data.month).padStart(2, "0")}/${data.year}`;
  cardDetailBody.innerHTML = "";
  cardDetailEmpty.hidden = data.expenses.length > 0;
  data.expenses.forEach((expense) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(expense.statement_month || "No informado")}</td>
      <td>${escapeHtml(expense.date)}</td>
      <td>${escapeHtml(expense.description)}</td>
      <td>${expense.movement_type === "refund" ? "Reintegro" : "Gasto"}</td>
      <td class="amount">${expense.movement_type === "refund" ? "−" : ""}${money.format(expense.amount)}</td>
      <td class="actions">
        <button class="edit-button card-edit-button" type="button" data-id="${expense.id}" title="Editar">Editar</button>
        <button class="delete-button card-delete-button" type="button" data-id="${expense.id}" title="Eliminar">X</button>
      </td>
    `;
    cardDetailBody.appendChild(row);
  });
  cardDetailPanel.hidden = false;
}

function renderTransferTotals(data) {
  transferExpensesTotal.textContent = money.format(data.expenses_total);
  transfersTotal.textContent = money.format(data.total);
  totalSpent.textContent = money.format(data.total_spent);
  totalRefunds.textContent = money.format(data.total_refunds);
  transferBalance.textContent = money.format(data.balance);
  transferBalanceInline.textContent = money.format(data.balance);
}

function resetForm() {
  form.querySelectorAll("option[data-legacy]").forEach((option) => option.remove());
  form.reset();
  form.elements.id.value = "";
  setMonthYear(
    form.elements.month_number,
    form.elements.year,
    currentMonth(),
  );
  form.elements.date.value = today();
  form.elements.card_type.value = "";
  form.elements.payment_month.value = "";
  form.elements.statement_month.value = "";
  saveButton.textContent = "Guardar gasto";
  cancelEdit.hidden = true;
}

function resetTransferForm() {
  transferForm.reset();
  transferForm.elements.date.value = today();
}

async function loadExpenses() {
  try {
    const data = await readJson(
      await fetch(`/api/expenses?${currentFilters().toString()}`),
      "No se pudieron cargar los gastos.",
    );
    renderExpenses(data.expenses);
    renderSummary(data.summary);
    total.textContent = money.format(data.total);
    const cards = await readJson(
      await fetch(`/api/expenses/card-summary?${cardPeriodFilters().toString()}`),
      "No se pudo cargar el resumen de tarjetas.",
    );
    renderCardSummary(cards.cards);
    message.textContent = "";
  } catch (error) {
    message.textContent = error.message;
  }
}

async function loadCardExpenses(cardType) {
  try {
    const params = cardPeriodFilters();
    const data = await readJson(
      await fetch(`/api/expenses/cards/${cardType}?${params.toString()}`),
      "No se pudo cargar el detalle de la tarjeta.",
    );
    renderCardExpenses(data);
  } catch (error) {
    pdfMessage.textContent = error.message;
  }
}

async function loadTransfers() {
  try {
    const data = await readJson(
      await fetch(`/api/transfers?${currentTransferFilters().toString()}`),
      "No se pudieron cargar las transferencias.",
    );
    renderTransfers(data.transfers);
    renderTransferTotals(data);
    transferMessage.textContent = "";
  } catch (error) {
    transferMessage.textContent = error.message;
  }
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
  payload.month = `${payload.year}-${String(payload.month_number).padStart(2, "0")}`;
  delete payload.month_number;
  delete payload.year;
  delete payload.id;

  try {
    const data = await readJson(
      await fetch(id ? `/api/expenses/${id}` : "/api/expenses", {
        method: id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
      "No se pudo guardar el gasto.",
    );
    resetForm();
    setMonthYear(filterMonth, filterYear, data.payment_month);
    filterDate.value = "";
    filterFrom.value = "";
    filterTo.value = "";
    await loadExpenses();
  } catch (error) {
    message.textContent = error.message;
  }
});

transferForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  transferMessage.textContent = "";
  const payload = Object.fromEntries(new FormData(transferForm).entries());
  try {
    await readJson(
      await fetch("/api/transfers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
      "No se pudo guardar la transferencia.",
    );
    setMonthYear(
      transferFilterMonth,
      transferFilterYear,
      payload.date.slice(0, 7),
    );
    transferFilterDate.value = "";
    transferFilterFrom.value = "";
    transferFilterTo.value = "";
    resetTransferForm();
    await loadTransfers();
  } catch (error) {
    transferMessage.textContent = error.message;
  }
});

async function deleteExpense(id) {
  try {
    const response = await fetch(`/api/expenses/${id}`, { method: "DELETE" });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "No se pudo eliminar el gasto.");
    }
    cardDetailPanel.hidden = true;
    await loadExpenses();
  } catch (error) {
    message.textContent = error.message;
  }
}

expensesBody.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-button");
  const deleteButton = event.target.closest(".delete-button");
  if (editButton) {
    const expense = currentExpenses.find((item) => item.id === Number(editButton.dataset.id));
    if (!expense) return;
    form.elements.id.value = expense.id;
    setMonthYear(form.elements.month_number, form.elements.year, expense.month);
    form.elements.date.value = expense.date;
    setExpenseDescription(expense.description);
    form.elements.amount.value = expense.amount;
    form.elements.movement_type.value = expense.movement_type || "expense";
    form.elements.card_type.value = expense.card_type || "";
    form.elements.payment_month.value = expense.payment_month || "";
    form.elements.statement_month.value = expense.statement_month || "";
    saveButton.textContent = "Guardar cambios";
    cancelEdit.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (deleteButton) await deleteExpense(deleteButton.dataset.id);
});

cardSummary.addEventListener("click", (event) => {
  const button = event.target.closest("[data-card-type]");
  if (button) loadCardExpenses(button.dataset.cardType);
});

cardDetailBody.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".card-edit-button");
  const deleteButton = event.target.closest(".card-delete-button");
  if (editButton) {
    const expense = currentCardExpenses.find((item) => item.id === Number(editButton.dataset.id));
    if (!expense) return;
    form.elements.id.value = expense.id;
    setMonthYear(form.elements.month_number, form.elements.year, expense.payment_month);
    form.elements.date.value = expense.date;
    setExpenseDescription(expense.description);
    form.elements.amount.value = expense.amount;
    form.elements.movement_type.value = expense.movement_type;
    form.elements.card_type.value = expense.card_type;
    form.elements.payment_month.value = expense.payment_month;
    form.elements.statement_month.value = expense.statement_month || "";
    saveButton.textContent = "Guardar cambios";
    cancelEdit.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (deleteButton) await deleteExpense(deleteButton.dataset.id);
});

closeCardDetail.addEventListener("click", () => {
  cardDetailPanel.hidden = true;
  cardDetailBody.innerHTML = "";
});

transfersBody.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest(".delete-button");
  if (!deleteButton) return;
  try {
    const response = await fetch(`/api/transfers/${deleteButton.dataset.id}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "No se pudo eliminar la transferencia.");
    }
    await loadTransfers();
  } catch (error) {
    transferMessage.textContent = error.message;
  }
});

pdfForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  pdfMessage.textContent = "";
  const formData = new FormData(pdfForm);
  formData.set(
    "payment_month",
    `${formData.get("payment_year")}-${String(formData.get("payment_month_number")).padStart(2, "0")}`,
  );
  formData.set(
    "statement_month",
    `${formData.get("statement_year")}-${String(formData.get("statement_month_number")).padStart(2, "0")}`,
  );
  try {
    const data = await readJson(
      await fetch("/api/import/pdf", { method: "POST", body: formData }),
      "No se pudo procesar el PDF.",
    );
    previewCardType = data.card_type;
    renderPdfPreview(data.preview);
    pdfForm.reset();
    setMonthYear(
      pdfForm.elements.payment_month_number,
      pdfForm.elements.payment_year,
      currentMonth(),
    );
    setMonthYear(
      pdfForm.elements.statement_month_number,
      pdfForm.elements.statement_year,
      currentMonth(),
    );
    pdfMessage.textContent = `Se detectaron ${data.preview.length} movimientos. Revisalos antes de confirmar.`;
  } catch (error) {
    pdfMessage.textContent = error.message;
  }
});

function renderPdfPreview(expenses) {
  pdfPreviewBody.innerHTML = expenses.map((expense) => `
    <tr>
      <td>${escapeHtml(expense.date)}</td>
      <td>${escapeHtml(expense.payment_month)}</td>
      <td>${escapeHtml(expense.statement_month)}</td>
      <td><input type="text" class="preview-description description-input" value="${escapeHtml(expense.description)}" maxlength="180" required></td>
      <td><input type="number" class="preview-amount" min="0.01" step="0.01" value="${Number(expense.amount)}" required></td>
      <td>
        <select class="preview-kind">
          <option value="expense" ${expense.movement_type === "expense" ? "selected" : ""}>Gasto</option>
          <option value="refund" ${expense.movement_type === "refund" ? "selected" : ""}>Reintegro</option>
        </select>
      </td>
      <td><button type="button" class="delete-button preview-remove">Quitar</button></td>
    </tr>
  `).join("");
  pdfPreview.dataset.paymentMonth = expenses[0]?.payment_month || "";
  pdfPreview.dataset.statementMonth = expenses[0]?.statement_month || "";
  pdfPreview.hidden = false;
  pdfPreview.scrollIntoView({ behavior: "smooth", block: "start" });
}

function closePdfPreview() {
  pdfPreview.hidden = true;
  pdfPreviewBody.innerHTML = "";
  previewCardType = "";
}

pdfPreviewBody.addEventListener("click", (event) => {
  const removeButton = event.target.closest(".preview-remove");
  if (removeButton) removeButton.closest("tr").remove();
});

confirmPdf.addEventListener("click", async () => {
  const expenses = [...pdfPreviewBody.querySelectorAll("tr")].map((row) => ({
    date: row.cells[0].textContent,
    payment_month: row.cells[1].textContent,
    statement_month: row.cells[2].textContent,
    description: row.querySelector(".preview-description").value,
    amount: row.querySelector(".preview-amount").value,
    movement_type: row.querySelector(".preview-kind").value,
  }));
  if (!expenses.length) {
    pdfMessage.textContent = "No hay movimientos seleccionados para confirmar.";
    return;
  }

  confirmPdf.disabled = true;
  try {
    const data = await readJson(
      await fetch("/api/import/pdf/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ card_type: previewCardType, expenses }),
      }),
      "No se pudieron guardar los movimientos.",
    );
    const paymentMonth = expenses[0].payment_month;
    setMonthYear(filterMonth, filterYear, paymentMonth);
    filterDate.value = "";
    filterFrom.value = "";
    filterTo.value = "";
    pdfMessage.textContent = `Se confirmaron ${data.imported} movimientos.`;
    closePdfPreview();
    await loadExpenses();
  } catch (error) {
    pdfMessage.textContent = error.message;
  } finally {
    confirmPdf.disabled = false;
  }
});

cancelPdf.addEventListener("click", () => {
  closePdfPreview();
  pdfMessage.textContent = "Importacion cancelada; no se guardaron movimientos.";
});

function onExpensePeriodChange() {
  filterDate.value = "";
  filterFrom.value = "";
  filterTo.value = "";
  cardDetailPanel.hidden = true;
  loadExpenses();
}

filterMonth.addEventListener("change", onExpensePeriodChange);
filterYear.addEventListener("change", onExpensePeriodChange);
filterDate.addEventListener("change", () => {
  filterFrom.value = "";
  filterTo.value = "";
  loadExpenses();
});
[filterFrom, filterTo].forEach((control) => {
  control.addEventListener("change", () => {
    filterDate.value = "";
    loadExpenses();
  });
});
filterSearch.addEventListener("input", loadExpenses);

function onTransferPeriodChange() {
  transferFilterDate.value = "";
  transferFilterFrom.value = "";
  transferFilterTo.value = "";
  loadTransfers();
}

transferFilterMonth.addEventListener("change", onTransferPeriodChange);
transferFilterYear.addEventListener("change", onTransferPeriodChange);
transferFilterDate.addEventListener("change", () => {
  transferFilterFrom.value = "";
  transferFilterTo.value = "";
  loadTransfers();
});
[transferFilterFrom, transferFilterTo].forEach((control) => {
  control.addEventListener("change", () => {
    transferFilterDate.value = "";
    loadTransfers();
  });
});

clearFilters.addEventListener("click", () => {
  setMonthYear(filterMonth, filterYear, currentMonth());
  filterDate.value = "";
  filterFrom.value = "";
  filterTo.value = "";
  filterSearch.value = "";
  cardDetailPanel.hidden = true;
  loadExpenses();
});

clearTransferFilters.addEventListener("click", () => {
  setMonthYear(transferFilterMonth, transferFilterYear, currentMonth());
  transferFilterDate.value = "";
  transferFilterFrom.value = "";
  transferFilterTo.value = "";
  loadTransfers();
});

cancelEdit.addEventListener("click", resetForm);

setMonthYear(form.elements.month_number, form.elements.year, currentMonth());
form.elements.date.value = today();
form.elements.movement_type.value = "expense";
setMonthYear(
  pdfForm.elements.payment_month_number,
  pdfForm.elements.payment_year,
  currentMonth(),
);
setMonthYear(
  pdfForm.elements.statement_month_number,
  pdfForm.elements.statement_year,
  currentMonth(),
);
setMonthYear(filterMonth, filterYear, currentMonth());
setMonthYear(transferFilterMonth, transferFilterYear, currentMonth());
transferForm.elements.date.value = today();
showView("home");
