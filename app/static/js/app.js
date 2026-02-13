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
const refreshInstagramPhotoBtn = document.getElementById("refreshInstagramPhotoBtn");
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
const seasonArchiveSummary = document.getElementById("seasonArchiveSummary");
const seasonArchivePhrase = document.getElementById("seasonArchivePhrase");
const seasonArchiveLabel = document.getElementById("seasonArchiveLabel");
const seasonHeadChairConfirm = document.getElementById("seasonHeadChairConfirm");
const seasonResetBtn = document.getElementById("seasonResetBtn");
const seasonArchiveDownloadBtn = document.getElementById("seasonArchiveDownloadBtn");

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

const rushEventForm = document.getElementById("rushEventForm");
const rushEventTitle = document.getElementById("rushEventTitle");
const rushEventType = document.getElementById("rushEventType");
const rushEventDate = document.getElementById("rushEventDate");
const rushEventStartTime = document.getElementById("rushEventStartTime");
const rushEventEndTime = document.getElementById("rushEventEndTime");
const rushEventLocation = document.getElementById("rushEventLocation");
const rushEventDetails = document.getElementById("rushEventDetails");
const rushEventOfficial = document.getElementById("rushEventOfficial");
const rushEventPermissionNotice = document.getElementById("rushEventPermissionNotice");
const rushCalendarStats = document.getElementById("rushCalendarStats");
const rushCalendarTable = document.getElementById("rushCalendarTable");
const copyRushCalendarFeedBtn = document.getElementById("copyRushCalendarFeedBtn");
const openRushGoogleSubscribeBtn = document.getElementById("openRushGoogleSubscribeBtn");
const rushCalendarFeedPreview = document.getElementById("rushCalendarFeedPreview");
const copyLunchOnlyFeedBtn = document.getElementById("copyLunchOnlyFeedBtn");
const lunchOnlyFeedPreview = document.getElementById("lunchOnlyFeedPreview");

const weeklyGoalForm = document.getElementById("weeklyGoalForm");
const weeklyGoalTitle = document.getElementById("weeklyGoalTitle");
const weeklyGoalDescription = document.getElementById("weeklyGoalDescription");
const weeklyGoalMetric = document.getElementById("weeklyGoalMetric");
const weeklyGoalTarget = document.getElementById("weeklyGoalTarget");
const weeklyGoalWeekStart = document.getElementById("weeklyGoalWeekStart");
const weeklyGoalWeekEnd = document.getElementById("weeklyGoalWeekEnd");
const weeklyGoalAssignedUser = document.getElementById("weeklyGoalAssignedUser");
const weeklyGoalSummary = document.getElementById("weeklyGoalSummary");
const weeklyGoalsList = document.getElementById("weeklyGoalsList");

const notificationsReadAllBtn = document.getElementById("notificationsReadAllBtn");
const notificationsList = document.getElementById("notificationsList");
const officerChatForm = document.getElementById("officerChatForm");
const officerChatMessage = document.getElementById("officerChatMessage");
const officerChatTags = document.getElementById("officerChatTags");
const officerChatStats = document.getElementById("officerChatStats");
const officerChatList = document.getElementById("officerChatList");
const officerChatQuickTags = document.getElementById("officerChatQuickTags");

