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

if (APP_CONFIG.theme_primary) {
  document.documentElement.style.setProperty("--accent", APP_CONFIG.theme_primary);
  document.documentElement.style.setProperty("--accent-bright", APP_CONFIG.theme_primary);
}
if (APP_CONFIG.theme_secondary) {
  document.documentElement.style.setProperty("--gold", APP_CONFIG.theme_secondary);
}

const toastEl = document.getElementById("mobileToast");

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

function renderHomeStats(pnms) {
  const pnmCountEl = document.getElementById("mobilePnmCount");
  const ratingCountEl = document.getElementById("mobileRatingCount");
  const lunchCountEl = document.getElementById("mobileLunchCount");
  if (!pnmCountEl || !ratingCountEl || !lunchCountEl) {
    return;
  }
  const pnmCount = pnms.length;
  const ratingCount = pnms.reduce((sum, pnm) => sum + Number(pnm.rating_count || 0), 0);
  const lunchCount = pnms.reduce((sum, pnm) => sum + Number(pnm.total_lunches || 0), 0);
  pnmCountEl.textContent = String(pnmCount);
  ratingCountEl.textContent = String(ratingCount);
  lunchCountEl.textContent = String(lunchCount);
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
  const payload = await api("/api/pnms");
  renderHomeStats(payload.pnms || []);
}

async function loadPnmsPage() {
  const payload = await api("/api/pnms");
  renderPnmCards(payload.pnms || []);
}

async function loadMembersPage() {
  const payload = await api("/api/users");
  renderMembers(payload.users || []);
}

async function handleCreateSubmit(event) {
  event.preventDefault();
  const body = {
    first_name: document.getElementById("mobilePnmFirstName").value.trim(),
    last_name: document.getElementById("mobilePnmLastName").value.trim(),
    class_year: document.getElementById("mobilePnmClassYear").value,
    hometown: document.getElementById("mobilePnmHometown").value.trim(),
    phone_number: document.getElementById("mobilePnmPhone").value.trim(),
    instagram_handle: document.getElementById("mobilePnmInstagram").value.trim(),
    first_event_date: document.getElementById("mobilePnmEventDate").value,
    interests: document.getElementById("mobilePnmInterests").value.trim(),
    stereotype: document.getElementById("mobilePnmStereotype").value.trim(),
    lunch_stats: document.getElementById("mobilePnmLunchStats").value.trim(),
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
