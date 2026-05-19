document.addEventListener("DOMContentLoaded", () => {
    const charts = {};
    const periodEl = document.getElementById("filter-period");
    const typeEl = document.getElementById("filter-type");

    function getParams() {
        const params = new URLSearchParams();
        if (periodEl.value && periodEl.value !== "all") params.set("period", periodEl.value);
        if (typeEl.value) params.set("bet_type", typeEl.value);
        return params.toString();
    }

    function fmt(v) { return "R$ " + parseFloat(v).toFixed(2); }
    function pct(v) { return parseFloat(v).toFixed(2) + "%"; }

    async function fetchJson(url) {
        const qs = getParams();
        const resp = await fetch(url + (qs ? "?" + qs : ""));
        return resp.json();
    }

    async function loadKPIs() {
        const data = await fetchJson("/api/stats");
        document.getElementById("kpi-banca").textContent = fmt(data.banca_atual);
        document.getElementById("kpi-variacao").textContent = pct(data.variacao_pct);
        document.getElementById("kpi-total").textContent = fmt(data.total_apostado);
        document.getElementById("kpi-lucro").textContent = fmt(data.lucro_liquido);
        document.getElementById("kpi-roi").textContent = pct(data.roi);
        document.getElementById("kpi-taxa").textContent = pct(data.taxa_acerto);
        document.getElementById("kpi-odd").textContent = parseFloat(data.odd_media_ponderada).toFixed(3);
        document.getElementById("kpi-breakeven").textContent = pct(data.breakeven);

        const edgeEl = document.getElementById("kpi-edge");
        edgeEl.textContent = pct(data.edge);
        edgeEl.className = "kpi-value " + (parseFloat(data.edge) >= 0 ? "positive" : "negative");

        document.getElementById("kpi-streak").textContent =
            data.streak_atual + " " + data.streak_tipo + (data.streak_atual !== 1 ? "s" : "");
        document.getElementById("kpi-drawdown").textContent = fmt(data.drawdown_maximo);
    }

    function destroyChart(id) {
        if (charts[id]) { charts[id].destroy(); delete charts[id]; }
    }

    const chartDefaults = {
        color: "#ccc",
        borderColor: "#444",
    };
    Chart.defaults.color = "#ccc";
    Chart.defaults.borderColor = "#333";

    async function loadBancaChart() {
        const data = await fetchJson("/api/stats/timeseries");
        destroyChart("banca");
        const ctx = document.getElementById("chart-banca");
        if (!data.length) return;
        charts["banca"] = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map(p => p.date),
                datasets: [{
                    label: "Banca",
                    data: data.map(p => parseFloat(p.banca)),
                    borderColor: "#2196f3",
                    fill: false,
                    tension: 0.2,
                }, {
                    label: "Banca Inicial",
                    data: data.map(() => 1000),
                    borderColor: "#666",
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                }]
            },
            options: { responsive: true, plugins: { legend: { display: true } } }
        });
    }

    async function loadProfitTypeChart() {
        const data = await fetchJson("/api/stats/profit-by-type");
        destroyChart("profitType");
        const ctx = document.getElementById("chart-profit-type");
        if (!data.length) return;
        charts["profitType"] = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map(p => p.date),
                datasets: [
                    { label: "Principal", data: data.map(p => parseFloat(p.principal)), borderColor: "#2196f3", fill: false, tension: 0.2 },
                    { label: "Zoião", data: data.map(p => parseFloat(p.zoiao)), borderColor: "#ff9800", fill: false, tension: 0.2 },
                ]
            },
            options: { responsive: true }
        });
    }

    async function loadOddsDistChart() {
        const data = await fetchJson("/api/stats/odds-distribution");
        destroyChart("oddsDist");
        const ctx = document.getElementById("chart-odds-dist");
        if (!data.length) return;
        charts["oddsDist"] = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(b => parseFloat(b.range_start).toFixed(1)),
                datasets: [{ label: "Apostas", data: data.map(b => b.count), backgroundColor: "#2196f3" }]
            },
            options: { responsive: true }
        });
    }

    async function loadHitRateChart() {
        const data = await fetchJson("/api/stats/hit-rate-by-odds");
        destroyChart("hitRate");
        const ctx = document.getElementById("chart-hit-rate");
        if (!data.length) return;
        charts["hitRate"] = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.range_label),
                datasets: [{ label: "Taxa %", data: data.map(d => parseFloat(d.rate)), backgroundColor: "#4caf50" }]
            },
            options: { responsive: true, scales: { y: { max: 100 } } }
        });
    }

    async function loadWeekdayChart() {
        const data = await fetchJson("/api/stats/weekday");
        destroyChart("weekday");
        const ctx = document.getElementById("chart-weekday");
        if (!data.length) return;
        charts["weekday"] = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.weekday_name),
                datasets: [{
                    label: "Lucro",
                    data: data.map(d => parseFloat(d.profit)),
                    backgroundColor: data.map(d => parseFloat(d.profit) >= 0 ? "#4caf50" : "#f44336"),
                }]
            },
            options: { responsive: true }
        });
    }

    async function loadAll() {
        await Promise.all([
            loadKPIs(),
            loadBancaChart(),
            loadProfitTypeChart(),
            loadOddsDistChart(),
            loadHitRateChart(),
            loadWeekdayChart(),
        ]);
    }

    periodEl.addEventListener("change", loadAll);
    typeEl.addEventListener("change", loadAll);

    loadAll();
});
