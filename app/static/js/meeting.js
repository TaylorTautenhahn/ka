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
const DESKTOP_ROUTES = APP_CONFIG.desktop_routes || {};

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

const pnmSelect = document.getElementById("meetingPnmSelect");
const loadBtn = document.getElementById("meetingLoadBtn");
const refreshBtn = document.getElementById("meetingRefreshBtn");
const pdfBtn = document.getElementById("meetingPdfBtn");
const logoutBtn = document.getElementById("meetingLogoutBtn");
const adminNavLink = document.getElementById("meetingAdminNavLink");
const sessionTitle = document.getElementById("meetingSessionTitle");
const sessionSubtitle = document.getElementById("meetingSessionSubtitle");
const packetEl = document.getElementById("meetingPacket");
const toastEl = document.getElementById("meetingToast");

let currentPnmId = null;
let currentUser = null;
let currentMeetingPins = [];
let currentPacketLabel = "";

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

function requestedPnmIdFromQuery() {
  const pnmId = Number(new URLSearchParams(window.location.search).get("pnm_id") || 0);
  return pnmId > 0 ? pnmId : null;
}

function syncMeetingPacketRoute(pnmId, historyMode = "replace") {
  const mode = String(historyMode || "replace").trim().toLowerCase();
  if (mode === "none") {
    return;
  }
  const url = new URL(window.location.href);
  const selectedId = Number(pnmId || 0);
  if (selectedId > 0) {
    url.searchParams.set("pnm_id", String(selectedId));
  } else {
    url.searchParams.delete("pnm_id");
  }
  const nextUrl = `${url.pathname}${url.search}${url.hash}`;
  const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (nextUrl === currentUrl) {
    return;
  }
  if (mode === "push") {
    window.history.pushState({}, "", nextUrl);
    return;
  }
  window.history.replaceState({}, "", nextUrl);
}

