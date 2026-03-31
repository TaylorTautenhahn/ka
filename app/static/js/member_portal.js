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
  const tertiaryBase = hexToRgb(config.theme_tertiary) || hexToRgb("#1d7a4b");
  if (!accentBase || !goldBase || !tertiaryBase) {
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
  root.style.setProperty("--good", rgbToHex(tertiaryBase));
}

applyTenantTheme(APP_CONFIG);

const BASE_RATING_CRITERIA = [
  { field: "good_with_girls", label: "Good with girls", short_label: "Girls", max: 10 },
  { field: "will_make_it", label: "Will make it through process", short_label: "Process", max: 10 },
  { field: "personable", label: "Personable", short_label: "Personable", max: 10 },
  { field: "alcohol_control", label: "Alcohol control", short_label: "Alcohol", max: 10 },
  { field: "instagram_marketability", label: "Instagram marketability", short_label: "IG", max: 5 },
];
const RATING_FIELD_LIMITS = {
  good_with_girls: 10,
  will_make_it: 10,
  personable: 10,
  alcohol_control: 10,
  instagram_marketability: 5,
};

function parseRatingCriteria(raw) {
  const byField = new Map();
  if (Array.isArray(raw)) {
    raw.forEach((item) => {
      if (!item || typeof item !== "object" || !item.field) {
        return;
      }
      byField.set(String(item.field), item);
    });
  }
  return BASE_RATING_CRITERIA.map((base) => {
    const incoming = byField.get(base.field) || {};
    const limit = RATING_FIELD_LIMITS[base.field] || base.max;
    const parsedMax = Number.parseInt(String(incoming.max ?? base.max), 10);
    const max = Number.isFinite(parsedMax) ? Math.max(1, Math.min(limit, parsedMax)) : base.max;
    const label = String(incoming.label || base.label).trim() || base.label;
    const shortLabel = String(incoming.short_label || base.short_label).trim() || base.short_label;
    return {
      field: base.field,
      label,
      short_label: shortLabel,
      max,
    };
  });
}

const RATING_CRITERIA = parseRatingCriteria(APP_CONFIG.rating_criteria);
const RATING_CRITERIA_BY_FIELD = new Map(RATING_CRITERIA.map((item) => [item.field, item]));
const RATING_TOTAL_MAX =
  Number.isFinite(Number(APP_CONFIG.rating_total_max)) && Number(APP_CONFIG.rating_total_max) > 0
    ? Number(APP_CONFIG.rating_total_max)
    : RATING_CRITERIA.reduce((sum, item) => sum + Number(item.max || 0), 0);

function ratingTierMeta(score, totalMax = RATING_TOTAL_MAX) {
  const safeTotal = Number(totalMax) > 0 ? Number(totalMax) : 45;
  const normalized = (Number(score || 0) / safeTotal) * 45;
  if (normalized >= 40) {
    return { label: "A Tier", className: "score-tier-a" };
  }
  if (normalized >= 30) {
    return { label: "B Tier", className: "score-tier-b" };
  }
  if (normalized >= 20) {
    return { label: "C Tier", className: "score-tier-c" };
  }
  if (normalized >= 10) {
    return { label: "D Tier", className: "score-tier-d" };
  }
  return { label: "F Tier", className: "score-tier-f" };
}

function ratingTierBadgeMarkup(score, totalMax = RATING_TOTAL_MAX) {
  const tier = ratingTierMeta(score, totalMax);
  return `<span class="pill score-tier ${tier.className}">${tier.label}</span>`;
}

function formatWeightedScore(score, totalMax = RATING_TOTAL_MAX) {
  return `${Number(score || 0).toFixed(2)} / ${Number(totalMax || RATING_TOTAL_MAX).toFixed(0)}`;
}

function confirmRusheeRatingSubmission() {
  return "Are you finished with this Rushee profile and ready to save this rating?";
}

const authSection = document.getElementById("memberAuthSection");
const appSection = document.getElementById("memberAppSection");
const memberLoginForm = document.getElementById("memberLoginForm");
const memberRegisterForm = document.getElementById("memberRegisterForm");
const memberLogoutBtn = document.getElementById("memberLogoutBtn");
const memberLoginRememberMe = document.getElementById("memberLoginRememberMe");
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
const memberApprovedList = document.getElementById("memberApprovedList");

const state = {
  user: null,
  pnms: [],
  visiblePnms: [],
  selectedPnmId: null,
  selectedRatings: [],
  toastTimer: null,
};

