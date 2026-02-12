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
const BASE_PATH = (APP_CONFIG.base_path || "").replace(/\/$/, "");
const API_BASE = (APP_CONFIG.api_base || "/api").replace(/\/$/, "");
const MEETING_BASE = (APP_CONFIG.meeting_base || `${BASE_PATH}/meeting`).replace(/\/$/, "");

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

const authSection = document.getElementById("authSection");
const appSection = document.getElementById("appSection");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const logoutBtn = document.getElementById("logoutBtn");
const installBtn = document.getElementById("installBtn");
const backupCsvBtn = document.getElementById("backupCsvBtn");
const backupDbBtn = document.getElementById("backupDbBtn");

const regEmoji = document.getElementById("regEmoji");

const sessionTitle = document.getElementById("sessionTitle");
const sessionSubtitle = document.getElementById("sessionSubtitle");
const toastEl = document.getElementById("toast");
const heroStats = document.getElementById("heroStats");
const heroPnmCount = document.getElementById("heroPnmCount");
const heroRatingCount = document.getElementById("heroRatingCount");
const heroLunchCount = document.getElementById("heroLunchCount");

const filterInterest = document.getElementById("filterInterest");
const filterStereotype = document.getElementById("filterStereotype");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const interestHints = document.getElementById("interestHints");
const adminNavLink = document.getElementById("adminNavLink");

const pnmForm = document.getElementById("pnmForm");
const lunchForm = document.getElementById("lunchForm");
const ratingForm = document.getElementById("ratingForm");
const photoForm = document.getElementById("photoForm");
const pnmPhotoInput = document.getElementById("pnmPhoto");
const selectedPnmPhotoFile = document.getElementById("selectedPnmPhotoFile");
const selectedPnmPhoto = document.getElementById("selectedPnmPhoto");
const selectedPnmPhotoPlaceholder = document.getElementById("selectedPnmPhotoPlaceholder");

const pnmTable = document.getElementById("pnmTable");
const memberTable = document.getElementById("memberTable");
const ratingList = document.getElementById("ratingList");
const lunchHistory = document.getElementById("lunchHistory");
const selectedPnmLabel = document.getElementById("selectedPnmLabel");
const meetingView = document.getElementById("meetingView");
const ratingPnm = document.getElementById("ratingPnm");
const lunchPnm = document.getElementById("lunchPnm");
const lunchStartTime = document.getElementById("lunchStartTime");
const lunchEndTime = document.getElementById("lunchEndTime");
const lunchLocation = document.getElementById("lunchLocation");
const autoOpenGoogleLunchEvent = document.getElementById("autoOpenGoogleLunchEvent");
const assignPanel = document.getElementById("assignPanel");
const assignOfficerSelect = document.getElementById("assignOfficerSelect");
const assignOfficerBtn = document.getElementById("assignOfficerBtn");
const clearAssignBtn = document.getElementById("clearAssignBtn");

const approvalsPanel = document.getElementById("approvalsPanel");
const pendingList = document.getElementById("pendingList");
const adminPanel = document.getElementById("adminPanel");
const adminPnmTable = document.getElementById("adminPnmTable");
const headAdminSummary = document.getElementById("headAdminSummary");
const officerMetricsTable = document.getElementById("officerMetricsTable");
const currentHeadsList = document.getElementById("currentHeadsList");
const promoteOfficerSelect = document.getElementById("promoteOfficerSelect");
const demoteExistingHeads = document.getElementById("demoteExistingHeads");
const promoteOfficerBtn = document.getElementById("promoteOfficerBtn");
const adminPnmEditorForm = document.getElementById("adminPnmEditorForm");
const adminEditPnmSelect = document.getElementById("adminEditPnmSelect");
const googleImportForm = document.getElementById("googleImportForm");
const googleImportFile = document.getElementById("googleImportFile");
const googleImportResult = document.getElementById("googleImportResult");
const googleImportBtn = document.getElementById("googleImportBtn");
const downloadGoogleImportTemplateBtn = document.getElementById("downloadGoogleImportTemplateBtn");

const analyticsCards = document.getElementById("analyticsCards");
const matchingPnms = document.getElementById("matchingPnms");
const matchingMembers = document.getElementById("matchingMembers");
const leaderboardTable = document.getElementById("leaderboardTable");
const copyCalendarFeedBtn = document.getElementById("copyCalendarFeedBtn");
const openGoogleSubscribeBtn = document.getElementById("openGoogleSubscribeBtn");
const calendarFeedPreview = document.getElementById("calendarFeedPreview");
const lastLunchCalendarActions = document.getElementById("lastLunchCalendarActions");
const openLastLunchGoogleLink = document.getElementById("openLastLunchGoogleLink");
const refreshScheduledLunchesBtn = document.getElementById("refreshScheduledLunchesBtn");
const scheduledLunchesList = document.getElementById("scheduledLunchesList");
const desktopPageNav = document.getElementById("desktopPageNav");
const desktopPages = Array.from(document.querySelectorAll(".desktop-page[data-page]"));
const desktopPageLinks = Array.from(document.querySelectorAll(".desktop-page-link[data-page]"));

const assignedRushPanel = document.getElementById("assignedRushPanel");
const assignedRushTitle = document.getElementById("assignedRushTitle");
const assignedRushSubtitle = document.getElementById("assignedRushSubtitle");
const assignedRushTable = document.getElementById("assignedRushTable");

const headAssignmentForm = document.getElementById("headAssignmentForm");
const headAssignPnmSelect = document.getElementById("headAssignPnmSelect");
const headAssignOfficerSelect = document.getElementById("headAssignOfficerSelect");
const headAssignClearBtn = document.getElementById("headAssignClearBtn");
const headAssignmentTable = document.getElementById("headAssignmentTable");

const DEFAULT_DESKTOP_PAGE = "overview";
const DEFAULT_INTEREST_TAGS = [
  "Leadership",
  "Sports",
  "Fitness",
  "Finance",
  "Outdoors",
  "Music",
  "Faith",
  "Academics",
  "Entrepreneurship",
  "Philanthropy",
  "Gaming",
  "Travel",
];
const DEFAULT_STEREOTYPE_TAGS = [
  "Leader",
  "Connector",
  "Scholar",
  "Athlete",
  "Social",
  "Creative",
  "Mentor",
  "Builder",
];

const state = {
  user: null,
  pnms: [],
  members: [],
  selectedPnmId: null,
  deferredPrompt: null,
  toastTimer: null,
  filters: {
    interest: "",
    stereotype: "",
  },
  heroStats: {
    pnmCount: 0,
    ratingCount: 0,
    lunchCount: 0,
  },
  calendarShare: null,
  activeDesktopPage: DEFAULT_DESKTOP_PAGE,
  liveRefreshTimer: null,
  headAdmin: {
    summary: null,
    currentHeads: [],
    rushOfficers: [],
  },
  scheduledLunches: [],
  adminEditPnmId: null,
  headAssignmentPnmId: null,
};

function parseTagInput(raw) {
  return String(raw || "")
    .split(/[,;\n]+/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function uniqueNormalized(values) {
  const out = [];
  const seen = new Set();
  values.forEach((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    out.push(value);
  });
  return out;
}

function renderTagPickerButtons(pickerEl, tags, selectedSet) {
  if (!pickerEl) {
    return;
  }
  pickerEl.innerHTML = tags
    .map((tag) => {
      const active = selectedSet.has(tag.toLowerCase()) ? " is-active" : "";
      const pressed = active ? "true" : "false";
      return `<span class="tag-pill${active}" data-tag="${escapeHtml(tag)}" role="button" tabindex="0" aria-pressed="${pressed}">${escapeHtml(tag)}</span>`;
    })
    .join("");
}

function syncInterestPickerFromInput(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker) {
    return;
  }
  const selected = new Set(parseTagInput(input.value).map((value) => value.toLowerCase()));
  renderTagPickerButtons(picker, DEFAULT_INTEREST_TAGS, selected);
}

function syncStereotypePickerFromInput(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker) {
    return;
  }
  const selected = new Set();
  const value = String(input.value || "").trim().toLowerCase();
  if (value) {
    selected.add(value);
  }
  renderTagPickerButtons(picker, DEFAULT_STEREOTYPE_TAGS, selected);
}

function bindInterestPicker(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker || picker.dataset.bound === "1") {
    return;
  }
  picker.dataset.bound = "1";

  const applyTagToggle = (tag) => {
    if (!tag) {
      return;
    }
    const tokens = parseTagInput(input.value);
    const existing = new Set(tokens.map((value) => value.toLowerCase()));
    if (existing.has(tag.toLowerCase())) {
      input.value = tokens.filter((value) => value.toLowerCase() !== tag.toLowerCase()).join(",");
    } else {
      tokens.push(tag);
      input.value = uniqueNormalized(tokens).join(",");
    }
    syncInterestPickerFromInput(inputId, pickerId);
  };

  picker.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const tag = String(chip.dataset.tag || "").trim();
    applyTagToggle(tag);
  });

  picker.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    const tag = String(chip.dataset.tag || "").trim();
    applyTagToggle(tag);
  });

  input.addEventListener("input", () => syncInterestPickerFromInput(inputId, pickerId));
  syncInterestPickerFromInput(inputId, pickerId);
}

function bindStereotypePicker(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker || picker.dataset.bound === "1") {
    return;
  }
  picker.dataset.bound = "1";

  const applyStereotype = (tag) => {
    if (!tag) {
      return;
    }
    const current = String(input.value || "").trim().toLowerCase();
    input.value = current === tag.toLowerCase() ? "" : tag;
    syncStereotypePickerFromInput(inputId, pickerId);
  };

  picker.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const tag = String(chip.dataset.tag || "").trim();
    applyStereotype(tag);
  });

  picker.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    const tag = String(chip.dataset.tag || "").trim();
    applyStereotype(tag);
  });

  input.addEventListener("input", () => syncStereotypePickerFromInput(inputId, pickerId));
  syncStereotypePickerFromInput(inputId, pickerId);
}

