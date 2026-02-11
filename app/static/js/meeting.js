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

if (APP_CONFIG.theme_primary) {
  document.documentElement.style.setProperty("--accent", APP_CONFIG.theme_primary);
  document.documentElement.style.setProperty("--accent-bright", APP_CONFIG.theme_primary);
}
if (APP_CONFIG.theme_secondary) {
  document.documentElement.style.setProperty("--gold", APP_CONFIG.theme_secondary);
}

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
  const { pnm, summary, ratings, lunches, matches, can_view_rater_identity: canSeeRaters } = payload;
  const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
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
      .map((row) => `<li><strong>${escapeHtml(row.lunch_date)}</strong>: ${escapeHtml(row.username)} (${escapeHtml(row.role)})</li>`)
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
        <p class="muted">Assigned Rush Officer: ${escapeHtml(assignedOfficer)}</p>
      </div>
    </div>
    <div class="meeting-metrics">
      <article class="card"><strong>Weighted Total</strong><p>${summary.weighted_total.toFixed(2)} / 45</p></article>
      <article class="card"><strong>Ratings Count</strong><p>${summary.ratings_count}</p></article>
      <article class="card"><strong>Highest / Lowest</strong><p>${summary.highest_rating_total ?? "-"} / ${summary.lowest_rating_total ?? "-"}</p></article>
      <article class="card"><strong>Total Lunches</strong><p>${summary.total_lunches}</p></article>
    </div>
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
