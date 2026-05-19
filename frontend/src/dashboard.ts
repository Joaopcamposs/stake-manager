/**
 * Dashboard page: Chart.js charts with filters
 */
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

// Register Chart.js components
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

// Chart defaults for dark theme
Chart.defaults.color = "#ccc";
Chart.defaults.borderColor = "#333";

const charts: Record<string, Chart> = {};

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

async function loadKPIs() {
  interface Stats {
    banca_atual: number;
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
  }

  const data = await fetchJson<Stats>("/api/stats");
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

  const edgeEl = document.getElementById("kpi-edge");
  if (edgeEl) {
    edgeEl.textContent = pct(data.edge);
    edgeEl.className = "kpi-value " + (data.edge >= 0 ? "positive" : "negative");
  }

  set("kpi-streak", `${data.streak_atual} ${data.streak_tipo}${data.streak_atual !== 1 ? "s" : ""}`);
  set("kpi-drawdown", fmt(data.drawdown_maximo));
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
          data: data.map(() => 1000),
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

async function loadOddsDistChart() {
  interface OddsBucket { range_start: string; count: number }
  const data = await fetchJson<OddsBucket[]>("/api/stats/odds-distribution");
  destroyChart("oddsDist");
  const ctx = document.getElementById("chart-odds-dist") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["oddsDist"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((b) => parseFloat(b.range_start).toFixed(1)),
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

async function loadHitRateChart() {
  interface HitRate { range_label: string; rate: string }
  const data = await fetchJson<HitRate[]>("/api/stats/hit-rate-by-odds");
  destroyChart("hitRate");
  const ctx = document.getElementById("chart-hit-rate") as HTMLCanvasElement;
  if (!data.length || !ctx) return;

  charts["hitRate"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.range_label),
      datasets: [
        {
          label: "Taxa %",
          data: data.map((d) => parseFloat(d.rate)),
          backgroundColor: "rgba(76, 175, 80, 0.7)",
          borderColor: "#4caf50",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600, easing: "easeOutQuart" },
      scales: { y: { max: 100 } },
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

// Filter listeners
periodEl?.addEventListener("change", loadAll);
typeEl?.addEventListener("change", loadAll);

// Initial load
loadAll();
