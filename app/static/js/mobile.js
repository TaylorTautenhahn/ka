function readAppConfig() {
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
const BASE_PATH = (APP_CONFIG.base_path || "").replace(/\/$/, "");
const API_BASE = (APP_CONFIG.api_base || "/api").replace(/\/$/, "");
const MOBILE_BASE = (APP_CONFIG.mobile_base || `${BASE_PATH}/mobile`).replace(/\/$/, "");
const MOBILE_ROUTES = {
  dashboard: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.dashboard ? APP_CONFIG.mobile_routes.dashboard : MOBILE_BASE,
  rushees: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.rushees ? APP_CONFIG.mobile_routes.rushees : `${MOBILE_BASE}/pnms`,
  team: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.team ? APP_CONFIG.mobile_routes.team : `${MOBILE_BASE}/members`,
  calendar: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.calendar ? APP_CONFIG.mobile_routes.calendar : `${MOBILE_BASE}/calendar`,
  admin: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.admin ? APP_CONFIG.mobile_routes.admin : `${MOBILE_BASE}/admin`,
  create: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.create ? APP_CONFIG.mobile_routes.create : `${MOBILE_BASE}/create`,
  meeting: APP_CONFIG.mobile_routes && APP_CONFIG.mobile_routes.meeting ? APP_CONFIG.mobile_routes.meeting : `${MOBILE_BASE}/meeting`,
};
const MOBILE_PAGE = (document.body && document.body.dataset.mobilePage) || "";
const BASE_DEFAULT_INTEREST_TAGS = [
  "Leadership",
  "Academics",
  "Career",
  "Community",
  "Culture",
  "Service",
  "Sports",
  "Fitness",
  "Finance",
  "Business",
  "Outdoors",
  "Music",
  "Technology",
  "Wellness",
  "Faith",
  "Philanthropy",
  "Gaming",
  "Travel",
  "Food",
  "Fashion",
  "Entrepreneurship",
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
const ROLE_HEAD = "Head Rush Officer";
const ROLE_RUSH_OFFICER = "Rush Officer";
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

function debounce(callback, wait = 220) {
  let timer = null;
  return (...args) => {
    if (timer) {
      window.clearTimeout(timer);
    }
    timer = window.setTimeout(() => {
      callback(...args);
    }, wait);
  };
}

function normalizeStateCodeToken(value) {
  const token = String(value || "").trim().toUpperCase();
  return /^[A-Z]{2}$/.test(token) ? token : "";
}

function parseStateOptions(raw) {
  if (!Array.isArray(raw)) {
    return [];
  }
  const out = [];
  const seen = new Set();
  raw.forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const code = normalizeStateCodeToken(item.code);
    const name = toTitleCase(item.name || "");
    if (!code || !name || seen.has(code)) {
      return;
    }
    seen.add(code);
    out.push({ code, name });
  });
  return out;
}

const DEFAULT_INTEREST_TAGS = parseConfiguredTagList(APP_CONFIG.default_interest_tags, BASE_DEFAULT_INTEREST_TAGS);
const DEFAULT_STEREOTYPE_TAGS = parseConfiguredTagList(
  APP_CONFIG.default_stereotype_tags,
  BASE_DEFAULT_STEREOTYPE_TAGS
);
const RATING_CRITERIA = parseRatingCriteria(APP_CONFIG.rating_criteria);
const RATING_CRITERIA_BY_FIELD = new Map(RATING_CRITERIA.map((item) => [item.field, item]));
const RATING_TOTAL_MAX =
  Number.isFinite(Number(APP_CONFIG.rating_total_max)) && Number(APP_CONFIG.rating_total_max) > 0
    ? Number(APP_CONFIG.rating_total_max)
    : RATING_CRITERIA.reduce((sum, item) => sum + Number(item.max || 0), 0);
const STATE_OPTIONS = parseStateOptions(APP_CONFIG.state_options);
const mobileStateHints = document.getElementById("mobileStateHints");
const mobilePnmStateHints = document.getElementById("mobilePnmStateHints");
const mobileMemberStateHints = document.getElementById("mobileMemberStateHints");

const toastEl = document.getElementById("mobileToast");
let mobileCalendarShare = null;
let mobilePnmRows = [];
let mobileMemberRows = [];
let mobileCurrentUser = null;
let mobileSelectedManagePnmId = null;
const mobileContactDownloads = new Map();
let mobileSelectedContactPnmId = null;
let mobilePackagePrimaryPnmId = null;
let mobilePackagePartnerPnmId = null;
let mobileSelectedTeamMemberId = null;
const mobileCommandCenter = {
  queue: [],
  staleAlerts: [],
  recentChanges: [],
  summary: null,
  selectedPnmId: null,
  windowHours: 72,
  limit: 30,
  error: "",
};
let mobileHomePnmRows = [];
let mobileHomeRecentLunchRows = [];
let mobileHomeSelectedPnmId = null;
const mobileFilters = {
  pnms: {
    state: "",
  },
  members: {
    role: "all",
    state: "",
    city: "",
    sort: "location",
  },
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
  if (!toastEl) {
    return;
  }
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toastEl.classList.add("hidden"), 2500);
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

function mobileCanUseCommandCenter() {
  return Boolean(
    mobileCurrentUser &&
      (mobileCurrentUser.role === ROLE_HEAD || mobileCurrentUser.role === ROLE_RUSH_OFFICER)
  );
}

function contactDownloadedAt(pnmId) {
  const normalized = Number(pnmId || 0);
  if (!normalized) {
    return null;
  }
  return mobileContactDownloads.get(normalized) || null;
}

function isContactDownloaded(pnmId) {
  return Boolean(contactDownloadedAt(pnmId));
}

function setContactDownloadStatus(pnmId, downloadedAt) {
  const normalized = Number(pnmId || 0);
  if (!normalized) {
    return;
  }
  const stamp = String(downloadedAt || "").trim();
  if (!stamp) {
    mobileContactDownloads.delete(normalized);
    return;
  }
  mobileContactDownloads.set(normalized, stamp);
}

