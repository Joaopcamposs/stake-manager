import {
  Chart,
  LineController,
  BarController,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
  Filler,
} from "chart.js";

Chart.register(
  LineController,
  BarController,
  LineElement,
  BarElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip,
  Filler
);

Chart.defaults.color = "#ccc";
Chart.defaults.borderColor = "#333";

const charts: Record<string, Chart> = {};
let bancaInicial = 1000;

const periodEl = document.getElementById("filter-period") as HTMLSelectElement;
const typeEl = document.getElementById("filter-type") as HTMLSelectElement;

function getParams(): string {
  const params = new URLSearchParams();
  if (periodEl?.value && periodEl.value !== "all") params.set("period", periodEl.value);
  if (typeEl?.value) params.set("bet_type", typeEl.value);
  return params.toString();
}

function fmt(v: number | string): string {
  return "R$ " + parseFloat(String(v)).toFixed(2);
}

function pct(v: number | string): string {
  return parseFloat(String(v)).toFixed(2) + "%";
}

async function fetchJson<T>(url: string): Promise<T> {
  const qs = getParams();
  const resp = await fetch(url + (qs ? "?" + qs : ""));
  return resp.json();
}

function destroyChart(id: string) {
  if (charts[id]) {
    charts[id].destroy();
    delete charts[id];
  }
}

function marketLabel(raw: string): string {
  const overMatch = raw.match(/^over_(\d+)_(\d+)$/);
  if (overMatch) return `Over ${overMatch[1]}.${overMatch[2]}`;

  const asiMatch = raw.match(/^asiatico_(\d+)(?:_(\d+))?$/);
  if (asiMatch) {
    const n = asiMatch[1];
    const dec = asiMatch[2];
    return dec ? `Asiático ${n}.${dec}` : `Asiático ${n}`;
  }

  if (raw === "sem_mercado") return "Sem mercado";
  return raw;
}

interface Stats {
  banca_atual: number;
  banca_inicial: number;
  variacao_pct: number;
  total_apostado: number;
  lucro_liquido: number;
  roi: number;
  taxa_acerto: number;
  odd_media_ponderada: number;
  breakeven: number;
  edge: number;
  streak_atual: number;
  streak_tipo: string;
  drawdown_maximo: number;
  total_apostas: number;
  stake_medio: number;
}

async function loadKPIs() {
  const data = await fetchJson<Stats>("/api/stats");
  bancaInicial = data.banca_inicial;

  const set = (id: string, val: string) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  set("kpi-banca", fmt(data.banca_atual));
  set("kpi-variacao", pct(data.variacao_pct));
  set("kpi-total", fmt(data.total_apostado));
  set("kpi-lucro", fmt(data.lucro_liquido));
  set("kpi-roi", pct(data.roi));
  set("kpi-taxa", pct(data.taxa_acerto));
  set("kpi-odd", parseFloat(String(data.odd_media_ponderada)).toFixed(3));
  set("kpi-breakeven", pct(data.breakeven));
  set("kpi-total-apostas", String(data.total_apostas));
  set("kpi-stake-medio", fmt(data.stake_medio));

  const edgeEl = document.getElementById("kpi-edge");
  if (edgeEl) {
    edgeEl.textContent = pct(data.edge);
    edgeEl.className = "block text-2xl font-bold " + (data.edge >= 0 ? "text-green-400" : "text-red-400");
  }

  const lucroEl = document.getElementById("kpi-lucro");
  if (lucroEl) {
    lucroEl.className = "block text-2xl font-bold " + (data.lucro_liquido >= 0 ? "text-green-400" : "text-red-400");
  }

  const varEl = document.getElementById("kpi-variacao");
  if (varEl) {
    varEl.className = "block text-2xl font-bold " + (data.variacao_pct >= 0 ? "text-green-400" : "text-red-400");
  }

  set("kpi-streak", `${data.streak_atual} ${data.streak_tipo}${data.streak_atual !== 1 ? "s" : ""}`);
  set("kpi-drawdown", fmt(data.drawdown_maximo));
}

