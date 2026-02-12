function readAppConfig() {
  if (window.APP_CONFIG) {
    return window.APP_CONFIG;
  }
  const bodyValue = document.body ? document.body.dataset.appConfig : "";
  if (!bodyValue) {
    return {};
  }
  try {
    return JSON.parse(bodyValue);
  } catch {
    return {};
  }
}

const APP_CONFIG = readAppConfig();
const API_BASE = (APP_CONFIG.api_base || "/api").replace(/\/$/, "");

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

const authSection = document.getElementById("memberAuthSection");
const appSection = document.getElementById("memberAppSection");
const memberLoginForm = document.getElementById("memberLoginForm");
const memberRegisterForm = document.getElementById("memberRegisterForm");
const memberLogoutBtn = document.getElementById("memberLogoutBtn");
const memberSessionTitle = document.getElementById("memberSessionTitle");
const memberSessionSubtitle = document.getElementById("memberSessionSubtitle");
const memberToast = document.getElementById("memberToast");
const memberSearchInput = document.getElementById("memberSearchInput");
const memberSortSelect = document.getElementById("memberSortSelect");
const memberResultCount = document.getElementById("memberResultCount");
const memberPnmList = document.getElementById("memberPnmList");
const memberEmptyState = document.getElementById("memberEmptyState");
const memberPnmDetail = document.getElementById("memberPnmDetail");
const memberPnmPhoto = document.getElementById("memberPnmPhoto");
const memberPnmName = document.getElementById("memberPnmName");
const memberPnmMeta = document.getElementById("memberPnmMeta");
const memberPnmKpis = document.getElementById("memberPnmKpis");
const memberRatingForm = document.getElementById("memberRatingForm");
const memberRatingHistory = document.getElementById("memberRatingHistory");
const memberApprovalsPanel = document.getElementById("memberApprovalsPanel");
const memberPendingList = document.getElementById("memberPendingList");

const state = {
  user: null,
  pnms: [],
  visiblePnms: [],
  selectedPnmId: null,
  selectedRatings: [],
  toastTimer: null,
};