function formatDownloadStamp(value) {
  if (!value) {
    return "Not downloaded yet";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function normalizePackageGroupId(value) {
  const token = String(value || "").trim();
  return token || "";
}

function packageGroupLabel(groupId) {
  const token = normalizePackageGroupId(groupId);
  if (!token) {
    return "Solo";
  }
  const raw = token.startsWith("pkg_") ? token.slice(4) : token;
  return `PKG-${raw.slice(0, 6).toUpperCase()}`;
}

function mobilePackageInfoForPnm(pnm) {
  if (!pnm) {
    return { id: "", label: "Solo", count: 1, members: [] };
  }
  const groupId = normalizePackageGroupId(pnm.package_group_id);
  if (!groupId) {
    return { id: "", label: "Solo", count: 1, members: [pnm] };
  }
  const members = mobilePnmRows.filter((item) => normalizePackageGroupId(item.package_group_id) === groupId);
  const label = String(pnm.package_group_label || "").trim() || packageGroupLabel(groupId);
  return {
    id: groupId,
    label,
    count: members.length || 1,
    members: members.length ? members : [pnm],
  };
}

function contactSelectDisplayName(pnm) {
  const downloaded = isContactDownloaded(pnm.pnm_id) ? " ✓" : "";
  return `${pnm.first_name} ${pnm.last_name} (${pnm.pnm_code})${downloaded}`;
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

function renderMobileStateHints(options) {
  const hintTargets = [mobileStateHints, mobilePnmStateHints, mobileMemberStateHints].filter(Boolean);
  if (!hintTargets.length) {
    return;
  }
  const rows = [];
  const seen = new Set();
  (options || []).forEach((entry) => {
    const code = normalizeStateCodeToken(entry && entry.code);
    const name = toTitleCase(entry && entry.name ? entry.name : "");
    if (!code || !name) {
      return;
    }
    const keyCode = `code:${code}`;
    if (!seen.has(keyCode)) {
      rows.push(`<option value="${escapeHtml(code)}">${escapeHtml(name)}</option>`);
      seen.add(keyCode);
    }
    const keyName = `name:${name.toLowerCase()}`;
    if (!seen.has(keyName)) {
      rows.push(`<option value="${escapeHtml(name)}">${escapeHtml(code)}</option>`);
      seen.add(keyName);
    }
  });
  const markup = rows.join("");
  hintTargets.forEach((target) => {
    target.innerHTML = markup;
  });
}

function normalizeStateFilterInput(value) {
  const token = String(value || "").trim();
  if (!token) {
    return "";
  }
  const directCode = normalizeStateCodeToken(token);
  if (directCode) {
    return directCode;
  }
  const byName = STATE_OPTIONS.find((entry) => entry.name.toLowerCase() === token.toLowerCase());
  if (byName) {
    return byName.code;
  }
  return "";
}

function buildQueryString(params) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, rawValue]) => {
    const value = String(rawValue || "").trim();
    if (!value) {
      return;
    }
    query.set(key, value);
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
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
  input.readOnly = true;
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
  input.readOnly = true;
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

function initializeMobileTagPickers() {
  bindInterestPicker("mobilePnmInterests", "mobileInterestTags");
  bindStereotypePicker("mobilePnmStereotype", "mobileStereotypeTags");
  bindInterestPicker("mobileManageInterests", "mobileManageInterestTags");
  bindStereotypePicker("mobileManageStereotype", "mobileManageStereotypeTags");
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
  const isFormData = options.body instanceof FormData;
  const method = String(options.method || "GET").toUpperCase();
  const headers = csrfHeadersForMethod(
    method,
    isFormData
      ? { ...(options.headers || {}) }
      : {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        }
  );
  const response = await fetch(resolveApiPath(path), {
    method,
    credentials: "same-origin",
    headers,
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

function fileNameFromDisposition(value, fallback) {
  const source = String(value || "");
  if (!source) {
    return fallback;
  }
  const utfMatch = source.match(/filename\\*=UTF-8''([^;]+)/i);
  if (utfMatch && utfMatch[1]) {
    try {
      return decodeURIComponent(utfMatch[1].replace(/['"]/g, "")).trim() || fallback;
    } catch {
      return fallback;
    }
  }
  const plainMatch = source.match(/filename=\"?([^\";]+)\"?/i);
  if (!plainMatch || !plainMatch[1]) {
    return fallback;
  }
  return plainMatch[1].trim() || fallback;
}

async function loadContactDownloadStatuses() {
  const payload = await api("/api/export/contacts/status");
  mobileContactDownloads.clear();
  const rows = Array.isArray(payload.downloads) ? payload.downloads : [];
  rows.forEach((row) => {
    if (!row) {
      return;
    }
    setContactDownloadStatus(row.pnm_id, row.downloaded_at);
  });
}

function renderContactsPanel() {
  const select = document.getElementById("mobileContactPnmSelect");
  const progress = document.getElementById("mobileContactProgress");
  const statusList = document.getElementById("mobileContactStatusList");
  if (!select || !progress || !statusList) {
    return;
  }

  if (!mobilePnmRows.length) {
    select.innerHTML = '<option value="">No rushees available</option>';
    select.disabled = true;
    progress.textContent = "No contacts available to download yet.";
    statusList.innerHTML = '<p class="muted">Add rushees to start building contact exports.</p>';
    return;
  }

  const availableIds = new Set(mobilePnmRows.map((pnm) => Number(pnm.pnm_id)));
  if (!mobileSelectedContactPnmId || !availableIds.has(Number(mobileSelectedContactPnmId))) {
    mobileSelectedContactPnmId = Number(mobilePnmRows[0].pnm_id);
  }

  select.disabled = false;
  select.innerHTML = mobilePnmRows
    .map(
      (pnm) =>
        `<option value="${pnm.pnm_id}"${Number(pnm.pnm_id) === Number(mobileSelectedContactPnmId) ? " selected" : ""}>${escapeHtml(
          contactSelectDisplayName(pnm)
        )}</option>`
    )
    .join("");

  const downloadedCount = mobilePnmRows.filter((pnm) => isContactDownloaded(pnm.pnm_id)).length;
  progress.textContent = `Downloaded ${downloadedCount} of ${mobilePnmRows.length} rushee contacts for this account.`;

  statusList.classList.add("contact-status-list");
  statusList.innerHTML = mobilePnmRows
    .map((pnm) => {
      const downloadedAt = contactDownloadedAt(pnm.pnm_id);
      const checkClass = downloadedAt ? "contact-check is-downloaded" : "contact-check";
      const checkLabel = downloadedAt ? "✓ Downloaded" : "○ Pending";
      return `
        <article class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span class="${checkClass}">${checkLabel}</span>
          </div>
          <p class="muted">${escapeHtml(pnm.pnm_code)} | ${escapeHtml(formatDownloadStamp(downloadedAt))}</p>
        </article>
      `;
    })
    .join("");
}

function sortedMobilePnms() {
  return [...mobilePnmRows].sort((a, b) => {
    const left = `${a.last_name || ""} ${a.first_name || ""}`.trim();
    const right = `${b.last_name || ""} ${b.first_name || ""}`.trim();
    return left.localeCompare(right);
  });
}

function renderMobilePackageControls() {
  const primarySelect = document.getElementById("mobilePackagePrimarySelect");
  const partnerSelect = document.getElementById("mobilePackagePartnerSelect");
  const summary = document.getElementById("mobilePackageSummary");
  const linkButton = document.getElementById("mobilePackageLinkBtn");
  const unlinkButton = document.getElementById("mobilePackageUnlinkBtn");
  if (!primarySelect || !partnerSelect || !summary || !linkButton || !unlinkButton) {
    return;
  }

  const rows = sortedMobilePnms();
  if (!rows.length) {
    primarySelect.innerHTML = '<option value="">No rushees available</option>';
    partnerSelect.innerHTML = '<option value="">No partner available</option>';
    primarySelect.disabled = true;
    partnerSelect.disabled = true;
    linkButton.disabled = true;
    unlinkButton.disabled = true;
    summary.textContent = "No package deal selected.";
    mobilePackagePrimaryPnmId = null;
    mobilePackagePartnerPnmId = null;
    return;
  }

  const availableIds = new Set(rows.map((pnm) => Number(pnm.pnm_id)));
  if (!mobilePackagePrimaryPnmId || !availableIds.has(Number(mobilePackagePrimaryPnmId))) {
    mobilePackagePrimaryPnmId = Number(rows[0].pnm_id);
  }

  primarySelect.disabled = false;
  primarySelect.innerHTML = rows
    .map((pnm) => {
      const packageInfo = mobilePackageInfoForPnm(pnm);
      const marker = packageInfo.id ? ` (${packageInfo.label})` : "";
      const selected = Number(pnm.pnm_id) === Number(mobilePackagePrimaryPnmId) ? " selected" : "";
      return `<option value="${pnm.pnm_id}"${selected}>${escapeHtml(
        `${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}${marker}`
      )}</option>`;
    })
    .join("");

  const selectedPrimary = rows.find((pnm) => Number(pnm.pnm_id) === Number(mobilePackagePrimaryPnmId)) || rows[0];
  if (selectedPrimary) {
    mobilePackagePrimaryPnmId = Number(selectedPrimary.pnm_id);
  }

  const partnerRows = rows.filter((pnm) => Number(pnm.pnm_id) !== Number(mobilePackagePrimaryPnmId));
  const partnerIds = new Set(partnerRows.map((pnm) => Number(pnm.pnm_id)));
  if (!mobilePackagePartnerPnmId || !partnerIds.has(Number(mobilePackagePartnerPnmId))) {
    mobilePackagePartnerPnmId = partnerRows.length ? Number(partnerRows[0].pnm_id) : null;
  }

  if (!partnerRows.length) {
    partnerSelect.innerHTML = '<option value="">Add another rushee to link package deals</option>';
    partnerSelect.disabled = true;
    linkButton.disabled = true;
  } else {
    partnerSelect.disabled = false;
    partnerSelect.innerHTML = partnerRows
      .map((pnm) => {
        const packageInfo = mobilePackageInfoForPnm(pnm);
        const marker = packageInfo.id ? ` (${packageInfo.label})` : "";
        const selected = Number(pnm.pnm_id) === Number(mobilePackagePartnerPnmId) ? " selected" : "";
        return `<option value="${pnm.pnm_id}"${selected}>${escapeHtml(
          `${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}${marker}`
        )}</option>`;
      })
      .join("");
    linkButton.disabled = !mobilePackagePartnerPnmId;
  }

  const packageInfo = mobilePackageInfoForPnm(selectedPrimary);
  if (!packageInfo.id) {
    summary.textContent = `No package deal linked for ${selectedPrimary.first_name} ${selectedPrimary.last_name}.`;
    unlinkButton.disabled = true;
    return;
  }
  const names = packageInfo.members.map((pnm) => `${pnm.first_name} ${pnm.last_name}`).join(", ");
  summary.textContent = `${packageInfo.label} includes ${packageInfo.count} rushees: ${names}.`;
  unlinkButton.disabled = false;
}

function updateContactsUi() {
  renderPnmCards(mobilePnmRows);
  renderContactsPanel();
  renderMobilePackageControls();
}

async function downloadContactsFile(button, apiPath, fallbackFileName) {
  if (!button) {
    return;
  }
  button.disabled = true;
  const originalLabel = button.textContent;
  button.textContent = "Preparing...";
  try {
    const response = await fetch(resolveApiPath(apiPath), {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "text/x-vcard,text/vcard,text/plain,*/*",
      },
    });
    if (!response.ok) {
      const contentType = response.headers.get("content-type") || "";
      let detail = "Unable to export contacts.";
      if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => ({}));
        detail = String(payload.detail || detail);
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    if (!blob || blob.size <= 0) {
      throw new Error("No contacts available yet.");
    }
    const disposition = response.headers.get("content-disposition") || "";
    const filename = fileNameFromDisposition(disposition, fallbackFileName);
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    showToast("Contacts export started.");
    return true;
  } catch (error) {
    showToast(error.message || "Unable to export contacts.");
    return false;
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

async function handleDownloadAllContacts(button) {
  const exported = await downloadContactsFile(
    button,
    "/api/export/contacts.vcf",
    `bidboard-contacts-${new Date().toISOString().slice(0, 10)}.vcf`
  );
  if (!exported) {
    return;
  }
  await loadContactDownloadStatuses();
  updateContactsUi();
}

async function handleDownloadSelectedContact(button) {
  const selectedId = Number(
    (document.getElementById("mobileContactPnmSelect") && document.getElementById("mobileContactPnmSelect").value) || 0
  );
  if (!selectedId) {
    showToast("Select a rushee first.");
    return;
  }
  const selectedPnm = mobilePnmRows.find((pnm) => Number(pnm.pnm_id) === selectedId);
  const safeCode = selectedPnm ? String(selectedPnm.pnm_code || "pnm").replace(/[^A-Za-z0-9_-]+/g, "-") : "pnm";
  const exported = await downloadContactsFile(
    button,
    `/api/export/contacts/${selectedId}.vcf`,
    `pnm-contact-${safeCode}.vcf`
  );
  if (!exported) {
    return;
  }
  await loadContactDownloadStatuses();
  updateContactsUi();
}

async function handleMobilePackageLink(button) {
  const primaryId = Number(
    (document.getElementById("mobilePackagePrimarySelect") && document.getElementById("mobilePackagePrimarySelect").value) || 0
  );
  const partnerId = Number(
    (document.getElementById("mobilePackagePartnerSelect") && document.getElementById("mobilePackagePartnerSelect").value) || 0
  );
  if (!primaryId) {
    showToast("Select a primary rushee first.");
    return;
  }
  if (!partnerId || primaryId === partnerId) {
    showToast("Select a different partner rushee.");
    return;
  }

  const primary = mobilePnmRows.find((pnm) => Number(pnm.pnm_id) === primaryId) || null;
  const partner = mobilePnmRows.find((pnm) => Number(pnm.pnm_id) === partnerId) || null;
  if (!primary || !partner) {
    showToast("Could not find selected rushees.");
    return;
  }
  const primaryGroupId = normalizePackageGroupId(primary.package_group_id);
  const partnerGroupId = normalizePackageGroupId(partner.package_group_id);
  if (primaryGroupId && primaryGroupId === partnerGroupId) {
    showToast("These rushees are already linked in the same package.");
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = "Linking...";
  }
  try {
    const payload = await api("/api/pnms/package/link", {
      method: "POST",
      body: {
        pnm_ids: [primaryId, partnerId],
        sync_assignment: mobileCurrentUser && mobileCurrentUser.role === "Head Rush Officer",
      },
    });
    mobilePackagePrimaryPnmId = primaryId;
    mobilePackagePartnerPnmId = partnerId;
    await loadPnmsPage();
    showToast(payload.message || "Package deal linked.");
  } catch (error) {
    showToast(error.message || "Unable to link package deal.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Link Package Deal";
    }
  }
}

async function handleMobilePackageUnlink(button) {
  const primaryId = Number(
    (document.getElementById("mobilePackagePrimarySelect") && document.getElementById("mobilePackagePrimarySelect").value) || 0
  );
  if (!primaryId) {
    showToast("Select a rushee first.");
    return;
  }
  if (button) {
    button.disabled = true;
    button.textContent = "Unlinking...";
  }
  try {
    const payload = await api(`/api/pnms/${primaryId}/package/unlink`, { method: "POST" });
    mobilePackagePrimaryPnmId = primaryId;
    mobilePackagePartnerPnmId = null;
    await loadPnmsPage();
    showToast(payload.message || "Package deal updated.");
  } catch (error) {
    showToast(error.message || "Unable to unlink package deal.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Unlink Primary";
    }
  }
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    mobileCurrentUser = payload && payload.authenticated && payload.user ? payload.user : null;
    if (!mobileCurrentUser) {
      window.location.href = BASE_PATH || "/";
      throw new Error("Not authenticated");
    }
  } catch {
    window.location.href = BASE_PATH || "/";
    throw new Error("Not authenticated");
  }
}

function renderMobileCalendarShare(data) {
  mobileCalendarShare = data;
  const mainSubscribeLinks = [
    document.getElementById("mobileGoogleSubscribeLink"),
    document.getElementById("mobileCalendarGoogleSubscribeLink"),
  ].filter(Boolean);
  mainSubscribeLinks.forEach((link) => {
    link.href = data.google_subscribe_url || "#";
    link.classList.toggle("hidden", !data.google_subscribe_url);
  });

  const lunchSubscribeLink = document.getElementById("mobileCalendarGoogleLunchSubscribeLink");
  if (lunchSubscribeLink) {
    lunchSubscribeLink.href = data.lunch_google_subscribe_url || "#";
    lunchSubscribeLink.classList.toggle("hidden", !data.lunch_google_subscribe_url);
  }

  const mainPreview = document.getElementById("mobileCalendarFeedPreview");
  if (mainPreview) {
    mainPreview.textContent = data.feed_url || "Calendar URL unavailable.";
  }

  const lunchPreview = document.getElementById("mobileCalendarLunchFeedPreview");
  if (lunchPreview) {
    lunchPreview.textContent = data.lunch_feed_url || "Touchpoint feed URL unavailable.";
  }
}

async function copyTextToClipboard(value, successMessage) {
  const token = String(value || "").trim();
  if (!token) {
    showToast("Nothing to copy.");
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(token);
    } else {
      const input = document.createElement("input");
      input.value = token;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      input.remove();
    }
    showToast(successMessage);
  } catch {
    showToast("Unable to copy URL.");
  }
}

async function handleMobileCopyCalendar() {
  if (!mobileCalendarShare || !mobileCalendarShare.feed_url) {
    showToast("Calendar URL is not ready yet.");
    return;
  }
  await copyTextToClipboard(mobileCalendarShare.feed_url, "Calendar URL copied.");
}

function renderHomeStats(stats) {
  const pnmCountEl = document.getElementById("mobilePnmCount");
  const ratingCountEl = document.getElementById("mobileRatingCount");
  const lunchCountEl = document.getElementById("mobileLunchCount");
  if (!pnmCountEl || !ratingCountEl || !lunchCountEl) {
    return;
  }
  pnmCountEl.textContent = String(Number(stats.pnm_count || 0));
  ratingCountEl.textContent = String(Number(stats.rating_count || 0));
  lunchCountEl.textContent = String(Number(stats.lunch_count || 0));
}

function mobileHomeSelectedPnm() {
  const selectedId = Number(mobileHomeSelectedPnmId || mobileCommandCenter.selectedPnmId || 0);
  if (!selectedId) {
    return null;
  }
  return (
    mobileHomePnmRows.find((item) => Number(item.pnm_id) === selectedId) ||
    mobileCommandCenter.queue.find((item) => Number(item.pnm_id) === selectedId) ||
    null
  );
}

function mobileHomeAssignedLabel(pnm) {
  if (!pnm) {
    return "Unassigned";
  }
  if (pnm.assigned_officer && pnm.assigned_officer.username) {
    return pnm.assigned_officer.username;
  }
  if (pnm.assigned_officer_username) {
    return pnm.assigned_officer_username;
  }
  const assignedTeam = Array.isArray(pnm.assigned_officers) ? pnm.assigned_officers : [];
  if (!assignedTeam.length) {
    return "Unassigned";
  }
  return assignedTeam
    .map((officer) => officer && officer.username ? officer.username : "Unknown")
    .join(", ");
}

function mobileHomeDisplayName(pnm) {
  if (!pnm) {
    return "Unknown Rushee";
  }
  if (pnm.name) {
    return String(pnm.name);
  }
  return `${String(pnm.first_name || "").trim()} ${String(pnm.last_name || "").trim()}`.trim() || String(pnm.pnm_code || "Unknown Rushee");
}

function mobileHomePhotoMarkup(pnm, className = "mobile-home-pnm-photo") {
  if (pnm && pnm.photo_url) {
    return `<img src="${escapeHtml(pnm.photo_url)}" class="${escapeHtml(className)}" alt="${escapeHtml(mobileHomeDisplayName(pnm))}" loading="lazy" />`;
  }
  const initials = String((pnm && (pnm.first_name || pnm.name || pnm.pnm_code) || "P").trim()).charAt(0).toUpperCase() || "P";
  return `<div class="${escapeHtml(className)} empty">${escapeHtml(initials)}</div>`;
}

function mobileHomeSearchRows() {
  const input = document.getElementById("mobileHomeSearchInput");
  const query = String(input && input.value ? input.value : "").trim().toLowerCase();
  if (!query) {
    return mobileHomePnmRows.slice(0, 12);
  }
  return mobileHomePnmRows.filter((pnm) => {
    const haystack = [
      pnm.pnm_code,
      pnm.first_name,
      pnm.last_name,
      pnm.hometown,
      pnm.hometown_state_code,
      pnm.instagram_handle,
      pnm.phone_number,
      Array.isArray(pnm.interests) ? pnm.interests.join(" ") : "",
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function renderMobileHomeSearchResults() {
  const listEl = document.getElementById("mobileHomeSearchResults");
  const metaEl = document.getElementById("mobileHomeSearchMeta");
  if (!listEl || !metaEl) {
    return;
  }
  const input = document.getElementById("mobileHomeSearchInput");
  const query = String(input && input.value ? input.value : "").trim();
  const rows = mobileHomeSearchRows();
  metaEl.textContent = query
    ? `${rows.length} match${rows.length === 1 ? "" : "es"} for "${query}"`
    : `Showing ${rows.length} quick results`;
  if (!rows.length) {
    listEl.innerHTML = '<p class="muted">No rushees match that search yet.</p>';
    return;
  }
  listEl.innerHTML = rows
    .map((pnm) => {
      const selectedClass = Number(mobileHomeSelectedPnmId) === Number(pnm.pnm_id) ? " is-selected" : "";
      const ownRating = pnm.own_rating && Number.isFinite(Number(pnm.own_rating.total_score))
        ? `Mine ${Number(pnm.own_rating.total_score).toFixed(0)}/${RATING_TOTAL_MAX}`
        : "Not rated";
      const touchpointCount = Number(pnm.total_lunches || 0);
      const touchpointLabel = touchpointCount === 1 ? "1 touchpoint" : `${touchpointCount} touchpoints`;
      return `
        <article class="entry mobile-card${selectedClass}">
          <button type="button" class="mobile-home-pnm-btn" data-mobile-home-pnm-id="${Number(pnm.pnm_id)}">
            ${mobileHomePhotoMarkup(pnm)}
            <div class="mobile-home-pnm-copy">
              <strong class="mobile-home-pnm-name">${escapeHtml(mobileHomeDisplayName(pnm))}</strong>
              <div class="mobile-home-pnm-meta">${escapeHtml(pnm.pnm_code)} • ${escapeHtml(ownRating)} • ${escapeHtml(touchpointLabel)}</div>
            </div>
            <div class="mobile-home-pnm-score">
              <strong>${formatWeightedScore(pnm.weighted_total)}</strong>
              ${ratingTierBadgeMarkup(pnm.weighted_total)}
            </div>
          </button>
        </article>
      `;
    })
    .join("");
}

function renderMobileHomeRecentLunches() {
  const listEl = document.getElementById("mobileHomeRecentLunches");
  const countEl = document.getElementById("mobileHomeRecentLunchCount");
  if (!listEl || !countEl) {
    return;
  }
  countEl.textContent = String(mobileHomeRecentLunchRows.length);
  if (!mobileHomeRecentLunchRows.length) {
    listEl.innerHTML = '<p class="muted">No touchpoint follow-up yet. Once you log touchpoints, they appear here for fast post-event rating updates.</p>';
    return;
  }
  listEl.innerHTML = mobileHomeRecentLunchRows
    .map((row) => {
      const selectedClass = Number(mobileHomeSelectedPnmId) === Number(row.pnm_id) ? " is-selected" : "";
      const timing = [row.last_lunch_date, row.start_time || "", row.location || ""].filter(Boolean).join(" • ");
      return `
        <article class="entry mobile-card${selectedClass}">
          <button type="button" class="mobile-home-pnm-btn" data-mobile-home-pnm-id="${Number(row.pnm_id)}">
            ${mobileHomePhotoMarkup(row)}
            <div class="mobile-home-pnm-copy">
              <strong class="mobile-home-pnm-name">${escapeHtml(row.name)}</strong>
              <div class="mobile-home-pnm-meta">${escapeHtml(row.pnm_code)} • ${escapeHtml(timing || "Recent touchpoint")}</div>
            </div>
            <div class="mobile-home-pnm-score">
              <strong>${formatWeightedScore(row.weighted_total)}</strong>
              ${ratingTierBadgeMarkup(row.weighted_total)}
            </div>
          </button>
        </article>
      `;
    })
    .join("");
}

function selectMobileHomePnm(pnmId, options = {}) {
  const targetId = Number(pnmId || 0);
  if (!targetId) {
    return;
  }
  mobileHomeSelectedPnmId = targetId;
  mobileCommandCenter.selectedPnmId = targetId;
  renderMobileHomeSearchResults();
  renderMobileHomeRecentLunches();
  renderMobileCommandSelection();
  if (options.scrollToForm) {
    const panel = document.getElementById("mobileHomeQuickRatePanel");
    if (panel) {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
}

function renderHomeLeaderboard(rows) {
  const listEl = document.getElementById("mobileLeaderboard");
  if (!listEl) {
    return;
  }
  if (!rows.length) {
    listEl.innerHTML = '<p class="muted">No ranked rushees yet.</p>';
    return;
  }
  listEl.innerHTML = rows
    .slice(0, 10)
    .map((entry) => {
      const assigned = entry.assigned_officer_username || "Unassigned";
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>#${entry.rank} ${escapeHtml(entry.pnm_code)} | ${escapeHtml(entry.name)}</strong>
            <span>${entry.weighted_total.toFixed(2)}</span>
          </div>
          <div class="muted">Ratings: ${entry.rating_count} | Touchpoints: ${entry.total_lunches} | Days: ${entry.days_since_first_event}</div>
          <div class="muted">Assigned: ${escapeHtml(assigned)}</div>
        </article>
      `;
    })
    .join("");
}

function mobileCommandStaleLabel(value) {
  if (value === "never_rated") {
    return "Never Rated";
  }
  if (value === "rating_older_than_recent_touchpoint") {
    return "Behind Touchpoint";
  }
  if (value === "no_recent_rating") {
    return "No Recent Rating";
  }
  return "Needs Update";
}

function mobileCommandSelectedItem() {
  return mobileHomeSelectedPnm();
}

function applyMobileCommandRatingCriteriaUi() {
  const fields = [
    { field: "good_with_girls", inputId: "mobileCommandRateGirls", labelId: "mobileCommandRateGirlsLabel" },
    { field: "will_make_it", inputId: "mobileCommandRateProcess", labelId: "mobileCommandRateProcessLabel" },
    { field: "personable", inputId: "mobileCommandRatePersonable", labelId: "mobileCommandRatePersonableLabel" },
    { field: "alcohol_control", inputId: "mobileCommandRateAlcohol", labelId: "mobileCommandRateAlcoholLabel" },
    { field: "instagram_marketability", inputId: "mobileCommandRateIg", labelId: "mobileCommandRateIgLabel" },
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

function renderMobileCommandCenterVisibility() {
  const officerSection = document.getElementById("mobileOfficerCommandCenter");
  const noticeSection = document.getElementById("mobileNonOfficerNotice");
  const canUse = mobileCanUseCommandCenter();
  if (officerSection) {
    officerSection.classList.toggle("hidden", !canUse);
  }
  if (noticeSection) {
    noticeSection.classList.toggle("hidden", canUse);
  }
}

function renderMobileCommandSelection() {
  const metaEl = document.getElementById("mobileCommandSelectedMeta");
  const meetingShortcut = document.getElementById("mobileCommandMeetingShortcut");
  const selectedCard = document.getElementById("mobileCommandSelectedCard");
  const selected = mobileCommandSelectedItem();
  if (!selected) {
    if (metaEl) {
      metaEl.textContent = "Select a rushee from search results or lunch follow-up to start rating.";
    }
    if (meetingShortcut) {
      meetingShortcut.href = MOBILE_ROUTES.meeting;
      meetingShortcut.classList.add("disabled");
      meetingShortcut.setAttribute("aria-disabled", "true");
    }
    if (selectedCard) {
      selectedCard.innerHTML = '<p class="muted">Choose a rushee above to load their photo, score, and rating details here.</p>';
    }
    const ratingForm = document.getElementById("mobileCommandRatingForm");
    if (ratingForm) {
      ratingForm.reset();
      clearInlineConfirmBar(ratingForm, "mobile-rating");
      clearInlineConfirmBar(ratingForm, "mobile-comment");
    }
    return;
  }
  const ratingForm = document.getElementById("mobileCommandRatingForm");
  clearInlineConfirmBar(ratingForm, "mobile-rating");
  clearInlineConfirmBar(ratingForm, "mobile-comment");

  const assigned = mobileHomeAssignedLabel(selected);
  const touchpoint = selected.last_lunch_with_me_at
    ? formatDownloadStamp(selected.last_lunch_with_me_at)
    : selected.last_touchpoint_at
      ? formatDownloadStamp(selected.last_touchpoint_at)
      : "None";
  const mine = selected.own_rating && selected.own_rating.updated_at ? formatDownloadStamp(selected.own_rating.updated_at) : selected.last_rating_by_me_at ? formatDownloadStamp(selected.last_rating_by_me_at) : "Never";
  const stale = selected.needs_rating_update ? mobileCommandStaleLabel(selected.stale_reason) : "Fresh";
  const lunchContext = [
    selected.last_lunch_with_me_date || "",
    selected.last_lunch_with_me_location || "",
  ]
    .filter(Boolean)
    .join(" | ");
  if (metaEl) {
    metaEl.textContent =
      `${selected.pnm_code} | ${selected.name || `${selected.first_name} ${selected.last_name}`} | Score ${formatWeightedScore(selected.weighted_total)} (${ratingTierMeta(selected.weighted_total).label}) | Assigned: ${assigned} | Last lunch: ${touchpoint}${lunchContext ? ` (${lunchContext})` : ""} | My Rating: ${mine} | ${stale}`;
  }
  if (meetingShortcut) {
    meetingShortcut.href = `${MOBILE_ROUTES.meeting}?pnm_id=${Number(selected.pnm_id)}`;
    meetingShortcut.classList.remove("disabled");
    meetingShortcut.removeAttribute("aria-disabled");
  }
  if (selectedCard) {
    selectedCard.innerHTML = `
      <div class="mobile-command-selected-head">
        ${mobileHomePhotoMarkup(selected, "mobile-command-selected-photo")}
        <div>
          <div class="mobile-command-selected-title">
            <strong>${escapeHtml(mobileHomeDisplayName(selected))}</strong>
            ${ratingTierBadgeMarkup(selected.weighted_total)}
          </div>
          <div class="mobile-command-selected-note">Weighted ${formatWeightedScore(selected.weighted_total)} • Assigned: ${escapeHtml(assigned)}</div>
        </div>
      </div>
      <div class="mobile-command-selected-note">Last touchpoint: ${escapeHtml(touchpoint)}${lunchContext ? ` • ${escapeHtml(lunchContext)}` : ""} • My rating: ${escapeHtml(mine)} • ${escapeHtml(stale)}</div>
    `;
  }

  const own = selected.own_rating || null;
  const girlsMax = ratingCriteriaForField("good_with_girls")?.max || 10;
  const processMax = ratingCriteriaForField("will_make_it")?.max || 10;
  const personableMax = ratingCriteriaForField("personable")?.max || 10;
  const alcoholMax = ratingCriteriaForField("alcohol_control")?.max || 10;
  const igMax = ratingCriteriaForField("instagram_marketability")?.max || 5;
  const girlsInput = document.getElementById("mobileCommandRateGirls");
  const processInput = document.getElementById("mobileCommandRateProcess");
  const personableInput = document.getElementById("mobileCommandRatePersonable");
  const alcoholInput = document.getElementById("mobileCommandRateAlcohol");
  const igInput = document.getElementById("mobileCommandRateIg");
  const commentInput = document.getElementById("mobileCommandRateComment");
  if (girlsInput) {
    girlsInput.value = own ? Math.min(Number(own.good_with_girls || 0), girlsMax) : 0;
  }
  if (processInput) {
    processInput.value = own ? Math.min(Number(own.will_make_it || 0), processMax) : 0;
  }
  if (personableInput) {
    personableInput.value = own ? Math.min(Number(own.personable || 0), personableMax) : 0;
  }
  if (alcoholInput) {
    alcoholInput.value = own ? Math.min(Number(own.alcohol_control || 0), alcoholMax) : 0;
  }
  if (igInput) {
    igInput.value = own ? Math.min(Number(own.instagram_marketability || 0), igMax) : 0;
  }
  if (commentInput) {
    commentInput.value = selected.last_lunch_with_me_notes ? selected.last_lunch_with_me_notes : own && own.comment ? own.comment : "";
  }
}

function renderMobileCommandCenter() {
  renderMobileCommandCenterVisibility();
  if (!mobileCanUseCommandCenter()) {
    return;
  }

  const summary = mobileCommandCenter.summary || {};
  const queueCountEl = document.getElementById("mobileCommandQueueCount");
  const staleCountEl = document.getElementById("mobileCommandStaleCount");
  const recentCountEl = document.getElementById("mobileCommandRecentCount");
  const windowLabelEl = document.getElementById("mobileCommandWindowLabel");
  if (queueCountEl) {
    queueCountEl.textContent = String(Number(summary.queue_count || 0));
  }
  if (staleCountEl) {
    staleCountEl.textContent = String(Number(summary.stale_count || 0));
  }
  if (recentCountEl) {
    recentCountEl.textContent = String(Number(summary.recent_change_count || 0));
  }
  if (windowLabelEl) {
    windowLabelEl.textContent = `Last ${Number(summary.window_hours || mobileCommandCenter.windowHours || 72)}h`;
  }

  const queueEl = document.getElementById("mobileCommandQueueList");
  const queueRows = Array.isArray(mobileCommandCenter.queue) ? mobileCommandCenter.queue : [];
  if (!mobileCommandCenter.selectedPnmId || !queueRows.some((item) => Number(item.pnm_id) === Number(mobileCommandCenter.selectedPnmId))) {
    mobileCommandCenter.selectedPnmId = queueRows.length ? Number(queueRows[0].pnm_id) : null;
  }
  if (queueEl) {
    if (!queueRows.length) {
      const detail = mobileCommandCenter.error || "No queue items available yet.";
      queueEl.innerHTML = `<p class="muted">${escapeHtml(detail)}</p>`;
    } else {
      queueEl.innerHTML = queueRows
        .map((item) => {
          const selectedClass = Number(item.pnm_id) === Number(mobileCommandCenter.selectedPnmId) ? " is-selected" : "";
          const staleBadge = item.needs_rating_update
            ? `<span class="pill warn">${escapeHtml(mobileCommandStaleLabel(item.stale_reason))}</span>`
            : '<span class="pill good">Fresh</span>';
          const assignedBadge = item.is_assigned_to_me ? '<span class="pill">Assigned To Me</span>' : "";
          const touchpoint = item.last_touchpoint_at ? formatDownloadStamp(item.last_touchpoint_at) : "No touchpoint";
          return `
            <article class="entry mobile-card${selectedClass}">
              <button type="button" class="mobile-command-queue-btn" data-mobile-command-pnm-id="${Number(item.pnm_id)}">
                <div class="entry-title">
                  <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</strong>
                  <span>${formatWeightedScore(item.weighted_total)}</span>
                </div>
                <div class="muted">Touchpoint: ${escapeHtml(touchpoint)}</div>
                <div class="muted">Assigned: ${escapeHtml(item.assigned_officer_username || "Unassigned")}</div>
                <div class="command-chip-row">${ratingTierBadgeMarkup(item.weighted_total)}${staleBadge}${assignedBadge}</div>
              </button>
            </article>
          `;
        })
        .join("");
    }
  }

  const recentEl = document.getElementById("mobileCommandRecentChanges");
  const changeRows = Array.isArray(mobileCommandCenter.recentChanges) ? mobileCommandCenter.recentChanges : [];
  if (recentEl) {
    if (!changeRows.length) {
      recentEl.innerHTML = '<p class="muted">No rating changes in this window.</p>';
    } else {
      recentEl.innerHTML = changeRows
        .map((item) => {
          const delta = Number(item.delta_total || 0);
          const deltaClass = delta > 0 ? "good" : delta < 0 ? "bad" : "";
          const deltaLabel = delta > 0 ? `+${delta}` : `${delta}`;
          const changedBy = item.changed_by && item.changed_by.username ? item.changed_by.username : "Member";
          return `
            <article class="entry mobile-card">
              <div class="entry-title">
                <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.pnm_name)}</strong>
                <span class="${deltaClass}">${escapeHtml(deltaLabel)}</span>
              </div>
              <div class="muted">${escapeHtml(changedBy)} | ${escapeHtml(formatDownloadStamp(item.changed_at))}</div>
              <div class="muted">${escapeHtml(String(item.comment || "").trim() || "Rating update logged.")}</div>
            </article>
          `;
        })
        .join("");
    }
  }

  renderMobileCommandSelection();
}

async function loadMobileCommandCenter(options = {}) {
  const surfaceErrors = Boolean(options.surfaceErrors);
  if (!mobileCanUseCommandCenter()) {
    mobileCommandCenter.queue = [];
    mobileCommandCenter.staleAlerts = [];
    mobileCommandCenter.recentChanges = [];
    mobileCommandCenter.summary = null;
    mobileCommandCenter.selectedPnmId = null;
    mobileCommandCenter.error = "";
    renderMobileCommandCenter();
    return;
  }

  const query = buildQueryString({
    window_hours: mobileCommandCenter.windowHours || 72,
    limit: mobileCommandCenter.limit || 30,
  });
  try {
    const payload = await api(`/api/dashboard/command-center${query}`);
    mobileCommandCenter.queue = Array.isArray(payload.queue) ? payload.queue : [];
    mobileCommandCenter.staleAlerts = Array.isArray(payload.stale_alerts) ? payload.stale_alerts : [];
    mobileCommandCenter.recentChanges = Array.isArray(payload.recent_rating_changes) ? payload.recent_rating_changes : [];
    mobileCommandCenter.summary = payload.summary || null;
    mobileCommandCenter.error = "";
  } catch (error) {
    mobileCommandCenter.queue = [];
    mobileCommandCenter.staleAlerts = [];
    mobileCommandCenter.recentChanges = [];
    mobileCommandCenter.summary = {
      window_hours: mobileCommandCenter.windowHours || 72,
      queue_count: 0,
      stale_count: 0,
      recent_change_count: 0,
    };
    mobileCommandCenter.selectedPnmId = null;
    mobileCommandCenter.error = error.message || "Unable to load command center.";
    if (surfaceErrors) {
      throw error;
    }
  }

  if (!mobileCommandCenter.selectedPnmId) {
    mobileCommandCenter.selectedPnmId = mobileCommandCenter.queue.length
      ? Number(mobileCommandCenter.queue[0].pnm_id)
      : null;
  }
  renderMobileCommandCenter();
}

async function loadHomeSnapshot() {
  const payload = await api("/api/mobile/home");
  renderHomeStats(payload.stats || {});
  renderHomeLeaderboard(payload.leaderboard || []);
  mobileHomePnmRows = Array.isArray(payload.pnms) ? payload.pnms : [];
  mobileHomeRecentLunchRows = Array.isArray(payload.recent_lunches) ? payload.recent_lunches : [];
  const pnmById = new Map();
  mobileHomePnmRows.forEach((pnm) => {
    const pnmId = Number(pnm && pnm.pnm_id ? pnm.pnm_id : 0);
    if (pnmId) {
      pnmById.set(pnmId, pnm);
    }
  });
  mobileHomeRecentLunchRows = mobileHomeRecentLunchRows.map((row) => {
    const match = pnmById.get(Number(row && row.pnm_id ? row.pnm_id : 0));
    if (!match) {
      return row;
    }
    return {
      ...row,
      photo_url: row.photo_url || match.photo_url || "",
    };
  });
  const lunchByPnm = new Map();
  mobileHomeRecentLunchRows.forEach((row) => {
    const pnmId = Number(row && row.pnm_id ? row.pnm_id : 0);
    if (!pnmId || lunchByPnm.has(pnmId)) {
      return;
    }
    lunchByPnm.set(pnmId, row);
  });
  mobileHomePnmRows = mobileHomePnmRows.map((pnm) => {
    const lunch = lunchByPnm.get(Number(pnm.pnm_id));
    if (!lunch) {
      return pnm;
    }
    return {
      ...pnm,
      last_lunch_with_me_at: lunch.created_at || lunch.last_lunch_date || "",
      last_lunch_with_me_date: lunch.last_lunch_date || "",
      last_lunch_with_me_location: lunch.location || "",
      last_lunch_with_me_notes: lunch.notes || "",
    };
  });
  if (!mobileHomeSelectedPnmId) {
    mobileHomeSelectedPnmId = mobileHomeRecentLunchRows.length
      ? Number(mobileHomeRecentLunchRows[0].pnm_id)
      : mobileHomePnmRows.length
        ? Number(mobileHomePnmRows[0].pnm_id)
        : null;
  }
  renderMobileHomeSearchResults();
  renderMobileHomeRecentLunches();
  renderMobileCommandSelection();
  if (payload.calendar_share) {
    renderMobileCalendarShare(payload.calendar_share);
  }
}

function renderPnmCards(pnms) {
  const listEl = document.getElementById("mobilePnmList");
  if (!listEl) {
    return;
  }
  if (!pnms.length) {
    listEl.innerHTML = '<p class="muted">No rushees found.</p>';
    return;
  }
  listEl.innerHTML = pnms
    .map((pnm) => {
      const photo = pnm.photo_url
        ? `<img src="${escapeHtml(pnm.photo_url)}" class="mini-photo" alt="${escapeHtml(pnm.first_name)}" loading="lazy" />`
        : '<div class="mini-photo empty">No photo</div>';
      const assigned = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const downloaded = isContactDownloaded(pnm.pnm_id);
      const packageInfo = mobilePackageInfoForPnm(pnm);
      const linkedNames = packageInfo.members
        .filter((item) => Number(item.pnm_id) !== Number(pnm.pnm_id))
        .map((item) => `${item.first_name} ${item.last_name}`);
      const packageText = linkedNames.length ? linkedNames.join(", ") : "None";
      const selectedClass = Number(mobileSelectedManagePnmId) === Number(pnm.pnm_id) ? " is-selected" : "";
      const creator = String(pnm.created_by_username || "").trim();
      const ownershipLabel = pnm.can_manage_profile
        ? creator
          ? `Editable by you · Created by ${creator}`
          : "Editable by you"
        : creator
          ? `Created by ${creator}`
          : "Locked";
      return `
        <article class="entry mobile-card${selectedClass}">
          <div class="entry-title">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span>${formatWeightedScore(pnm.weighted_total)}</span>
          </div>
          <div class="command-chip-row">${ratingTierBadgeMarkup(pnm.weighted_total)}</div>
          <div class="mobile-card-row">
            ${photo}
            <div>
              <div class="muted">${escapeHtml(pnm.phone_number || "No phone")} | ${escapeHtml(pnm.instagram_handle)}</div>
              <div class="muted">Hometown: ${escapeHtml(pnm.hometown || "Unknown")} ${escapeHtml(pnm.hometown_state_code || "")}</div>
              <div class="muted">Assigned: ${escapeHtml(assigned)}</div>
              <div class="muted">Linked With: ${escapeHtml(packageText)}</div>
              <div class="muted">Contact export: ${downloaded ? "✓ Downloaded" : "○ Pending"}</div>
              <div class="muted">Interests: ${pnm.interests.map((x) => escapeHtml(x)).join(", ")}</div>
              <div class="muted">${escapeHtml(ownershipLabel)}</div>
            </div>
          </div>
          <div class="action-row">
            <button type="button" class="secondary" data-mobile-manage-pnm-id="${pnm.pnm_id}"${pnm.can_manage_profile ? "" : " disabled"}>${pnm.can_manage_profile ? "Manage" : "Locked"}</button>
            <a class="quick-nav-link" href="${escapeHtml(`${MOBILE_ROUTES.meeting}?pnm_id=${pnm.pnm_id}`)}">Meeting Packet</a>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderMembers(members) {
  const listEl = document.getElementById("mobileMemberList");
  if (!listEl) {
    return;
  }
  if (!members.length) {
    listEl.innerHTML = '<p class="muted">No members available.</p>';
    const header = document.getElementById("mobileSameStateHeader");
    const hint = document.getElementById("mobileSameStateHint");
    const sameStateList = document.getElementById("mobileSameStateList");
    if (header) {
      header.textContent = "Same-State Rushees";
    }
    if (hint) {
      hint.textContent = "No member results for current filters.";
    }
    if (sameStateList) {
      sameStateList.innerHTML = "";
    }
    return;
  }
  listEl.innerHTML = members
    .map((member) => {
      const avg = member.avg_rating_given == null ? "-" : member.avg_rating_given.toFixed(2);
      const ratings = member.rating_count == null ? "-" : member.rating_count;
      const stateCode = String(member.state_code || "").trim();
      const city = String(member.city || "").trim();
      const location = stateCode ? `${city ? `${city}, ` : ""}${stateCode}` : city || "No location set";
      const selectedClass = Number(member.user_id) === Number(mobileSelectedTeamMemberId) ? " is-selected" : "";
      const stateActionDisabled = stateCode ? "" : " disabled";
      return `
        <article class="entry mobile-card${selectedClass}" data-member-id="${member.user_id}">
          <div class="entry-title">
            <strong>${escapeHtml(member.username)}</strong>
            <span>${escapeHtml(member.role)}</span>
          </div>
          <div class="muted">Stereotype: ${escapeHtml(member.stereotype)}</div>
          <div class="muted">Location: ${escapeHtml(location)}</div>
          <div class="muted">Touchpoints: ${member.total_lunches} | Week: ${member.lunches_per_week.toFixed(2)}</div>
          <div class="muted">Ratings: ${ratings} | Avg Given: ${avg}</div>
          <div class="action-row">
            <button type="button" class="secondary mobile-member-same-state-btn" data-member-id="${member.user_id}"${stateActionDisabled}>Same-State Rushees</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderSameStatePnms(member, pnms, errorMessage = "") {
  const header = document.getElementById("mobileSameStateHeader");
  const hint = document.getElementById("mobileSameStateHint");
  const listEl = document.getElementById("mobileSameStateList");
  if (!header || !hint || !listEl) {
    return;
  }
  if (errorMessage) {
    header.textContent = "Same-State Rushees";
    hint.textContent = errorMessage;
    listEl.innerHTML = "";
    return;
  }
  if (!member) {
    header.textContent = "Same-State Rushees";
    hint.textContent = "Select a member card to load same-state rushees.";
    listEl.innerHTML = "";
    return;
  }

  const stateCode = String(member.state_code || "").trim();
  const labelName = String(member.username || "Selected member");
  header.textContent = `Same-State Rushees • ${labelName}`;
  if (!stateCode) {
    hint.textContent = "No state set for this member.";
    listEl.innerHTML = "";
    return;
  }
  hint.textContent = `${pnms.length} result(s) in ${stateCode}.`;
  if (!pnms.length) {
    listEl.innerHTML = '<p class="muted">No rushees found for this state.</p>';
    return;
  }
  listEl.innerHTML = pnms
    .map((pnm) => {
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span>${formatWeightedScore(pnm.weighted_total)}</span>
          </div>
          <div class="command-chip-row">${ratingTierBadgeMarkup(pnm.weighted_total)}</div>
          <div class="muted">${escapeHtml(pnm.hometown || "")}${pnm.hometown_state_code ? `, ${escapeHtml(pnm.hometown_state_code)}` : ""}</div>
          <div class="action-row">
            <a class="quick-nav-link" href="${escapeHtml(`${MOBILE_ROUTES.meeting}?pnm_id=${pnm.pnm_id}`)}">Open Meeting Packet</a>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadHomePage() {
  await loadHomeSnapshot();
  await loadMobileCommandCenter();
}

function handleMobileCommandQueueSelect(event) {
  const trigger = event.target.closest("[data-mobile-command-pnm-id]");
  if (!trigger) {
    return;
  }
  const pnmId = Number(trigger.dataset.mobileCommandPnmId || 0);
  if (!pnmId) {
    return;
  }
  selectMobileHomePnm(pnmId, { scrollToForm: true });
  renderMobileCommandCenter();
}

async function handleMobileCommandSaveRating() {
  if (!mobileCanUseCommandCenter()) {
    showToast("Rush Officer access required.");
    return;
  }
  const selected = mobileCommandSelectedItem();
  if (!selected) {
    showToast("Select a queue item first.");
    return;
  }
  const girlsInput = document.getElementById("mobileCommandRateGirls");
  const processInput = document.getElementById("mobileCommandRateProcess");
  const personableInput = document.getElementById("mobileCommandRatePersonable");
  const alcoholInput = document.getElementById("mobileCommandRateAlcohol");
  const igInput = document.getElementById("mobileCommandRateIg");
  const commentInput = document.getElementById("mobileCommandRateComment");
  const ratingForm = document.getElementById("mobileCommandRatingForm");
  if (!girlsInput || !processInput || !personableInput || !alcoholInput || !igInput || !commentInput) {
    showToast("Rating controls are unavailable.");
    return;
  }

  const saveBtn = document.getElementById("mobileCommandSaveBtn");
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";
  }
  promptInlineConfirm(ratingForm, "mobile-rating", {
    message: confirmRusheeRatingSubmission(),
    confirmLabel: "Yes, Save Rating",
    onConfirm: async () => {
      try {
        const payload = await api("/api/ratings", {
          method: "POST",
          body: {
            pnm_id: Number(selected.pnm_id),
            good_with_girls: Number(girlsInput.value),
            will_make_it: Number(processInput.value),
            personable: Number(personableInput.value),
            alcohol_control: Number(alcoholInput.value),
            instagram_marketability: Number(igInput.value),
            comment: String(commentInput.value || "").trim(),
          },
        });
        await Promise.all([loadMobileCommandCenter(), loadHomeSnapshot()]);
        if (payload.change && Number(payload.change.delta_total) > 0) {
          showToast(`Rating up +${payload.change.delta_total}.`);
        } else {
          showToast("Rating saved.");
        }
      } catch (error) {
        showToast(error.message || "Unable to save rating.");
      } finally {
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save Rating";
        }
      }
    },
  });
  if (saveBtn) {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Rating";
  }
  showToast("Confirm the rating below to avoid accidental saves.");
}

async function handleMobileCommandAddComment() {
  if (!mobileCanUseCommandCenter()) {
    showToast("Rush Officer access required.");
    return;
  }
  const selected = mobileCommandSelectedItem();
  if (!selected) {
    showToast("Select a rushee first.");
    return;
  }
  const commentInput = document.getElementById("mobileCommandRateComment");
  const ratingForm = document.getElementById("mobileCommandRatingForm");
  const commentBtn = document.getElementById("mobileCommandCommentBtn");
  if (!commentInput) {
    showToast("Comment box is unavailable.");
    return;
  }
  const comment = String(commentInput.value || "").trim();
  if (!comment) {
    showToast("Write a quick comment first.");
    commentInput.focus();
    return;
  }

  if (commentBtn) {
    commentBtn.disabled = true;
    commentBtn.textContent = "Saving...";
  }

  promptInlineConfirm(ratingForm, "mobile-comment", {
    message: "Add this note without changing the rating?",
    confirmLabel: "Yes, Add Comment",
    onConfirm: async () => {
      try {
        await api(`/api/pnms/${Number(selected.pnm_id)}/comments`, {
          method: "POST",
          body: { comment },
        });
        await Promise.all([loadMobileCommandCenter(), loadHomeSnapshot()]);
        showToast("Comment added to the meeting packet.");
      } catch (error) {
        showToast(error.message || "Unable to add the comment.");
      } finally {
        if (commentBtn) {
          commentBtn.disabled = false;
          commentBtn.textContent = "Add Comment Only";
        }
      }
    },
  });

  if (commentBtn) {
    commentBtn.disabled = false;
    commentBtn.textContent = "Add Comment Only";
  }
  showToast("Confirm the note below so we don't post it by accident.");
}

async function handleMobileCommandScheduleLunch() {
  if (!mobileCanUseCommandCenter()) {
    showToast("Rush Officer access required.");
    return;
  }
  const selected = mobileCommandSelectedItem();
  if (!selected) {
    showToast("Select a queue item first.");
    return;
  }
  const dateInput = document.getElementById("mobileCommandLunchDate");
  const startInput = document.getElementById("mobileCommandLunchStartTime");
  const endInput = document.getElementById("mobileCommandLunchEndTime");
  const locationInput = document.getElementById("mobileCommandLunchLocation");
  const notesInput = document.getElementById("mobileCommandLunchNotes");
  if (!dateInput || !startInput || !endInput || !locationInput || !notesInput) {
    showToast("Lunch controls are unavailable.");
    return;
  }
  if (!String(dateInput.value || "").trim()) {
    showToast("Lunch date is required.");
    return;
  }

  const lunchBtn = document.getElementById("mobileCommandStickyLunchBtn");
  if (lunchBtn) {
    lunchBtn.disabled = true;
    lunchBtn.textContent = "Scheduling...";
  }
  try {
    await api("/api/lunches", {
      method: "POST",
      body: {
        pnm_id: Number(selected.pnm_id),
        lunch_date: dateInput.value,
        start_time: startInput.value ? startInput.value : null,
        end_time: endInput.value ? endInput.value : null,
        location: locationInput.value.trim(),
        notes: notesInput.value.trim(),
      },
    });
    startInput.value = "";
    endInput.value = "";
    locationInput.value = "";
    notesInput.value = "";
    await Promise.all([loadMobileCommandCenter(), loadHomeSnapshot()]);
    showToast("Lunch scheduled.");
  } catch (error) {
    showToast(error.message || "Unable to schedule lunch.");
  } finally {
    if (lunchBtn) {
      lunchBtn.disabled = false;
      lunchBtn.textContent = "Schedule Lunch";
    }
  }
}

async function loadPnmsPage() {
  const stateFilter = normalizeStateFilterInput(mobileFilters.pnms.state);
  const query = buildQueryString({ state: stateFilter });
  const [pnmPayload] = await Promise.all([api(`/api/pnms${query}`), loadContactDownloadStatuses()]);
  mobilePnmRows = Array.isArray(pnmPayload.pnms) ? pnmPayload.pnms : [];
  if (!mobilePnmRows.some((pnm) => Number(pnm.pnm_id) === Number(mobileSelectedManagePnmId))) {
    mobileSelectedManagePnmId = null;
  }
  updateContactsUi();
  renderMobilePnmManagement();
}

function mobileSelectedManagePnm() {
  return mobilePnmRows.find((pnm) => Number(pnm.pnm_id) === Number(mobileSelectedManagePnmId)) || null;
}

function resetMobilePnmManagement(message = "Select a rushee from the roster to edit identity, contact, and meeting details.") {
  const hint = document.getElementById("mobilePnmManageHint");
  const locked = document.getElementById("mobilePnmManageLocked");
  const form = document.getElementById("mobilePnmManageForm");
  if (hint) {
    hint.textContent = message;
  }
  if (locked) {
    locked.classList.add("hidden");
    locked.innerHTML = "";
  }
  if (form) {
    form.classList.add("hidden");
    form.reset();
  }
  const interests = document.getElementById("mobileManageInterests");
  const stereotype = document.getElementById("mobileManageStereotype");
  if (interests) {
    interests.value = "";
  }
  if (stereotype) {
    stereotype.value = "";
  }
  syncInterestPickerFromInput("mobileManageInterests", "mobileManageInterestTags");
  syncStereotypePickerFromInput("mobileManageStereotype", "mobileManageStereotypeTags");
}

function renderMobilePnmManagement() {
  const selected = mobileSelectedManagePnm();
  const hint = document.getElementById("mobilePnmManageHint");
  const locked = document.getElementById("mobilePnmManageLocked");
  const form = document.getElementById("mobilePnmManageForm");
  if (!form) {
    return;
  }
  if (!selected) {
    resetMobilePnmManagement();
    return;
  }
  const creator = String(selected.created_by_username || "").trim() || "another rush team member";
  if (hint) {
    hint.textContent = selected.can_manage_profile
      ? `Created by ${creator}. You can update this rushee here.`
      : `Created by ${creator}. Only the creator or Head Rush Officer can edit this rushee.`;
  }
  if (!selected.can_manage_profile) {
    form.classList.add("hidden");
    if (locked) {
      locked.classList.remove("hidden");
      locked.innerHTML = `
        <div class="entry-title">
          <strong>Editing locked</strong>
          <span>${escapeHtml(creator)}</span>
        </div>
        <div class="muted">You can still open Meeting Packet, but only the creator or Head Rush Officer can change profile details.</div>
      `;
    }
    return;
  }
  if (locked) {
    locked.classList.add("hidden");
    locked.innerHTML = "";
  }
  form.classList.remove("hidden");
  const setValue = (id, value) => {
    const el = document.getElementById(id);
    if (el) {
      el.value = String(value ?? "");
    }
  };
  setValue("mobileManageFirstName", selected.first_name);
  setValue("mobileManageLastName", selected.last_name);
  setValue("mobileManageClassYear", selected.class_year || "F");
  setValue("mobileManageEventDate", selected.first_event_date);
  setValue("mobileManageHometown", selected.hometown);
  setValue("mobileManageState", selected.hometown_state_code);
  setValue("mobileManagePhone", selected.phone_number);
  setValue("mobileManageInstagram", selected.instagram_handle);
  setValue("mobileManageInterests", Array.isArray(selected.interests) ? selected.interests.join(",") : "");
  setValue("mobileManageStereotype", selected.stereotype);
  setValue("mobileManageLunchStats", selected.lunch_stats);
  setValue("mobileManageNotes", selected.notes);
  syncInterestPickerFromInput("mobileManageInterests", "mobileManageInterestTags");
  syncStereotypePickerFromInput("mobileManageStereotype", "mobileManageStereotypeTags");
}

function handleMobileHomeSearchClick(event) {
  const trigger = event.target.closest("[data-mobile-home-pnm-id]");
  if (!trigger) {
    return;
  }
  const pnmId = Number(trigger.dataset.mobileHomePnmId || 0);
  if (!pnmId) {
    return;
  }
  selectMobileHomePnm(pnmId, { scrollToForm: true });
}

async function loadMembersPage() {
  const roleFilter = String(mobileFilters.members.role || "all").trim() || "all";
  const stateFilter = normalizeStateFilterInput(mobileFilters.members.state);
  const cityFilter = String(mobileFilters.members.city || "").trim();
  const sortFilter = String(mobileFilters.members.sort || "location").trim() || "location";
  const query = buildQueryString({
    role: roleFilter,
    state: stateFilter,
    city: cityFilter,
    sort: sortFilter,
  });
  const payload = await api(`/api/users${query}`);
  mobileMemberRows = Array.isArray(payload.users) ? payload.users : [];
  renderMembers(mobileMemberRows);

  if (!mobileMemberRows.length) {
    mobileSelectedTeamMemberId = null;
    renderSameStatePnms(null, []);
    return;
  }
  const existing = mobileMemberRows.find((item) => Number(item.user_id) === Number(mobileSelectedTeamMemberId));
  const fallback = existing || mobileMemberRows[0];
  mobileSelectedTeamMemberId = fallback ? Number(fallback.user_id) : null;
  if (fallback) {
    await loadSameStatePnmsForMember(fallback);
  } else {
    renderSameStatePnms(null, []);
  }
}

async function loadSameStatePnmsForMember(member) {
  if (!member) {
    renderSameStatePnms(null, []);
    return;
  }
  const stateCode = normalizeStateFilterInput(member.state_code);
  if (!stateCode) {
    renderSameStatePnms(member, []);
    return;
  }
  try {
    const payload = await api(`/api/pnms${buildQueryString({ state: stateCode })}`);
    const rows = Array.isArray(payload.pnms) ? payload.pnms : [];
    renderSameStatePnms(member, rows);
  } catch (error) {
    renderSameStatePnms(member, [], error.message || "Unable to load same-state rushees.");
  }
}

function renderCalendarStats(stats) {
  const totalEl = document.getElementById("mobileCalendarTotalCount");
  const eventEl = document.getElementById("mobileCalendarEventCount");
  const lunchEl = document.getElementById("mobileCalendarLunchCount");
  if (!totalEl || !eventEl || !lunchEl) {
    return;
  }
  totalEl.textContent = String(Number(stats.total_count || 0));
  eventEl.textContent = String(Number(stats.official_event_count || 0));
  lunchEl.textContent = String(Number(stats.lunch_count || 0));
}

function renderCalendarItems(items) {
  const listEl = document.getElementById("mobileCalendarList");
  if (!listEl) {
    return;
  }
  if (!items.length) {
    listEl.innerHTML = '<p class="muted">No upcoming rush events or lunches.</p>';
    return;
  }
  listEl.innerHTML = items
    .map((item) => {
      const typeLabel = item.item_type === "lunch" ? "Lunch" : "Rush Event";
      const timeLabel =
        item.start_time && item.end_time
          ? `${item.start_time} - ${item.end_time}`
          : item.start_time
            ? `${item.start_time}`
            : "All Day";
      const pnmMeta = item.pnm_code ? ` | ${item.pnm_code}` : "";
      const location = item.location ? ` | ${item.location}` : "";
      const details = item.details ? `<div class="muted">${escapeHtml(item.details)}</div>` : "";
      const googleAction = item.google_calendar_url
        ? `<a class="quick-nav-link" href="${escapeHtml(item.google_calendar_url)}" target="_blank" rel="noopener">Open in Google</a>`
        : "";
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(item.title || typeLabel)}</strong>
            <span>${escapeHtml(typeLabel)}</span>
          </div>
          <div class="muted">${escapeHtml(item.event_date || "")} | ${escapeHtml(timeLabel)}${escapeHtml(pnmMeta)}${escapeHtml(location)}</div>
          ${details}
          <div class="action-row">
            ${googleAction}
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadCalendarPage() {
  const payload = await api("/api/rush-calendar?limit=250");
  const items = Array.isArray(payload.items) ? payload.items : [];
  renderCalendarItems(items);
  renderCalendarStats(payload.stats || {});
  if (payload.calendar_share) {
    renderMobileCalendarShare(payload.calendar_share);
  }
}

async function createMobileRushEvent(form) {
  const button = document.getElementById("mobileRushEventCreateBtn");
  const body = {
    title: String(document.getElementById("mobileRushEventTitle")?.value || "").trim(),
    event_type: String(document.getElementById("mobileRushEventType")?.value || "official").trim() || "official",
    event_date: String(document.getElementById("mobileRushEventDate")?.value || "").trim(),
    start_time: String(document.getElementById("mobileRushEventStart")?.value || "").trim() || null,
    end_time: String(document.getElementById("mobileRushEventEnd")?.value || "").trim() || null,
    location: String(document.getElementById("mobileRushEventLocation")?.value || "").trim(),
    details: String(document.getElementById("mobileRushEventDetails")?.value || "").trim(),
    is_official: true,
  };
  if (!body.title || !body.event_date) {
    showToast("Title and date are required.");
    return;
  }
  if (button) {
    button.disabled = true;
    button.textContent = "Creating...";
  }
  try {
    await api("/api/rush-events", {
      method: "POST",
      body,
    });
    showToast("Rush event created.");
    if (form) {
      form.reset();
    }
    await loadCalendarPage();
  } catch (error) {
    showToast(error.message || "Unable to create rush event.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Create Event";
    }
  }
}

async function downloadBackupFile(button, path, fallbackName) {
  if (!button) {
    return;
  }
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "Preparing...";
  try {
    const response = await fetch(resolveApiPath(path), {
      method: "GET",
      credentials: "same-origin",
    });
    if (!response.ok) {
      let detail = "Backup request failed.";
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => ({}));
        detail = String(payload.detail || detail);
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition") || "";
    const filename = fileNameFromDisposition(disposition, fallbackName);
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = "noopener";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    showToast("Backup download started.");
  } catch (error) {
    showToast(error.message || "Unable to download backup.");
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

function renderMobileAdminSummary(pendingRows, officerPayload, assignmentsPayload) {
  const pendingEl = document.getElementById("mobileAdminPendingCount");
  const officerEl = document.getElementById("mobileAdminOfficerCount");
  const activeAssignmentsEl = document.getElementById("mobileAdminActiveAssignments");
  const pendingCount = Array.isArray(pendingRows) ? pendingRows.length : 0;
  const officerCount = Number((officerPayload && officerPayload.summary && officerPayload.summary.officer_count) || 0);
  const statusCounts = (assignmentsPayload && assignmentsPayload.status_counts) || {};
  const activeAssignments =
    Number(statusCounts.assigned || 0) + Number(statusCounts.in_progress || 0) + Number(statusCounts.needs_help || 0);
  if (pendingEl) {
    pendingEl.textContent = String(pendingCount);
  }
  if (officerEl) {
    officerEl.textContent = String(officerCount);
  }
  if (activeAssignmentsEl) {
    activeAssignmentsEl.textContent = String(activeAssignments);
  }
}

function renderMobileAdminPending(pendingRows) {
  const listEl = document.getElementById("mobileAdminPendingList");
  if (!listEl) {
    return;
  }
  if (!pendingRows.length) {
    listEl.innerHTML = '<p class="muted">No pending approvals.</p>';
    return;
  }
  listEl.innerHTML = pendingRows
    .map((entry) => {
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(entry.username)}</strong>
            <span>${escapeHtml(entry.role || "")}</span>
          </div>
          <div class="muted">Stereotype: ${escapeHtml(entry.stereotype || "-")}</div>
          <div class="action-row">
            <button type="button" data-approve-user-id="${entry.user_id}">Approve</button>
            <button type="button" class="secondary" data-disapprove-user-id="${entry.user_id}">Disapprove</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderMobileAdminOfficers(officerPayload) {
  const listEl = document.getElementById("mobileAdminOfficerList");
  if (!listEl) {
    return;
  }
  const rows = Array.isArray(officerPayload && officerPayload.rush_officers) ? officerPayload.rush_officers : [];
  if (!rows.length) {
    listEl.innerHTML = '<p class="muted">No officer metrics available.</p>';
    return;
  }
  listEl.innerHTML = rows
    .map((officer) => {
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(officer.username)}</strong>
            <span>${escapeHtml(officer.emoji || "")}</span>
          </div>
          <div class="muted">Ratings: ${Number(officer.rating_count || 0)} | Touchpoints: ${Number(officer.total_lunches || 0)}</div>
          <div class="muted">Avg Given: ${Number(officer.avg_rating_given || 0).toFixed(2)} | Participation: ${Number(officer.participation_score || 0).toFixed(2)}</div>
        </article>
      `;
    })
    .join("");
}

function renderMobileAdminStorage(storagePayload) {
  const listEl = document.getElementById("mobileAdminStorage");
  if (!listEl) {
    return;
  }
  const counters = (storagePayload && storagePayload.counters) || {};
  const warnings = Array.isArray(storagePayload && storagePayload.warnings) ? storagePayload.warnings : [];
  listEl.innerHTML = `
    <article class="entry mobile-card">
      <div class="entry-title">
        <strong>Persistent Paths</strong>
        <span>${storagePayload && storagePayload.persistent_paths_ok ? "OK" : "Check"}</span>
      </div>
      <div class="muted">Tenants: ${Number(storagePayload && storagePayload.active_tenants ? storagePayload.active_tenants : 0)}</div>
      <div class="muted">Rushees: ${Number(counters.pnms || 0)} | Users: ${Number(counters.users || 0)}</div>
      <div class="muted">Ratings: ${Number(counters.ratings || 0)} | Touchpoints: ${Number(counters.lunches || 0)}</div>
      ${warnings.length ? `<div class="muted">${escapeHtml(warnings.join(" | "))}</div>` : ""}
    </article>
  `;
}

async function loadAdminPage() {
  const deniedPanel = document.getElementById("mobileAdminDeniedPanel");
  const adminPanel = document.getElementById("mobileAdminPanel");
  if (!mobileCurrentUser || mobileCurrentUser.role !== "Head Rush Officer") {
    if (deniedPanel) {
      deniedPanel.classList.remove("hidden");
    }
    if (adminPanel) {
      adminPanel.classList.add("hidden");
    }
    return;
  }
  if (deniedPanel) {
    deniedPanel.classList.add("hidden");
  }
  if (adminPanel) {
    adminPanel.classList.remove("hidden");
  }

  const [pendingPayload, officerPayload, assignmentsPayload, storagePayload] = await Promise.all([
    api("/api/users/pending"),
    api("/api/admin/rush-officers"),
    api("/api/assignments/overview"),
    api("/api/admin/storage"),
  ]);
  const pendingRows = Array.isArray(pendingPayload && pendingPayload.pending) ? pendingPayload.pending : [];
  renderMobileAdminSummary(pendingRows, officerPayload, assignmentsPayload);
  renderMobileAdminPending(pendingRows);
  renderMobileAdminOfficers(officerPayload || {});
  renderMobileAdminStorage(storagePayload || {});
}

async function handleCreateSubmit(event) {
  event.preventDefault();
  const interestsValue = document.getElementById("mobilePnmInterests").value.trim();
  if (!interestsValue) {
    showToast("Select at least one approved interest tag.");
    return;
  }
  const stereotypeValue = document.getElementById("mobilePnmStereotype").value.trim();
  if (!stereotypeValue) {
    showToast("Select one approved stereotype tag.");
    return;
  }
  const body = {
    first_name: document.getElementById("mobilePnmFirstName").value.trim(),
    last_name: document.getElementById("mobilePnmLastName").value.trim(),
    class_year: document.getElementById("mobilePnmClassYear").value,
    hometown: document.getElementById("mobilePnmHometown").value.trim(),
    state: document.getElementById("mobilePnmState").value.trim(),
    phone_number: document.getElementById("mobilePnmPhone").value.trim(),
    instagram_handle: document.getElementById("mobilePnmInstagram").value.trim(),
    first_event_date: document.getElementById("mobilePnmEventDate").value,
    interests: interestsValue,
    stereotype: stereotypeValue,
    lunch_stats: document.getElementById("mobilePnmLunchStats").value.trim(),
    notes: document.getElementById("mobilePnmNotes").value.trim(),
  };
  if (!body.state) {
    showToast("State is required.");
    return;
  }

  const form = document.getElementById("mobileCreatePnmForm");
  const submitButton = form.querySelector("button[type='submit']");
  submitButton.disabled = true;
  submitButton.textContent = "Creating...";
  try {
    const created = await api("/api/pnms", {
      method: "POST",
      body,
    });

    const fileInput = document.getElementById("mobilePnmPhoto");
    const file = fileInput.files && fileInput.files.length ? fileInput.files[0] : null;
    if (file) {
      const formData = new FormData();
      formData.append("photo", file);
      await api(`/api/pnms/${created.pnm.pnm_id}/photo`, {
        method: "POST",
        body: formData,
      });
    }

    form.reset();
    document.getElementById("mobilePnmEventDate").value = new Date().toISOString().slice(0, 10);
    syncInterestPickerFromInput("mobilePnmInterests", "mobileInterestTags");
    syncStereotypePickerFromInput("mobilePnmStereotype", "mobileStereotypeTags");
    showToast("Rushee created.");
    window.location.href = MOBILE_ROUTES.rushees;
  } catch (error) {
    showToast(error.message || "Unable to create rushee.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Create Rushee";
  }
}

async function handleMobilePnmManageSubmit(event) {
  event.preventDefault();
  const selected = mobileSelectedManagePnm();
  if (!selected) {
    showToast("Select a rushee first.");
    return;
  }
  if (!selected.can_manage_profile) {
    showToast("You can only edit rushees you created unless you are Head Rush Officer.");
    return;
  }
  const interestsValue = String(document.getElementById("mobileManageInterests")?.value || "").trim();
  const stereotypeValue = String(document.getElementById("mobileManageStereotype")?.value || "").trim();
  if (!interestsValue) {
    showToast("Select at least one approved interest tag.");
    return;
  }
  if (!stereotypeValue) {
    showToast("Select one approved stereotype tag.");
    return;
  }
  const body = {
    first_name: String(document.getElementById("mobileManageFirstName")?.value || "").trim(),
    last_name: String(document.getElementById("mobileManageLastName")?.value || "").trim(),
    class_year: String(document.getElementById("mobileManageClassYear")?.value || "").trim(),
    hometown: String(document.getElementById("mobileManageHometown")?.value || "").trim(),
    state: String(document.getElementById("mobileManageState")?.value || "").trim(),
    phone_number: String(document.getElementById("mobileManagePhone")?.value || "").trim(),
    instagram_handle: String(document.getElementById("mobileManageInstagram")?.value || "").trim(),
    first_event_date: String(document.getElementById("mobileManageEventDate")?.value || "").trim(),
    interests: interestsValue,
    stereotype: stereotypeValue,
    lunch_stats: String(document.getElementById("mobileManageLunchStats")?.value || "").trim(),
    notes: String(document.getElementById("mobileManageNotes")?.value || "").trim(),
  };
  if (!body.first_name || !body.last_name || !body.hometown || !body.state || !body.instagram_handle || !body.first_event_date) {
    showToast("First name, last name, hometown, state, Instagram, and first event date are required.");
    return;
  }
  const submitButton = document.getElementById("mobilePnmManageSaveBtn");
  const originalLabel = submitButton ? submitButton.textContent : "Save Rushee Details";
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = "Saving...";
  }
  try {
    await api(`/api/pnms/${Number(selected.pnm_id)}`, {
      method: "PATCH",
      body,
    });
    showToast("Rushee details updated.");
    await loadPnmsPage();
    mobileSelectedManagePnmId = Number(selected.pnm_id);
    renderPnmCards(mobilePnmRows);
    renderMobilePnmManagement();
  } catch (error) {
    showToast(error.message || "Unable to update rushee.");
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = originalLabel;
    }
  }
}

function attachPageEvents() {
  if (MOBILE_PAGE === "home") {
    const copyBtn = document.getElementById("mobileCopyCalendarBtn");
    const searchInput = document.getElementById("mobileHomeSearchInput");
    const clearSearchBtn = document.getElementById("mobileHomeClearSearchBtn");
    const searchResults = document.getElementById("mobileHomeSearchResults");
    const recentLunches = document.getElementById("mobileHomeRecentLunches");
    const queueList = document.getElementById("mobileCommandQueueList");
    const ratingForm = document.getElementById("mobileCommandRatingForm");
    if (copyBtn) {
      copyBtn.addEventListener("click", handleMobileCopyCalendar);
    }
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        renderMobileHomeSearchResults();
      });
    }
    if (clearSearchBtn) {
      clearSearchBtn.addEventListener("click", () => {
        if (searchInput) {
          searchInput.value = "";
        }
        renderMobileHomeSearchResults();
      });
    }
    if (searchResults) {
      searchResults.addEventListener("click", handleMobileHomeSearchClick);
    }
    if (recentLunches) {
      recentLunches.addEventListener("click", handleMobileHomeSearchClick);
    }
    if (queueList) {
      queueList.addEventListener("click", handleMobileCommandQueueSelect);
    }
    if (ratingForm) {
      ratingForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await handleMobileCommandSaveRating();
      });
    }
    const mobileCommentBtn = document.getElementById("mobileCommandCommentBtn");
    if (mobileCommentBtn) {
      mobileCommentBtn.addEventListener("click", handleMobileCommandAddComment);
    }
  }

  if (MOBILE_PAGE === "pnms") {
    const refreshBtn = document.getElementById("mobileRefreshPnmsBtn");
    const applyFiltersBtn = document.getElementById("mobileApplyPnmFiltersBtn");
    const stateInput = document.getElementById("mobilePnmStateFilter");
    const downloadBtn = document.getElementById("mobileDownloadContactsBtn");
    const downloadSelectedBtn = document.getElementById("mobileDownloadSelectedContactBtn");
    const contactSelect = document.getElementById("mobileContactPnmSelect");
    const packagePrimarySelect = document.getElementById("mobilePackagePrimarySelect");
    const packagePartnerSelect = document.getElementById("mobilePackagePartnerSelect");
    const packageLinkBtn = document.getElementById("mobilePackageLinkBtn");
    const packageUnlinkBtn = document.getElementById("mobilePackageUnlinkBtn");
    const manageForm = document.getElementById("mobilePnmManageForm");
    const list = document.getElementById("mobilePnmList");
    initializeMobileTagPickers();
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        try {
          await loadPnmsPage();
          showToast("Refreshed.");
        } catch (error) {
          showToast(error.message || "Unable to refresh rushees.");
        }
      });
    }
    const applyPnmFilters = async () => {
      mobileFilters.pnms.state = stateInput ? stateInput.value : "";
      await loadPnmsPage();
    };
    const debouncedPnmFilters = debounce(async () => {
      try {
        await applyPnmFilters();
      } catch (error) {
        showToast(error.message || "Unable to apply rushee filters.");
      }
    }, 200);
    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener("click", async () => {
        mobileFilters.pnms.state = stateInput ? stateInput.value : "";
        try {
          await loadPnmsPage();
          showToast("Rushee filters applied.");
        } catch (error) {
          showToast(error.message || "Unable to apply filters.");
        }
      });
    }
    if (stateInput) {
      stateInput.value = mobileFilters.pnms.state;
      stateInput.addEventListener("input", () => {
        debouncedPnmFilters();
      });
      stateInput.addEventListener("change", () => {
        debouncedPnmFilters();
      });
      stateInput.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter") {
          return;
        }
        event.preventDefault();
        try {
          await applyPnmFilters();
        } catch (error) {
          showToast(error.message || "Unable to apply filters.");
        }
      });
    }
    if (list) {
      list.addEventListener("click", (event) => {
        const manageBtn = event.target.closest("[data-mobile-manage-pnm-id]");
        if (!manageBtn) {
          return;
        }
        const pnmId = Number(manageBtn.dataset.mobileManagePnmId || 0);
        if (!pnmId) {
          return;
        }
        mobileSelectedManagePnmId = pnmId;
        renderPnmCards(mobilePnmRows);
        renderMobilePnmManagement();
        document.getElementById("mobilePnmManageForm")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
    if (manageForm) {
      manageForm.addEventListener("submit", handleMobilePnmManageSubmit);
    }
    if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
        handleDownloadAllContacts(downloadBtn);
      });
    }
    if (downloadSelectedBtn) {
      downloadSelectedBtn.addEventListener("click", () => {
        handleDownloadSelectedContact(downloadSelectedBtn);
      });
    }
    if (contactSelect) {
      contactSelect.addEventListener("change", () => {
        mobileSelectedContactPnmId = Number(contactSelect.value || 0) || null;
      });
    }
    if (packagePrimarySelect) {
      packagePrimarySelect.addEventListener("change", () => {
        mobilePackagePrimaryPnmId = Number(packagePrimarySelect.value || 0) || null;
        renderMobilePackageControls();
      });
    }
    if (packagePartnerSelect) {
      packagePartnerSelect.addEventListener("change", () => {
        mobilePackagePartnerPnmId = Number(packagePartnerSelect.value || 0) || null;
        renderMobilePackageControls();
      });
    }
    if (packageLinkBtn) {
      packageLinkBtn.addEventListener("click", () => {
        handleMobilePackageLink(packageLinkBtn);
      });
    }
    if (packageUnlinkBtn) {
      packageUnlinkBtn.addEventListener("click", () => {
        handleMobilePackageUnlink(packageUnlinkBtn);
      });
    }
  }

  if (MOBILE_PAGE === "members") {
    const refreshBtn = document.getElementById("mobileRefreshMembersBtn");
    const applyFiltersBtn = document.getElementById("mobileApplyMemberFiltersBtn");
    const roleInput = document.getElementById("mobileMemberRoleFilter");
    const stateInput = document.getElementById("mobileMemberStateFilter");
    const cityInput = document.getElementById("mobileMemberCityFilter");
    const sortInput = document.getElementById("mobileMemberSortFilter");
    const memberList = document.getElementById("mobileMemberList");
    if (roleInput) {
      roleInput.value = mobileFilters.members.role;
    }
    if (stateInput) {
      stateInput.value = mobileFilters.members.state;
    }
    if (cityInput) {
      cityInput.value = mobileFilters.members.city;
    }
    if (sortInput) {
      sortInput.value = mobileFilters.members.sort;
    }
    const applyMemberFilters = async () => {
      mobileFilters.members.role = roleInput ? roleInput.value : "all";
      mobileFilters.members.state = stateInput ? stateInput.value : "";
      mobileFilters.members.city = cityInput ? cityInput.value : "";
      mobileFilters.members.sort = sortInput ? sortInput.value : "location";
      await loadMembersPage();
    };
    const debouncedMemberFilters = debounce(async () => {
      try {
        await applyMemberFilters();
      } catch (error) {
        showToast(error.message || "Unable to apply team filters.");
      }
    }, 220);
    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener("click", async () => {
        try {
          await applyMemberFilters();
          showToast("Team filters applied.");
        } catch (error) {
          showToast(error.message || "Unable to apply team filters.");
        }
      });
    }
    [roleInput, stateInput, cityInput, sortInput].forEach((input) => {
      if (!input) {
        return;
      }
      const eventName = input.tagName === "SELECT" ? "change" : "input";
      input.addEventListener(eventName, () => {
        debouncedMemberFilters();
      });
      if (eventName !== "change") {
        input.addEventListener("change", () => {
          debouncedMemberFilters();
        });
      }
    });
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        try {
          await loadMembersPage();
          showToast("Refreshed.");
        } catch (error) {
          showToast(error.message || "Unable to refresh members.");
        }
      });
    }
    if (memberList) {
      memberList.addEventListener("click", async (event) => {
        const trigger = event.target.closest("[data-member-id]");
        if (!trigger) {
          return;
        }
        const memberId = Number(trigger.dataset.memberId || 0);
        if (!memberId) {
          return;
        }
        const member = mobileMemberRows.find((item) => Number(item.user_id) === memberId);
        if (!member) {
          return;
        }
        mobileSelectedTeamMemberId = memberId;
        renderMembers(mobileMemberRows);
        await loadSameStatePnmsForMember(member);
      });
    }
  }

  if (MOBILE_PAGE === "create") {
    const form = document.getElementById("mobileCreatePnmForm");
    if (form) {
      form.addEventListener("submit", handleCreateSubmit);
    }
    initializeMobileTagPickers();
  }

  if (MOBILE_PAGE === "calendar") {
    const copyFeedBtn = document.getElementById("mobileCalendarCopyFeedBtn");
    const copyLunchFeedBtn = document.getElementById("mobileCalendarCopyLunchFeedBtn");
    const refreshBtn = document.getElementById("mobileRefreshCalendarBtn");
    const form = document.getElementById("mobileRushEventForm");
    const headTools = document.getElementById("mobileCalendarHeadTools");
    const dateInput = document.getElementById("mobileRushEventDate");

    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    if (headTools) {
      headTools.classList.toggle("hidden", !mobileCurrentUser || mobileCurrentUser.role !== "Head Rush Officer");
    }
    if (copyFeedBtn) {
      copyFeedBtn.addEventListener("click", async () => {
        await copyTextToClipboard(mobileCalendarShare && mobileCalendarShare.feed_url, "Main calendar feed copied.");
      });
    }
    if (copyLunchFeedBtn) {
      copyLunchFeedBtn.addEventListener("click", async () => {
        await copyTextToClipboard(
          mobileCalendarShare && mobileCalendarShare.lunch_feed_url,
          "Lunch calendar feed copied."
        );
      });
    }
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        try {
          await loadCalendarPage();
          showToast("Calendar refreshed.");
        } catch (error) {
          showToast(error.message || "Unable to refresh calendar.");
        }
      });
    }
    if (form) {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await createMobileRushEvent(form);
      });
    }
  }

  if (MOBILE_PAGE === "admin") {
    const refreshBtn = document.getElementById("mobileAdminRefreshBtn");
    const pendingList = document.getElementById("mobileAdminPendingList");
    const csvBtn = document.getElementById("mobileAdminBackupCsvBtn");
    const dbBtn = document.getElementById("mobileAdminBackupDbBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        try {
          await loadAdminPage();
          showToast("Admin panel refreshed.");
        } catch (error) {
          showToast(error.message || "Unable to refresh admin panel.");
        }
      });
    }
    if (csvBtn) {
      csvBtn.addEventListener("click", () => {
        downloadBackupFile(csvBtn, "/api/export/csv", `bidboard-backup-${new Date().toISOString().slice(0, 10)}.zip`);
      });
    }
    if (dbBtn) {
      dbBtn.addEventListener("click", () => {
        downloadBackupFile(dbBtn, "/api/export/sqlite", `bidboard-db-${new Date().toISOString().slice(0, 10)}.db`);
      });
    }
    if (pendingList) {
      pendingList.addEventListener("click", async (event) => {
        const approveTrigger = event.target.closest("[data-approve-user-id]");
        if (approveTrigger) {
          const userId = Number(approveTrigger.dataset.approveUserId || 0);
          if (!userId) {
            return;
          }
          try {
            await api(`/api/users/pending/${userId}/approve`, { method: "POST" });
            await loadAdminPage();
            showToast("User approved.");
          } catch (error) {
            showToast(error.message || "Unable to approve user.");
          }
          return;
        }
        const disapproveTrigger = event.target.closest("[data-disapprove-user-id]");
        if (disapproveTrigger) {
          const userId = Number(disapproveTrigger.dataset.disapproveUserId || 0);
          if (!userId) {
            return;
          }
          try {
            await api(`/api/users/${userId}/disapprove`, { method: "POST" });
            await loadAdminPage();
            showToast("User moved back to pending.");
          } catch (error) {
            showToast(error.message || "Unable to disapprove user.");
          }
        }
      });
    }
  }
}

async function loadPageData() {
  if (MOBILE_PAGE === "home") {
    await loadHomePage();
    return;
  }
  if (MOBILE_PAGE === "pnms") {
    await loadPnmsPage();
    return;
  }
  if (MOBILE_PAGE === "members") {
    await loadMembersPage();
    return;
  }
  if (MOBILE_PAGE === "create") {
    const dateInput = document.getElementById("mobilePnmEventDate");
    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    return;
  }
  if (MOBILE_PAGE === "calendar") {
    await loadCalendarPage();
    return;
  }
  if (MOBILE_PAGE === "admin") {
    await loadAdminPage();
    return;
  }
}

async function init() {
  renderMobileStateHints(STATE_OPTIONS);
  applyMobileCommandRatingCriteriaUi();
  await ensureSession();
  attachPageEvents();
  const commandLunchDateInput = document.getElementById("mobileCommandLunchDate");
  if (commandLunchDateInput && !commandLunchDateInput.value) {
    commandLunchDateInput.value = new Date().toISOString().slice(0, 10);
  }
  await loadPageData();
}

init();