async function loadEvolutionChart() {
  interface EvoPoint { index: number; banca: string; lucro_acumulado: string; date: string; result: string }
  const data = await fetchJson<EvoPoint[]>("/api/stats/evolution");
  destroyChart("evolution");
  const ctx = document.getElementById("chart-evolution") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  // Find indices where date changes (day boundaries)
  const dayBoundaries: number[] = [];
  for (let i = 1; i < data.length; i++) {
    if (data[i].date !== data[i - 1].date) {
      dayBoundaries.push(i);
    }
  }

  const dayLinePlugin = {
    id: "dayLines",
    afterDraw(chart: Chart) {
      const { ctx: c, chartArea, scales } = chart;
      if (!scales.x) return;
      c.save();
      c.strokeStyle = "rgba(255, 255, 255, 0.15)";
      c.lineWidth = 1;
      c.setLineDash([4, 4]);

      for (const idx of dayBoundaries) {
        const x = scales.x.getPixelForValue(idx);
        if (x >= chartArea.left && x <= chartArea.right) {
          c.beginPath();
          c.moveTo(x, chartArea.top);
          c.lineTo(x, chartArea.bottom);
          c.stroke();
        }
      }

      // Draw date labels at boundaries
      c.setLineDash([]);
      c.fillStyle = "rgba(255, 255, 255, 0.4)";
      c.font = "10px sans-serif";
      c.textAlign = "center";
      for (const idx of dayBoundaries) {
        const x = scales.x.getPixelForValue(idx);
        if (x >= chartArea.left && x <= chartArea.right) {
          const dateStr = data[idx].date.slice(5); // MM-DD
          c.fillText(dateStr, x, chartArea.top - 4);
        }
      }

      c.restore();
    },
  };

  charts["evolution"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((p) => `#${p.index}`),
      datasets: [
        {
          label: "Banca",
          data: data.map((p) => parseFloat(p.banca)),
          borderColor: "#2196f3",
          backgroundColor: "rgba(33, 150, 243, 0.05)",
          fill: true,
          tension: 0.2,
          pointRadius: 3,
          pointBackgroundColor: data.map((p) =>
            p.result === "green" ? "#4caf50" : p.result === "red" ? "#f44336" : "#999"
          ),
        },
        {
          label: "Banca Inicial",
          data: data.map(() => bancaInicial),
          borderColor: "#666",
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: "easeOutQuart" },
      plugins: { legend: { display: true } },
      layout: { padding: { top: 16 } },
      scales: {
        x: { title: { display: true, text: "Aposta #" } },
      },
    },
    plugins: [dayLinePlugin],
  });
}

async function loadBancaChart() {
  interface TimePoint { date: string; banca: string }
  const data = await fetchJson<TimePoint[]>("/api/stats/timeseries");
  destroyChart("banca");
  const ctx = document.getElementById("chart-banca") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["banca"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((p) => p.date),
      datasets: [
        {
          label: "Banca",
          data: data.map((p) => parseFloat(p.banca)),
          borderColor: "#2196f3",
          backgroundColor: "rgba(33, 150, 243, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 2,
        },
        {
          label: "Banca Inicial",
          data: data.map(() => bancaInicial),
          borderColor: "#666",
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
      plugins: { legend: { display: true } },
    },
  });
}

async function loadProfitTypeChart() {
  interface ProfitPoint { date: string; principal: string; zoiao: string }
  const data = await fetchJson<ProfitPoint[]>("/api/stats/profit-by-type");
  destroyChart("profitType");
  const ctx = document.getElementById("chart-profit-type") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["profitType"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((p) => p.date),
      datasets: [
        {
          label: "Principal",
          data: data.map((p) => parseFloat(p.principal)),
          borderColor: "#2196f3",
          fill: false,
          tension: 0.3,
          pointRadius: 2,
        },
        {
          label: "Zoião",
          data: data.map((p) => parseFloat(p.zoiao)),
          borderColor: "#ff9800",
          fill: false,
          tension: 0.3,
          pointRadius: 2,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
    },
  });
}

async function loadMonthlyChart() {
  interface MonthPoint { month: string; profit: string; count: number }
  const data = await fetchJson<MonthPoint[]>("/api/stats/monthly");
  destroyChart("monthly");
  const ctx = document.getElementById("chart-monthly") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["monthly"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.month),
      datasets: [
        {
          label: "Lucro Mensal",
          data: data.map((d) => parseFloat(d.profit)),
          backgroundColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "rgba(76, 175, 80, 0.7)" : "rgba(244, 67, 54, 0.7)"
          ),
          borderColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "#4caf50" : "#f44336"
          ),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
    },
  });
}

async function loadMarketChart() {
  interface MarketPoint { market: string; profit: string; count: number; rate: string }
  const data = await fetchJson<MarketPoint[]>("/api/stats/market-profit");
  destroyChart("market");
  const ctx = document.getElementById("chart-market") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["market"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => marketLabel(d.market)),
      datasets: [
        {
          label: "Lucro",
          data: data.map((d) => parseFloat(d.profit)),
          backgroundColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "rgba(33, 150, 243, 0.7)" : "rgba(244, 67, 54, 0.7)"
          ),
          borderColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "#2196f3" : "#f44336"
          ),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
    },
  });
}