function escapeHtml(input) {
  return String(input)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  if (!memberToast) {
    return;
  }
  memberToast.textContent = message;
  memberToast.classList.remove("hidden");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    memberToast.classList.add("hidden");
  }, 3200);
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
  const requestPath = resolveApiPath(path);
  const response = await fetch(requestPath, {
    method: options.method || "GET",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json().catch(() => ({}));
  } else {
    payload = await response.text().catch(() => "");
  }

  if (!response.ok) {
    let detail = "";
    if (typeof payload === "object" && payload && "detail" in payload) {
      detail = String(payload.detail || "");
    } else if (typeof payload === "string") {
      detail = payload.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return payload;
}

function setAuthView(isAuthenticated) {
  authSection.classList.toggle("hidden", isAuthenticated);
  appSection.classList.toggle("hidden", !isAuthenticated);
}

function isRushTeamRole(role) {
  return role === "Head Rush Officer" || role === "Rush Officer";
}

function setSessionHeading() {
  if (!state.user) {
    memberSessionTitle.textContent = "Member Portal";
    memberSessionSubtitle.textContent = "";
    return;
  }
  memberSessionTitle.textContent = state.user.username;
  memberSessionSubtitle.textContent = `${state.user.role} | ${state.user.stereotype || "Unassigned"}`;
}

function selectedPnm() {
  return state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId) || null;
}

function formatDateLabel(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function scoreBadgeClass(score) {
  if (score >= 34) {
    return "good";
  }
  if (score >= 24) {
    return "warn";
  }
  return "bad";
}

function sortPnms(rows) {
  const mode = memberSortSelect ? memberSortSelect.value : "rank";
  const sorted = [...rows];
  if (mode === "name") {
    sorted.sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`));
    return sorted;
  }
  if (mode === "recent") {
    sorted.sort((a, b) => (b.first_event_date || "").localeCompare(a.first_event_date || ""));
    return sorted;
  }
  sorted.sort((a, b) => {
    const diff = Number(b.weighted_total || 0) - Number(a.weighted_total || 0);
    if (diff !== 0) {
      return diff;
    }
    return Number(b.rating_count || 0) - Number(a.rating_count || 0);
  });
  return sorted;
}

function applySearchAndRender() {
  const query = (memberSearchInput ? memberSearchInput.value : "").trim().toLowerCase();
  const filtered = state.pnms.filter((pnm) => {
    if (!query) {
      return true;
    }
    const blob = [pnm.pnm_code, pnm.first_name, pnm.last_name, pnm.hometown, pnm.instagram_handle]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return blob.includes(query);
  });

  state.visiblePnms = sortPnms(filtered);
  if (memberResultCount) {
    memberResultCount.textContent = `${state.visiblePnms.length} result${state.visiblePnms.length === 1 ? "" : "s"}`;
  }

  if (state.selectedPnmId && !state.visiblePnms.some((pnm) => pnm.pnm_id === state.selectedPnmId)) {
    state.selectedPnmId = null;
    state.selectedRatings = [];
  }
  if (!state.selectedPnmId && state.visiblePnms.length) {
    state.selectedPnmId = state.visiblePnms[0].pnm_id;
  }

  renderPnmList();
  renderSelectedPnm();
}

function renderPnmList() {
  if (!memberPnmList) {
    return;
  }
  if (!state.visiblePnms.length) {
    memberPnmList.innerHTML = '<p class="muted">No rushees match your search.</p>';
    return;
  }

  memberPnmList.innerHTML = state.visiblePnms
    .map((pnm) => {
      const selectedClass = pnm.pnm_id === state.selectedPnmId ? " is-active" : "";
      const ownScore = pnm.own_rating ? `${pnm.own_rating.total_score}/45` : "Not rated";
      return `
        <button class="member-pnm-row${selectedClass}" data-pnm-id="${pnm.pnm_id}" type="button">
          <div class="member-pnm-row-main">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span class="${scoreBadgeClass(Number(pnm.weighted_total || 0))}">${Number(pnm.weighted_total || 0).toFixed(2)}</span>
          </div>
          <div class="muted">Ratings: ${pnm.rating_count} | My Score: ${escapeHtml(ownScore)} | ${escapeHtml(pnm.instagram_handle || "")}</div>
        </button>
      `;
    })
    .join("");
}

function renderSelectedPnm() {
  const pnm = selectedPnm();
  if (!pnm) {
    memberPnmDetail.classList.add("hidden");
    memberEmptyState.classList.remove("hidden");
    memberEmptyState.textContent = "Select a rushee to view details and rate.";
    return;
  }

  memberEmptyState.classList.add("hidden");
  memberPnmDetail.classList.remove("hidden");

  memberPnmName.textContent = `${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`;
  memberPnmMeta.textContent = `${pnm.class_year} | ${pnm.hometown} | ${pnm.instagram_handle} | ${pnm.phone_number || "No phone"}`;

  if (pnm.photo_url) {
    memberPnmPhoto.src = pnm.photo_url;
    memberPnmPhoto.classList.remove("hidden");
  } else {
    memberPnmPhoto.classList.add("hidden");
    memberPnmPhoto.removeAttribute("src");
  }

  memberPnmKpis.innerHTML = `
    <article class="card"><strong>${Number(pnm.weighted_total || 0).toFixed(2)}</strong><p>Weighted Total</p></article>
    <article class="card"><strong>${pnm.rating_count}</strong><p>Total Ratings</p></article>
    <article class="card"><strong>${pnm.total_lunches}</strong><p>Total Lunches</p></article>
    <article class="card"><strong>${pnm.days_since_first_event}</strong><p>Days Since First Event</p></article>
  `;

  const own = pnm.own_rating;
  document.getElementById("memberRateGirls").value = own ? own.good_with_girls : 0;
  document.getElementById("memberRateProcess").value = own ? own.will_make_it : 0;
  document.getElementById("memberRatePersonable").value = own ? own.personable : 0;
  document.getElementById("memberRateAlcohol").value = own ? own.alcohol_control : 0;
  document.getElementById("memberRateIg").value = own ? own.instagram_marketability : 0;
  document.getElementById("memberRateComment").value = own ? own.comment || "" : "";

  renderRatingHistory();
}

function renderRatingHistory() {
  if (!memberRatingHistory) {
    return;
  }
  if (!state.selectedRatings.length) {
    memberRatingHistory.innerHTML = '<p class="muted">No ratings yet for this rushee.</p>';
    return;
  }

  memberRatingHistory.innerHTML = state.selectedRatings
    .slice(0, 10)
    .map((row) => {
      const who = row.from_me ? "Your rating" : "Member rating";
      const comment = row.comment ? `<div class="muted">Comment: ${escapeHtml(row.comment)}</div>` : "";
      const delta = row.last_change && typeof row.last_change.delta_total === "number"
        ? ` | Delta ${row.last_change.delta_total > 0 ? "+" : ""}${row.last_change.delta_total}`
        : "";
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${who}</strong>
            <span>Score ${row.total_score}/45${delta}</span>
          </div>
          <div class="muted">Updated ${escapeHtml(formatDateLabel(row.updated_at))}</div>
          ${comment}
        </div>
      `;
    })
    .join("");
}

async function loadSelectedRatings() {
  const pnm = selectedPnm();
  if (!pnm) {
    state.selectedRatings = [];
    renderRatingHistory();
    return;
  }
  try {
    const payload = await api(`/api/pnms/${pnm.pnm_id}/ratings`);
    state.selectedRatings = payload.ratings || [];
    renderRatingHistory();
  } catch (error) {
    state.selectedRatings = [];
    renderRatingHistory();
    showToast(error.message || "Unable to load rating history.");
  }
}

async function loadPnms() {
  const payload = await api("/api/pnms");
  state.pnms = payload.pnms || [];
  applySearchAndRender();
  await loadSelectedRatings();
}

function renderPendingApprovals(payload) {
  if (!memberPendingList) {
    return;
  }
  const pending = payload.pending || [];
  if (!pending.length) {
    memberPendingList.innerHTML = '<p class="muted">No pending requests.</p>';
    return;
  }

  const rows = pending
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.username)}</td>
          <td>${escapeHtml(item.role)}</td>
          <td>${escapeHtml(item.created_at || "")}</td>
          <td><button type="button" class="approve-user" data-user-id="${item.user_id}">Approve</button></td>
        </tr>
      `
    )
    .join("");

  memberPendingList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Role</th>
          <th>Requested</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function loadApprovals() {
  if (!state.user || !isRushTeamRole(state.user.role)) {
    memberApprovalsPanel.classList.add("hidden");
    return;
  }
  memberApprovalsPanel.classList.remove("hidden");
  const payload = await api("/api/users/pending");
  renderPendingApprovals(payload);
}

async function refreshPortal() {
  await Promise.all([loadPnms(), loadApprovals()]);
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    await refreshPortal();
  } catch {
    state.user = null;
    setAuthView(false);
    memberApprovalsPanel.classList.add("hidden");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("memberLoginUsername").value.trim();
  const password = document.getElementById("memberLoginPassword").value;

  if (!username || !password) {
    showToast("Username and password are required.");
    return;
  }

  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: { username, password },
    });
    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    showToast("Logged in.");
    await refreshPortal();
  } catch (error) {
    showToast(error.message || "Login failed.");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const username = document.getElementById("memberRegisterUsername").value.trim();
  const password = document.getElementById("memberRegisterPassword").value;

  if (!username) {
    showToast("Username is required.");
    return;
  }
  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    showToast("Password must be 8+ characters with letters and numbers.");
    return;
  }

  try {
    const payload = await api("/api/auth/register-member", {
      method: "POST",
      body: { username, password },
    });
    memberRegisterForm.reset();
    showToast(payload.message || "Registration submitted.");
  } catch (error) {
    showToast(error.message || "Registration failed.");
  }
}

async function handleLogout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore transport errors, local reset still applies.
  }
  state.user = null;
  state.pnms = [];
  state.visiblePnms = [];
  state.selectedPnmId = null;
  state.selectedRatings = [];
  memberPnmList.innerHTML = "";
  memberApprovalsPanel.classList.add("hidden");
  setAuthView(false);
  showToast("Logged out.");
}

async function handleRatingSave(event) {
  event.preventDefault();
  const pnm = selectedPnm();
  if (!pnm) {
    showToast("Select a rushee first.");
    return;
  }

  const body = {
    pnm_id: pnm.pnm_id,
    good_with_girls: Number(document.getElementById("memberRateGirls").value),
    will_make_it: Number(document.getElementById("memberRateProcess").value),
    personable: Number(document.getElementById("memberRatePersonable").value),
    alcohol_control: Number(document.getElementById("memberRateAlcohol").value),
    instagram_marketability: Number(document.getElementById("memberRateIg").value),
    comment: document.getElementById("memberRateComment").value.trim(),
  };

  try {
    await api("/api/ratings", {
      method: "POST",
      body,
    });
    showToast("Rating saved.");
    await loadPnms();
  } catch (error) {
    showToast(error.message || "Unable to save rating.");
  }
}

async function handlePnmListClick(event) {
  const row = event.target.closest(".member-pnm-row[data-pnm-id]");
  if (!row) {
    return;
  }
  const pnmId = Number(row.dataset.pnmId || 0);
  if (!pnmId) {
    return;
  }
  state.selectedPnmId = pnmId;
  renderPnmList();
  renderSelectedPnm();
  await loadSelectedRatings();
}

async function handlePendingClick(event) {
  const button = event.target.closest("button.approve-user");
  if (!button) {
    return;
  }
  const userId = Number(button.dataset.userId || 0);
  if (!userId) {
    return;
  }

  try {
    await api(`/api/users/pending/${userId}/approve`, {
      method: "POST",
    });
    showToast("User approved.");
    await loadApprovals();
  } catch (error) {
    showToast(error.message || "Unable to approve user.");
  }
}

function attachEvents() {
  memberLoginForm.addEventListener("submit", handleLogin);
  memberRegisterForm.addEventListener("submit", handleRegister);
  memberLogoutBtn.addEventListener("click", handleLogout);
  memberRatingForm.addEventListener("submit", handleRatingSave);
  memberPnmList.addEventListener("click", handlePnmListClick);
  memberPendingList.addEventListener("click", handlePendingClick);

  memberSearchInput.addEventListener("input", applySearchAndRender);
  memberSortSelect.addEventListener("change", applySearchAndRender);
}

async function init() {
  attachEvents();
  await ensureSession();
}

init();