function initializePresetTagPickers() {
  bindInterestPicker("pnmInterests", "pnmInterestTags");
  bindInterestPicker("adminEditInterests", "adminEditInterestTags");
  bindStereotypePicker("pnmStereotype", "pnmStereotypeTags");
  bindStereotypePicker("adminEditStereotype", "adminEditStereotypeTags");
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
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    toastEl.classList.add("hidden");
  }, 3300);
}

function animateCounter(element, nextValue) {
  if (!element) {
    return;
  }
  const startValue = Number(element.textContent || "0");
  const target = Number(nextValue || 0);
  if (startValue === target) {
    return;
  }

  const startedAt = performance.now();
  const duration = 420;

  function tick(now) {
    const progress = Math.min(1, (now - startedAt) / duration);
    const eased = 1 - (1 - progress) ** 3;
    const current = Math.round(startValue + (target - startValue) * eased);
    element.textContent = String(current);
    if (progress < 1) {
      requestAnimationFrame(tick);
    } else {
      element.classList.remove("count-up");
      void element.offsetWidth;
      element.classList.add("count-up");
    }
  }

  requestAnimationFrame(tick);
}

function updateHeroStats() {
  const ratingCount = state.pnms.reduce((sum, pnm) => sum + Number(pnm.rating_count || 0), 0);
  const lunchCount = state.pnms.reduce((sum, pnm) => sum + Number(pnm.total_lunches || 0), 0);
  const pnmCount = state.pnms.length;

  state.heroStats = { pnmCount, ratingCount, lunchCount };
  animateCounter(heroPnmCount, pnmCount);
  animateCounter(heroRatingCount, ratingCount);
  animateCounter(heroLunchCount, lunchCount);
}

function spawnSuccessBurst() {
  const burst = document.createElement("div");
  burst.className = "burst-wrap";

  for (let index = 0; index < 14; index += 1) {
    const spark = document.createElement("span");
    spark.className = "burst-spark";
    burst.appendChild(spark);
  }

  document.body.appendChild(burst);
  setTimeout(() => burst.remove(), 720);
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
  const isFormData = options.body instanceof FormData;
  let response;
  try {
    response = await fetch(requestPath, {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: isFormData
        ? {
            ...(options.headers || {}),
          }
        : {
            "Content-Type": "application/json",
            ...(options.headers || {}),
          },
      body: options.body ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined,
    });
  } catch (networkError) {
    const text = networkError instanceof Error ? networkError.message : "Network error";
    throw new Error(`Network error: ${text}`);
  }

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json().catch(() => ({}));
  } else {
    payload = await response.text().catch(() => "");
  }

  if (!response.ok) {
    let detail = "";
    if (typeof payload === "object" && payload !== null && "detail" in payload) {
      const rawDetail = payload.detail;
      if (Array.isArray(rawDetail)) {
        detail = rawDetail.map((item) => String(item?.msg || JSON.stringify(item))).join("; ");
      } else {
        detail = String(rawDetail || "");
      }
    } else if (typeof payload === "string") {
      detail = payload.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return payload;
}

async function downloadFile(url, fallbackFileName) {
  const response = await fetch(resolveApiPath(url), { method: "GET", credentials: "same-origin" });
  if (!response.ok) {
    const detail = await response.text().catch(() => "Download failed.");
    throw new Error(detail || "Download failed.");
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const fileNameMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
  const fileName = fileNameMatch ? fileNameMatch[1] : fallbackFileName;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function setAuthView(isAuthenticated) {
  authSection.classList.toggle("hidden", isAuthenticated);
  appSection.classList.toggle("hidden", !isAuthenticated);
  if (heroStats) {
    heroStats.classList.toggle("hidden", !isAuthenticated);
  }
  if (isAuthenticated) {
    setActiveDesktopPage(currentRequestedDesktopPage(), false);
  }
}

function availableDesktopPages() {
  return desktopPages.map((panel) => panel.dataset.page).filter(Boolean);
}

function currentRequestedDesktopPage() {
  const requested = new URLSearchParams(window.location.search).get("view");
  if (!requested) {
    return DEFAULT_DESKTOP_PAGE;
  }
  return requested.trim().toLowerCase();
}

function setActiveDesktopPage(page, updateUrl = true) {
  if (!desktopPages.length) {
    return;
  }
  const available = new Set(availableDesktopPages());
  let target = available.has(page) ? page : DEFAULT_DESKTOP_PAGE;
  if (target === "admin" && !roleCanUseAdminPanel()) {
    target = DEFAULT_DESKTOP_PAGE;
  }
  state.activeDesktopPage = target;
  desktopPages.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.page === target);
  });
  desktopPageLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.page === target);
  });

  if (!updateUrl) {
    return;
  }
  const url = new URL(window.location.href);
  url.searchParams.set("view", target);
  window.history.replaceState({}, "", url.toString());
}

function updateTopbarActions() {
  const isHead = roleCanUseAdminPanel();
  backupCsvBtn.classList.toggle("hidden", !isHead);
  backupDbBtn.classList.toggle("hidden", !isHead);
  if (adminNavLink) {
    adminNavLink.classList.toggle("hidden", !isHead);
  }
  if (!isHead && state.activeDesktopPage === "admin") {
    setActiveDesktopPage(DEFAULT_DESKTOP_PAGE);
  }
}

function startLiveRefresh() {
  if (state.liveRefreshTimer) {
    clearInterval(state.liveRefreshTimer);
  }
  state.liveRefreshTimer = setInterval(async () => {
    if (!state.user) {
      return;
    }
    try {
      await Promise.all([
        loadPnms(),
        loadMembers(),
        loadMatching(),
        loadAnalytics(),
        loadLeaderboard(),
        loadCalendarShare(),
        loadScheduledLunches(),
        loadApprovals(),
        loadHeadAdminData(),
      ]);
    } catch {
      // Passive sync should fail silently; explicit actions already report errors.
    }
  }, 18000);
}

function stopLiveRefresh() {
  if (state.liveRefreshTimer) {
    clearInterval(state.liveRefreshTimer);
    state.liveRefreshTimer = null;
  }
}

function setSessionHeading() {
  if (!state.user) {
    sessionTitle.textContent = "Welcome";
    sessionSubtitle.textContent = "";
    return;
  }

  sessionTitle.textContent = state.user.username;
  const emoji = state.user.emoji ? `${state.user.emoji} ` : "";
  sessionSubtitle.textContent = `${emoji}${state.user.role} | Stereotype: ${state.user.stereotype}`;
}

function roleCanSeeRaters() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanManagePhotos() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanUseAdminPanel() {
  return state.user && state.user.role === "Head Rush Officer";
}

function roleCanAssignOfficer() {
  return state.user && state.user.role === "Head Rush Officer";
}

function roleCanViewAssignedRushes() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function shouldPreferMobileUi() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("desktop") === "1") {
    return false;
  }
  if (window.matchMedia && window.matchMedia("(max-width: 900px)").matches) {
    return true;
  }
  const ua = navigator.userAgent.toLowerCase();
  return /iphone|ipad|ipod|android|mobile/.test(ua);
}