function clearPacket(message = "Select a rushee to load a meeting packet.") {
  currentPnmId = null;
  currentPacketLabel = "";
  packetEl.innerHTML = `<p class="muted">${escapeHtml(message)}</p>`;
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

function renderCategoryRankingBars(rankings) {
  if (!Array.isArray(rankings) || !rankings.length) {
    return '<p class="muted">Category ranking graph appears after ratings are submitted.</p>';
  }
  const rows = rankings
    .map((row, index) => {
      const max = Math.max(1, Number(row.max || 0));
      const value = Math.max(0, Number(row.value || 0));
      const percent = Math.max(0, Math.min(100, (value / max) * 100));
      const rank = Number(row.rank || 0);
      const cohort = Number(row.cohort_size || 0);
      const percentile = Number.isFinite(Number(row.percentile)) ? Number(row.percentile) : 0;
      const pointsFromLeader = Number.isFinite(Number(row.points_from_leader)) ? Number(row.points_from_leader) : 0;
      const leaderLabel = pointsFromLeader <= 0 ? "Leader" : `${pointsFromLeader.toFixed(2)} behind`;
      return `
        <div class="meeting-bar-row">
          <div class="meeting-bar-head">
            <strong>${escapeHtml(row.label || row.field || "Category")}</strong>
            <span>${value.toFixed(2)} / ${max}</span>
          </div>
          <div class="meeting-bar-track">
            <svg class="meeting-bar-track-svg" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true">
              <rect class="meeting-bar-track-base" x="0" y="0" width="100" height="10" rx="5" ry="5"></rect>
              <rect class="meeting-bar-fill-rect" x="0" y="0" width="${percent.toFixed(1)}" height="10" rx="5" ry="5"></rect>
            </svg>
          </div>
          <div class="meeting-bar-meta">
            <span>Rank #${rank || "-"}${cohort ? ` / ${cohort}` : ""}</span>
            <span>${percentile.toFixed(1)} percentile</span>
            <span>${escapeHtml(leaderLabel)}</span>
          </div>
        </div>
      `;
    })
    .join("");
  return `<div class="meeting-bar-graph">${rows}</div>`;
}

function renderRushCommentTimeline(entries) {
  if (!Array.isArray(entries) || !entries.length) {
    return '<p class="muted">No rush comments captured yet.</p>';
  }
  return `
    <div class="meeting-comment-feed">
      ${entries
        .map((entry) => {
          const source = entry.source === "rating_update" ? "Rating Update" : "Lunch Note";
          const chipClass = entry.source === "rating_update" ? "rating" : "lunch";
          const actor = entry.role ? `${entry.username} (${entry.role})` : `${entry.username}`;
          const metaBits = [formatTrendTimestamp(entry.occurred_at), actor].filter(Boolean);
          if (entry.source === "rating_update" && typeof entry.delta_total === "number") {
            metaBits.push(`Delta ${entry.delta_total > 0 ? "+" : ""}${entry.delta_total}`);
          }
          if (entry.source === "lunch_note") {
            if (entry.lunch_date) {
              metaBits.push(entry.lunch_date);
            }
            if (entry.location) {
              metaBits.push(entry.location);
            }
          }
          return `
            <article class="meeting-comment-item">
              <div class="entry-title">
                <span class="comment-chip ${chipClass}">${escapeHtml(source)}</span>
                <span class="comment-meta">${escapeHtml(metaBits.join(" | "))}</span>
              </div>
              <p class="meeting-list-note">${escapeHtml(entry.comment || "")}</p>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function showToast(message) {
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toastEl.classList.add("hidden"), 2600);
}

function currentMeetingPinnedIds() {
  return Array.isArray(currentMeetingPins) ? currentMeetingPins.map((item) => Number(item.pnm_id || 0)).filter((value) => value > 0) : [];
}

function isMeetingPinned(pnmId) {
  return currentMeetingPinnedIds().includes(Number(pnmId));
}

function desktopRoutePath(key, fallbackSuffix) {
  const fromConfig = DESKTOP_ROUTES && DESKTOP_ROUTES[key] ? String(DESKTOP_ROUTES[key]) : "";
  if (fromConfig) {
    return fromConfig;
  }
  return `${BASE_PATH}/${fallbackSuffix}`;
}

function applySessionHeader(user) {
  if (!sessionTitle || !sessionSubtitle) {
    return;
  }
  const packetLabel = currentPacketLabel || "Meeting Packet";
  if (!user) {
    sessionTitle.textContent = packetLabel;
    sessionSubtitle.textContent = "";
    return;
  }
  sessionTitle.textContent = packetLabel;
  const emoji = user.emoji ? `${user.emoji} ` : "";
  const identity = [emoji ? emoji.trimEnd() : "", user.username || "", user.role || ""].filter(Boolean).join(" · ");
  sessionSubtitle.textContent = identity;
}

function applyRoleNavVisibility(user) {
  if (!adminNavLink) {
    return;
  }
  const isHead = Boolean(user && user.role === "Head Rush Officer");
  adminNavLink.classList.toggle("hidden", !isHead);
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

function renderPacket(payload) {
  const {
    pnm,
    summary,
    ratings,
    lunches,
    matches,
    linked_pnms: linkedPnms = [],
    rating_trend: trend,
    category_rankings: categoryRankings = [],
    rating_update_comments: ratingUpdateComments = [],
    lunch_comment_history: lunchCommentHistory = [],
    rush_comment_timeline: rushCommentTimeline = [],
    can_view_rater_identity: canSeeRaters,
    meeting_pin: meetingPin = {},
  } = payload;
  const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
  const linkedSummaryText = Array.isArray(linkedPnms) && linkedPnms.length
    ? linkedPnms.map((item) => `${item.first_name} ${item.last_name}`).join(", ")
    : "None";
  const linkedActionMarkup = Array.isArray(linkedPnms) && linkedPnms.length
    ? `<div class="linked-meeting-actions">
        ${linkedPnms
          .map(
            (item) =>
              `<button type="button" class="secondary linked-meeting-open-btn" data-pnm-id="${Number(item.pnm_id)}">Open ${escapeHtml(item.first_name)} ${escapeHtml(item.last_name)}</button>`
          )
          .join("")}
      </div>`
    : "";
  const trendPoints = trend && Array.isArray(trend.points) ? trend.points : [];
  const trendDelta = trend && typeof trend.delta_weighted_total === "number" ? trend.delta_weighted_total : null;
  const trendDeltaClass = trendDelta == null ? "warn" : trendDelta > 0 ? "good" : trendDelta < 0 ? "bad" : "warn";
  const trendDeltaLabel = trendDelta == null ? "N/A" : `${trendDelta > 0 ? "+" : ""}${trendDelta.toFixed(2)}`;
  const trendEvents = trend && typeof trend.events_count === "number" ? trend.events_count : trendPoints.length;
  const weightedRankLabel =
    summary && Number(summary.weighted_total_rank) > 0 && Number(summary.cohort_size) > 0
      ? `Rank #${Number(summary.weighted_total_rank)} / ${Number(summary.cohort_size)}`
      : "Rank N/A";
  const weightedPercentileLabel =
    summary && Number.isFinite(Number(summary.weighted_total_percentile))
      ? `${Number(summary.weighted_total_percentile).toFixed(1)} percentile`
      : "Percentile N/A";
  const interestsText = Array.isArray(pnm.interests) && pnm.interests.length
    ? pnm.interests.map((item) => escapeHtml(item)).join(", ")
    : "No interests tagged";
  const contactText = pnm.phone_number ? escapeHtml(pnm.phone_number) : "No phone on file";
  const instagramText = pnm.instagram_handle ? escapeHtml(pnm.instagram_handle) : "No Instagram linked";
  const notesText = pnm.notes ? escapeHtml(pnm.notes) : "No notes recorded yet.";
  const photoMarkup = pnm.photo_url
    ? `<img src="${escapeHtml(pnm.photo_url)}" alt="${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}" class="meeting-photo large" loading="lazy" />`
    : '<div class="photo-placeholder large">No photo uploaded.</div>';
  const pinLabel = meetingPin && meetingPin.is_pinned ? "Pinned for Meetings" : "Pin for Meetings";
  const pinMeta = meetingPin && meetingPin.is_pinned
    ? `Pinned by ${meetingPin.pinned_by_username || "Rush team"} | ${formatTrendTimestamp(meetingPin.pinned_at)}`
    : "Use the Meetings shortlist as the single source of truth for packet prep.";
  currentPacketLabel = `${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`;
  applySessionHeader(currentUser);

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
        return `<li><strong>${who}</strong>: ${row.total_score}/${RATING_TOTAL_MAX}${delta}</li>`;
      })
      .join("") || "<li>No ratings yet.</li>";

  const lunchMarkup =
    lunches
      .slice(0, 18)
      .map((row) => {
        const timing = formatLunchWindow(row);
        const detail = timing ? ` | ${escapeHtml(timing)}` : "";
        const notes = row.notes ? `<br /><span class="meeting-list-note">${escapeHtml(row.notes)}</span>` : "";
        return `<li><strong>${escapeHtml(row.lunch_date)}</strong>: ${escapeHtml(row.username)} (${escapeHtml(row.role)})${detail}${notes}</li>`;
      })
      .join("") || "<li>No touchpoint logs yet.</li>";

  const ratingCommentMarkup =
    ratingUpdateComments
      .map((row) => {
        const author = row.author && row.author.username
          ? `${row.author.username}${row.author.role ? ` (${row.author.role})` : ""}`
          : row.from_me
            ? "You"
            : "Member";
        const deltaText = typeof row.delta_total === "number" ? `${row.delta_total > 0 ? "+" : ""}${row.delta_total}` : "0";
        const eventText = row.event_type === "create" ? "Initial Rating" : `Update (${deltaText})`;
        return `
          <li>
            <strong>${escapeHtml(eventText)}</strong> | ${escapeHtml(formatTrendTimestamp(row.changed_at))}
            <span class="comment-meta">${escapeHtml(author)} | ${Number(row.new_total || 0).toFixed(0)} / ${RATING_TOTAL_MAX}</span>
            <p class="meeting-list-note">${escapeHtml(row.comment || "")}</p>
          </li>
        `;
      })
      .join("") || "<li>No rating update comments yet.</li>";

  const lunchCommentMarkup =
    lunchCommentHistory
      .map((row) => {
        return `
          <li>
            <strong>${escapeHtml(row.lunch_date)}</strong> | ${escapeHtml(row.username)} (${escapeHtml(row.role)})
            <span class="comment-meta">${escapeHtml(formatLunchWindow(row) || row.location || "")}</span>
            <p class="meeting-list-note">${escapeHtml(row.notes || "")}</p>
          </li>
        `;
      })
      .join("") || "<li>No touchpoint notes yet.</li>";

  const matchMarkup =
    matches
      .slice(0, 10)
      .map((row) => {
        const shared = row.shared_interests.length ? row.shared_interests.map((x) => escapeHtml(x)).join(", ") : "None";
        return `<li><strong>${escapeHtml(row.username)}</strong> (${escapeHtml(row.role)}) | Fit ${row.fit_score} | Shared: ${shared}</li>`;
      })
      .join("") || "<li>No fit matches yet.</li>";

  packetEl.innerHTML = `
    <div class="meeting-parent-strip">
      <div>
        <p class="eyebrow">Meetings Workspace</p>
        <h3>Meeting Packet</h3>
        <p class="muted">${escapeHtml(pinMeta)}</p>
      </div>
      <div class="action-row">
        <button type="button" class="secondary meeting-pin-toggle-btn" data-meeting-pin-id="${Number(pnm.pnm_id)}">${escapeHtml(pinLabel)}</button>
        <a class="quick-nav-link" href="${escapeHtml(`${desktopRoutePath("rushees", "rushees")}?pnm_id=${Number(pnm.pnm_id)}`)}">Open Rushee Workspace</a>
        <a class="quick-nav-link" href="${escapeHtml(desktopRoutePath("meetings", "meetings"))}">Back to Meetings Queue</a>
      </div>
    </div>
    <div class="meeting-header">
      ${photoMarkup}
      <div class="meeting-hero-copy">
        <div>
          <p class="eyebrow">Packet Read</p>
          <h3>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</h3>
          <p class="muted">Meeting-ready context, linked packet relationships, and rush-team notes in one review surface.</p>
        </div>
        <div class="meeting-meta-grid">
          <article class="meeting-meta-card">
            <span>Profile</span>
            <strong>${escapeHtml(pnm.hometown)} | ${escapeHtml(pnm.class_year)}</strong>
            <p>Stereotype: ${escapeHtml(pnm.stereotype || "Not set")} | Interests: ${interestsText}</p>
          </article>
          <article class="meeting-meta-card">
            <span>Contact</span>
            <strong>${instagramText}</strong>
            <p>${contactText}</p>
          </article>
          <article class="meeting-meta-card">
            <span>Assignment</span>
            <strong>${escapeHtml(assignedOfficer)}</strong>
            <p>${escapeHtml(weightedRankLabel)} | ${escapeHtml(weightedPercentileLabel)}</p>
          </article>
          <article class="meeting-meta-card">
            <span>Linked With</span>
            <strong>${escapeHtml(linkedSummaryText)}</strong>
            <p>${escapeHtml(pinMeta)}</p>
          </article>
        </div>
        <div class="meeting-note-callout">
          <span>Notes</span>
          <p>${notesText}</p>
        </div>
        ${linkedActionMarkup}
      </div>
    </div>
    <div class="meeting-metrics">
      <article class="card">
        <strong>Weighted Total</strong>
        <p>${formatWeightedScore(summary.weighted_total)}</p>
        ${ratingTierBadgeMarkup(summary.weighted_total)}
        <small class="metric-sub">${escapeHtml(weightedRankLabel)} | ${escapeHtml(weightedPercentileLabel)}</small>
      </article>
      <article class="card"><strong>Ratings Count</strong><p>${summary.ratings_count}</p></article>
      <article class="card"><strong>Highest / Lowest</strong><p>${summary.highest_rating_total ?? "-"} / ${summary.lowest_rating_total ?? "-"}</p></article>
      <article class="card"><strong>Total Touchpoints</strong><p>${summary.total_lunches}</p></article>
    </div>
    <div class="meeting-analytics-grid">
    <article class="list-column meeting-section-card">
      <div class="entry-title">
        <h3>Long-Term Rating Trend</h3>
        <span class="${trendDeltaClass}">${trendDeltaLabel}</span>
      </div>
      <p class="muted">Weighted total trajectory over time from rating history events: ${trendEvents}</p>
      ${renderTrendChart(trendPoints)}
    </article>
    <article class="list-column meeting-section-card">
      <div class="entry-title">
        <h3>Category Ranking Averages</h3>
        <span class="warn">${Number(summary.cohort_size || 0)} Rushees</span>
      </div>
      <p class="muted">Weighted category averages with standing across the active roster.</p>
      ${renderCategoryRankingBars(categoryRankings)}
    </article>
    </div>
    <div class="grid-two meeting-detail-grid">
      <article class="list-column meeting-section-card">
        <h3>Ratings</h3>
        <ul class="meeting-list">${ratingsMarkup}</ul>
      </article>
      <article class="list-column meeting-section-card">
        <h3>Touchpoints</h3>
        <ul class="meeting-list">${lunchMarkup}</ul>
      </article>
    </div>
    <div class="grid-two meeting-comment-grid">
      <article class="list-column meeting-section-card">
        <h3>All Rating Update Comments</h3>
        <ul class="meeting-list meeting-list-detailed">${ratingCommentMarkup}</ul>
      </article>
      <article class="list-column meeting-section-card">
        <h3>All Touchpoint Notes</h3>
        <ul class="meeting-list meeting-list-detailed">${lunchCommentMarkup}</ul>
      </article>
    </div>
    <article class="list-column meeting-section-card">
      <h3>Rush Comment Timeline</h3>
      ${renderRushCommentTimeline(rushCommentTimeline)}
    </article>
    <article class="list-column meeting-section-card">
      <h3>Best Member Matches</h3>
      <ul class="meeting-list">${matchMarkup}</ul>
    </article>
  `;
}