const desktopPageNav = document.getElementById("desktopPageNav");
const desktopPages = Array.from(document.querySelectorAll(".desktop-page[data-page]"));
const desktopPageLinks = Array.from(document.querySelectorAll(".desktop-page-link[data-page]"));
const operationsUnreadBadge = document.getElementById("operationsUnreadBadge");

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
const BASE_DEFAULT_INTEREST_TAGS = [
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
const BASE_DEFAULT_STEREOTYPE_TAGS = [
  "Leader",
  "Connector",
  "Scholar",
  "Athlete",
  "Social",
  "Creative",
  "Mentor",
  "Builder",
];
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
const PNM_AVG_FIELD_BY_RATING_FIELD = {
  good_with_girls: "avg_good_with_girls",
  will_make_it: "avg_will_make_it",
  personable: "avg_personable",
  alcohol_control: "avg_alcohol_control",
  instagram_marketability: "avg_instagram_marketability",
};

function toTitleCase(text) {
  return String(text || "")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function parseConfiguredTagList(raw, fallback) {
  if (!Array.isArray(raw)) {
    return [...fallback];
  }
  const out = [];
  const seen = new Set();
  raw.forEach((item) => {
    const token = toTitleCase(item);
    if (!token) {
      return;
    }
    const key = token.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    out.push(token);
  });
  return out.length ? out.slice(0, 20) : [...fallback];
}

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
const DEFAULT_INTEREST_TAGS = parseConfiguredTagList(APP_CONFIG.default_interest_tags, BASE_DEFAULT_INTEREST_TAGS);
const DEFAULT_STEREOTYPE_TAGS = parseConfiguredTagList(
  APP_CONFIG.default_stereotype_tags,
  BASE_DEFAULT_STEREOTYPE_TAGS
);

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
  rushCalendarItems: [],
  rushCalendarStats: null,
  weeklyGoals: [],
  weeklyGoalSummary: null,
  weeklyGoalMetricOptions: [],
  notifications: [],
  unreadNotifications: 0,
  officerChatMessages: [],
  officerChatStats: null,
  adminEditPnmId: null,
  headAssignmentPnmId: null,
  seasonArchive: null,
};

function ratingCriteriaForField(field) {
  return RATING_CRITERIA_BY_FIELD.get(field) || BASE_RATING_CRITERIA.find((item) => item.field === field);
}

function ratingLabelWithRange(field) {
  const criterion = ratingCriteriaForField(field);
  if (!criterion) {
    return `${field} (0-10)`;
  }
  return `${criterion.short_label} (0-${criterion.max})`;
}

function formatScoreBreakdown(row) {
  return RATING_CRITERIA.map((criterion) => {
    const value = Number(row[criterion.field] || 0);
    return `${criterion.short_label} ${value}`;
  }).join(" | ");
}

function applyRatingCriteriaUi() {
  const fields = [
    { field: "good_with_girls", inputId: "rateGirls", labelId: "rateGirlsLabel" },
    { field: "will_make_it", inputId: "rateProcess", labelId: "rateProcessLabel" },
    { field: "personable", inputId: "ratePersonable", labelId: "ratePersonableLabel" },
    { field: "alcohol_control", inputId: "rateAlcohol", labelId: "rateAlcoholLabel" },
    { field: "instagram_marketability", inputId: "rateIg", labelId: "rateIgLabel" },
  ];
  fields.forEach(({ field, inputId, labelId }) => {
    const criterion = ratingCriteriaForField(field);
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    if (input && criterion) {
      input.min = "0";
      input.max = String(criterion.max);
    }
    if (label) {
      label.textContent = ratingLabelWithRange(field);
    }
  });
}

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
        loadRushCalendar(),
        loadWeeklyGoals(),
        loadNotifications(),
        loadOfficerChat(),
        loadOfficerChatStats(),
        loadApprovals(),
        loadHeadAdminData(),
        loadSeasonArchiveStatus(),
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

function roleCanApproveUsers() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanAssignOfficer() {
  return state.user && state.user.role === "Head Rush Officer";
}

function roleCanViewAssignedRushes() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanManageOperations() {
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

function shouldRedirectToMemberPortal(user) {
  if (!user || user.role !== "Rusher" || !APP_CONFIG.member_base) {
    return false;
  }
  const currentPath = window.location.pathname.replace(/\/$/, "");
  const memberPath = APP_CONFIG.member_base.replace(/\/$/, "");
  if (!memberPath) {
    return false;
  }
  return currentPath !== memberPath;
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
    maxY = Math.min(RATING_TOTAL_MAX, maxY + 0.5);
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

function formatCalendarWindow(item) {
  const start = item.start_time || "";
  const end = item.end_time || "";
  if (start && end) {
    return `${start}-${end}`;
  }
  if (start) {
    return start;
  }
  return "All day";
}

function renderRushCalendar() {
  if (!rushCalendarTable || !rushCalendarStats) {
    return;
  }
  const canManageEvents = roleCanUseAdminPanel();
  if (rushEventForm) {
    rushEventForm.classList.toggle("hidden", !canManageEvents);
  }
  if (rushEventPermissionNotice) {
    rushEventPermissionNotice.classList.toggle("hidden", canManageEvents);
  }
  const items = state.rushCalendarItems || [];
  const stats = state.rushCalendarStats || { total_count: 0, official_event_count: 0, lunch_count: 0, this_week_count: 0 };
  rushCalendarStats.innerHTML = `
    <div class="card"><strong>${Number(stats.total_count || 0)}</strong><p>Total Timeline Items</p></div>
    <div class="card"><strong>${Number(stats.official_event_count || 0)}</strong><p>Official Rush Events</p></div>
    <div class="card"><strong>${Number(stats.lunch_count || 0)}</strong><p>Scheduled Lunches</p></div>
    <div class="card"><strong>${Number(stats.this_week_count || 0)}</strong><p>This Week</p></div>
  `;

  if (!items.length) {
    rushCalendarTable.innerHTML = '<p class="muted">No rush calendar items yet.</p>';
    return;
  }

  const rows = items
    .map((item) => {
      const isEvent = item.item_type === "rush_event";
      const typeLabel = isEvent ? (item.event_type || "event") : "lunch";
      const title = item.title || (item.pnm_name ? `Lunch with ${item.pnm_name}` : "Calendar Item");
      const creator = item.created_by_username || "-";
      const official = isEvent && item.is_official ? '<span class="pill">Official</span>' : "";
      const details = item.details || "-";
      const googleAction = item.google_calendar_url
        ? `<a class="quick-nav-link" href="${escapeHtml(item.google_calendar_url)}" target="_blank" rel="noopener">Open</a>`
        : "";
      const deleteAction = canManageEvents && isEvent
        ? `<button type="button" class="secondary calendar-remove-btn" data-rush-event-delete="${item.event_id}">Remove</button>`
        : "";
      return `
        <tr>
          <td><strong>${escapeHtml(item.event_date || "")}</strong></td>
          <td>${escapeHtml(formatCalendarWindow(item))}</td>
          <td><span class="pill">${escapeHtml(typeLabel)}</span> ${official}</td>
          <td>${escapeHtml(title)}</td>
          <td>${escapeHtml(item.location || "-")}</td>
          <td>${escapeHtml(details)}</td>
          <td>${escapeHtml(creator)}</td>
          <td>
            <div class="action-row">
              ${googleAction}
              ${deleteAction}
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  rushCalendarTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Time</th>
          <th>Type</th>
          <th>Title</th>
          <th>Location</th>
          <th>Details</th>
          <th>Created By</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderWeeklyGoalMetricOptions() {
  if (!weeklyGoalMetric) {
    return;
  }
  const options = (state.weeklyGoalMetricOptions || [])
    .map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`)
    .join("");
  weeklyGoalMetric.innerHTML = options || `
    <option value="manual">Manual Progress</option>
    <option value="ratings_submitted">Ratings Submitted</option>
    <option value="lunches_logged">Lunches Logged</option>
    <option value="pnms_created">PNMs Added</option>
    <option value="chat_messages">Chat Messages</option>
    <option value="rush_events_created">Rush Events Created</option>
  `;
}

function renderWeeklyGoalAssignedUsers() {
  if (!weeklyGoalAssignedUser) {
    return;
  }
  const options = ['<option value="">Team goal (unassigned)</option>'];
  const members = state.members || [];
  members
    .filter((member) => member && member.user_id && member.username)
    .forEach((member) => {
      const emoji = member.emoji ? `${member.emoji} ` : "";
      options.push(
        `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username} (${member.role})`)}</option>`
      );
    });
  weeklyGoalAssignedUser.innerHTML = options.join("");
}

function renderWeeklyGoals() {
  if (!weeklyGoalsList || !weeklyGoalSummary) {
    return;
  }
  if (weeklyGoalForm) {
    weeklyGoalForm.classList.toggle("hidden", !roleCanManageOperations());
  }
  const summary = state.weeklyGoalSummary || {
    total: 0,
    active: 0,
    completed: 0,
    overdue: 0,
    completion_rate: 0,
  };
  weeklyGoalSummary.innerHTML = `
    <div class="card"><strong>${Number(summary.total || 0)}</strong><p>Total Goals</p></div>
    <div class="card"><strong>${Number(summary.active || 0)}</strong><p>Active</p></div>
    <div class="card"><strong>${Number(summary.completed || 0)}</strong><p>Completed</p></div>
    <div class="card"><strong>${Number(summary.overdue || 0)}</strong><p>Overdue</p></div>
    <div class="card"><strong>${Number(summary.completion_rate || 0)}%</strong><p>Completion Rate</p></div>
  `;

  const goals = state.weeklyGoals || [];
  if (!goals.length) {
    weeklyGoalsList.innerHTML = '<p class="muted">No weekly goals created yet.</p>';
    return;
  }

  const canManage = roleCanManageOperations();
  const isHead = roleCanUseAdminPanel();
  weeklyGoalsList.innerHTML = goals
    .map((goal) => {
      const statusClass = goal.status === "completed" ? "good" : goal.status === "overdue" ? "bad" : "warn";
      const assignment = goal.assigned_username ? `Assigned: ${goal.assigned_username}` : "Team Goal";
      const weekWindow = `${goal.week_start} to ${goal.week_end}`;
      const actions = [];
      if (canManage && goal.metric_type === "manual" && !goal.is_completed && !goal.is_archived) {
        actions.push(`<button type="button" class="secondary" data-goal-progress="${goal.goal_id}">+1 Progress</button>`);
      }
      if (canManage && !goal.is_completed && !goal.is_archived) {
        actions.push(`<button type="button" class="secondary" data-goal-complete="${goal.goal_id}">Mark Complete</button>`);
      }
      if (isHead) {
        const label = goal.is_archived ? "Unarchive" : "Archive";
        actions.push(`<button type="button" class="secondary" data-goal-archive="${goal.goal_id}" data-goal-archived="${goal.is_archived ? "1" : "0"}">${label}</button>`);
      }
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(goal.title)}</strong>
            <span class="${statusClass}">${escapeHtml(goal.status)}</span>
          </div>
          <div class="muted">${escapeHtml(goal.metric_label)} | Target ${goal.target_count} | Progress ${goal.progress_count} (${goal.percent_complete}%)</div>
          <div class="muted">${escapeHtml(assignment)} | ${escapeHtml(weekWindow)}</div>
          ${goal.description ? `<div class="muted">${escapeHtml(goal.description)}</div>` : ""}
          ${actions.length ? `<div class="action-row">${actions.join("")}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderNotifications() {
  if (!notificationsList || !notificationsReadAllBtn) {
    renderOperationsUnreadBadge();
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  notificationsReadAllBtn.textContent = unread > 0 ? `Mark All Read (${unread})` : "Mark All Read";
  notificationsReadAllBtn.disabled = unread <= 0;

  const rows = state.notifications || [];
  if (!rows.length) {
    notificationsList.innerHTML = '<p class="muted">No notifications yet.</p>';
    renderOperationsUnreadBadge();
    return;
  }
  notificationsList.innerHTML = rows
    .map((item) => {
      const readClass = item.is_read ? "" : " notification-unread";
      const markBtn = item.is_read
        ? ""
        : `<button type="button" class="secondary" data-notification-read="${item.notification_id}">Mark Read</button>`;
      const linkBtn = item.link_path
        ? `<a class="quick-nav-link" href="${escapeHtml(item.link_path)}">Open</a>`
        : "";
      return `
        <div class="entry${readClass}">
          <div class="entry-title">
            <strong>${escapeHtml(item.title || "Update")}</strong>
            <span>${escapeHtml(formatLastSeen(item.created_at))}</span>
          </div>
          ${item.body ? `<div class="muted">${escapeHtml(item.body)}</div>` : ""}
          <div class="action-row">
            ${markBtn}
            ${linkBtn}
          </div>
        </div>
      `;
    })
    .join("");

  renderOperationsUnreadBadge();
}

function renderOperationsUnreadBadge() {
  if (!operationsUnreadBadge) {
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  if (unread <= 0) {
    operationsUnreadBadge.classList.add("hidden");
    operationsUnreadBadge.textContent = "0";
    return;
  }
  operationsUnreadBadge.classList.remove("hidden");
  operationsUnreadBadge.textContent = unread > 99 ? "99+" : String(unread);
}

function renderOfficerChatStats() {
  if (!officerChatStats) {
    return;
  }
  if (!roleCanManageOperations()) {
    officerChatStats.innerHTML = '<p class="muted">Rush Officer access required.</p>';
    return;
  }
  const payload = state.officerChatStats;
  if (!payload || !payload.summary) {
    officerChatStats.innerHTML = '<p class="muted">Chat stats unavailable.</p>';
    return;
  }
  const summary = payload.summary;
  const topTag = payload.top_tags && payload.top_tags.length ? `#${payload.top_tags[0].tag}` : "None";
  const topSender = payload.top_senders && payload.top_senders.length ? payload.top_senders[0].username : "None";
  officerChatStats.innerHTML = `
    <div class="card"><strong>${Number(summary.total_messages || 0)}</strong><p>Total Messages</p></div>
    <div class="card"><strong>${Number(summary.messages_last_24h || 0)}</strong><p>Last 24h</p></div>
    <div class="card"><strong>${Number(summary.active_senders_7d || 0)}</strong><p>Active Senders (7d)</p></div>
    <div class="card"><strong>${escapeHtml(topTag)}</strong><p>Top Tag</p></div>
    <div class="card"><strong>${escapeHtml(topSender)}</strong><p>Top Contributor</p></div>
  `;
}

function formatChatClock(value) {
  if (!value) {
    return "--:--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--:--";
  }
  return parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatChatDayLabel(value) {
  if (!value) {
    return "Recent";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Recent";
  }
  const dayStart = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.round((dayStart.getTime() - todayStart.getTime()) / 86400000);
  if (diffDays === 0) {
    return "Today";
  }
  if (diffDays === -1) {
    return "Yesterday";
  }
  return parsed.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function chatRoleLabel(role) {
  if (role === "Head Rush Officer") {
    return "Head";
  }
  if (role === "Rush Officer") {
    return "Officer";
  }
  return "Member";
}

function shouldAutoScrollChatFeed() {
  if (!officerChatList) {
    return true;
  }
  const remaining = officerChatList.scrollHeight - officerChatList.scrollTop - officerChatList.clientHeight;
  return remaining <= 120;
}

function renderOfficerChat() {
  if (!officerChatList || !officerChatForm) {
    return;
  }
  const canUse = roleCanManageOperations();
  officerChatForm.classList.toggle("hidden", !canUse);
  if (!canUse) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>Rush Officer access required.</strong><p class="muted">Only approved Rush Officers and Head Rush Officers can access this thread.</p></div>';
    return;
  }

  const rows = state.officerChatMessages || [];
  if (!rows.length) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>No messages yet.</strong><p class="muted">Start the thread with a kickoff update, assignment, or concern.</p></div>';
    return;
  }

  const keepPinnedToBottom = shouldAutoScrollChatFeed();
  const parts = [];
  let lastDayKey = "";

  rows.forEach((message) => {
    const createdAt = message.created_at || "";
    const parsed = new Date(createdAt);
    if (!Number.isNaN(parsed.getTime())) {
      const nextDayKey = `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}`;
      if (nextDayKey !== lastDayKey) {
        parts.push(`<div class="chat-day-separator"><span>${escapeHtml(formatChatDayLabel(createdAt))}</span></div>`);
        lastDayKey = nextDayKey;
      }
    }

    const sender = message.sender || {};
    const username = sender.username || "Unknown";
    const emoji = sender.emoji ? String(sender.emoji).trim() : "";
    const avatarText = emoji || username.charAt(0).toUpperCase() || "?";
    const role = chatRoleLabel(sender.role);
    const classes = ["discord-message"];
    if (message.from_me) {
      classes.push("is-own");
    }
    if (message.mentions_me) {
      classes.push("is-mention");
    }
    const tags = (message.tags || [])
      .map((tag) => `<span class="pill chat-pill-tag">#${escapeHtml(tag)}</span>`)
      .join("");
    const mentions = (message.mentions || [])
      .map((item) => `<span class="pill chat-pill-mention">@${escapeHtml(item.username)}</span>`)
      .join("");
    const edited = message.edited_at ? '<span class="chat-edited">(edited)</span>' : "";
    const text = escapeHtml(message.message || "").replace(/\n/g, "<br />");
    const metadata = `${tags}${mentions}${edited}`;
    parts.push(`
      <article class="${classes.join(" ")}">
        <div class="chat-avatar${emoji ? "" : " is-fallback"}">${escapeHtml(avatarText)}</div>
        <div class="chat-bubble">
          <div class="chat-head-row">
            <strong class="chat-user">${escapeHtml(username)}</strong>
            <span class="chat-role-pill">${escapeHtml(role)}</span>
            <time class="chat-time" datetime="${escapeHtml(createdAt)}" title="${escapeHtml(formatLastSeen(createdAt))}">
              ${escapeHtml(formatChatClock(createdAt))}
            </time>
          </div>
          <p class="chat-message-body">${text}</p>
          ${metadata ? `<div class="chat-meta-row">${metadata}</div>` : ""}
        </div>
      </article>
    `);
  });

  officerChatList.innerHTML = parts.join("");
  if (keepPinnedToBottom || rows.length <= 12) {
    officerChatList.scrollTop = officerChatList.scrollHeight;
  }
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
  if (calendarFeedPreview && openGoogleSubscribeBtn) {
    calendarFeedPreview.textContent = data.feed_url || "Calendar URL unavailable.";
    openGoogleSubscribeBtn.href = data.google_subscribe_url || "#";
    openGoogleSubscribeBtn.classList.toggle("hidden", !data.google_subscribe_url);
  }
  if (rushCalendarFeedPreview) {
    rushCalendarFeedPreview.textContent = data.rush_feed_url || data.feed_url || "Rush calendar URL unavailable.";
  }
  if (openRushGoogleSubscribeBtn) {
    openRushGoogleSubscribeBtn.href = data.google_subscribe_url || "#";
    openRushGoogleSubscribeBtn.classList.toggle("hidden", !data.google_subscribe_url);
  }
  if (lunchOnlyFeedPreview) {
    lunchOnlyFeedPreview.textContent = data.lunch_feed_url || "Lunch feed URL unavailable.";
  }
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
  if (rushEventDate) {
    rushEventDate.value = today;
  }
  if (weeklyGoalWeekStart && weeklyGoalWeekEnd) {
    const now = new Date();
    const dayIndex = now.getDay();
    const mondayOffset = dayIndex === 0 ? -6 : 1 - dayIndex;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    weeklyGoalWeekStart.value = monday.toISOString().slice(0, 10);
    weeklyGoalWeekEnd.value = sunday.toISOString().slice(0, 10);
  }
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
      const ownDisplay = own ? `${own.total_score}/${RATING_TOTAL_MAX}` : "Not rated";
      const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const weightedPct = Math.max(0, Math.min(100, (Number(pnm.weighted_total) / RATING_TOTAL_MAX) * 100));
      const barWidth = Math.round((weightedPct / 100) * 58);
      const selectedClass = state.selectedPnmId === pnm.pnm_id ? "selected-row" : "";
      const categoryCells = RATING_CRITERIA.map((criterion) => {
        const avgField = PNM_AVG_FIELD_BY_RATING_FIELD[criterion.field];
        const value = Number(pnm[avgField] || 0);
        return `<td>${value.toFixed(2)}</td>`;
      }).join("");
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
          ${categoryCells}
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
          ${RATING_CRITERIA.map((criterion) => `<th>${escapeHtml(criterion.short_label)}</th>`).join("")}
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

  const canDisapproveUsers = roleCanApproveUsers();
  const rows = state.members
    .map((member) => {
      const avgRating = member.avg_rating_given == null ? "Hidden" : member.avg_rating_given.toFixed(2);
      const ratingCount = member.rating_count == null ? "Hidden" : member.rating_count;
      const canDisapprove =
        canDisapproveUsers &&
        state.user &&
        member.user_id !== state.user.user_id &&
        member.role !== "Head Rush Officer";
      const actionCell = canDisapprove
        ? `<button type="button" class="secondary disapprove-user" data-user-id="${member.user_id}" data-username="${escapeHtml(member.username)}">Disapprove</button>`
        : "-";
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
          <td>${actionCell}</td>
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
          <th>Actions</th>
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
  if (!roleCanApproveUsers()) {
    approvalsPanel.classList.add("hidden");
    return;
  }

  approvalsPanel.classList.remove("hidden");

  if (!data.pending.length) {
    pendingList.innerHTML = '<p class="muted">No pending requests.</p>';
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

function renderSeasonArchiveStatusPanel() {
  if (!seasonArchiveSummary || !seasonArchivePhrase || !seasonArchiveDownloadBtn) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    seasonArchiveSummary.innerHTML = '<p class="muted">Head Rush Officer access required.</p>';
    seasonArchiveDownloadBtn.classList.add("hidden");
    return;
  }
  const payload = state.seasonArchive;
  if (!payload) {
    seasonArchiveSummary.innerHTML = '<p class="muted">Loading season archive status...</p>';
    seasonArchiveDownloadBtn.classList.add("hidden");
    return;
  }

  const phrase = payload.confirmation_phrase || "RESET RUSH SEASON";
  seasonArchivePhrase.placeholder = `Type: ${phrase}`;

  const current = payload.current_counts || { pnm_count: 0, rating_count: 0, lunch_count: 0 };
  const archive = payload.archive || null;
  const archiveMeta = archive
    ? `
      <div class="entry">
        <div class="entry-title">
          <strong>Last Archive</strong>
          <span>${escapeHtml(archive.archive_label || "Season Archive")}</span>
        </div>
        <p class="muted">Created: ${escapeHtml(formatLastSeen(archive.archived_at))} by ${escapeHtml(archive.archived_by_username || "Unknown")}</p>
        <p class="muted">Archived counts: PNMs ${archive.pnm_count}, Ratings ${archive.rating_count}, Lunches ${archive.lunch_count}</p>
      </div>
    `
    : '<p class="muted">No archived season yet.</p>';

  seasonArchiveSummary.innerHTML = `
    <div class="entry">
      <div class="entry-title">
        <strong>Current Live Data</strong>
        <span>Before Reset</span>
      </div>
      <p class="muted">PNMs: ${current.pnm_count} | Ratings: ${current.rating_count} | Lunches: ${current.lunch_count}</p>
      <p class="muted">Confirmation phrase: <strong>${escapeHtml(phrase)}</strong></p>
    </div>
    ${archiveMeta}
  `;

  seasonArchiveDownloadBtn.classList.toggle("hidden", !payload.archive_download_path);
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
    renderSeasonArchiveStatusPanel();
    return;
  }

  adminPanel.classList.remove("hidden");
  renderHeadAdminSummary();
  renderCurrentHeadsList();
  renderPromotionControls();
  renderSeasonArchiveStatusPanel();
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
  const girlsMax = ratingCriteriaForField("good_with_girls")?.max || 10;
  const processMax = ratingCriteriaForField("will_make_it")?.max || 10;
  const personableMax = ratingCriteriaForField("personable")?.max || 10;
  const alcoholMax = ratingCriteriaForField("alcohol_control")?.max || 10;
  const igMax = ratingCriteriaForField("instagram_marketability")?.max || 5;
  document.getElementById("rateGirls").value = own ? Math.min(Number(own.good_with_girls || 0), girlsMax) : 0;
  document.getElementById("rateProcess").value = own ? Math.min(Number(own.will_make_it || 0), processMax) : 0;
  document.getElementById("ratePersonable").value = own ? Math.min(Number(own.personable || 0), personableMax) : 0;
  document.getElementById("rateAlcohol").value = own ? Math.min(Number(own.alcohol_control || 0), alcoholMax) : 0;
  document.getElementById("rateIg").value = own ? Math.min(Number(own.instagram_marketability || 0), igMax) : 0;
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
            <span>Score ${row.total_score}/${RATING_TOTAL_MAX} ${deltaMarkup}</span>
          </div>
          <div class="muted">${escapeHtml(formatScoreBreakdown(row))}</div>
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
        return `<li><strong>${who}</strong>: ${row.total_score}/${RATING_TOTAL_MAX}${delta}</li>`;
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
      <article class="card"><strong>Weighted Total</strong><p>${summary.weighted_total.toFixed(2)} / ${RATING_TOTAL_MAX}</p></article>
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
  renderWeeklyGoalAssignedUsers();
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
    if (rushCalendarFeedPreview) {
      rushCalendarFeedPreview.textContent = "Unable to load rush calendar link right now.";
    }
    if (lunchOnlyFeedPreview) {
      lunchOnlyFeedPreview.textContent = "Unable to load lunch feed link right now.";
    }
    if (openRushGoogleSubscribeBtn) {
      openRushGoogleSubscribeBtn.href = "#";
      openRushGoogleSubscribeBtn.classList.add("hidden");
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

async function loadRushCalendar() {
  try {
    const payload = await api("/api/rush-calendar?limit=600");
    state.rushCalendarItems = payload.items || [];
    state.rushCalendarStats = payload.stats || null;
    renderRushCalendar();
  } catch {
    state.rushCalendarItems = [];
    state.rushCalendarStats = null;
    if (rushCalendarTable) {
      rushCalendarTable.innerHTML = '<p class="muted">Unable to load rush calendar right now.</p>';
    }
    if (rushCalendarStats) {
      rushCalendarStats.innerHTML = '<p class="muted">Rush calendar metrics unavailable.</p>';
    }
  }
}

async function loadWeeklyGoals() {
  try {
    const payload = await api("/api/tasks/weekly");
    state.weeklyGoals = payload.goals || [];
    state.weeklyGoalSummary = payload.summary || null;
    state.weeklyGoalMetricOptions = payload.metric_options || [];
    renderWeeklyGoalMetricOptions();
    renderWeeklyGoals();
  } catch {
    state.weeklyGoals = [];
    state.weeklyGoalSummary = null;
    state.weeklyGoalMetricOptions = [];
    if (weeklyGoalsList) {
      weeklyGoalsList.innerHTML = '<p class="muted">Unable to load weekly goals right now.</p>';
    }
  }
}

async function loadNotifications() {
  try {
    const payload = await api("/api/notifications?limit=120");
    state.notifications = payload.notifications || [];
    state.unreadNotifications = Number(payload.unread_count || 0);
    renderNotifications();
  } catch {
    state.notifications = [];
    state.unreadNotifications = 0;
    if (notificationsList) {
      notificationsList.innerHTML = '<p class="muted">Unable to load notifications right now.</p>';
    }
    renderOperationsUnreadBadge();
  }
}

async function loadOfficerChat() {
  if (!roleCanManageOperations()) {
    state.officerChatMessages = [];
    renderOfficerChat();
    return;
  }
  try {
    const payload = await api("/api/chat/officer?limit=220");
    state.officerChatMessages = payload.messages || [];
    renderOfficerChat();
  } catch {
    state.officerChatMessages = [];
    if (officerChatList) {
      officerChatList.innerHTML = '<p class="muted">Unable to load officer chat right now.</p>';
    }
  }
}

async function loadOfficerChatStats() {
  if (!roleCanManageOperations()) {
    state.officerChatStats = null;
    renderOfficerChatStats();
    return;
  }
  try {
    const payload = await api("/api/chat/officer/stats");
    state.officerChatStats = payload;
    renderOfficerChatStats();
  } catch {
    state.officerChatStats = null;
    if (officerChatStats) {
      officerChatStats.innerHTML = '<p class="muted">Unable to load chat stats right now.</p>';
    }
  }
}

async function loadApprovals() {
  if (!roleCanApproveUsers()) {
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

async function loadSeasonArchiveStatus() {
  if (!roleCanUseAdminPanel()) {
    state.seasonArchive = null;
    renderSeasonArchiveStatusPanel();
    return;
  }
  try {
    const payload = await api("/api/admin/season/archive");
    state.seasonArchive = payload;
  } catch (error) {
    state.seasonArchive = {
      confirmation_phrase: "RESET RUSH SEASON",
      archive_download_path: null,
      archive: null,
      current_counts: { pnm_count: 0, rating_count: 0, lunch_count: 0 },
    };
    showToast(error.message || "Unable to load season archive status.");
  }
  renderSeasonArchiveStatusPanel();
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
    loadRushCalendar(),
    loadWeeklyGoals(),
    loadNotifications(),
    loadOfficerChat(),
    loadOfficerChatStats(),
    loadApprovals(),
    loadHeadAdminData(),
    loadSeasonArchiveStatus(),
  ]);
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    state.user = payload.user;
    if (shouldRedirectToMemberPortal(state.user)) {
      window.location.replace(APP_CONFIG.member_base);
      return;
    }
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

    if (shouldRedirectToMemberPortal(payload.user)) {
      window.location.href = APP_CONFIG.member_base;
      return;
    }

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
  state.rushCalendarItems = [];
  state.rushCalendarStats = null;
  state.weeklyGoals = [];
  state.weeklyGoalSummary = null;
  state.weeklyGoalMetricOptions = [];
  state.notifications = [];
  state.unreadNotifications = 0;
  state.officerChatMessages = [];
  state.officerChatStats = null;
  state.headAdmin = {
    summary: null,
    currentHeads: [],
    rushOfficers: [],
  };
  state.seasonArchive = null;
  state.adminEditPnmId = null;
  state.headAssignmentPnmId = null;
  animateCounter(heroPnmCount, 0);
  animateCounter(heroRatingCount, 0);
  animateCounter(heroLunchCount, 0);
  if (calendarFeedPreview) {
    calendarFeedPreview.textContent = "Sign in to load shared calendar link.";
  }
  if (rushCalendarFeedPreview) {
    rushCalendarFeedPreview.textContent = "Sign in to load rush calendar link.";
  }
  if (lunchOnlyFeedPreview) {
    lunchOnlyFeedPreview.textContent = "Sign in to load lunch feed link.";
  }
  if (scheduledLunchesList) {
    scheduledLunchesList.innerHTML = '<p class="muted">Sign in to view scheduled lunches.</p>';
  }
  if (rushCalendarTable) {
    rushCalendarTable.innerHTML = '<p class="muted">Sign in to view rush calendar items.</p>';
  }
  if (weeklyGoalsList) {
    weeklyGoalsList.innerHTML = '<p class="muted">Sign in to view weekly goals.</p>';
  }
  if (notificationsList) {
    notificationsList.innerHTML = '<p class="muted">Sign in to view notifications.</p>';
  }
  if (officerChatList) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>Sign in to view officer chat.</strong><p class="muted">Rush Officer accounts can access the live thread after login.</p></div>';
  }
  if (openGoogleSubscribeBtn) {
    openGoogleSubscribeBtn.href = "#";
    openGoogleSubscribeBtn.classList.add("hidden");
  }
  if (openRushGoogleSubscribeBtn) {
    openRushGoogleSubscribeBtn.href = "#";
    openRushGoogleSubscribeBtn.classList.add("hidden");
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
  if (seasonArchivePhrase) {
    seasonArchivePhrase.value = "";
  }
  if (seasonArchiveLabel) {
    seasonArchiveLabel.value = "";
  }
  if (seasonHeadChairConfirm) {
    seasonHeadChairConfirm.checked = false;
  }
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.classList.add("hidden");
  }
  renderOperationsUnreadBadge();
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
  const photoFile = pnmPhotoInput.files && pnmPhotoInput.files.length ? pnmPhotoInput.files[0] : null;
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
    auto_photo_from_instagram: !photoFile,
  };

  try {
    const payload = await api("/api/pnms", {
      method: "POST",
      body,
    });
    pnmForm.reset();
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

async function handleRefreshInstagramPhoto() {
  const selectedId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!selectedId) {
    showToast("Select a PNM first.");
    return;
  }
  if (!roleCanManagePhotos()) {
    showToast("Only Rush Officers and Head Rush Officer can refresh photos.");
    return;
  }

  if (refreshInstagramPhotoBtn) {
    refreshInstagramPhotoBtn.disabled = true;
    refreshInstagramPhotoBtn.textContent = "Refreshing...";
  }

  try {
    await api(`/api/pnms/${selectedId}/photo/refresh-instagram`, {
      method: "POST",
    });
    await loadPnms();
    await loadPnmDetail(selectedId);
    showToast("Instagram photo refreshed.");
  } catch (error) {
    showToast(error.message || "Unable to refresh from Instagram right now.");
  } finally {
    if (refreshInstagramPhotoBtn) {
      refreshInstagramPhotoBtn.disabled = false;
      refreshInstagramPhotoBtn.textContent = "Pull From Instagram";
    }
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
      showToast(`Rating increased to ${payload.change.new_total}/${RATING_TOTAL_MAX} (+${payload.change.delta_total}).`);
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

async function handleMemberTableClick(event) {
  const button = event.target.closest("button.disapprove-user");
  if (!button) {
    return;
  }

  const userId = Number(button.dataset.userId || 0);
  if (!userId) {
    return;
  }
  const username = button.dataset.username || "this user";
  const confirmed = window.confirm(`Disapprove ${username}? They will be moved back to pending and signed out.`);
  if (!confirmed) {
    return;
  }

  try {
    await api(`/api/users/${userId}/disapprove`, {
      method: "POST",
    });
    showToast("User disapproved.");
    await Promise.all([loadApprovals(), loadMembers(), loadMatching(), loadHeadAdminData()]);
  } catch (error) {
    showToast(error.message || "Unable to disapprove user.");
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

async function handleSeasonArchiveDownload() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const downloadPath = (state.seasonArchive && state.seasonArchive.archive_download_path) || "/api/admin/season/archive/download";
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.disabled = true;
    seasonArchiveDownloadBtn.textContent = "Preparing...";
  }
  try {
    await downloadFile(downloadPath, "rush-season-archive.sqlite");
    showToast("Season archive downloaded.");
  } catch (error) {
    showToast(error.message || "Unable to download season archive.");
  } finally {
    if (seasonArchiveDownloadBtn) {
      seasonArchiveDownloadBtn.disabled = false;
      seasonArchiveDownloadBtn.textContent = "Download Archived Season";
    }
  }
}

async function handleSeasonReset() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const expectedPhrase = (state.seasonArchive && state.seasonArchive.confirmation_phrase) || "RESET RUSH SEASON";
  const typedPhrase = seasonArchivePhrase ? seasonArchivePhrase.value.trim() : "";
  if (!typedPhrase) {
    showToast(`Type the confirmation phrase: ${expectedPhrase}`);
    return;
  }
  if (typedPhrase.toUpperCase() !== expectedPhrase.toUpperCase()) {
    showToast(`Phrase mismatch. Type exactly: ${expectedPhrase}`);
    return;
  }
  if (!seasonHeadChairConfirm || !seasonHeadChairConfirm.checked) {
    showToast("Confirm that all head rush chairs approved before resetting.");
    return;
  }
  const confirmed = window.confirm(
    "Archive the current rush season and reset PNMs, ratings, lunches, and participation counters for next season?"
  );
  if (!confirmed) {
    return;
  }

  if (seasonResetBtn) {
    seasonResetBtn.disabled = true;
    seasonResetBtn.textContent = "Archiving...";
  }
  try {
    const payload = await api("/api/admin/season/reset", {
      method: "POST",
      body: {
        confirm_phrase: typedPhrase,
        archive_label: seasonArchiveLabel && seasonArchiveLabel.value.trim() ? seasonArchiveLabel.value.trim() : null,
        head_chair_confirmation: true,
      },
    });
    if (seasonArchivePhrase) {
      seasonArchivePhrase.value = "";
    }
    if (seasonArchiveLabel) {
      seasonArchiveLabel.value = "";
    }
    if (seasonHeadChairConfirm) {
      seasonHeadChairConfirm.checked = false;
    }
    showToast(payload.message || "Season reset completed.");
    await refreshAll();
    setActiveDesktopPage("admin", false);
  } catch (error) {
    showToast(error.message || "Unable to reset rush season.");
  } finally {
    if (seasonResetBtn) {
      seasonResetBtn.disabled = false;
      seasonResetBtn.textContent = "Archive + Reset Season";
    }
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

async function copyTextToClipboard(value) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const input = document.createElement("input");
  input.value = value;
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

async function handleCopyCalendarFeed() {
  if (!state.calendarShare || !state.calendarShare.feed_url) {
    showToast("Shared calendar link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(state.calendarShare.feed_url);
    showToast("Shared calendar URL copied.");
  } catch {
    showToast("Unable to copy URL. Use the link shown below the button.");
  }
}

async function handleCopyRushCalendarFeed() {
  const value = state.calendarShare && (state.calendarShare.rush_feed_url || state.calendarShare.feed_url);
  if (!value) {
    showToast("Rush calendar link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(value);
    showToast("Rush calendar URL copied.");
  } catch {
    showToast("Unable to copy rush feed URL right now.");
  }
}

async function handleCopyLunchOnlyFeed() {
  const value = state.calendarShare && state.calendarShare.lunch_feed_url;
  if (!value) {
    showToast("Lunch-only feed link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(value);
    showToast("Lunch-only calendar URL copied.");
  } catch {
    showToast("Unable to copy lunch feed URL right now.");
  }
}

async function handleRushEventCreate(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const body = {
    title: rushEventTitle ? rushEventTitle.value.trim() : "",
    event_type: rushEventType ? rushEventType.value : "official",
    event_date: rushEventDate ? rushEventDate.value : "",
    start_time: rushEventStartTime && rushEventStartTime.value ? rushEventStartTime.value : null,
    end_time: rushEventEndTime && rushEventEndTime.value ? rushEventEndTime.value : null,
    location: rushEventLocation ? rushEventLocation.value.trim() : "",
    details: rushEventDetails ? rushEventDetails.value.trim() : "",
    is_official: rushEventOfficial ? Boolean(rushEventOfficial.checked) : true,
  };
  if (!body.title || !body.event_date) {
    showToast("Event title and date are required.");
    return;
  }
  const submitBtn = document.getElementById("rushEventSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
  }
  try {
    await api("/api/rush-events", { method: "POST", body });
    if (rushEventForm) {
      rushEventForm.reset();
    }
    setDefaultDates();
    if (rushEventOfficial) {
      rushEventOfficial.checked = true;
    }
    showToast("Rush event created.");
    await Promise.all([loadRushCalendar(), loadCalendarShare(), loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to create rush event.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Event";
    }
  }
}

async function handleRushCalendarTableClick(event) {
  const removeBtn = event.target.closest("[data-rush-event-delete]");
  if (!removeBtn) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const eventId = Number(removeBtn.dataset.rushEventDelete || 0);
  if (!eventId) {
    return;
  }
  const confirmed = window.confirm("Remove this rush event from the calendar?");
  if (!confirmed) {
    return;
  }
  removeBtn.disabled = true;
  try {
    await api(`/api/rush-events/${eventId}`, { method: "DELETE" });
    showToast("Rush event removed.");
    await Promise.all([loadRushCalendar(), loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to remove rush event.");
  } finally {
    removeBtn.disabled = false;
  }
}

async function handleWeeklyGoalCreate(event) {
  event.preventDefault();
  if (!roleCanManageOperations()) {
    showToast("Rush Officer access required.");
    return;
  }
  const body = {
    title: weeklyGoalTitle ? weeklyGoalTitle.value.trim() : "",
    description: weeklyGoalDescription ? weeklyGoalDescription.value.trim() : "",
    metric_type: weeklyGoalMetric ? weeklyGoalMetric.value : "manual",
    target_count: weeklyGoalTarget ? Number(weeklyGoalTarget.value || 0) : 0,
    week_start: weeklyGoalWeekStart && weeklyGoalWeekStart.value ? weeklyGoalWeekStart.value : null,
    week_end: weeklyGoalWeekEnd && weeklyGoalWeekEnd.value ? weeklyGoalWeekEnd.value : null,
    assigned_user_id: weeklyGoalAssignedUser && weeklyGoalAssignedUser.value ? Number(weeklyGoalAssignedUser.value) : null,
  };
  if (!body.title || !body.target_count) {
    showToast("Goal title and target are required.");
    return;
  }
  const submitBtn = document.getElementById("weeklyGoalSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
  }
  try {
    await api("/api/tasks/weekly", { method: "POST", body });
    if (weeklyGoalForm) {
      weeklyGoalForm.reset();
    }
    setDefaultDates();
    renderWeeklyGoalMetricOptions();
    renderWeeklyGoalAssignedUsers();
    showToast("Weekly goal created.");
    await Promise.all([loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to create weekly goal.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Goal";
    }
  }
}

async function handleWeeklyGoalsActionClick(event) {
  const progressBtn = event.target.closest("[data-goal-progress]");
  if (progressBtn) {
    const goalId = Number(progressBtn.dataset.goalProgress || 0);
    if (!goalId) {
      return;
    }
    progressBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}/progress`, {
        method: "POST",
        body: { delta: 1 },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast("Goal progress updated.");
    } catch (error) {
      showToast(error.message || "Unable to update goal progress.");
    } finally {
      progressBtn.disabled = false;
    }
    return;
  }

  const completeBtn = event.target.closest("[data-goal-complete]");
  if (completeBtn) {
    const goalId = Number(completeBtn.dataset.goalComplete || 0);
    if (!goalId) {
      return;
    }
    completeBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}`, {
        method: "PATCH",
        body: { complete_now: true },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast("Goal marked complete.");
    } catch (error) {
      showToast(error.message || "Unable to mark goal complete.");
    } finally {
      completeBtn.disabled = false;
    }
    return;
  }

  const archiveBtn = event.target.closest("[data-goal-archive]");
  if (archiveBtn) {
    const goalId = Number(archiveBtn.dataset.goalArchive || 0);
    if (!goalId) {
      return;
    }
    const archived = archiveBtn.dataset.goalArchived === "1";
    archiveBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}`, {
        method: "PATCH",
        body: { is_archived: !archived },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast(archived ? "Goal unarchived." : "Goal archived.");
    } catch (error) {
      showToast(error.message || "Unable to update goal archive state.");
    } finally {
      archiveBtn.disabled = false;
    }
  }
}

async function handleNotificationListClick(event) {
  const btn = event.target.closest("[data-notification-read]");
  if (!btn) {
    return;
  }
  const notificationId = Number(btn.dataset.notificationRead || 0);
  if (!notificationId) {
    return;
  }
  btn.disabled = true;
  try {
    await api(`/api/notifications/${notificationId}/read`, { method: "POST" });
    await loadNotifications();
  } catch (error) {
    showToast(error.message || "Unable to mark notification read.");
  } finally {
    btn.disabled = false;
  }
}

async function handleNotificationsReadAll() {
  if (!state.unreadNotifications) {
    return;
  }
  notificationsReadAllBtn.disabled = true;
  try {
    await api("/api/notifications/read-all", { method: "POST" });
    await loadNotifications();
    showToast("All notifications marked read.");
  } catch (error) {
    showToast(error.message || "Unable to mark notifications read.");
  } finally {
    notificationsReadAllBtn.disabled = false;
  }
}

function sanitizeChatTagToken(raw) {
  return String(raw || "")
    .trim()
    .replace(/^#+/, "")
    .replace(/[^a-zA-Z0-9_-]/g, "");
}

function appendQuickChatTag(rawTag) {
  if (!officerChatTags) {
    return;
  }
  const tag = sanitizeChatTagToken(rawTag);
  if (!tag) {
    return;
  }
  const tokens = parseTagInput(officerChatTags.value).map(sanitizeChatTagToken).filter(Boolean);
  tokens.push(tag);
  officerChatTags.value = uniqueNormalized(tokens).join(", ");
}

function handleOfficerChatQuickTagClick(event) {
  const button = event.target.closest("[data-chat-quick-tag]");
  if (!button) {
    return;
  }
  const tag = button.dataset.chatQuickTag || "";
  appendQuickChatTag(tag);
  button.classList.add("is-selected");
  clearTimeout(button._flashTimer);
  button._flashTimer = setTimeout(() => button.classList.remove("is-selected"), 520);
  if (officerChatMessage) {
    officerChatMessage.focus();
  }
}

function handleOfficerChatMessageKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  if (!officerChatForm) {
    return;
  }
  if (typeof officerChatForm.requestSubmit === "function") {
    officerChatForm.requestSubmit();
    return;
  }
  officerChatForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

async function handleOfficerChatSubmit(event) {
  event.preventDefault();
  if (!roleCanManageOperations()) {
    showToast("Rush Officer access required.");
    return;
  }
  const message = officerChatMessage ? officerChatMessage.value.trim() : "";
  const tags = officerChatTags ? officerChatTags.value.trim() : "";
  if (!message) {
    showToast("Enter a chat message first.");
    return;
  }
  const submitBtn = document.getElementById("officerChatSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending...";
  }
  try {
    await api("/api/chat/officer", {
      method: "POST",
      body: { message, tags: tags || null },
    });
    if (officerChatForm) {
      officerChatForm.reset();
    }
    if (officerChatMessage) {
      officerChatMessage.focus();
    }
    await Promise.all([loadOfficerChat(), loadOfficerChatStats(), loadWeeklyGoals(), loadNotifications()]);
    showToast("Message sent.");
  } catch (error) {
    showToast(error.message || "Unable to send chat message.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Send Message";
    }
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
  if (seasonResetBtn) {
    seasonResetBtn.addEventListener("click", handleSeasonReset);
  }
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.addEventListener("click", handleSeasonArchiveDownload);
  }
  if (googleImportForm) {
    googleImportForm.addEventListener("submit", handleGoogleImport);
  }
  if (downloadGoogleImportTemplateBtn) {
    downloadGoogleImportTemplateBtn.addEventListener("click", handleDownloadGoogleImportTemplate);
  }
  if (copyCalendarFeedBtn) {
    copyCalendarFeedBtn.addEventListener("click", handleCopyCalendarFeed);
  }
  if (copyRushCalendarFeedBtn) {
    copyRushCalendarFeedBtn.addEventListener("click", handleCopyRushCalendarFeed);
  }
  if (copyLunchOnlyFeedBtn) {
    copyLunchOnlyFeedBtn.addEventListener("click", handleCopyLunchOnlyFeed);
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
  if (rushEventForm) {
    rushEventForm.addEventListener("submit", handleRushEventCreate);
  }
  if (rushCalendarTable) {
    rushCalendarTable.addEventListener("click", handleRushCalendarTableClick);
  }
  if (weeklyGoalForm) {
    weeklyGoalForm.addEventListener("submit", handleWeeklyGoalCreate);
  }
  if (weeklyGoalsList) {
    weeklyGoalsList.addEventListener("click", handleWeeklyGoalsActionClick);
  }
  if (notificationsList) {
    notificationsList.addEventListener("click", handleNotificationListClick);
  }
  if (notificationsReadAllBtn) {
    notificationsReadAllBtn.addEventListener("click", handleNotificationsReadAll);
  }
  if (officerChatForm) {
    officerChatForm.addEventListener("submit", handleOfficerChatSubmit);
  }
  if (officerChatQuickTags) {
    officerChatQuickTags.addEventListener("click", handleOfficerChatQuickTagClick);
  }
  if (officerChatMessage) {
    officerChatMessage.addEventListener("keydown", handleOfficerChatMessageKeydown);
  }
  if (refreshInstagramPhotoBtn) {
    refreshInstagramPhotoBtn.addEventListener("click", handleRefreshInstagramPhoto);
  }

  pnmTable.addEventListener("click", handlePnmTableClick);
  pendingList.addEventListener("click", handlePendingClick);
  memberTable.addEventListener("click", handleMemberTableClick);
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
  applyRatingCriteriaUi();
  setRoleEmojiRequirement();
  initializePresetTagPickers();
  attachEvents();
  setActiveDesktopPage(currentRequestedDesktopPage(), false);
  updateTopbarActions();
  renderWeeklyGoalMetricOptions();
  renderWeeklyGoalAssignedUsers();
  renderWeeklyGoals();
  renderNotifications();
  renderOfficerChat();
  renderOfficerChatStats();
  renderRushCalendar();
  setupPwaInstall();
  await ensureSession();
}

init();