function shouldRedirectToMobileNow() {
  if (!APP_CONFIG.mobile_base || !shouldPreferMobileUi()) {
    return false;
  }
  const currentPath = window.location.pathname.replace(/\/$/, "");
  const mobilePath = APP_CONFIG.mobile_base.replace(/\/$/, "");
  if (!mobilePath) {
    return false;
  }
  if (currentPath === mobilePath || currentPath.startsWith(`${mobilePath}/`)) {
    return false;
  }
  return true;
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

function renderScheduledLunches() {
  if (!scheduledLunchesList) {
    return;
  }
  const rows = state.scheduledLunches || [];
  if (!rows.length) {
    scheduledLunchesList.innerHTML = '<p class="muted">No scheduled lunches yet.</p>';
    return;
  }

  scheduledLunchesList.innerHTML = rows
    .map((row) => {
      const timing = formatLunchWindow(row);
      const timingText = timing || "All-day lunch";
      const assigned = row.assigned_officer_username ? `Assigned: ${row.assigned_officer_username}` : "Assigned: Unassigned";
      const notes = row.notes || "No notes";
      const calendarAction = row.google_calendar_url
        ? `<a class="quick-nav-link" href="${escapeHtml(row.google_calendar_url)}" target="_blank" rel="noopener">Open Event</a>`
        : "";
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(row.lunch_date)} | ${escapeHtml(row.pnm_code)} | ${escapeHtml(row.pnm_name)}</strong>
            <span>${escapeHtml(timingText)}</span>
          </div>
          <div class="muted">${escapeHtml(assigned)} | Scheduled by ${escapeHtml(row.scheduled_by_username)}</div>
          <div class="muted">${escapeHtml(notes)}</div>
          ${calendarAction ? `<div class="action-row">${calendarAction}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderAssignedRushSection() {
  if (!assignedRushPanel || !assignedRushTable || !assignedRushTitle || !assignedRushSubtitle) {
    return;
  }
  if (!roleCanViewAssignedRushes()) {
    assignedRushPanel.classList.add("hidden");
    assignedRushTable.innerHTML = "";
    return;
  }

  assignedRushPanel.classList.remove("hidden");
  const isHead = state.user && state.user.role === "Head Rush Officer";
  const rows = isHead
    ? state.pnms
    : state.pnms.filter((pnm) => Number(pnm.assigned_officer_id || 0) === Number(state.user.user_id));

  if (isHead) {
    assignedRushTitle.textContent = "Assignment Visibility";
    assignedRushSubtitle.textContent = "Live overview of who each rushee is assigned to.";
  } else {
    assignedRushTitle.textContent = "My Assigned Rushees";
    assignedRushSubtitle.textContent = `Rushees currently assigned to ${state.user.username}.`;
  }

  if (!rows.length) {
    assignedRushTable.innerHTML = '<p class="muted">No assignments to display yet.</p>';
    return;
  }

  const tableRows = rows
    .map((pnm) => {
      const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const assignedAt = pnm.assigned_at ? formatLastSeen(pnm.assigned_at) : "-";
      const officerCell = isHead ? `<td>${escapeHtml(assignedOfficer)}</td>` : "";
      const assignedAtCell = isHead ? `<td>${escapeHtml(assignedAt)}</td>` : "";
      return `
        <tr>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
          <td>${escapeHtml(pnm.phone_number || "-")}</td>
          ${officerCell}
          ${assignedAtCell}
          <td>${pnm.weighted_total.toFixed(2)}</td>
          <td>${pnm.total_lunches}</td>
        </tr>
      `;
    })
    .join("");

  const officerHeader = isHead ? "<th>Assigned Officer</th><th>Assigned At</th>" : "";
  assignedRushTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th>Phone</th>
          ${officerHeader}
          <th>Weighted Total</th>
          <th>Lunches</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

function renderCalendarShareLinks(data) {
  state.calendarShare = data;
  if (!calendarFeedPreview || !openGoogleSubscribeBtn) {
    return;
  }
  calendarFeedPreview.textContent = data.feed_url || "Calendar URL unavailable.";
  openGoogleSubscribeBtn.href = data.google_subscribe_url || "#";
  openGoogleSubscribeBtn.classList.toggle("hidden", !data.google_subscribe_url);
}

function renderSelectedPnmPhoto(pnm) {
  if (!pnm || !pnm.photo_url) {
    selectedPnmPhoto.classList.add("hidden");
    selectedPnmPhoto.removeAttribute("src");
    selectedPnmPhotoPlaceholder.classList.remove("hidden");
    return;
  }
  selectedPnmPhoto.src = pnm.photo_url;
  selectedPnmPhoto.alt = `${pnm.first_name} ${pnm.last_name}`;
  selectedPnmPhoto.classList.remove("hidden");
  selectedPnmPhotoPlaceholder.classList.add("hidden");
}

function smallPhotoCell(pnm) {
  if (!pnm.photo_url) {
    return '<div class="mini-photo empty">No photo</div>';
  }
  return `<img src="${escapeHtml(pnm.photo_url)}" alt="${escapeHtml(pnm.first_name)}" class="mini-photo" loading="lazy" />`;
}

function toQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      q.set(key, value);
    }
  });
  const asText = q.toString();
  return asText ? `?${asText}` : "";
}

function setDefaultDates() {
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("pnmEventDate").value = today;
  document.getElementById("lunchDate").value = today;
}

function setRoleEmojiRequirement() {
  regEmoji.required = false;
}

function rushOfficerMembers() {
  return state.members.filter((member) => member.role === "Rush Officer");
}

function renderAssignmentControls() {
  if (!assignPanel || !assignOfficerSelect) {
    return;
  }
  const canAssign = roleCanAssignOfficer();
  assignPanel.classList.toggle("hidden", !canAssign);
  if (!canAssign) {
    return;
  }

  const officers = rushOfficerMembers();
  const options =
    '<option value="">Unassigned</option>' +
    officers
      .map((member) => {
        const emoji = member.emoji ? `${member.emoji} ` : "";
        return `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username}`)}</option>`;
      })
      .join("");
  assignOfficerSelect.innerHTML = options;

  const selected = state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId);
  assignOfficerSelect.value = selected && selected.assigned_officer_id ? String(selected.assigned_officer_id) : "";
}

function renderInterestHints(interests) {
  interestHints.innerHTML = interests.map((interest) => `<option value="${escapeHtml(interest)}"></option>`).join("");
}

function renderPnmSelectOptions() {
  const options =
    '<option value="">Select PNM</option>' +
    state.pnms
      .map((pnm) => {
        const label = `${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`;
        return `<option value="${pnm.pnm_id}">${escapeHtml(label)}</option>`;
      })
      .join("");
  ratingPnm.innerHTML = options;
  lunchPnm.innerHTML = options;

  if (state.selectedPnmId) {
    ratingPnm.value = String(state.selectedPnmId);
    lunchPnm.value = String(state.selectedPnmId);
  }
}

