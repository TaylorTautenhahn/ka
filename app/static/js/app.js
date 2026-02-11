const inputEl = document.getElementById("tickerInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const pdfBtn = document.getElementById("pdfBtn");
const rangeLabel = document.getElementById("rangeLabel");
const metricCards = document.getElementById("metricCards");
const metricsTableBody = document.querySelector("#metricsTable tbody");
const excludedNote = document.getElementById("excludedNote");
const toast = document.getElementById("toast");
const chartCanvas = document.getElementById("performanceChart");

const state = {
  chart: null,
  lastPayload: null,
  toastTimer: null,
};

const colorPalette = [
  "#007f8a",
  "#d46734",
  "#1d8758",
  "#2f5f9a",
  "#a6513f",
  "#318276",
  "#8e7b35",
  "#424a98",
];

function parseTickers(raw) {
  return [...new Set(raw.toUpperCase().split(/[\s,]+/).map((value) => value.trim()).filter(Boolean))];
}

function formatPct(value) {
  const signClass = value >= 0 ? "positive" : "negative";
  const prefix = value > 0 ? "+" : "";
  return `<span class="${signClass}">${prefix}${value.toFixed(2)}%</span>`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function setLoading(isLoading) {
  inputEl.disabled = isLoading;
  analyzeBtn.disabled = isLoading;
  analyzeBtn.textContent = isLoading ? "Analyzing..." : "Analyze 10Y";
  if (isLoading) {
    pdfBtn.disabled = true;
  } else {
    pdfBtn.disabled = !state.lastPayload;
  }
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  if (state.toastTimer) {
    clearTimeout(state.toastTimer);
  }
  state.toastTimer = setTimeout(() => {
    toast.classList.add("hidden");
  }, 3200);
}

function renderChart(payload) {
  const labels = payload.chart.timeline;
  const tickerNames = Object.keys(payload.chart.series);
  const datasets = tickerNames.map((ticker, index) => ({
    label: ticker,
    data: payload.chart.series[ticker],
    borderColor: colorPalette[index % colorPalette.length],
    backgroundColor: "transparent",
    borderWidth: 2.5,
    pointRadius: 0,
    pointHitRadius: 8,
    tension: 0.22,
  }));

  if (state.chart) {
    state.chart.destroy();
  }

  state.chart = new Chart(chartCanvas.getContext("2d"), {
    type: "line",
    data: { labels, datasets },
    options: {
      maintainAspectRatio: false,
      responsive: true,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { position: "bottom" },
        tooltip: {
          callbacks: {
            label(context) {
              const value = context.parsed.y;
              return `${context.dataset.label}: ${value.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        y: {
          title: { display: true, text: "Growth Index (Base 100)" },
          grid: { color: "rgba(24,49,74,0.14)" },
          ticks: {
            callback(value) {
              return Number(value).toFixed(0);
            },
          },
        },
        x: {
          grid: { display: false },
          ticks: {
            maxTicksLimit: 10,
          },
        },
      },
    },
  });
}

function renderCards(metrics) {
  if (!metrics.length) {
    metricCards.innerHTML = '<p class="muted">No comparable data found.</p>';
    return;
  }

  metricCards.innerHTML = metrics
    .map(
      (metric) => `
        <article class="metric-card">
          <p class="metric-card-title">${metric.ticker}</p>
          <div class="metric-main">
            <span class="metric-total">${formatPct(metric.total_return_pct)}</span>
            <span class="metric-sub">CAGR ${metric.cagr_pct.toFixed(2)}%</span>
          </div>
          <p class="metric-sub">Volatility ${metric.annualized_volatility_pct.toFixed(2)}% | Max DD ${metric.max_drawdown_pct.toFixed(2)}%</p>
        </article>
      `
    )
    .join("");
}

function renderTable(metrics) {
  if (!metrics.length) {
    metricsTableBody.innerHTML =
      '<tr><td colspan="8" class="empty-row">No comparable data was returned.</td></tr>';
    return;
  }

  metricsTableBody.innerHTML = metrics
    .map(
      (row) => `
      <tr>
        <td>${row.ticker}</td>
        <td>${formatPct(row.total_return_pct)}</td>
        <td>${row.cagr_pct.toFixed(2)}%</td>
        <td>${row.annualized_volatility_pct.toFixed(2)}%</td>
        <td>${row.max_drawdown_pct.toFixed(2)}%</td>
        <td>${formatCurrency(row.start_price)}</td>
        <td>${formatCurrency(row.end_price)}</td>
        <td>${formatCurrency(row.ending_value_of_10000)}</td>
      </tr>
    `
    )
    .join("");
}

function renderPayload(payload) {
  renderChart(payload);
  renderCards(payload.metrics);
  renderTable(payload.metrics);
  rangeLabel.textContent = `${payload.common_start_date} to ${payload.common_end_date}`;

  if (payload.excluded_tickers.length) {
    excludedNote.textContent = `Excluded due to missing data: ${payload.excluded_tickers.join(", ")}`;
  } else {
    excludedNote.textContent = "";
  }
}

async function requestAnalysis() {
  const tickers = parseTickers(inputEl.value);
  if (!tickers.length) {
    showToast("Enter at least one ticker.");
    return;
  }

  setLoading(true);
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tickers }),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || "Analysis request failed.");
    }

    const payload = await response.json();
    state.lastPayload = payload;
    renderPayload(payload);
    pdfBtn.disabled = false;
  } catch (error) {
    showToast(error.message || "Unable to complete analysis.");
  } finally {
    setLoading(false);
  }
}

async function downloadPdf() {
  const tickers =
    state.lastPayload?.requested_tickers && state.lastPayload.requested_tickers.length
      ? state.lastPayload.requested_tickers
      : parseTickers(inputEl.value);

  if (!tickers.length) {
    showToast("Run an analysis before exporting.");
    return;
  }

  pdfBtn.disabled = true;
  pdfBtn.textContent = "Building PDF...";

  try {
    const response = await fetch("/api/report/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tickers,
        report_title: `Financial Modeling Report (${new Date().toISOString().slice(0, 10)})`,
      }),
    });

    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || "PDF generation failed.");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const fileNameMatch = disposition.match(/filename="?([^"]+)"?/);
    anchor.href = url;
    anchor.download = fileNameMatch ? fileNameMatch[1] : "financial-report.pdf";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    showToast(error.message || "Unable to generate PDF.");
  } finally {
    pdfBtn.textContent = "Download PDF";
    pdfBtn.disabled = false;
  }
}

function bindEvents() {
  analyzeBtn.addEventListener("click", requestAnalysis);
  pdfBtn.addEventListener("click", downloadPdf);

  inputEl.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      requestAnalysis();
    }
  });

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      inputEl.value = chip.dataset.tickers || "";
      requestAnalysis();
    });
  });
}

bindEvents();