function ratingCriteriaForField(field) {
  return RATING_CRITERIA_BY_FIELD.get(field) || BASE_RATING_CRITERIA.find((item) => item.field === field);
}

function ratingLabelWithRange(field) {
  const criterion = ratingCriteriaForField(field);
  if (!criterion) {
    return `${field} (0-10, optional)`;
  }
  return `${criterion.short_label} (0-${criterion.max}, optional)`;
}

function applyRatingCriteriaUi() {
  const fields = [
    { field: "good_with_girls", inputId: "memberRateGirls", labelId: "memberRateGirlsLabel" },
    { field: "will_make_it", inputId: "memberRateProcess", labelId: "memberRateProcessLabel" },
    { field: "personable", inputId: "memberRatePersonable", labelId: "memberRatePersonableLabel" },
    { field: "alcohol_control", inputId: "memberRateAlcohol", labelId: "memberRateAlcoholLabel" },
    { field: "instagram_marketability", inputId: "memberRateIg", labelId: "memberRateIgLabel" },
  ];
  fields.forEach(({ field, inputId, labelId }) => {
    const criterion = ratingCriteriaForField(field);
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    if (input && criterion) {
      input.min = "0";
      input.max = String(criterion.max);
      input.placeholder = "Skip";
    }
    if (label) {
      label.textContent = ratingLabelWithRange(field);
    }
  });
}

function formatScoreBreakdown(row) {
  return RATING_CRITERIA.map((criterion) => {
    const rawValue = row[criterion.field];
    const value = rawValue === null || rawValue === undefined || rawValue === "" ? "—" : Number(rawValue);
    return `${criterion.short_label} ${value}`;
  }).join(" | ");
}

function readOptionalRatingValue(input) {
  if (!input) {
    return null;
  }
  const rawValue = String(input.value || "").trim();
  if (!rawValue) {
    return null;
  }
  return Number(rawValue);
}

function writeOptionalRatingValue(input, rawValue, maxValue) {
  if (!input) {
    return;
  }
  if (rawValue === null || rawValue === undefined || rawValue === "") {
    input.value = "";
    return;
  }
  input.value = Math.min(Number(rawValue), Number(maxValue || input.max || 0));
}

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

const inlineConfirmActions = new WeakMap();

function ensureInlineConfirmBar(form, key) {
  if (!form) {
    return null;
  }
  const selector = `.inline-confirm-bar[data-confirm-key="${key}"]`;
  let bar = form.parentElement ? form.parentElement.querySelector(selector) : null;
  if (!bar) {
    bar = document.createElement("div");
    bar.className = "inline-confirm-bar hidden";
    bar.dataset.confirmKey = key;
    bar.innerHTML = `
      <div class="inline-confirm-copy">
        <strong>Confirm Rating Submission</strong>
        <p class="muted">Double-check this rushee profile before saving.</p>
      </div>
      <div class="action-row inline-confirm-actions">
        <button type="button" class="secondary inline-confirm-cancel">Keep Editing</button>
        <button type="button" class="inline-confirm-accept">Yes, Save Rating</button>
      </div>
    `;
    form.insertAdjacentElement("afterend", bar);
    const cancelBtn = bar.querySelector(".inline-confirm-cancel");
    const confirmBtn = bar.querySelector(".inline-confirm-accept");
    cancelBtn?.addEventListener("click", () => {
      inlineConfirmActions.delete(form);
      bar.classList.add("hidden");
    });
    confirmBtn?.addEventListener("click", async () => {
      const action = inlineConfirmActions.get(form);
      inlineConfirmActions.delete(form);
      bar.classList.add("hidden");
      if (typeof action === "function") {
        await action();
      }
    });
  }
  return bar;
}

function clearInlineConfirmBar(form, key) {
  if (!form) {
    return;
  }
  inlineConfirmActions.delete(form);
  const bar = form.parentElement ? form.parentElement.querySelector(`.inline-confirm-bar[data-confirm-key="${key}"]`) : null;
  if (bar) {
    bar.classList.add("hidden");
  }
}