function renderPnmTable() {
  if (!state.pnms.length) {
    pnmTable.innerHTML = '<p class="muted">No PNMs match current filters.</p>';
    return;
  }

  const rows = state.pnms
    .map((pnm) => {
      const own = pnm.own_rating;
      const ownDisplay = own ? `${own.total_score}/45` : "Not rated";
      const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const weightedPct = Math.max(0, Math.min(100, (Number(pnm.weighted_total) / 45) * 100));
      const barWidth = Math.round((weightedPct / 100) * 58);
      const selectedClass = state.selectedPnmId === pnm.pnm_id ? "selected-row" : "";
      return `
        <tr class="${selectedClass}">
          <td>${smallPhotoCell(pnm)}</td>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
          <td>${escapeHtml(pnm.phone_number || "-")}</td>
          <td>${escapeHtml(pnm.class_year)}</td>
          <td>${pnm.days_since_first_event}</td>
          <td>${pnm.rating_count}</td>
          <td>
            <div class="score-wrap">
              <strong>${pnm.weighted_total.toFixed(2)}</strong>
              <svg class="score-bar" viewBox="0 0 58 7" aria-hidden="true" focusable="false">
                <rect x="0" y="0" width="58" height="7" rx="4" class="score-bar-track"></rect>
                <rect x="0" y="0" width="${barWidth}" height="7" rx="4" class="score-bar-fill"></rect>
              </svg>
            </div>
          </td>
          <td>${pnm.avg_good_with_girls.toFixed(2)}</td>
          <td>${pnm.avg_will_make_it.toFixed(2)}</td>
          <td>${pnm.avg_personable.toFixed(2)}</td>
          <td>${pnm.avg_alcohol_control.toFixed(2)}</td>
          <td>${pnm.avg_instagram_marketability.toFixed(2)}</td>
          <td>${pnm.total_lunches}</td>
          <td>${escapeHtml(assignedOfficer)}</td>
          <td>${ownDisplay}</td>
          <td><button type="button" class="secondary select-pnm" data-pnm-id="${pnm.pnm_id}">Select</button></td>
        </tr>
      `;
    })
    .join("");

  pnmTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Photo</th>
          <th>Code</th>
          <th>Name</th>
          <th>Phone</th>
          <th>Class</th>
          <th>Days Since Event</th>
          <th>Ratings</th>
          <th>Weighted Total</th>
          <th>Girls</th>
          <th>Process</th>
          <th>Personable</th>
          <th>Alcohol</th>
          <th>IG</th>
          <th>Lunches</th>
          <th>Assigned Officer</th>
          <th>My Rating</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderMemberTable() {
  if (!state.members.length) {
    memberTable.innerHTML = '<p class="muted">No members match current filters.</p>';
    return;
  }

  const rows = state.members
    .map((member) => {
      const avgRating = member.avg_rating_given == null ? "Hidden" : member.avg_rating_given.toFixed(2);
      const ratingCount = member.rating_count == null ? "Hidden" : member.rating_count;
      return `
        <tr>
          <td>${escapeHtml(member.username)}</td>
          <td>${escapeHtml(member.role)}</td>
          <td>${member.emoji ? escapeHtml(member.emoji) : "-"}</td>
          <td>${escapeHtml(member.stereotype)}</td>
          <td>${member.interests.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</td>
          <td>${member.total_lunches}</td>
          <td>${member.lunches_per_week.toFixed(2)}</td>
          <td>${ratingCount}</td>
          <td>${avgRating}</td>
        </tr>
      `;
    })
    .join("");

  memberTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Role</th>
          <th>Emoji</th>
          <th>Stereotype</th>
          <th>Interests</th>
          <th>Total Lunches</th>
          <th>Lunches / Week</th>
          <th>Ratings Given</th>
          <th>Avg Rating Given</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderAnalytics(overview) {
  const pnmCards = overview.top_pnms
    .slice(0, 5)
    .map(
      (pnm) => `
      <article class="card">
        <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.name)}</strong>
        <p>Weighted Total: ${pnm.weighted_total.toFixed(2)} | Ratings: ${pnm.rating_count} | Lunches: ${pnm.total_lunches}</p>
      </article>
    `
    )
    .join("");

  const memberCards = overview.member_participation
    .slice(0, 5)
    .map(
      (member) => `
      <article class="card">
        <strong>${escapeHtml(member.username)}</strong>
        <p>Lunches: ${member.total_lunches} | Lunches/Week: ${member.lunches_per_week.toFixed(2)}</p>
      </article>
    `
    )
    .join("");

  analyticsCards.innerHTML = `${pnmCards}${memberCards}` || '<p class="muted">No analytics yet.</p>';
}

function renderLeaderboard(rows) {
  if (!leaderboardTable) {
    return;
  }
  if (!rows.length) {
    leaderboardTable.innerHTML = '<p class="muted">No PNM rankings available yet.</p>';
    return;
  }

  const rankBadge = (rank) => {
    if (rank === 1) {
      return '<span class="rank-chip rank-gold">#1</span>';
    }
    if (rank === 2) {
      return '<span class="rank-chip rank-silver">#2</span>';
    }
    if (rank === 3) {
      return '<span class="rank-chip rank-bronze">#3</span>';
    }
    return `<span class="rank-chip">#${rank}</span>`;
  };

  const tableRows = rows
    .map((item) => {
      const assigned = item.assigned_officer_username || "Unassigned";
      return `
        <tr>
          <td>${rankBadge(item.rank)}</td>
          <td><strong>${escapeHtml(item.pnm_code)}</strong></td>
          <td>${escapeHtml(item.name)}</td>
          <td>${item.weighted_total.toFixed(2)}</td>
          <td>${item.rating_count}</td>
          <td>${item.total_lunches}</td>
          <td>${item.days_since_first_event}</td>
          <td>${escapeHtml(assigned)}</td>
        </tr>
      `;
    })
    .join("");

  leaderboardTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Code</th>
          <th>Name</th>
          <th>Weighted Total</th>
          <th>Ratings</th>
          <th>Lunches</th>
          <th>Days</th>
          <th>Assigned Officer</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

function renderMatching(data) {
  matchingPnms.innerHTML =
    data.pnms
      .map(
        (pnm) => `
      <div class="entry">
        <div class="entry-title">
          <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
          <span>${pnm.weighted_total.toFixed(2)}</span>
        </div>
        <div class="muted">${escapeHtml(pnm.stereotype)} | ${pnm.interests.map((item) => escapeHtml(item)).join(", ")}</div>
      </div>
    `
      )
      .join("") || '<p class="muted">No matching PNMs.</p>';

  matchingMembers.innerHTML =
    data.members
      .map(
        (member) => `
      <div class="entry">
        <div class="entry-title">
          <strong>${escapeHtml(member.username)}</strong>
          <span>${escapeHtml(member.role)}</span>
        </div>
        <div class="muted">${escapeHtml(member.stereotype)} | ${member.interests
          .map((item) => escapeHtml(item))
          .join(", ")}</div>
      </div>
    `
      )
      .join("") || '<p class="muted">No matching members.</p>';
}

function renderPendingApprovals(data) {
  if (!state.user || state.user.role !== "Head Rush Officer") {
    approvalsPanel.classList.add("hidden");
    return;
  }

  approvalsPanel.classList.remove("hidden");

  if (!data.pending.length) {
    pendingList.innerHTML = '<p class="muted">No pending usernames.</p>';
    return;
  }

  const rows = data.pending
    .map(
      (item) => `
      <tr>
        <td>${escapeHtml(item.username)}</td>
        <td>${escapeHtml(item.role)}</td>
        <td>${escapeHtml(item.stereotype)}</td>
        <td>${item.interests.map((interest) => `<span class="pill">${escapeHtml(interest)}</span>`).join("")}</td>
        <td><button type="button" class="approve-user" data-user-id="${item.user_id}">Approve</button></td>
      </tr>
    `
    )
    .join("");

  pendingList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Role</th>
          <th>Stereotype</th>
          <th>Interests</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function formatLastSeen(value) {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown";
  }
  return parsed.toLocaleString();
}

function renderHeadAdminSummary() {
  if (!headAdminSummary) {
    return;
  }
  const summary = state.headAdmin.summary;
  if (!summary) {
    headAdminSummary.innerHTML = '<p class="muted">Head admin metrics unavailable.</p>';
    return;
  }
  headAdminSummary.innerHTML = `
    <div class="card">
      <strong>${summary.head_count}</strong>
      <p>Current Head Rush Officers</p>
    </div>
    <div class="card">
      <strong>${summary.officer_count}</strong>
      <p>Active Rush Officers</p>
    </div>
    <div class="card">
      <strong>${summary.total_officer_ratings}</strong>
      <p>Total Officer Ratings</p>
    </div>
    <div class="card">
      <strong>${summary.total_officer_lunches}</strong>
      <p>Total Officer Lunches</p>
    </div>
    <div class="card">
      <strong>${Number(summary.avg_officer_score_given || 0).toFixed(2)}</strong>
      <p>Avg Officer Score Given</p>
    </div>
  `;
}

function renderCurrentHeadsList() {
  if (!currentHeadsList) {
    return;
  }
  const heads = state.headAdmin.currentHeads || [];
  if (!heads.length) {
    currentHeadsList.innerHTML = '<p class="muted">No head officers found.</p>';
    return;
  }
  currentHeadsList.innerHTML = heads
    .map(
      (head) => `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(head.username)}</strong>
            <span>${head.rating_count} ratings</span>
          </div>
          <div class="muted">Lunches: ${head.total_lunches} | Per week: ${Number(head.lunches_per_week || 0).toFixed(2)}</div>
          <div class="muted">Last login: ${escapeHtml(formatLastSeen(head.last_login_at))}</div>
        </div>
      `
    )
    .join("");
}

function renderPromotionControls() {
  if (!promoteOfficerSelect || !promoteOfficerBtn) {
    return;
  }
  const officers = state.headAdmin.rushOfficers || [];
  if (!officers.length) {
    promoteOfficerSelect.innerHTML = '<option value="">No rush officers available</option>';
    promoteOfficerSelect.disabled = true;
    promoteOfficerBtn.disabled = true;
    return;
  }
  const options = officers
    .map((officer) => {
      const emoji = officer.emoji ? `${officer.emoji} ` : "";
      return `<option value="${officer.user_id}">${escapeHtml(`${emoji}${officer.username}`)}</option>`;
    })
    .join("");
  promoteOfficerSelect.innerHTML = `<option value="">Select an officer</option>${options}`;
  promoteOfficerSelect.disabled = false;
  promoteOfficerBtn.disabled = false;
}

function renderOfficerMetrics() {
  if (!officerMetricsTable) {
    return;
  }
  const officers = state.headAdmin.rushOfficers || [];
  if (!officers.length) {
    officerMetricsTable.innerHTML = '<p class="muted">No Rush Officer metrics yet.</p>';
    return;
  }
  const rows = officers
    .map(
      (officer) => `
      <tr>
        <td><strong>${escapeHtml(officer.username)}</strong></td>
        <td>${escapeHtml(officer.emoji || "-")}</td>
        <td>${officer.rating_count}</td>
        <td>${Number(officer.avg_rating_given || 0).toFixed(2)}</td>
        <td>${Number(officer.avg_rating_total || 0).toFixed(2)}</td>
        <td>${officer.total_lunches}</td>
        <td>${Number(officer.lunches_per_week || 0).toFixed(2)}</td>
        <td>${officer.assigned_pnms_count}</td>
        <td>${Number(officer.participation_score || 0).toFixed(2)}</td>
        <td>${escapeHtml(formatLastSeen(officer.last_login_at))}</td>
      </tr>
    `
    )
    .join("");
  officerMetricsTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Officer</th>
          <th>Emoji</th>
          <th>Ratings</th>
          <th>Avg Given</th>
          <th>Avg Score</th>
          <th>Lunches</th>
          <th>Lunches/Week</th>
          <th>Assigned PNMs</th>
          <th>Participation</th>
          <th>Last Login</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderAdminPnmEditorOptions() {
  if (!adminEditPnmSelect || !adminPnmEditorForm) {
    return;
  }
  if (!state.pnms.length) {
    adminEditPnmSelect.innerHTML = '<option value="">No rushees available</option>';
    adminPnmEditorForm.classList.add("hidden");
    state.adminEditPnmId = null;
    return;
  }

  const options = state.pnms
    .map((pnm) => `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`)}</option>`)
    .join("");
  adminEditPnmSelect.innerHTML = options;
  adminPnmEditorForm.classList.remove("hidden");

  if (!state.adminEditPnmId || !state.pnms.some((pnm) => pnm.pnm_id === Number(state.adminEditPnmId))) {
    state.adminEditPnmId = state.selectedPnmId || state.pnms[0].pnm_id;
  }
  adminEditPnmSelect.value = String(state.adminEditPnmId);
  populateAdminPnmEditor(state.adminEditPnmId);
}

function populateAdminPnmEditor(pnmId) {
  const pnm = state.pnms.find((item) => item.pnm_id === Number(pnmId));
  if (!pnm) {
    return;
  }
  state.adminEditPnmId = pnm.pnm_id;
  document.getElementById("adminEditFirstName").value = pnm.first_name || "";
  document.getElementById("adminEditLastName").value = pnm.last_name || "";
  document.getElementById("adminEditClassYear").value = pnm.class_year || "F";
  document.getElementById("adminEditFirstEventDate").value = pnm.first_event_date || "";
  document.getElementById("adminEditHometown").value = pnm.hometown || "";
  document.getElementById("adminEditPhoneNumber").value = pnm.phone_number || "";
  document.getElementById("adminEditInstagramHandle").value = pnm.instagram_handle || "";
  document.getElementById("adminEditInterests").value = (pnm.interests || []).join(",");
  document.getElementById("adminEditStereotype").value = pnm.stereotype || "";
  document.getElementById("adminEditLunchStats").value = pnm.lunch_stats || "";
  document.getElementById("adminEditNotes").value = pnm.notes || "";
  syncInterestPickerFromInput("adminEditInterests", "adminEditInterestTags");
  syncStereotypePickerFromInput("adminEditStereotype", "adminEditStereotypeTags");
}

function renderAdminPnmTable() {
  if (!adminPnmTable) {
    return;
  }
  if (!state.pnms.length) {
    adminPnmTable.innerHTML = '<p class="muted">No rushees to manage.</p>';
    return;
  }

  const rows = state.pnms
    .map(
      (pnm) => `
      <tr>
        <td>${smallPhotoCell(pnm)}</td>
        <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
        <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
        <td>${escapeHtml(pnm.phone_number || "-")}</td>
        <td>${escapeHtml(pnm.instagram_handle)}</td>
        <td>${pnm.weighted_total.toFixed(2)}</td>
        <td>${pnm.rating_count}</td>
        <td>${pnm.total_lunches}</td>
        <td>
          <div class="action-row">
            <button type="button" class="secondary edit-pnm" data-pnm-id="${pnm.pnm_id}">Edit</button>
            <button type="button" class="delete-pnm" data-pnm-id="${pnm.pnm_id}">Remove</button>
          </div>
        </td>
      </tr>
    `
    )
    .join("");

  adminPnmTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Photo</th>
          <th>Code</th>
          <th>Name</th>
          <th>Phone</th>
          <th>Instagram</th>
          <th>Weighted Total</th>
          <th>Ratings</th>
          <th>Lunches</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function syncHeadAssignmentSelection() {
  if (!headAssignPnmSelect || !headAssignOfficerSelect) {
    return;
  }
  const pnmId = Number(headAssignPnmSelect.value || 0);
  if (!pnmId) {
    headAssignOfficerSelect.value = "";
    return;
  }
  const pnm = state.pnms.find((item) => item.pnm_id === pnmId);
  if (!pnm || !pnm.assigned_officer_id) {
    headAssignOfficerSelect.value = "";
    return;
  }
  headAssignOfficerSelect.value = String(pnm.assigned_officer_id);
}

function renderHeadAssignmentTable() {
  if (!headAssignmentTable) {
    return;
  }
  if (!state.pnms.length) {
    headAssignmentTable.innerHTML = '<p class="muted">No rushees available for assignment.</p>';
    return;
  }

  const rows = [...state.pnms]
    .sort((a, b) => {
      const aOfficer = (a.assigned_officer && a.assigned_officer.username) || "zzzz";
      const bOfficer = (b.assigned_officer && b.assigned_officer.username) || "zzzz";
      if (aOfficer !== bOfficer) {
        return aOfficer.localeCompare(bOfficer);
      }
      return `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`);
    })
    .map((pnm) => {
      const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const assignedAt = pnm.assigned_at ? formatLastSeen(pnm.assigned_at) : "-";
      return `
        <tr>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
          <td>${escapeHtml(assignedOfficer)}</td>
          <td>${escapeHtml(assignedAt)}</td>
          <td>${pnm.weighted_total.toFixed(2)}</td>
        </tr>
      `;
    })
    .join("");

  headAssignmentTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Rushee</th>
          <th>Assigned Officer</th>
          <th>Assigned At</th>
          <th>Weighted Total</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderHeadAssignmentManager() {
  if (!headAssignmentForm || !headAssignPnmSelect || !headAssignOfficerSelect || !headAssignmentTable) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    headAssignmentForm.classList.add("hidden");
    headAssignmentTable.innerHTML = "";
    return;
  }

  headAssignmentForm.classList.remove("hidden");
  const pnmOptions = state.pnms
    .map((pnm) => `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`)}</option>`)
    .join("");
  headAssignPnmSelect.innerHTML = pnmOptions || '<option value="">No rushees available</option>';

  const officers = rushOfficerMembers();
  const officerOptions =
    '<option value="">Unassigned</option>' +
    officers
      .map((member) => {
        const emoji = member.emoji ? `${member.emoji} ` : "";
        return `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username}`)}</option>`;
      })
      .join("");
  headAssignOfficerSelect.innerHTML = officerOptions;

  const hasActiveSelection = state.pnms.some((pnm) => pnm.pnm_id === Number(state.headAssignmentPnmId));
  if (!hasActiveSelection) {
    state.headAssignmentPnmId = state.selectedPnmId || (state.pnms.length ? state.pnms[0].pnm_id : null);
  }
  if (state.headAssignmentPnmId) {
    headAssignPnmSelect.value = String(state.headAssignmentPnmId);
  }
  syncHeadAssignmentSelection();
  renderHeadAssignmentTable();
}

function renderAdminPanel() {
  if (!roleCanUseAdminPanel()) {
    adminPanel.classList.add("hidden");
    if (adminPnmTable) {
      adminPnmTable.innerHTML = "";
    }
    if (officerMetricsTable) {
      officerMetricsTable.innerHTML = "";
    }
    if (headAssignmentTable) {
      headAssignmentTable.innerHTML = "";
    }
    return;
  }

  adminPanel.classList.remove("hidden");
  renderHeadAdminSummary();
  renderCurrentHeadsList();
  renderPromotionControls();
  renderHeadAssignmentManager();
  renderOfficerMetrics();
  renderAdminPnmEditorOptions();
  renderAdminPnmTable();
}

function applyRatingFormForSelected() {
  if (!state.selectedPnmId) {
    ratingForm.reset();
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    renderAssignmentControls();
    return;
  }

  const selected = state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId);
  if (!selected) {
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    renderAssignmentControls();
    return;
  }

  const assigned = selected.assigned_officer ? selected.assigned_officer.username : "Unassigned";
  const phone = selected.phone_number || "No phone";
  selectedPnmLabel.textContent = `${selected.pnm_code} | ${selected.first_name} ${selected.last_name} | ${phone} | Assigned: ${assigned}`;
  ratingPnm.value = String(selected.pnm_id);
  lunchPnm.value = String(selected.pnm_id);

  const own = selected.own_rating;
  document.getElementById("rateGirls").value = own ? own.good_with_girls : 0;
  document.getElementById("rateProcess").value = own ? own.will_make_it : 0;
  document.getElementById("ratePersonable").value = own ? own.personable : 0;
  document.getElementById("rateAlcohol").value = own ? own.alcohol_control : 0;
  document.getElementById("rateIg").value = own ? own.instagram_marketability : 0;
  document.getElementById("rateComment").value = own ? own.comment || "" : "";
  renderSelectedPnmPhoto(selected);
  photoForm.classList.toggle("hidden", !roleCanManagePhotos());
  renderAssignmentControls();
}

function renderRatingEntries(data) {
  if (!data.ratings.length) {
    ratingList.innerHTML = '<p class="muted">No ratings for this PNM yet.</p>';
    return;
  }

  ratingList.innerHTML = data.ratings
    .map((row) => {
      const rater = data.can_view_rater_identity
        ? `${escapeHtml(row.rater.username)} (${escapeHtml(row.rater.role)})`
        : row.from_me
          ? "Your rating"
          : "Member rating";

      const delta = row.last_change ? Number(row.last_change.delta_total) : 0;
      let deltaMarkup = "";
      if (row.last_change) {
        if (delta > 0) {
          deltaMarkup = `<span class="good">+${delta}</span>`;
        } else if (delta < 0) {
          deltaMarkup = `<span class="bad">${delta}</span>`;
        } else {
          deltaMarkup = `<span class="warn">0</span>`;
        }
      }

      const comment = row.comment ? `<div class="muted">Comment: ${escapeHtml(row.comment)}</div>` : "";
      const changeComment = row.last_change
        ? `<div class="muted">Last change: ${escapeHtml(row.last_change.comment || "No comment")}</div>`
        : "";

      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${rater}</strong>
            <span>Score ${row.total_score}/45 ${deltaMarkup}</span>
          </div>
          <div class="muted">Girls ${row.good_with_girls} | Process ${row.will_make_it} | Personable ${row.personable} | Alcohol ${row.alcohol_control} | IG ${row.instagram_marketability}</div>
          ${comment}
          ${changeComment}
        </div>
      `;
    })
    .join("");
}