async function loadMeetingPins() {
  try {
    const payload = await api("/api/meetings/pins");
    currentMeetingPins = Array.isArray(payload.pins) ? payload.pins : [];
  } catch {
    currentMeetingPins = [];
  }
}

async function handleMeetingPinToggle(event) {
  const button = event.target.closest("[data-meeting-pin-id]");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.meetingPinId || 0);
  if (!pnmId) {
    return;
  }
  const wasPinned = isMeetingPinned(pnmId);
  const payload = wasPinned
    ? await api(`/api/meetings/pins/${pnmId}`, { method: "DELETE" })
    : await api("/api/meetings/pins", { method: "POST", body: { pnm_id: pnmId } });
  currentMeetingPins = Array.isArray(payload.pins) ? payload.pins : [];
  if (currentPnmId === pnmId) {
    await loadPacket();
  }
  showToast(wasPinned ? "Removed from Meetings pins." : "Pinned for Meetings.");
}

async function loadPacket(options = {}) {
  const selected = Number(pnmSelect.value || 0);
  if (!selected) {
    showToast("Select a rushee first.");
    return;
  }
  currentPnmId = selected;
  try {
    const payload = await api(`/api/pnms/${selected}/meeting`);
    renderPacket(payload);
    syncMeetingPacketRoute(selected, options.historyMode || "replace");
  } catch (error) {
    packetEl.innerHTML = '<p class="muted">Unable to load meeting packet.</p>';
    showToast(error.message || "Unable to load meeting packet.");
  }
}

