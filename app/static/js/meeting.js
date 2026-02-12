function readAppConfig() {
  if (window.APP_CONFIG) {
    return window.APP_CONFIG;
  }
  const bodyValue = document.body ? document.body.dataset.appConfig : "";
  if (bodyValue) {
    try {
      return JSON.parse(bodyValue);
    } catch {
      // ignore malformed config and continue to fallback
    }
  }
  const node = document.getElementById("appConfig");
  if (!node) {
    return {};
  }
  try {
    return JSON.parse(node.textContent || "{}");
  } catch {
    return {};
  }
}

const APP_CONFIG = readAppConfig();
const API_BASE = (APP_CONFIG.api_base || "/api").replace(/\/$/, "");
const BASE_PATH = (APP_CONFIG.base_path || "").replace(/\/$/, "");

function clampChannel(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function hexToRgb(hex) {
  const normalized = String(hex || "").trim();
  const match = normalized.match(/^#([0-9a-fA-F]{6})$/);
  if (!match) {
    return null;
  }
  const token = match[1];
  return {
    r: Number.parseInt(token.slice(0, 2), 16),
    g: Number.parseInt(token.slice(2, 4), 16),
    b: Number.parseInt(token.slice(4, 6), 16),
  };
}

function rgbToHex(rgb) {
  const toHex = (value) => clampChannel(value).toString(16).padStart(2, "0");
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

function mixRgb(base, target, ratio) {
  const t = Math.max(0, Math.min(1, ratio));
  return {
    r: clampChannel(base.r + (target.r - base.r) * t),
    g: clampChannel(base.g + (target.g - base.g) * t),
    b: clampChannel(base.b + (target.b - base.b) * t),
  };
}

function rgbTriplet(rgb) {
  return `${rgb.r}, ${rgb.g}, ${rgb.b}`;
}

function applyTenantTheme(config) {
  const root = document.documentElement;
  const accentBase = hexToRgb(config.theme_primary) || hexToRgb("#8a1538");
  const goldBase = hexToRgb(config.theme_secondary) || hexToRgb("#c99a2b");
  if (!accentBase || !goldBase) {
    return;
  }

  const accentBright = mixRgb(accentBase, { r: 255, g: 255, b: 255 }, 0.16);
  const accentSoft = mixRgb(accentBase, { r: 255, g: 255, b: 255 }, 0.11);
  const accentDeep = mixRgb(accentBase, { r: 0, g: 0, b: 0 }, 0.34);
  const accentShadow = mixRgb(accentBase, { r: 0, g: 0, b: 0 }, 0.42);
  const heading = mixRgb(accentBase, { r: 36, g: 24, b: 31 }, 0.32);

  root.style.setProperty("--accent", rgbToHex(accentBase));
  root.style.setProperty("--accent-bright", rgbToHex(accentBright));
  root.style.setProperty("--gold", rgbToHex(goldBase));
  root.style.setProperty("--accent-rgb", rgbTriplet(accentBase));
  root.style.setProperty("--accent-soft-rgb", rgbTriplet(accentSoft));
  root.style.setProperty("--accent-deep-rgb", rgbTriplet(accentDeep));
  root.style.setProperty("--accent-shadow-rgb", rgbTriplet(accentShadow));
  root.style.setProperty("--gold-rgb", rgbTriplet(goldBase));
  root.style.setProperty("--heading", rgbToHex(heading));
}

applyTenantTheme(APP_CONFIG);

const pnmSelect = document.getElementById("meetingPnmSelect");
const loadBtn = document.getElementById("meetingLoadBtn");
const refreshBtn = document.getElementById("meetingRefreshBtn");
const pdfBtn = document.getElementById("meetingPdfBtn");
const packetEl = document.getElementById("meetingPacket");
const toastEl = document.getElementById("meetingToast");

let currentPnmId = null;

function escapeHtml(input) {
  return String(input)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatLunchWindow(row) {
  const timeRange =
    row.start_time && row.end_time
      ? `${row.start_time}-${row.end_time}`
      : row.start_time
        ? `${row.start_time}`
        : "";
  const parts = [timeRange, row.location || ""].filter(Boolean);
  return parts.join(" | ");
}

function formatTrendTimestamp(value) {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function renderTrendChart(points) {
  if (!points || points.length < 2) {
    return '<p class="muted">Trend chart appears after at least two rating updates.</p>';
  }
  const width = 760;
  const height = 220;
  const left = 40;
  const right = 14;
  const top = 14;
  const bottom = 26;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const values = points.map((point) => Number(point.weighted_total || 0));
  let minY = Math.min(...values);
  let maxY = Math.max(...values);
  if (maxY - minY < 1) {
    minY = Math.max(0, minY - 0.5);
    maxY = Math.min(45, maxY + 0.5);
  }
  const yRange = Math.max(0.1, maxY - minY);
  const xStep = chartWidth / Math.max(1, points.length - 1);
  const toX = (index) => left + index * xStep;
  const toY = (value) => top + ((maxY - value) / yRange) * chartHeight;

  const polyline = points
    .map((point, index) => `${toX(index).toFixed(2)},${toY(Number(point.weighted_total || 0)).toFixed(2)}`)
    .join(" ");
  const areaPath = `M ${left},${height - bottom} L ${polyline.replaceAll(" ", " L ")} L ${left + chartWidth},${height - bottom} Z`;
  const horizontalGuides = [0, 1, 2, 3, 4]
    .map((step) => {
      const y = top + (chartHeight / 4) * step;
      return `<line x1="${left}" y1="${y.toFixed(2)}" x2="${(left + chartWidth).toFixed(2)}" y2="${y.toFixed(2)}" class="trend-grid"></line>`;
    })
    .join("");
  const markers = points
    .map((point, index) => {
      const x = toX(index);
      const y = toY(Number(point.weighted_total || 0));
      return `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="2.7" class="trend-point"></circle>`;
    })
    .join("");

  return `
    <div class="trend-chart-wrap">
      <svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        ${horizontalGuides}
        <path d="${areaPath}" class="trend-area"></path>
        <polyline points="${polyline}" class="trend-line"></polyline>
        ${markers}
      </svg>
      <div class="trend-axis">
        <span>${escapeHtml(formatTrendTimestamp(points[0].changed_at))}</span>
        <span>${escapeHtml(formatTrendTimestamp(points[points.length - 1].changed_at))}</span>
      </div>
    </div>
  `;
}

function showToast(message) {
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toastEl.classList.add("hidden"), 2600);
}

function resolveApiPath(path) {
  if (path.startsWith("/api/")) {
    return `${API_BASE}${path.slice(4)}`;
  }
  if (path === "/api") {
    return API_BASE;
  }
  return path;
}

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(resolveApiPath(path), {
    method: options.method || "GET",
    credentials: "same-origin",
    headers: isFormData
      ? { ...(options.headers || {}) }
      : {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
    body: options.body ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => ({}))
    : await response.text().catch(() => "");

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload && "detail" in payload
        ? String(payload.detail)
        : typeof payload === "string"
          ? payload.replace(/<[^>]*>/g, " ").trim()
          : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return payload;
}

function renderPacket(payload) {
  const { pnm, summary, ratings, lunches, matches, rating_trend: trend, can_view_rater_identity: canSeeRaters } = payload;
  const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
  const trendPoints = trend && Array.isArray(trend.points) ? trend.points : [];
  const trendDelta = trend && typeof trend.delta_weighted_total === "number" ? trend.delta_weighted_total : null;
  const trendDeltaClass = trendDelta == null ? "warn" : trendDelta > 0 ? "good" : trendDelta < 0 ? "bad" : "warn";
  const trendDeltaLabel = trendDelta == null ? "N/A" : `${trendDelta > 0 ? "+" : ""}${trendDelta.toFixed(2)}`;
  const trendEvents = trend && typeof trend.events_count === "number" ? trend.events_count : trendPoints.length;
  const photoMarkup = pnm.photo_url
    ? `<img src="${escapeHtml(pnm.photo_url)}" alt="${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}" class="meeting-photo large" loading="lazy" />`
    : '<div class="photo-placeholder large">No photo uploaded.</div>';

  const ratingsMarkup =
    ratings
      .slice(0, 12)
      .map((row) => {
        const who = canSeeRaters
          ? `${escapeHtml(row.rater.username)} (${escapeHtml(row.rater.role)})`
          : row.from_me
            ? "Your rating"
            : "Member rating";
        const delta =
          row.last_change && typeof row.last_change.delta_total === "number"
            ? ` | Delta ${row.last_change.delta_total > 0 ? "+" : ""}${row.last_change.delta_total}`
            : "";
        return `<li><strong>${who}</strong>: ${row.total_score}/45${delta}</li>`;
      })
      .join("") || "<li>No ratings yet.</li>";

  const lunchMarkup =
    lunches
      .slice(0, 12)
      .map((row) => {
        const timing = formatLunchWindow(row);
        const detail = timing ? ` | ${escapeHtml(timing)}` : "";
        return `<li><strong>${escapeHtml(row.lunch_date)}</strong>: ${escapeHtml(row.username)} (${escapeHtml(row.role)})${detail}</li>`;
      })
      .join("") || "<li>No lunch logs yet.</li>";

  const matchMarkup =
    matches
      .slice(0, 10)
      .map((row) => {
        const shared = row.shared_interests.length ? row.shared_interests.map((x) => escapeHtml(x)).join(", ") : "None";
        return `<li><strong>${escapeHtml(row.username)}</strong> (${escapeHtml(row.role)}) | Fit ${row.fit_score} | Shared: ${shared}</li>`;
      })
      .join("") || "<li>No fit matches yet.</li>";

  packetEl.innerHTML = `
    <div class="meeting-header">
      ${photoMarkup}
      <div>
        <h3>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</h3>
        <p class="muted">${escapeHtml(pnm.hometown)} | ${escapeHtml(pnm.class_year)} | ${escapeHtml(pnm.instagram_handle)} | ${escapeHtml(pnm.phone_number || "No phone")}</p>
        <p class="muted">Interests: ${pnm.interests.map((item) => escapeHtml(item)).join(", ")} | Stereotype: ${escapeHtml(pnm.stereotype)}</p>
        <p class="muted">Notes: ${escapeHtml(pnm.notes || "None")}</p>
        <p class="muted">Assigned Rush Officer: ${escapeHtml(assignedOfficer)}</p>
      </div>
    </div>
    <div class="meeting-metrics">
      <article class="card"><strong>Weighted Total</strong><p>${summary.weighted_total.toFixed(2)} / 45</p></article>
      <article class="card"><strong>Ratings Count</strong><p>${summary.ratings_count}</p></article>
      <article class="card"><strong>Highest / Lowest</strong><p>${summary.highest_rating_total ?? "-"} / ${summary.lowest_rating_total ?? "-"}</p></article>
      <article class="card"><strong>Total Lunches</strong><p>${summary.total_lunches}</p></article>
    </div>
    <article class="list-column">
      <div class="entry-title">
        <h3>Long-Term Rating Trend</h3>
        <span class="${trendDeltaClass}">${trendDeltaLabel}</span>
      </div>
      <p class="muted">Weighted total trajectory over time from rating history events: ${trendEvents}</p>
      ${renderTrendChart(trendPoints)}
    </article>
    <div class="grid-two">
      <article class="list-column">
        <h3>Ratings</h3>
        <ul class="meeting-list">${ratingsMarkup}</ul>
      </article>
      <article class="list-column">
        <h3>Lunches</h3>
        <ul class="meeting-list">${lunchMarkup}</ul>
      </article>
    </div>
    <article class="list-column">
      <h3>Best Member Matches</h3>
      <ul class="meeting-list">${matchMarkup}</ul>
    </article>
  `;
}

async function loadPacket() {
  const selected = Number(pnmSelect.value || 0);
  if (!selected) {
    showToast("Select a rushee first.");
    return;
  }
  currentPnmId = selected;
  try {
    const payload = await api(`/api/pnms/${selected}/meeting`);
    renderPacket(payload);
  } catch (error) {
    packetEl.innerHTML = '<p class="muted">Unable to load meeting packet.</p>';
    showToast(error.message || "Unable to load meeting packet.");
  }
}

async function loadPnms() {
  const payload = await api("/api/pnms");
  const pnms = payload.pnms || [];
  pnmSelect.innerHTML =
    '<option value="">Select PNM</option>' +
    pnms
      .map((pnm) => `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`)}</option>`)
      .join("");
  if (currentPnmId && pnms.find((item) => item.pnm_id === currentPnmId)) {
    pnmSelect.value = String(currentPnmId);
  }
}

async function ensureSession() {
  try {
    await api("/api/auth/me");
  } catch {
    window.location.href = BASE_PATH || "/";
  }
}

function attachEvents() {
  loadBtn.addEventListener("click", loadPacket);
  refreshBtn.addEventListener("click", async () => {
    try {
      await loadPnms();
      if (currentPnmId) {
        pnmSelect.value = String(currentPnmId);
        await loadPacket();
      }
      showToast("Refreshed.");
    } catch (error) {
      showToast(error.message || "Refresh failed.");
    }
  });
  pdfBtn.addEventListener("click", () => {
    window.print();
  });
}

async function init() {
  await ensureSession();
  const fromQuery = Number(new URLSearchParams(window.location.search).get("pnm_id") || 0);
  if (fromQuery) {
    currentPnmId = fromQuery;
  }
  await loadPnms();
  if (currentPnmId) {
    pnmSelect.value = String(currentPnmId);
    await loadPacket();
  }
  attachEvents();
}

init();