function renderLunchEntries(data) {
  if (!data.lunches.length) {
    lunchHistory.innerHTML = '<p class="muted">No lunches logged for this PNM.</p>';
    return;
  }

  lunchHistory.innerHTML = data.lunches
    .map(
      (row) => `
      <div class="entry">
        <div class="entry-title">
          <strong>${escapeHtml(row.lunch_date)}</strong>
          <span>${escapeHtml(row.username)}</span>
        </div>
        <div class="muted">${escapeHtml(formatLunchWindow(row) || "All-day lunch")}</div>
        <div class="muted">${escapeHtml(row.notes || "No notes")}</div>
      </div>
    `
    )
    .join("");
}

function renderMeetingView(payload) {
  if (!meetingView) {
    return;
  }
  const { pnm, summary, ratings, lunches, matches, can_view_rater_identity: canSeeRaters } = payload;
  const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
  const photoMarkup = pnm.photo_url
    ? `<img src="${escapeHtml(pnm.photo_url)}" alt="${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}" class="meeting-photo large" loading="lazy" />`
    : '<div class="photo-placeholder large">No photo uploaded.</div>';

  const ratingsMarkup =
    ratings
      .slice(0, 8)
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
      .slice(0, 8)
      .map((row) => {
        const timing = formatLunchWindow(row);
        const detail = timing ? ` | ${escapeHtml(timing)}` : "";
        return `<li><strong>${escapeHtml(row.lunch_date)}</strong>: ${escapeHtml(row.username)} (${escapeHtml(row.role)})${detail}</li>`;
      })
      .join("") || "<li>No lunch logs yet.</li>";

  const matchMarkup =
    matches
      .slice(0, 8)
      .map((row) => {
        const shared = row.shared_interests.length ? row.shared_interests.map((x) => escapeHtml(x)).join(", ") : "None";
        return `<li><strong>${escapeHtml(row.username)}</strong> (${escapeHtml(row.role)}) | Fit ${row.fit_score} | Shared: ${shared}</li>`;
      })
      .join("") || "<li>No fit matches yet.</li>";

  meetingView.innerHTML = `
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
    <div class="grid-two">
      <article class="list-column">
        <h3>Top Ratings</h3>
        <ul class="meeting-list">${ratingsMarkup}</ul>
      </article>
      <article class="list-column">
        <h3>Recent Lunches</h3>
        <ul class="meeting-list">${lunchMarkup}</ul>
      </article>
    </div>
    <article class="list-column">
      <h3>Best Member Matches</h3>
      <ul class="meeting-list">${matchMarkup}</ul>
    </article>
  `;
}

async function loadMeetingView(pnmId) {
  if (!meetingView) {
    return;
  }
  if (meetingView.classList.contains("hidden")) {
    return;
  }
  if (!pnmId) {
    meetingView.innerHTML = '<p class="muted">Select a PNM to load the meeting packet.</p>';
    return;
  }
  try {
    const payload = await api(`/api/pnms/${pnmId}/meeting`);
    renderMeetingView(payload);
  } catch (error) {
    meetingView.innerHTML = '<p class="muted">Unable to load meeting view.</p>';
    showToast(error.message || "Unable to load meeting view.");
  }
}

