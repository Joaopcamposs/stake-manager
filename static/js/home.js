document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("modal-aposta");
    const btnOpen = document.getElementById("btn-nova-aposta");
    const btnClose = document.getElementById("modal-close");
    const form = document.getElementById("form-aposta");
    const dateInput = document.getElementById("bet-date");

    // Set today's date
    const today = new Date().toISOString().split("T")[0];
    if (dateInput) dateInput.value = today;

    // Modal open/close
    if (btnOpen && modal) {
        btnOpen.addEventListener("click", () => modal.showModal());
    }
    if (btnClose && modal) {
        btnClose.addEventListener("click", () => modal.close());
    }

    // Real-time return calculation
    function calcReturn(stakeId, oddId, displayId) {
        const stakeEl = document.getElementById(stakeId);
        const oddEl = document.getElementById(oddId);
        const displayEl = document.getElementById(displayId);
        if (!stakeEl || !oddEl || !displayEl) return;

        function update() {
            const stake = parseFloat(stakeEl.value) || 0;
            const odd = parseFloat(oddEl.value) || 0;
            if (stake > 0 && odd > 0) {
                displayEl.textContent = "R$ " + (stake * odd).toFixed(2);
            } else {
                displayEl.textContent = "R$ —";
            }
        }

        stakeEl.addEventListener("input", update);
        oddEl.addEventListener("input", update);
    }

    calcReturn("principal-stake", "principal-odd", "retorno-principal");
    calcReturn("zoiao-stake", "zoiao-odd", "retorno-zoiao");

    // Form validation
    if (form) {
        form.addEventListener("submit", (e) => {
            const pOdd = parseFloat(document.getElementById("principal-odd").value) || 0;
            const zOdd = parseFloat(document.getElementById("zoiao-odd").value) || 0;
            if (pOdd <= 0 && zOdd <= 0) {
                e.preventDefault();
                alert("Preencha a odd de pelo menos uma aposta (principal ou zoião).");
            }
        });
    }

    // Result buttons
    document.querySelectorAll(".bet-actions").forEach((container) => {
        const betId = container.dataset.betId;
        container.querySelectorAll(".btn-result").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const result = btn.dataset.result;
                if (!confirm(`Confirma resultado ${result.toUpperCase()}?`)) return;

                try {
                    const resp = await fetch(`/bets/${betId}/result`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ result }),
                    });

                    if (resp.ok) {
                        const card = container.closest(".bet-card");
                        if (card) card.remove();
                        // Check if no more pending
                        const list = document.querySelector(".pending-list");
                        if (list && list.children.length === 0) {
                            list.innerHTML = '<p class="muted">Nenhuma aposta pendente.</p>';
                        }
                    } else {
                        alert("Erro ao atualizar resultado.");
                    }
                } catch (err) {
                    alert("Erro de conexão.");
                }
            });
        });
    });
});