function promptInlineConfirm(form, key, { message, confirmLabel, onConfirm }) {
  const bar = ensureInlineConfirmBar(form, key);
  if (!bar) {
    return;
  }
  const copy = bar.querySelector(".inline-confirm-copy p");
  const confirmBtn = bar.querySelector(".inline-confirm-accept");
  if (copy) {
    copy.textContent = message;
  }
  if (confirmBtn) {
    confirmBtn.textContent = confirmLabel;
  }
  inlineConfirmActions.set(form, onConfirm);
  bar.classList.remove("hidden");
  confirmBtn?.focus();
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

function readCookie(name) {
  const needle = `${name}=`;
  const parts = document.cookie ? document.cookie.split(";") : [];
  for (const rawPart of parts) {
    const part = rawPart.trim();
    if (part.startsWith(needle)) {
      return decodeURIComponent(part.slice(needle.length));
    }
  }
  return "";
}

function csrfHeadersForMethod(method, headers) {
  const normalizedMethod = String(method || "GET").toUpperCase();
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(normalizedMethod)) {
    return headers;
  }
  const token = readCookie("bb_csrf_token");
  if (!token) {
    return headers;
  }
  return {
    ...headers,
    "X-CSRF-Token": token,
  };
}

async function api(path, options = {}) {
  const requestPath = resolveApiPath(path);
  const method = String(options.method || "GET").toUpperCase();
  const headers = csrfHeadersForMethod(method, {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  });
  const response = await fetch(requestPath, {
    method,
    credentials: "same-origin",
    headers,
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

function sortPnms(rows) {
  const mode = memberSortSelect ? memberSortSelect.value : "name";
  const sorted = [...rows];
  if (mode === "name") {
    sorted.sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`));
    return sorted;
  }
  if (mode === "recent") {
    sorted.sort((a, b) => (b.first_event_date || "").localeCompare(a.first_event_date || ""));
    return sorted;
  }
  sorted.sort((a, b) => `${a.pnm_code}`.localeCompare(`${b.pnm_code}`));
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
      return `
        <button class="member-pnm-row${selectedClass}" data-pnm-id="${pnm.pnm_id}" type="button">
          <div class="member-pnm-row-main">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span>${escapeHtml(pnm.class_year || "")}</span>
          </div>
          <div class="muted">${escapeHtml(pnm.hometown || "")} | ${escapeHtml(pnm.instagram_handle || "")}</div>
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
    clearInlineConfirmBar(memberRatingForm, "member-rating");
    return;
  }

  memberEmptyState.classList.add("hidden");
  memberPnmDetail.classList.remove("hidden");
  clearInlineConfirmBar(memberRatingForm, "member-rating");

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
    <article class="card"><strong>${pnm.days_since_first_event}</strong><p>Days Since First Event</p></article>
    <article class="card"><strong>${pnm.total_lunches}</strong><p>Total Touchpoints</p></article>
    <article class="card"><strong>${formatWeightedScore(pnm.weighted_total)}</strong><p>${ratingTierMeta(pnm.weighted_total).label}</p></article>
    <article class="card"><strong>${escapeHtml(pnm.phone_number || "None")}</strong><p>Phone</p></article>
  `;

  const own = pnm.own_rating;
  const girlsMax = ratingCriteriaForField("good_with_girls")?.max || 10;
  const processMax = ratingCriteriaForField("will_make_it")?.max || 10;
  const personableMax = ratingCriteriaForField("personable")?.max || 10;
  const alcoholMax = ratingCriteriaForField("alcohol_control")?.max || 10;
  const igMax = ratingCriteriaForField("instagram_marketability")?.max || 5;
  writeOptionalRatingValue(document.getElementById("memberRateGirls"), own ? own.good_with_girls : null, girlsMax);
  writeOptionalRatingValue(document.getElementById("memberRateProcess"), own ? own.will_make_it : null, processMax);
  writeOptionalRatingValue(document.getElementById("memberRatePersonable"), own ? own.personable : null, personableMax);
  writeOptionalRatingValue(document.getElementById("memberRateAlcohol"), own ? own.alcohol_control : null, alcoholMax);
  writeOptionalRatingValue(document.getElementById("memberRateIg"), own ? own.instagram_marketability : null, igMax);
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
      const comment = row.comment ? `<div class="muted">Comment: ${escapeHtml(row.comment)}</div>` : "";
      const delta = row.last_change && typeof row.last_change.delta_total === "number"
        ? ` | Delta ${row.last_change.delta_total > 0 ? "+" : ""}${row.last_change.delta_total}`
        : "";
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>Your rating</strong>
            <span>Score ${row.total_score}/${RATING_TOTAL_MAX}${delta}</span>
          </div>
          <div class="muted">${escapeHtml(formatScoreBreakdown(row))}</div>
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
    state.selectedRatings = (payload.ratings || []).filter((row) => row.from_me);
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

function renderApprovedUsers(payload) {
  if (!memberApprovedList) {
    return;
  }
  const users = (payload.users || []).filter((item) => item.role !== "Head Rush Officer");
  if (!users.length) {
    memberApprovedList.innerHTML = '<p class="muted">No approved users available for disapproval.</p>';
    return;
  }

  const rows = users
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.username)}</td>
          <td>${escapeHtml(item.role)}</td>
          <td><button type="button" class="secondary disapprove-user" data-user-id="${item.user_id}" data-username="${escapeHtml(item.username)}">Disapprove</button></td>
        </tr>
      `
    )
    .join("");

  memberApprovedList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Role</th>
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
  const [pendingPayload, approvedPayload] = await Promise.all([api("/api/users/pending"), api("/api/users")]);
  renderPendingApprovals(pendingPayload);
  renderApprovedUsers(approvedPayload);
}

async function refreshPortal() {
  await Promise.all([loadPnms(), loadApprovals()]);
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    state.user = payload && payload.authenticated && payload.user ? payload.user : null;
    if (!state.user) {
      setAuthView(false);
      memberApprovalsPanel.classList.add("hidden");
      return;
    }
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
  const rememberMe = Boolean(memberLoginRememberMe && memberLoginRememberMe.checked);

  if (!username || !password) {
    showToast("Username and password are required.");
    return;
  }

  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: { username, password, remember_me: rememberMe },
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
  const city = document.getElementById("memberRegisterCity").value.trim();
  const stateCode = document.getElementById("memberRegisterState").value.trim();

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
      body: {
        username,
        password,
        city: city || null,
        state: stateCode || null,
      },
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
  if (memberPendingList) {
    memberPendingList.innerHTML = "";
  }
  if (memberApprovedList) {
    memberApprovedList.innerHTML = "";
  }
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
    good_with_girls: readOptionalRatingValue(document.getElementById("memberRateGirls")),
    will_make_it: readOptionalRatingValue(document.getElementById("memberRateProcess")),
    personable: readOptionalRatingValue(document.getElementById("memberRatePersonable")),
    alcohol_control: readOptionalRatingValue(document.getElementById("memberRateAlcohol")),
    instagram_marketability: readOptionalRatingValue(document.getElementById("memberRateIg")),
    comment: document.getElementById("memberRateComment").value.trim(),
  };
  promptInlineConfirm(memberRatingForm, "member-rating", {
    message: confirmRusheeRatingSubmission(),
    confirmLabel: "Yes, Save Rating",
    onConfirm: async () => {
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
    },
  });
  showToast("Confirm the rating below to avoid accidental saves.");
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
  const approveButton = event.target.closest("button.approve-user");
  if (approveButton) {
    const userId = Number(approveButton.dataset.userId || 0);
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
    return;
  }

  const disapproveButton = event.target.closest("button.disapprove-user");
  if (!disapproveButton) {
    return;
  }
  const userId = Number(disapproveButton.dataset.userId || 0);
  if (!userId) {
    return;
  }
  const username = disapproveButton.dataset.username || "this user";
  const confirmed = window.confirm(`Disapprove ${username}? They will be moved back to pending and signed out.`);
  if (!confirmed) {
    return;
  }

  try {
    await api(`/api/users/${userId}/disapprove`, {
      method: "POST",
    });
    showToast("User disapproved.");
    await loadApprovals();
  } catch (error) {
    showToast(error.message || "Unable to disapprove user.");
  }
}

function attachEvents() {
  memberLoginForm.addEventListener("submit", handleLogin);
  memberRegisterForm.addEventListener("submit", handleRegister);
  memberLogoutBtn.addEventListener("click", handleLogout);
  memberRatingForm.addEventListener("submit", handleRatingSave);
  memberPnmList.addEventListener("click", handlePnmListClick);
  memberPendingList.addEventListener("click", handlePendingClick);
  if (memberApprovedList) {
    memberApprovedList.addEventListener("click", handlePendingClick);
  }

  memberSearchInput.addEventListener("input", applySearchAndRender);
  memberSortSelect.addEventListener("change", applySearchAndRender);
}

async function init() {
  applyRatingCriteriaUi();
  attachEvents();
  await ensureSession();
}

init();
