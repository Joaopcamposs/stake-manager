const modal = document.getElementById("modal-aposta") as HTMLDialogElement | null;
const form = document.getElementById("form-aposta") as HTMLFormElement | null;
const btnOpen = document.getElementById("btn-nova-aposta");
const btnClose = document.getElementById("modal-close");
const modalTitle = document.getElementById("modal-title");
const editBetId = document.getElementById("edit-bet-id") as HTMLInputElement;
const editMode = document.getElementById("edit-mode") as HTMLInputElement;
const fieldsetPrincipal = document.getElementById("fieldset-principal");
const fieldsetZoiao = document.getElementById("fieldset-zoiao");
const btnSubmit = document.getElementById("btn-submit");
const btnDelete = document.getElementById("btn-delete");
const fieldResultPrincipal = document.getElementById("field-result-principal") as HTMLInputElement;
const fieldResultZoiao = document.getElementById("field-result-zoiao") as HTMLInputElement;

function toSaoPauloDate(date: Date): Date {
  const saoPauloOffset = -3; // UTC-3 for São Paulo (no DST since 2019)
  const utc = date.getTime() + (date.getTimezoneOffset() * 60000);
  return new Date(utc + (saoPauloOffset * 3600000));
}

function localDate(): string {
  const now = toSaoPauloDate(new Date());
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function resetModal() {
  if (!form) return;
  form.reset();
  editBetId.value = "";
  editMode.value = "create";
  modalTitle!.textContent = "Nova Aposta";
  btnSubmit!.textContent = "Salvar";
  btnDelete!.classList.add("hidden");
  fieldsetPrincipal!.classList.remove("hidden");
  fieldsetZoiao!.classList.remove("hidden");
  fieldResultPrincipal.value = "";
  fieldResultZoiao.value = "";
  clearResultSelection("principal");
  clearResultSelection("zoiao");

  const dateInput = document.getElementById("bet-date") as HTMLInputElement;
  dateInput.value = localDate();
  (document.getElementById("principal-stake") as HTMLInputElement).value = "100";
  (document.getElementById("zoiao-stake") as HTMLInputElement).value = "25";
}

function openCreateModal() {
  resetModal();
  modal?.showModal();
}

function openEditModal(row: HTMLElement) {
  resetModal();
  const betId = row.dataset.betId || "";
  const game = row.dataset.game || "";
  const betDate = row.dataset.date || "";
  const betType = row.dataset.type || "";
  const market = row.dataset.market || "";
  const stake = row.dataset.stake || "";
  const odd = row.dataset.odd || "";
  const result = row.dataset.result || "";
  editBetId.value = betId;
  editMode.value = "edit";
  (document.getElementById("edit-bet-type") as HTMLInputElement).value = betType;
  modalTitle!.textContent = "Editar Aposta";
  btnSubmit!.textContent = "Atualizar";
  btnDelete!.classList.remove("hidden");

  if (betType === "principal") {
    fieldsetZoiao!.classList.add("hidden");
    (document.getElementById("principal-market") as HTMLSelectElement).value = market;
    (document.getElementById("principal-stake") as HTMLInputElement).value = stake;
    (document.getElementById("principal-odd") as HTMLInputElement).value = odd;
    fieldResultPrincipal.value = result;
    highlightResult("principal", result);
  } else {
    fieldsetPrincipal!.classList.add("hidden");
    (document.getElementById("zoiao-market") as HTMLSelectElement).value = market;
    (document.getElementById("zoiao-stake") as HTMLInputElement).value = stake;
    (document.getElementById("zoiao-odd") as HTMLInputElement).value = odd;
    fieldResultZoiao.value = result;
    highlightResult("zoiao", result);
  }

  (document.getElementById("field-game") as HTMLInputElement).value = game;
  (document.getElementById("bet-date") as HTMLInputElement).value = betDate;

  modal?.showModal();
}

// Result button selection per group
function clearResultSelection(group: string) {
  document.querySelectorAll(`.result-btn-${group}`).forEach((btn) => {
    btn.classList.remove("ring-2", "ring-white", "!border-white");
  });
}

function highlightResult(group: string, value: string) {
  clearResultSelection(group);
  const btn = document.querySelector(`.result-btn-${group}[data-result="${value}"]`);
  if (btn) {
    btn.classList.add("ring-2", "ring-white", "!border-white");
  }
}

document.querySelectorAll(".result-btn-principal").forEach((btn) => {
  btn.addEventListener("click", () => {
    const val = (btn as HTMLElement).dataset.result || "";
    fieldResultPrincipal.value = val;
    highlightResult("principal", val);
  });
});

document.querySelectorAll(".result-btn-zoiao").forEach((btn) => {
  btn.addEventListener("click", () => {
    const val = (btn as HTMLElement).dataset.result || "";
    fieldResultZoiao.value = val;
    highlightResult("zoiao", val);
  });
});

// Delete bet
btnDelete?.addEventListener("click", async () => {
  const betId = editBetId.value;
  if (!betId) return;
  if (!confirm("Excluir esta aposta?")) return;
  const resp = await fetch(`/bets/${betId}`, { method: "DELETE" });
  if (resp.ok) {
    window.location.reload();
  } else {
    alert("Erro ao excluir.");
  }
});

// Modal open/close
btnOpen?.addEventListener("click", openCreateModal);
btnClose?.addEventListener("click", () => modal?.close());

// Bet rows click to edit
document.querySelectorAll(".bet-row").forEach((row) => {
  row.addEventListener("click", () => openEditModal(row as HTMLElement));
});

// Return calculation
function calcReturn(stakeId: string, oddId: string, displayId: string) {
  const stakeEl = document.getElementById(stakeId) as HTMLInputElement | null;
  const oddEl = document.getElementById(oddId) as HTMLInputElement | null;
  const displayEl = document.getElementById(displayId);
  if (!stakeEl || !oddEl || !displayEl) return;

  function update() {
    const stake = parseFloat(stakeEl!.value) || 0;
    const odd = parseFloat(normalizeOdd(oddEl!.value)) || 0;
    displayEl!.textContent = stake > 0 && odd > 0 ? `R$ ${(stake * odd).toFixed(2)}` : "R$ —";
  }

  stakeEl.addEventListener("input", update);
  oddEl.addEventListener("input", update);
}

calcReturn("principal-stake", "principal-odd", "retorno-principal");
calcReturn("zoiao-stake", "zoiao-odd", "retorno-zoiao");

// Normalize odd: "155" -> "1.55", "2" -> "2"
function normalizeOdd(value: string): string {
  const clean = value.replace(",", ".").trim();
  if (!clean) return "";
  if (clean.includes(".")) return clean;
  if (clean.length === 1) return clean;
  return clean[0] + "." + clean.slice(1);
}

function normalizeOddInputs() {
  const ids = ["principal-odd", "zoiao-odd"];
  for (const id of ids) {
    const el = document.getElementById(id) as HTMLInputElement | null;
    if (el && el.value) {
      el.value = normalizeOdd(el.value);
    }
  }
}

// Form submit
form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  normalizeOddInputs();
  const mode = editMode.value;

  if (mode === "create") {
    const pOdd = parseFloat((document.getElementById("principal-odd") as HTMLInputElement).value) || 0;
    const zOdd = parseFloat((document.getElementById("zoiao-odd") as HTMLInputElement).value) || 0;
    if (pOdd <= 0 && zOdd <= 0) {
      alert("Preencha a odd de pelo menos uma aposta.");
      return;
    }

    const formData = new FormData(form);
    formData.set("principal_result", fieldResultPrincipal.value);
    formData.set("zoiao_result", fieldResultZoiao.value);
    const resp = await fetch("/bets", { method: "POST", body: formData });
    if (resp.ok || resp.redirected) {
      window.location.reload();
    } else {
      alert("Erro ao salvar aposta.");
    }
  } else {
    // Edit mode
    const betId = editBetId.value;
    const betType = (document.getElementById("edit-bet-type") as HTMLInputElement)?.value || "";
    const formData = new FormData();
    formData.set("game_name", (document.getElementById("field-game") as HTMLInputElement).value);
    formData.set("bet_date", (document.getElementById("bet-date") as HTMLInputElement).value);

    if (betType === "principal") {
      formData.set("market", (document.getElementById("principal-market") as HTMLSelectElement).value);
      formData.set("stake", (document.getElementById("principal-stake") as HTMLInputElement).value);
      formData.set("odd", (document.getElementById("principal-odd") as HTMLInputElement).value);
      formData.set("result", fieldResultPrincipal.value);
    } else {
      formData.set("market", (document.getElementById("zoiao-market") as HTMLSelectElement).value);
      formData.set("stake", (document.getElementById("zoiao-stake") as HTMLInputElement).value);
      formData.set("odd", (document.getElementById("zoiao-odd") as HTMLInputElement).value);
      formData.set("result", fieldResultZoiao.value);
    }

    const resp = await fetch(`/bets/${betId}`, { method: "PUT", body: formData });
    if (!resp.ok) {
      alert("Erro ao atualizar aposta.");
      return;
    }
    window.location.reload();
  }
});

// Set default date on load
const dateInput = document.getElementById("bet-date") as HTMLInputElement;
if (dateInput && !dateInput.value) {
  dateInput.value = localDate();
}

// Day selector navigation
const daySelector = document.getElementById("day-selector") as HTMLInputElement;
daySelector?.addEventListener("change", () => {
  const val = daySelector.value;
  if (val) {
    window.location.href = `/?day=${val}`;
  }
});