async function loadOddsDistChart() {
  interface OddsBucket { range_start: string; range_end: string; count: number }
  const data = await fetchJson<OddsBucket[]>("/api/stats/odds-distribution");
  destroyChart("oddsDist");
  const ctx = document.getElementById("chart-odds-dist") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["oddsDist"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((b) => parseFloat(b.range_start).toFixed(2)),
      datasets: [
        {
          label: "Apostas",
          data: data.map((b) => b.count),
          backgroundColor: "rgba(33, 150, 243, 0.7)",
          borderColor: "#2196f3",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
    },
  });
}


async function loadWeekdayChart() {
  interface WeekdayData { weekday_name: string; profit: string }
  const data = await fetchJson<WeekdayData[]>("/api/stats/weekday");
  destroyChart("weekday");
  const ctx = document.getElementById("chart-weekday") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["weekday"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.weekday_name),
      datasets: [
        {
          label: "Lucro",
          data: data.map((d) => parseFloat(d.profit)),
          backgroundColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "rgba(76, 175, 80, 0.7)" : "rgba(244, 67, 54, 0.7)"
          ),
          borderColor: data.map((d) =>
            parseFloat(d.profit) >= 0 ? "#4caf50" : "#f44336"
          ),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
    },
  });
}

async function loadMarketResultsCharts() {
  interface MarketResult { market: string; greens: number; reds: number }
  const data = await fetchJson<MarketResult[]>("/api/stats/market-results");

  // Greens chart
  destroyChart("marketGreens");
  const ctxG = document.getElementById("chart-market-greens") as HTMLCanvasElement;
  if (data.length && ctxG) {
    const sorted = [...data].sort((a, b) => b.greens - a.greens);
    charts["marketGreens"] = new Chart(ctxG, {
      type: "bar",
      data: {
        labels: sorted.map((d) => marketLabel(d.market)),
        datasets: [{
          label: "Greens",
          data: sorted.map((d) => d.greens),
          backgroundColor: "rgba(76, 175, 80, 0.7)",
          borderColor: "#4caf50",
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        animation: { duration: 600, easing: "easeOutQuart" },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      },
    });
  }

  // Reds chart
  destroyChart("marketReds");
  const ctxR = document.getElementById("chart-market-reds") as HTMLCanvasElement;
  if (data.length && ctxR) {
    const sorted = [...data].sort((a, b) => b.reds - a.reds);
    charts["marketReds"] = new Chart(ctxR, {
      type: "bar",
      data: {
        labels: sorted.map((d) => marketLabel(d.market)),
        datasets: [{
          label: "Reds",
          data: sorted.map((d) => d.reds),
          backgroundColor: "rgba(244, 67, 54, 0.7)",
          borderColor: "#f44336",
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true,
        animation: { duration: 600, easing: "easeOutQuart" },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
      },
    });
  }
}

async function loadAll() {
  await loadKPIs();
  await Promise.all([
    loadEvolutionChart(),
    loadBancaChart(),
    loadProfitTypeChart(),
    loadMonthlyChart(),
    loadMarketChart(),
    loadOddsDistChart(),
    loadWeekdayChart(),
    loadMarketResultsCharts(),
  ]);
}

periodEl?.addEventListener("change", loadAll);
typeEl?.addEventListener("change", loadAll);

// KPI info tooltips (hover)
const tooltip = document.getElementById("kpi-tooltip");
document.querySelectorAll(".kpi-info-btn").forEach((btn) => {
  btn.addEventListener("mouseenter", () => {
    const el = btn as HTMLElement;
    const text = el.dataset.info || "";
    if (!tooltip) return;

    tooltip.textContent = text;
    tooltip.classList.remove("hidden");
    const btnRect = el.getBoundingClientRect();
    const tooltipWidth = 340;

    // Position below the icon
    tooltip.style.top = `${btnRect.bottom + 6}px`;

    // Try right-aligned to the icon, fallback left if overflows
    let left = btnRect.right - tooltipWidth;
    if (left < 8) left = btnRect.left;
    if (left + tooltipWidth > window.innerWidth - 8) {
      left = window.innerWidth - tooltipWidth - 8;
    }
    tooltip.style.left = `${left}px`;
  });

  btn.addEventListener("mouseleave", () => {
    tooltip?.classList.add("hidden");
  });
});

loadAll();