async function loadPnms() {
  const payload = await api("/api/pnms");
  const pnms = payload.pnms || [];
  pnmSelect.innerHTML =
    '<option value="">Select rushee</option>' +
    pnms
      .map((pnm) => `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`)}</option>`)
      .join("");
  if (currentPnmId && pnms.find((item) => item.pnm_id === currentPnmId)) {
    pnmSelect.value = String(currentPnmId);
  }
  return pnms;
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    currentUser = payload && payload.authenticated && payload.user ? payload.user : null;
    if (!currentUser) {
      window.location.href = BASE_PATH || "/";
      return false;
    }
    if (currentUser && currentUser.role === "Rusher" && APP_CONFIG.member_base) {
      window.location.replace(APP_CONFIG.member_base);
      return false;
    }
    applySessionHeader(currentUser);
    applyRoleNavVisibility(currentUser);
    return true;
  } catch {
    window.location.href = BASE_PATH || "/";
    return false;
  }
}

async function handleLogout() {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    // Fallback to redirect below even if logout call fails.
  }
  window.location.href = desktopRoutePath("dashboard", "dashboard");
}

function attachEvents() {
  loadBtn.addEventListener("click", () => {
    loadPacket({ historyMode: "push" });
  });
  refreshBtn.addEventListener("click", async () => {
    try {
      await loadPnms();
      if (currentPnmId) {
        pnmSelect.value = String(currentPnmId);
        await loadPacket({ historyMode: "none" });
      }
      showToast("Refreshed.");
    } catch (error) {
      showToast(error.message || "Refresh failed.");
    }
  });
  pdfBtn.addEventListener("click", () => {
    window.print();
  });
  if (logoutBtn) {
    logoutBtn.addEventListener("click", handleLogout);
  }
  packetEl.addEventListener("click", async (event) => {
    if (event.target.closest("[data-meeting-pin-id]")) {
      try {
        await handleMeetingPinToggle(event);
      } catch (error) {
        showToast(error.message || "Unable to update Meetings pin.");
      }
      return;
    }
    const button = event.target.closest(".linked-meeting-open-btn");
    if (!button) {
      return;
    }
    const linkedId = Number(button.dataset.pnmId || 0);
    if (!linkedId) {
      return;
    }
    currentPnmId = linkedId;
    pnmSelect.value = String(linkedId);
    await loadPacket({ historyMode: "push" });
  });
  window.addEventListener("popstate", async () => {
    currentPnmId = requestedPnmIdFromQuery();
    const pnms = await loadPnms();
    if (currentPnmId && pnms.some((item) => Number(item.pnm_id) === Number(currentPnmId))) {
      pnmSelect.value = String(currentPnmId);
      await loadPacket({ historyMode: "none" });
      return;
    }
    pnmSelect.value = "";
    clearPacket();
  });
}

async function init() {
  const ok = await ensureSession();
  if (!ok) {
    return;
  }
  await loadMeetingPins();
  const fromQuery = Number(requestedPnmIdFromQuery() || 0);
  if (fromQuery) {
    currentPnmId = fromQuery;
  }
  await loadPnms();
  if (currentPnmId) {
    pnmSelect.value = String(currentPnmId);
    await loadPacket({ historyMode: "none" });
  } else {
    clearPacket();
  }
  attachEvents();
}

init();
