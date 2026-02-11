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
const MOBILE_PAGE = (document.body && document.body.dataset.mobilePage) || "";
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

const toastEl = document.getElementById("mobileToast");
let mobileCalendarShare = null;

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
      return `<button type="button" class="tag-pill${active}" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`;
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

  picker.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag]");
    if (!button) {
      return;
    }
    const tag = String(button.dataset.tag || "").trim();
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

  picker.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag]");
    if (!button) {
      return;
    }
    const tag = String(button.dataset.tag || "").trim();
    if (!tag) {
      return;
    }
    const current = String(input.value || "").trim().toLowerCase();
    input.value = current === tag.toLowerCase() ? "" : tag;
    syncStereotypePickerFromInput(inputId, pickerId);
  });

  input.addEventListener("input", () => syncStereotypePickerFromInput(inputId, pickerId));
  syncStereotypePickerFromInput(inputId, pickerId);
}

function initializeMobileTagPickers() {
  bindInterestPicker("mobilePnmInterests", "mobileInterestTags");
  bindStereotypePicker("mobilePnmStereotype", "mobileStereotypeTags");
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

async function ensureSession() {
  try {
    await api("/api/auth/me");
  } catch {
    window.location.href = BASE_PATH || "/";
    throw new Error("Not authenticated");
  }
}

function renderMobileCalendarShare(data) {
  mobileCalendarShare = data;
  const googleLink = document.getElementById("mobileGoogleSubscribeLink");
  const preview = document.getElementById("mobileCalendarFeedPreview");
  if (googleLink) {
    googleLink.href = data.google_subscribe_url || "#";
    googleLink.classList.toggle("hidden", !data.google_subscribe_url);
  }
  if (preview) {
    preview.textContent = data.feed_url || "Calendar URL unavailable.";
  }
}

async function handleMobileCopyCalendar() {
  if (!mobileCalendarShare || !mobileCalendarShare.feed_url) {
    showToast("Calendar URL is not ready yet.");
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(mobileCalendarShare.feed_url);
    } else {
      const input = document.createElement("input");
      input.value = mobileCalendarShare.feed_url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      input.remove();
    }
    showToast("Calendar URL copied.");
  } catch {
    showToast("Unable to copy URL.");
  }
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

function renderHomeLeaderboard(rows) {
  const listEl = document.getElementById("mobileLeaderboard");
  if (!listEl) {
    return;
  }
  if (!rows.length) {
    listEl.innerHTML = '<p class="muted">No ranked PNMs yet.</p>';
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
          <div class="muted">Ratings: ${entry.rating_count} | Lunches: ${entry.total_lunches} | Days: ${entry.days_since_first_event}</div>
          <div class="muted">Assigned: ${escapeHtml(assigned)}</div>
        </article>
      `;
    })
    .join("");
}

function renderPnmCards(pnms) {
  const listEl = document.getElementById("mobilePnmList");
  if (!listEl) {
    return;
  }
  if (!pnms.length) {
    listEl.innerHTML = '<p class="muted">No PNMs found.</p>';
    return;
  }
  listEl.innerHTML = pnms
    .map((pnm) => {
      const photo = pnm.photo_url
        ? `<img src="${escapeHtml(pnm.photo_url)}" class="mini-photo" alt="${escapeHtml(pnm.first_name)}" loading="lazy" />`
        : '<div class="mini-photo empty">No photo</div>';
      const assigned = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span>${pnm.weighted_total.toFixed(2)}</span>
          </div>
          <div class="mobile-card-row">
            ${photo}
            <div>
              <div class="muted">${escapeHtml(pnm.phone_number || "No phone")} | ${escapeHtml(pnm.instagram_handle)}</div>
              <div class="muted">Assigned: ${escapeHtml(assigned)}</div>
              <div class="muted">Interests: ${pnm.interests.map((x) => escapeHtml(x)).join(", ")}</div>
            </div>
          </div>
          <div class="action-row">
            <a class="quick-nav-link" href="${escapeHtml(`${MOBILE_BASE}/meeting?pnm_id=${pnm.pnm_id}`)}">Meeting Packet</a>
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
    return;
  }
  listEl.innerHTML = members
    .map((member) => {
      const avg = member.avg_rating_given == null ? "-" : member.avg_rating_given.toFixed(2);
      const ratings = member.rating_count == null ? "-" : member.rating_count;
      return `
        <article class="entry mobile-card">
          <div class="entry-title">
            <strong>${escapeHtml(member.username)}</strong>
            <span>${escapeHtml(member.role)}</span>
          </div>
          <div class="muted">Stereotype: ${escapeHtml(member.stereotype)}</div>
          <div class="muted">Lunches: ${member.total_lunches} | Week: ${member.lunches_per_week.toFixed(2)}</div>
          <div class="muted">Ratings: ${ratings} | Avg Given: ${avg}</div>
        </article>
      `;
    })
    .join("");
}

async function loadHomePage() {
  const payload = await api("/api/mobile/home");
  renderHomeStats(payload.stats || {});
  renderHomeLeaderboard(payload.leaderboard || []);
  if (payload.calendar_share) {
    renderMobileCalendarShare(payload.calendar_share);
  }
}

async function loadPnmsPage() {
  const payload = await api("/api/mobile/pnms");
  renderPnmCards(payload.pnms || []);
}

async function loadMembersPage() {
  const payload = await api("/api/mobile/members");
  renderMembers(payload.users || []);
}

async function handleCreateSubmit(event) {
  event.preventDefault();
  const interestsValue = document.getElementById("mobilePnmInterests").value.trim();
  if (!interestsValue) {
    showToast("Select or type at least one interest.");
    return;
  }
  const body = {
    first_name: document.getElementById("mobilePnmFirstName").value.trim(),
    last_name: document.getElementById("mobilePnmLastName").value.trim(),
    class_year: document.getElementById("mobilePnmClassYear").value,
    hometown: document.getElementById("mobilePnmHometown").value.trim(),
    phone_number: document.getElementById("mobilePnmPhone").value.trim(),
    instagram_handle: document.getElementById("mobilePnmInstagram").value.trim(),
    first_event_date: document.getElementById("mobilePnmEventDate").value,
    interests: interestsValue,
    stereotype: document.getElementById("mobilePnmStereotype").value.trim(),
    lunch_stats: document.getElementById("mobilePnmLunchStats").value.trim(),
    notes: document.getElementById("mobilePnmNotes").value.trim(),
  };

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
    showToast("PNM created.");
    window.location.href = `${MOBILE_BASE}/pnms`;
  } catch (error) {
    showToast(error.message || "Unable to create PNM.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Create PNM";
  }
}

function attachPageEvents() {
  if (MOBILE_PAGE === "home") {
    const copyBtn = document.getElementById("mobileCopyCalendarBtn");
    if (copyBtn) {
      copyBtn.addEventListener("click", handleMobileCopyCalendar);
    }
  }

  if (MOBILE_PAGE === "pnms") {
    const refreshBtn = document.getElementById("mobileRefreshPnmsBtn");
    const downloadBtn = document.getElementById("mobileDownloadContactsBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", async () => {
        try {
          await loadPnmsPage();
          showToast("Refreshed.");
        } catch (error) {
          showToast(error.message || "Unable to refresh PNMs.");
        }
      });
    }
    if (downloadBtn) {
      downloadBtn.addEventListener("click", () => {
        window.location.href = resolveApiPath("/api/export/contacts.vcf");
      });
    }
  }

  if (MOBILE_PAGE === "members") {
    const refreshBtn = document.getElementById("mobileRefreshMembersBtn");
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
  }

  if (MOBILE_PAGE === "create") {
    const form = document.getElementById("mobileCreatePnmForm");
    if (form) {
      form.addEventListener("submit", handleCreateSubmit);
    }
    initializeMobileTagPickers();
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
  }
}

async function init() {
  await ensureSession();
  attachPageEvents();
  await loadPageData();
}

init();