async function loadPnmDetail(pnmId) {
  if (!pnmId) {
    ratingList.innerHTML = '<p class="muted">Select a PNM to view rating entries.</p>';
    lunchHistory.innerHTML = '<p class="muted">Select a PNM to view lunch logs.</p>';
    if (meetingView) {
      meetingView.innerHTML = '<p class="muted">Select a PNM to load the meeting packet.</p>';
    }
    renderSelectedPnmPhoto(null);
    renderAssignmentControls();
    return;
  }

  try {
    const [ratings, lunches] = await Promise.all([
      api(`/api/pnms/${pnmId}/ratings`),
      api(`/api/pnms/${pnmId}/lunches`),
    ]);
    renderRatingEntries(ratings);
    renderLunchEntries(lunches);
    renderAssignmentControls();
    await loadMeetingView(pnmId);
  } catch (error) {
    showToast(error.message || "Unable to load selected PNM details.");
  }
}

async function loadInterestHints() {
  const payload = await api("/api/interests");
  renderInterestHints(payload.interests || []);
}

async function loadPnms() {
  const query = toQuery(state.filters);
  const payload = await api(`/api/pnms${query}`);
  state.pnms = payload.pnms || [];
  updateHeroStats();
  renderPnmSelectOptions();

  if (state.selectedPnmId && !state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId)) {
    state.selectedPnmId = null;
  }

  if (!state.selectedPnmId && state.pnms.length) {
    state.selectedPnmId = state.pnms[0].pnm_id;
  }

  renderPnmTable();
  renderAdminPanel();
  renderAssignedRushSection();
  applyRatingFormForSelected();
  renderAssignmentControls();
  await loadPnmDetail(state.selectedPnmId);
}

async function loadMembers() {
  const query = toQuery(state.filters);
  const payload = await api(`/api/users${query}`);
  state.members = payload.users || [];
  renderMemberTable();
  renderAssignmentControls();
  renderAdminPanel();
  renderAssignedRushSection();
}

async function loadMatching() {
  const query = toQuery(state.filters);
  const payload = await api(`/api/matching${query}`);
  renderMatching(payload);
}

async function loadAnalytics() {
  const payload = await api("/api/analytics/overview");
  renderAnalytics(payload);
}

async function loadLeaderboard() {
  const payload = await api("/api/leaderboard/pnms?limit=250");
  renderLeaderboard(payload.leaderboard || []);
}

async function loadCalendarShare() {
  try {
    const payload = await api("/api/calendar/share");
    renderCalendarShareLinks(payload);
  } catch {
    if (calendarFeedPreview) {
      calendarFeedPreview.textContent = "Unable to load shared calendar link right now.";
    }
    if (openGoogleSubscribeBtn) {
      openGoogleSubscribeBtn.href = "#";
      openGoogleSubscribeBtn.classList.add("hidden");
    }
  }
}

async function loadScheduledLunches() {
  try {
    const payload = await api("/api/lunches/scheduled?limit=200");
    state.scheduledLunches = payload.lunches || [];
    renderScheduledLunches();
  } catch {
    state.scheduledLunches = [];
    if (scheduledLunchesList) {
      scheduledLunchesList.innerHTML = '<p class="muted">Unable to load scheduled lunches right now.</p>';
    }
  }
}

async function loadApprovals() {
  if (!state.user || state.user.role !== "Head Rush Officer") {
    approvalsPanel.classList.add("hidden");
    return;
  }

  const payload = await api("/api/users/pending");
  renderPendingApprovals(payload);
}

async function loadHeadAdminData() {
  if (!state.user || state.user.role !== "Head Rush Officer") {
    state.headAdmin = {
      summary: null,
      currentHeads: [],
      rushOfficers: [],
    };
    renderAdminPanel();
    return;
  }

  const payload = await api("/api/admin/rush-officers");
  state.headAdmin = {
    summary: payload.summary || null,
    currentHeads: payload.current_heads || [],
    rushOfficers: payload.rush_officers || [],
  };
  renderAdminPanel();
}

async function refreshAll() {
  await Promise.all([
    loadInterestHints(),
    loadPnms(),
    loadMembers(),
    loadMatching(),
    loadAnalytics(),
    loadLeaderboard(),
    loadCalendarShare(),
    loadScheduledLunches(),
    loadApprovals(),
    loadHeadAdminData(),
  ]);
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    state.user = payload.user;
    if (shouldRedirectToMobileNow()) {
      window.location.replace(APP_CONFIG.mobile_base);
      return;
    }
    setAuthView(true);
    setSessionHeading();
    updateTopbarActions();
    await refreshAll();
    startLiveRefresh();
  } catch {
    state.user = null;
    setAuthView(false);
    updateTopbarActions();
    stopLiveRefresh();
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginAccessCode").value;

  if (!username || !password) {
    showToast("Username and password are required.");
    return;
  }

  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: {
        username,
        password,
      },
    });

    if (APP_CONFIG.mobile_base && shouldPreferMobileUi()) {
      window.location.href = APP_CONFIG.mobile_base;
      return;
    }

    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    updateTopbarActions();
    showToast("Logged in.");
    await refreshAll();
    startLiveRefresh();
  } catch (error) {
    showToast(error.message || "Login failed.");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const username = document.getElementById("regUsername").value.trim();
  const password = document.getElementById("regAccessCode").value;
  const emoji = regEmoji.value.trim();
  if (!username) {
    showToast("Username is required.");
    return;
  }
  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    showToast("Password must be 8+ characters with letters and numbers.");
    return;
  }

  const body = {
    username,
    emoji: emoji || null,
    password,
  };

  try {
    const payload = await api("/api/auth/register", {
      method: "POST",
      body,
    });
    registerForm.reset();
    setRoleEmojiRequirement();
    showToast(`${payload.message} Username: ${payload.username}`);
  } catch (error) {
    showToast(error.message || "Registration failed.");
  }
}

async function handleLogout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    // ignore logout transport errors; local reset still required.
  }
  state.user = null;
  state.selectedPnmId = null;
  state.pnms = [];
  state.members = [];
  state.calendarShare = null;
  state.scheduledLunches = [];
  state.headAdmin = {
    summary: null,
    currentHeads: [],
    rushOfficers: [],
  };
  state.adminEditPnmId = null;
  state.headAssignmentPnmId = null;
  animateCounter(heroPnmCount, 0);
  animateCounter(heroRatingCount, 0);
  animateCounter(heroLunchCount, 0);
  if (calendarFeedPreview) {
    calendarFeedPreview.textContent = "Sign in to load shared calendar link.";
  }
  if (scheduledLunchesList) {
    scheduledLunchesList.innerHTML = '<p class="muted">Sign in to view scheduled lunches.</p>';
  }
  if (openGoogleSubscribeBtn) {
    openGoogleSubscribeBtn.href = "#";
    openGoogleSubscribeBtn.classList.add("hidden");
  }
  if (lastLunchCalendarActions) {
    lastLunchCalendarActions.classList.add("hidden");
  }
  if (openLastLunchGoogleLink) {
    openLastLunchGoogleLink.href = "#";
  }
  if (meetingView) {
    meetingView.innerHTML = '<p class="muted">Select a PNM to load the meeting packet.</p>';
  }
  renderSelectedPnmPhoto(null);
  renderAdminPanel();
  renderAssignmentControls();
  renderAssignedRushSection();
  renderGoogleImportResult(null);
  stopLiveRefresh();
  setAuthView(false);
  updateTopbarActions();
  showToast("Logged out.");
}

function getCurrentFilters() {
  return {
    interest: filterInterest.value.trim(),
    stereotype: filterStereotype.value.trim(),
  };
}

async function handleApplyFilters() {
  state.filters = getCurrentFilters();
  try {
    await Promise.all([loadPnms(), loadMembers(), loadMatching()]);
    showToast("Filters applied.");
  } catch (error) {
    showToast(error.message || "Unable to apply filters.");
  }
}

async function handlePnmCreate(event) {
  event.preventDefault();

  const interestsValue = document.getElementById("pnmInterests").value.trim();
  if (!interestsValue) {
    showToast("Select or type at least one interest.");
    return;
  }
  const body = {
    first_name: document.getElementById("pnmFirstName").value.trim(),
    last_name: document.getElementById("pnmLastName").value.trim(),
    class_year: document.getElementById("pnmClassYear").value,
    hometown: document.getElementById("pnmHometown").value.trim(),
    phone_number: document.getElementById("pnmPhone").value.trim(),
    instagram_handle: document.getElementById("pnmInstagram").value.trim(),
    first_event_date: document.getElementById("pnmEventDate").value,
    interests: interestsValue,
    stereotype: document.getElementById("pnmStereotype").value.trim(),
    lunch_stats: document.getElementById("pnmLunchStats").value.trim(),
    notes: document.getElementById("pnmNotes").value.trim(),
  };

  try {
    const payload = await api("/api/pnms", {
      method: "POST",
      body,
    });
    pnmForm.reset();
    const photoFile = pnmPhotoInput.files && pnmPhotoInput.files.length ? pnmPhotoInput.files[0] : null;
    if (photoFile) {
      const formData = new FormData();
      formData.append("photo", photoFile);
      await api(`/api/pnms/${payload.pnm.pnm_id}/photo`, {
        method: "POST",
        body: formData,
      });
    }
    pnmPhotoInput.value = "";
    setDefaultDates();
    syncInterestPickerFromInput("pnmInterests", "pnmInterestTags");
    syncStereotypePickerFromInput("pnmStereotype", "pnmStereotypeTags");
    showToast(`PNM added: ${payload.pnm.pnm_code}`);
    await refreshAll();
    state.selectedPnmId = payload.pnm.pnm_id;
    applyRatingFormForSelected();
    await loadPnmDetail(state.selectedPnmId);
  } catch (error) {
    showToast(error.message || "Unable to create PNM.");
  }
}

async function handlePhotoUpload(event) {
  event.preventDefault();
  const selectedId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!selectedId) {
    showToast("Select a PNM before uploading a photo.");
    return;
  }
  if (!roleCanManagePhotos()) {
    showToast("Only Rush Officers and Head Rush Officer can upload photos.");
    return;
  }
  const file = selectedPnmPhotoFile.files && selectedPnmPhotoFile.files.length ? selectedPnmPhotoFile.files[0] : null;
  if (!file) {
    showToast("Choose an image file first.");
    return;
  }

  const formData = new FormData();
  formData.append("photo", file);
  try {
    await api(`/api/pnms/${selectedId}/photo`, {
      method: "POST",
      body: formData,
    });
    selectedPnmPhotoFile.value = "";
    await loadPnms();
    await loadPnmDetail(selectedId);
    showToast("Photo uploaded.");
  } catch (error) {
    showToast(error.message || "Unable to upload photo.");
  }
}

async function handleRatingSave(event) {
  event.preventDefault();
  const selectedId = Number(ratingPnm.value || state.selectedPnmId || 0);

  if (!selectedId) {
    showToast("Select a PNM before saving a rating.");
    return;
  }

  const body = {
    pnm_id: selectedId,
    good_with_girls: Number(document.getElementById("rateGirls").value),
    will_make_it: Number(document.getElementById("rateProcess").value),
    personable: Number(document.getElementById("ratePersonable").value),
    alcohol_control: Number(document.getElementById("rateAlcohol").value),
    instagram_marketability: Number(document.getElementById("rateIg").value),
    comment: document.getElementById("rateComment").value.trim(),
  };

  try {
    const payload = await api("/api/ratings", {
      method: "POST",
      body,
    });
    state.selectedPnmId = selectedId;
    await refreshAll();
    await loadPnmDetail(selectedId);

    if (payload.change && Number(payload.change.delta_total) > 0) {
      spawnSuccessBurst();
      showToast(`Rating increased to ${payload.change.new_total}/45 (+${payload.change.delta_total}).`);
    } else {
      showToast("Rating saved.");
    }
  } catch (error) {
    showToast(error.message || "Unable to save rating.");
  }
}

async function handleLunchLog(event) {
  event.preventDefault();
  const selectedId = Number(lunchPnm.value || state.selectedPnmId || 0);

  if (!selectedId) {
    showToast("Select a PNM before logging lunch.");
    return;
  }

  const body = {
    pnm_id: selectedId,
    lunch_date: document.getElementById("lunchDate").value,
    start_time: lunchStartTime && lunchStartTime.value ? lunchStartTime.value : null,
    end_time: lunchEndTime && lunchEndTime.value ? lunchEndTime.value : null,
    location: lunchLocation ? lunchLocation.value.trim() : "",
    notes: document.getElementById("lunchNotes").value.trim(),
  };

  const shouldAutoOpenGoogle = Boolean(autoOpenGoogleLunchEvent && autoOpenGoogleLunchEvent.checked);
  let pendingGoogleWindow = null;
  if (shouldAutoOpenGoogle) {
    try {
      pendingGoogleWindow = window.open("", "_blank");
    } catch {
      pendingGoogleWindow = null;
    }
  }

  try {
    const payload = await api("/api/lunches", {
      method: "POST",
      body,
    });
    document.getElementById("lunchNotes").value = "";
    if (lunchStartTime) {
      lunchStartTime.value = "";
    }
    if (lunchEndTime) {
      lunchEndTime.value = "";
    }
    if (lunchLocation) {
      lunchLocation.value = "";
    }
    if (payload.lunch && payload.lunch.google_calendar_url && openLastLunchGoogleLink && lastLunchCalendarActions) {
      openLastLunchGoogleLink.href = payload.lunch.google_calendar_url;
      lastLunchCalendarActions.classList.remove("hidden");
      if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
        pendingGoogleWindow.location.href = payload.lunch.google_calendar_url;
      } else if (shouldAutoOpenGoogle) {
        window.location.assign(payload.lunch.google_calendar_url);
        return;
      }
    } else if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
      pendingGoogleWindow.close();
    }
    showToast("Lunch scheduled. Shared calendar updated; Google subscribed calendars may sync with delay.");
    state.selectedPnmId = selectedId;
    await refreshAll();
    await loadPnmDetail(selectedId);
  } catch (error) {
    if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
      pendingGoogleWindow.close();
    }
    showToast(error.message || "Unable to schedule lunch.");
  }
}

async function handleHeadAssignmentSubmit(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  const officerUserId = headAssignOfficerSelect && headAssignOfficerSelect.value ? Number(headAssignOfficerSelect.value) : null;

  const saveButton = document.getElementById("headAssignSaveBtn");
  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: officerUserId },
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment saved from Head Console.");
  } catch (error) {
    showToast(error.message || "Unable to update assignment.");
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save Assignment";
    }
  }
}

async function handleHeadAssignmentClear() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  const clearButton = document.getElementById("headAssignClearBtn");
  if (clearButton) {
    clearButton.disabled = true;
    clearButton.textContent = "Clearing...";
  }
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: null },
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment cleared.");
  } catch (error) {
    showToast(error.message || "Unable to clear assignment.");
  } finally {
    if (clearButton) {
      clearButton.disabled = false;
      clearButton.textContent = "Clear Assignment";
    }
  }
}

async function handlePnmTableClick(event) {
  const button = event.target.closest("button.select-pnm");
  if (!button) {
    return;
  }

  const pnmId = Number(button.dataset.pnmId || 0);
  if (!pnmId) {
    return;
  }

  state.selectedPnmId = pnmId;
  state.headAssignmentPnmId = pnmId;
  renderPnmTable();
  applyRatingFormForSelected();
  await loadPnmDetail(pnmId);
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
    await Promise.all([loadApprovals(), loadMembers(), loadMatching()]);
  } catch (error) {
    showToast(error.message || "Unable to approve user.");
  }
}

async function handlePromoteOfficer() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const officerId = Number(promoteOfficerSelect && promoteOfficerSelect.value ? promoteOfficerSelect.value : 0);
  if (!officerId) {
    showToast("Select a Rush Officer to promote.");
    return;
  }

  const officer = (state.headAdmin.rushOfficers || []).find((entry) => entry.user_id === officerId);
  const transferLeadership = Boolean(demoteExistingHeads && demoteExistingHeads.checked);
  const targetName = officer ? officer.username : "selected officer";
  const prompt = transferLeadership
    ? `Promote ${targetName} to Head Rush Officer and demote other heads to Rush Officer?`
    : `Promote ${targetName} to Head Rush Officer?`;
  const confirmed = window.confirm(prompt);
  if (!confirmed) {
    return;
  }

  promoteOfficerBtn.disabled = true;
  promoteOfficerBtn.textContent = "Promoting...";
  try {
    const payload = await api(`/api/admin/officers/${officerId}/promote-head`, {
      method: "POST",
      body: {
        demote_existing_heads: transferLeadership,
      },
    });
    showToast(payload.message || "Officer promoted.");
    await ensureSession();
  } catch (error) {
    showToast(error.message || "Unable to promote officer.");
  } finally {
    promoteOfficerBtn.disabled = false;
    promoteOfficerBtn.textContent = "Promote To Head";
  }
}

async function handleAdminPnmEditorSubmit(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(adminEditPnmSelect && adminEditPnmSelect.value ? adminEditPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }

  const interestsValue = document.getElementById("adminEditInterests").value.trim();
  if (!interestsValue) {
    showToast("Select or type at least one interest.");
    return;
  }
  const saveButton = document.getElementById("saveAdminPnmBtn");
  const body = {
    first_name: document.getElementById("adminEditFirstName").value.trim(),
    last_name: document.getElementById("adminEditLastName").value.trim(),
    class_year: document.getElementById("adminEditClassYear").value,
    first_event_date: document.getElementById("adminEditFirstEventDate").value,
    hometown: document.getElementById("adminEditHometown").value.trim(),
    phone_number: document.getElementById("adminEditPhoneNumber").value.trim(),
    instagram_handle: document.getElementById("adminEditInstagramHandle").value.trim(),
    interests: interestsValue,
    stereotype: document.getElementById("adminEditStereotype").value.trim(),
    lunch_stats: document.getElementById("adminEditLunchStats").value.trim(),
    notes: document.getElementById("adminEditNotes").value.trim(),
  };

  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  try {
    const payload = await api(`/api/pnms/${pnmId}`, {
      method: "PATCH",
      body,
    });
    state.selectedPnmId = pnmId;
    state.adminEditPnmId = pnmId;
    showToast(payload.message || "Rushee details saved.");
    await refreshAll();
    await loadPnmDetail(pnmId);
  } catch (error) {
    showToast(error.message || "Unable to update rushee details.");
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save Rushee Changes";
    }
  }
}

async function handleAdminPanelClick(event) {
  const editButton = event.target.closest("button.edit-pnm");
  if (editButton) {
    const pnmId = Number(editButton.dataset.pnmId || 0);
    if (!pnmId) {
      return;
    }
    state.adminEditPnmId = pnmId;
    if (adminEditPnmSelect) {
      adminEditPnmSelect.value = String(pnmId);
    }
    populateAdminPnmEditor(pnmId);
    setActiveDesktopPage("admin");
    showToast("Rushee loaded into editor.");
    return;
  }

  const button = event.target.closest("button.delete-pnm");
  if (!button) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }

  const pnmId = Number(button.dataset.pnmId || 0);
  if (!pnmId) {
    return;
  }
  const pnm = state.pnms.find((item) => item.pnm_id === pnmId);
  const name = pnm ? `${pnm.first_name} ${pnm.last_name}` : "this rushee";
  const confirmed = window.confirm(`Remove ${name}? This will also remove associated ratings and lunches.`);
  if (!confirmed) {
    return;
  }

  try {
    await api(`/api/pnms/${pnmId}`, { method: "DELETE" });
    if (state.selectedPnmId === pnmId) {
      state.selectedPnmId = null;
    }
    await refreshAll();
    showToast("Rushee removed.");
  } catch (error) {
    showToast(error.message || "Unable to remove rushee.");
  }
}

async function handleAssignOfficer() {
  if (!roleCanAssignOfficer()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!pnmId) {
    showToast("Select a PNM first.");
    return;
  }

  const officerUserId = assignOfficerSelect.value ? Number(assignOfficerSelect.value) : null;
  assignOfficerBtn.disabled = true;
  assignOfficerBtn.textContent = "Saving...";
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: officerUserId },
    });
    state.headAssignmentPnmId = pnmId;
    await refreshAll();
    state.selectedPnmId = pnmId;
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment updated.");
  } catch (error) {
    showToast(error.message || "Unable to assign Rush Officer.");
  } finally {
    assignOfficerBtn.disabled = false;
    assignOfficerBtn.textContent = "Assign";
  }
}

async function handleClearAssignment() {
  if (!roleCanAssignOfficer()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!pnmId) {
    showToast("Select a PNM first.");
    return;
  }
  clearAssignBtn.disabled = true;
  clearAssignBtn.textContent = "Clearing...";
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: null },
    });
    state.headAssignmentPnmId = pnmId;
    await refreshAll();
    state.selectedPnmId = pnmId;
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment cleared.");
  } catch (error) {
    showToast(error.message || "Unable to clear assignment.");
  } finally {
    clearAssignBtn.disabled = false;
    clearAssignBtn.textContent = "Clear";
  }
}

async function handleCsvBackupDownload() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  backupCsvBtn.disabled = true;
  backupCsvBtn.textContent = "Preparing...";
  try {
    await downloadFile("/api/export/csv", "kao-rush-backup.zip");
    showToast("CSV backup downloaded.");
  } catch (error) {
    showToast(error.message || "CSV backup download failed.");
  } finally {
    backupCsvBtn.disabled = false;
    backupCsvBtn.textContent = "Backup CSV";
  }
}

async function handleDbBackupDownload() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  backupDbBtn.disabled = true;
  backupDbBtn.textContent = "Preparing...";
  try {
    await downloadFile("/api/export/sqlite", "kao-rush-backup.sqlite");
    showToast("Database snapshot downloaded.");
  } catch (error) {
    showToast(error.message || "Database backup download failed.");
  } finally {
    backupDbBtn.disabled = false;
    backupDbBtn.textContent = "Backup DB";
  }
}

function renderGoogleImportResult(payload) {
  if (!googleImportResult) {
    return;
  }
  if (!payload) {
    googleImportResult.innerHTML = '<p class="muted">No imports yet.</p>';
    return;
  }
  const issues = (payload.errors || [])
    .map((item) => `<li>Row ${item.row}: ${escapeHtml(item.reason)}</li>`)
    .join("");
  const truncated = payload.errors_truncated ? '<p class="muted">Only the first set of errors are shown.</p>' : "";
  googleImportResult.innerHTML = `
    <div class="entry">
      <div class="entry-title">
        <strong>Last Import Result</strong>
        <span>${escapeHtml(payload.created_count || 0)} created</span>
      </div>
      <p class="muted">Rows processed: ${payload.rows_processed || 0} | Created: ${payload.created_count || 0} | Duplicates skipped: ${payload.skipped_duplicates || 0} | Errors: ${payload.error_count || 0}</p>
      <p class="muted">${escapeHtml(payload.message || "")}</p>
      ${issues ? `<ul class="import-error-list">${issues}</ul>${truncated}` : '<p class="muted">No row-level errors.</p>'}
    </div>
  `;
}

async function handleGoogleImport(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const file = googleImportFile && googleImportFile.files && googleImportFile.files.length ? googleImportFile.files[0] : null;
  if (!file) {
    showToast("Choose a Google Form CSV file first.");
    return;
  }

  if (googleImportBtn) {
    googleImportBtn.disabled = true;
    googleImportBtn.textContent = "Importing...";
  }
  try {
    const formData = new FormData();
    formData.append("file", file);
    const payload = await api("/api/admin/import/google-form", {
      method: "POST",
      body: formData,
    });
    renderGoogleImportResult(payload);
    if (googleImportForm) {
      googleImportForm.reset();
    }
    if (Number(payload.created_count || 0) > 0) {
      await refreshAll();
    }
    showToast(payload.message || "Google Form CSV imported.");
  } catch (error) {
    showToast(error.message || "Unable to import Google Form CSV.");
  } finally {
    if (googleImportBtn) {
      googleImportBtn.disabled = false;
      googleImportBtn.textContent = "Import Google Form CSV";
    }
  }
}

function handleDownloadGoogleImportTemplate() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  window.location.href = resolveApiPath("/api/admin/import/google-form/template");
}

async function handleCopyCalendarFeed() {
  if (!state.calendarShare || !state.calendarShare.feed_url) {
    showToast("Shared calendar link is not ready yet.");
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(state.calendarShare.feed_url);
    } else {
      const input = document.createElement("input");
      input.value = state.calendarShare.feed_url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      input.remove();
    }
    showToast("Shared calendar URL copied.");
  } catch {
    showToast("Unable to copy URL. Use the link shown below the button.");
  }
}

function setupPwaInstall() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {
      // service worker registration failure should not block core app.
    });
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    state.deferredPrompt = event;
    installBtn.classList.remove("hidden");
  });

  installBtn.addEventListener("click", async () => {
    if (!state.deferredPrompt) {
      return;
    }
    state.deferredPrompt.prompt();
    await state.deferredPrompt.userChoice;
    state.deferredPrompt = null;
    installBtn.classList.add("hidden");
  });
}

function attachEvents() {
  loginForm.addEventListener("submit", handleLogin);
  registerForm.addEventListener("submit", handleRegister);
  logoutBtn.addEventListener("click", handleLogout);
  backupCsvBtn.addEventListener("click", handleCsvBackupDownload);
  backupDbBtn.addEventListener("click", handleDbBackupDownload);
  if (googleImportForm) {
    googleImportForm.addEventListener("submit", handleGoogleImport);
  }
  if (downloadGoogleImportTemplateBtn) {
    downloadGoogleImportTemplateBtn.addEventListener("click", handleDownloadGoogleImportTemplate);
  }
  if (copyCalendarFeedBtn) {
    copyCalendarFeedBtn.addEventListener("click", handleCopyCalendarFeed);
  }
  if (refreshScheduledLunchesBtn) {
    refreshScheduledLunchesBtn.addEventListener("click", async () => {
      try {
        await loadScheduledLunches();
        showToast("Scheduled lunches refreshed.");
      } catch (error) {
        showToast(error.message || "Unable to refresh scheduled lunches.");
      }
    });
  }
  if (assignOfficerBtn) {
    assignOfficerBtn.addEventListener("click", handleAssignOfficer);
  }
  if (clearAssignBtn) {
    clearAssignBtn.addEventListener("click", handleClearAssignment);
  }

  applyFiltersBtn.addEventListener("click", handleApplyFilters);

  pnmForm.addEventListener("submit", handlePnmCreate);
  ratingForm.addEventListener("submit", handleRatingSave);
  lunchForm.addEventListener("submit", handleLunchLog);
  photoForm.addEventListener("submit", handlePhotoUpload);

  pnmTable.addEventListener("click", handlePnmTableClick);
  pendingList.addEventListener("click", handlePendingClick);
  adminPnmTable.addEventListener("click", handleAdminPanelClick);
  if (promoteOfficerBtn) {
    promoteOfficerBtn.addEventListener("click", handlePromoteOfficer);
  }
  if (adminPnmEditorForm) {
    adminPnmEditorForm.addEventListener("submit", handleAdminPnmEditorSubmit);
  }
  if (adminEditPnmSelect) {
    adminEditPnmSelect.addEventListener("change", (event) => {
      const nextId = Number(event.target.value || 0);
      if (!nextId) {
        return;
      }
      populateAdminPnmEditor(nextId);
    });
  }
  if (headAssignmentForm) {
    headAssignmentForm.addEventListener("submit", handleHeadAssignmentSubmit);
  }
  if (headAssignPnmSelect) {
    headAssignPnmSelect.addEventListener("change", () => {
      state.headAssignmentPnmId = Number(headAssignPnmSelect.value || 0) || null;
      syncHeadAssignmentSelection();
    });
  }
  if (headAssignClearBtn) {
    headAssignClearBtn.addEventListener("click", handleHeadAssignmentClear);
  }

  ratingPnm.addEventListener("change", async (event) => {
    const selectedId = Number(event.target.value || 0);
    if (!selectedId) {
      return;
    }
    state.selectedPnmId = selectedId;
    renderPnmTable();
    applyRatingFormForSelected();
    await loadPnmDetail(selectedId);
  });

  lunchPnm.addEventListener("change", (event) => {
    const selectedId = Number(event.target.value || 0);
    if (selectedId) {
      state.selectedPnmId = selectedId;
      renderPnmTable();
      applyRatingFormForSelected();
    }
  });

  if (desktopPageNav) {
    desktopPageNav.addEventListener("click", (event) => {
      const link = event.target.closest(".desktop-page-link[data-page]");
      if (!link) {
        return;
      }
      event.preventDefault();
      setActiveDesktopPage((link.dataset.page || DEFAULT_DESKTOP_PAGE).toLowerCase());
    });
  }

  window.addEventListener("popstate", () => {
    setActiveDesktopPage(currentRequestedDesktopPage(), false);
  });
}

async function init() {
  setDefaultDates();
  setRoleEmojiRequirement();
  initializePresetTagPickers();
  attachEvents();
  setActiveDesktopPage(currentRequestedDesktopPage(), false);
  updateTopbarActions();
  setupPwaInstall();
  await ensureSession();
}

init();
