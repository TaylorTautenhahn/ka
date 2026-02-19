const authSection = document.getElementById("platformAuth");
const consoleSection = document.getElementById("platformConsole");
const loginForm = document.getElementById("platformLoginForm");
const logoutBtn = document.getElementById("platformLogoutBtn");
const refreshBtn = document.getElementById("platformRefreshBtn");
const platformRememberMe = document.getElementById("platformRememberMe");
const createTenantForm = document.getElementById("createTenantForm");
const editTenantForm = document.getElementById("editTenantForm");
const editTenantSlug = document.getElementById("editTenantSlug");
const tenantList = document.getElementById("tenantList");
const toastEl = document.getElementById("platformToast");
const sessionTitle = document.getElementById("platformSessionTitle");
const createCriteriaGrid = document.getElementById("createCriteriaGrid");
const editCriteriaGrid = document.getElementById("editCriteriaGrid");
const editMemberSignupLink = document.getElementById("editMemberSignupLink");
const editMemberSignupQr = document.getElementById("editMemberSignupQr");

const BASE_RATING_CRITERIA = [
  { field: "good_with_girls", label: "Good with girls", short_label: "Girls", max: 10 },
  { field: "will_make_it", label: "Will make it through process", short_label: "Process", max: 10 },
  { field: "personable", label: "Personable", short_label: "Personable", max: 10 },
  { field: "alcohol_control", label: "Alcohol control", short_label: "Alcohol", max: 10 },
  { field: "instagram_marketability", label: "Instagram marketability", short_label: "IG", max: 5 },
];

const state = {
  tenants: [],
  activeEditSlug: "",
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
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toastEl.classList.add("hidden"), 3000);
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
  const response = await fetch(path, {
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

function setAuthView(isAuthed) {
  authSection.classList.toggle("hidden", isAuthed);
  consoleSection.classList.toggle("hidden", !isAuthed);
}

function parseTagCsv(raw) {
  return String(raw || "")
    .split(/[,;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function tagsToCsv(raw) {
  if (!Array.isArray(raw)) {
    return "";
  }
  return raw.join(",");
}

function optionalNumber(raw) {
  const token = String(raw || "").trim();
  if (!token) {
    return null;
  }
  const parsed = Number(token);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function criteriaByField(raw) {
  const byField = new Map();
  if (Array.isArray(raw)) {
    raw.forEach((item) => {
      if (!item || typeof item !== "object" || !item.field) {
        return;
      }
      byField.set(String(item.field), item);
    });
  }
  return byField;
}

function criteriaRowMarkup(criterion) {
  return `
    <div class="criteria-row" data-field="${escapeHtml(criterion.field)}">
      <div class="criteria-label-col">
        <label>
          Label
          <input class="criteria-label" type="text" value="${escapeHtml(criterion.label)}" maxlength="60" />
        </label>
      </div>
      <div class="criteria-short-col">
        <label>
          Short label
          <input class="criteria-short" type="text" value="${escapeHtml(criterion.short_label)}" maxlength="20" />
        </label>
      </div>
      <div class="criteria-max-col">
        <label>
          Max
          <input class="criteria-max" type="number" min="1" max="10" step="1" value="${escapeHtml(criterion.max)}" />
        </label>
      </div>
    </div>
  `;
}

function renderCriteriaGrid(container, criteria) {
  if (!container) {
    return;
  }
  const byField = criteriaByField(criteria);
  container.innerHTML = BASE_RATING_CRITERIA.map((base) => {
    const merged = {
      ...base,
      ...(byField.get(base.field) || {}),
    };
    return criteriaRowMarkup(merged);
  }).join("");
}

function readCriteriaGrid(container) {
  if (!container) {
    return BASE_RATING_CRITERIA.map((item) => ({ ...item }));
  }
  return Array.from(container.querySelectorAll(".criteria-row")).map((row) => {
    const field = String(row.dataset.field || "").trim();
    const labelInput = row.querySelector("input.criteria-label");
    const shortInput = row.querySelector("input.criteria-short");
    const maxInput = row.querySelector("input.criteria-max");
    return {
      field,
      label: labelInput ? labelInput.value.trim() : "",
      short_label: shortInput ? shortInput.value.trim() : "",
      max: maxInput ? Number(maxInput.value || 0) : null,
    };
  });
}

function currentTenantBySlug(slug) {
  return state.tenants.find((tenant) => tenant.slug === slug) || null;
}

function fillEditForm(tenant) {
  if (!tenant) {
    return;
  }
  state.activeEditSlug = tenant.slug;
  editTenantSlug.value = tenant.slug;
  document.getElementById("editTenantDisplayName").value = tenant.display_name || "";
  document.getElementById("editTenantChapterName").value = tenant.chapter_name || "";
  document.getElementById("editTenantOrgType").value = tenant.org_type || "Fraternity";
  document.getElementById("editTenantSetupTagline").value = tenant.setup_tagline || "";
  document.getElementById("editTenantThemePrimary").value = tenant.theme_primary || "";
  document.getElementById("editTenantThemeSecondary").value = tenant.theme_secondary || "";
  document.getElementById("editTenantThemeTertiary").value = tenant.theme_tertiary || "";
  document.getElementById("editTenantOfficerWeight").value = tenant.role_weights ? tenant.role_weights.officer : "";
  document.getElementById("editTenantRusherWeight").value = tenant.role_weights ? tenant.role_weights.rusher : "";
  document.getElementById("editTenantInterestTags").value = tagsToCsv(tenant.default_interest_tags);
  document.getElementById("editTenantStereotypeTags").value = tagsToCsv(tenant.default_stereotype_tags);
  renderCriteriaGrid(editCriteriaGrid, tenant.rating_criteria || BASE_RATING_CRITERIA);

  if (editMemberSignupLink) {
    editMemberSignupLink.href = tenant.member_signup_path || "#";
  }
  if (editMemberSignupQr) {
    editMemberSignupQr.src = tenant.member_signup_qr_path || "";
    editMemberSignupQr.classList.toggle("hidden", !tenant.member_signup_qr_path);
  }
}

function populateEditTenantSelector() {
  if (!editTenantSlug) {
    return;
  }
  if (!state.tenants.length) {
    editTenantSlug.innerHTML = '<option value="">No organizations available</option>';
    return;
  }
  editTenantSlug.innerHTML = state.tenants
    .map((tenant) => `<option value="${escapeHtml(tenant.slug)}">${escapeHtml(tenant.display_name)} (${escapeHtml(tenant.slug)})</option>`)
    .join("");

  const preferred = currentTenantBySlug(state.activeEditSlug) || state.tenants[0];
  fillEditForm(preferred);
}

function renderTenantList(rows) {
  if (!rows.length) {
    tenantList.innerHTML = '<p class="muted">No organizations configured.</p>';
    return;
  }

  const tableRows = rows
    .map((tenant) => {
      const logo = tenant.logo_path
        ? `<img src="${escapeHtml(tenant.logo_path)}" class="mini-photo" alt="logo" />`
        : "No logo";
      const status = tenant.is_active ? "Active" : "Disabled";
      const path = `/${tenant.slug}`;
      const qr = tenant.member_signup_qr_path
        ? `<img src="${escapeHtml(tenant.member_signup_qr_path)}" class="signup-qr tiny" alt="member signup QR" loading="lazy" />`
        : "";
      return `
        <tr>
          <td>${logo}</td>
          <td>
            <strong>${escapeHtml(tenant.display_name)}</strong>
            <div class="muted">${escapeHtml(path)} | ${escapeHtml(tenant.org_type || "Organization")}</div>
          </td>
          <td>${escapeHtml(tenant.chapter_name || "-")}</td>
          <td>${escapeHtml(tenant.head_seed_username || "-")}</td>
          <td>${escapeHtml(String(tenant.rating_total_max || "-"))}</td>
          <td>
            <div class="action-row">
              <a class="quick-nav-link" href="${escapeHtml(tenant.member_signup_path || `${path}/member`)}" target="_blank" rel="noopener">Member Signup</a>
              ${qr}
            </div>
          </td>
          <td>${escapeHtml(status)}</td>
          <td>
            <div class="action-row">
              <a class="quick-nav-link" href="${escapeHtml(path)}" target="_blank" rel="noopener">Open</a>
              <button type="button" class="secondary edit-tenant" data-slug="${escapeHtml(tenant.slug)}">Edit</button>
              <div class="tenant-logo-upload">
                <input type="file" class="tenant-logo-file" data-slug="${escapeHtml(tenant.slug)}" accept="image/png,image/jpeg,image/webp" />
                <button type="button" class="secondary upload-tenant-logo" data-slug="${escapeHtml(tenant.slug)}">Upload Logo</button>
              </div>
              ${
                tenant.is_default
                  ? ""
                  : `<button type="button" class="secondary disable-tenant" data-slug="${escapeHtml(tenant.slug)}">Disable</button>`
              }
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  tenantList.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Logo</th>
          <th>Name</th>
          <th>Chapter</th>
          <th>Head Login</th>
          <th>Scale</th>
          <th>Member QR</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

async function loadTenants() {
  try {
    const payload = await api("/platform/api/tenants");
    state.tenants = payload.tenants || [];
    renderTenantList(state.tenants);
    populateEditTenantSelector();
  } catch (error) {
    tenantList.innerHTML = '<p class="muted">Unable to load organizations.</p>';
    showToast(error.message || "Unable to load organizations.");
  }
}

async function ensureSession() {
  try {
    const payload = await api("/platform/api/auth/me");
    setAuthView(true);
    sessionTitle.textContent = payload.admin.username;
    await loadTenants();
  } catch {
    setAuthView(false);
  }
}

function readCreateCustomizationPayload() {
  return {
    org_type: document.getElementById("tenantOrgType").value,
    setup_tagline: document.getElementById("tenantSetupTagline").value.trim(),
    theme_primary: document.getElementById("tenantThemePrimary").value.trim() || null,
    theme_secondary: document.getElementById("tenantThemeSecondary").value.trim() || null,
    theme_tertiary: document.getElementById("tenantThemeTertiary").value.trim() || null,
    officer_weight: optionalNumber(document.getElementById("tenantOfficerWeight").value),
    rusher_weight: optionalNumber(document.getElementById("tenantRusherWeight").value),
    default_interest_tags: parseTagCsv(document.getElementById("tenantInterestTags").value),
    default_stereotype_tags: parseTagCsv(document.getElementById("tenantStereotypeTags").value),
    rating_criteria: readCriteriaGrid(createCriteriaGrid),
  };
}

function readEditCustomizationPayload() {
  return {
    display_name: document.getElementById("editTenantDisplayName").value.trim(),
    chapter_name: document.getElementById("editTenantChapterName").value.trim(),
    org_type: document.getElementById("editTenantOrgType").value,
    setup_tagline: document.getElementById("editTenantSetupTagline").value.trim(),
    theme_primary: document.getElementById("editTenantThemePrimary").value.trim() || null,
    theme_secondary: document.getElementById("editTenantThemeSecondary").value.trim() || null,
    theme_tertiary: document.getElementById("editTenantThemeTertiary").value.trim() || null,
    officer_weight: optionalNumber(document.getElementById("editTenantOfficerWeight").value),
    rusher_weight: optionalNumber(document.getElementById("editTenantRusherWeight").value),
    default_interest_tags: parseTagCsv(document.getElementById("editTenantInterestTags").value),
    default_stereotype_tags: parseTagCsv(document.getElementById("editTenantStereotypeTags").value),
    rating_criteria: readCriteriaGrid(editCriteriaGrid),
  };
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("platformUsername").value.trim();
  const password = document.getElementById("platformAccessCode").value;
  const rememberMe = Boolean(platformRememberMe && platformRememberMe.checked);
  try {
    await api("/platform/api/auth/login", {
      method: "POST",
      body: {
        username,
        password,
        remember_me: rememberMe,
      },
    });
    setAuthView(true);
    sessionTitle.textContent = username;
    showToast("Signed in. Loading organizations...");
    await ensureSession();
  } catch (error) {
    showToast(error.message || "Unable to sign in.");
  }
}

async function handleLogout() {
  try {
    await api("/platform/api/auth/logout", { method: "POST" });
  } catch {
    // ignore network errors on logout
  }
  setAuthView(false);
  showToast("Logged out.");
}

async function handleCreateTenant(event) {
  event.preventDefault();
  const body = {
    slug: document.getElementById("tenantSlug").value.trim().toLowerCase(),
    display_name: document.getElementById("tenantDisplayName").value.trim(),
    chapter_name: document.getElementById("tenantChapterName").value.trim(),
    head_seed_username: document.getElementById("tenantHeadUsername").value.trim(),
    head_seed_first_name: document.getElementById("tenantHeadFirstName").value.trim(),
    head_seed_last_name: document.getElementById("tenantHeadLastName").value.trim(),
    head_seed_pledge_class: document.getElementById("tenantHeadPledgeClass").value.trim(),
    head_seed_password: document.getElementById("tenantHeadAccessCode").value,
    ...readCreateCustomizationPayload(),
  };

  try {
    const payload = await api("/platform/api/tenants", {
      method: "POST",
      body,
    });

    const logoFileInput = document.getElementById("tenantLogoFile");
    const logo = logoFileInput.files && logoFileInput.files.length ? logoFileInput.files[0] : null;
    if (logo) {
      const formData = new FormData();
      formData.append("logo", logo);
      await api(`/platform/api/tenants/${payload.tenant.slug}/logo`, {
        method: "POST",
        body: formData,
      });
    }

    createTenantForm.reset();
    renderCriteriaGrid(createCriteriaGrid, BASE_RATING_CRITERIA);
    showToast(`Created ${payload.tenant.display_name}.`);
    await loadTenants();
    const created = currentTenantBySlug(payload.tenant.slug);
    if (created) {
      fillEditForm(created);
    }
  } catch (error) {
    showToast(error.message || "Unable to create organization.");
  }
}

async function handleEditTenant(event) {
  event.preventDefault();
  const slug = editTenantSlug.value.trim();
  if (!slug) {
    showToast("Select an organization first.");
    return;
  }

  try {
    await api(`/platform/api/tenants/${slug}`, {
      method: "PATCH",
      body: readEditCustomizationPayload(),
    });
    showToast(`Updated /${slug}.`);
    await loadTenants();
    const refreshed = currentTenantBySlug(slug);
    if (refreshed) {
      fillEditForm(refreshed);
    }
  } catch (error) {
    showToast(error.message || "Unable to update organization settings.");
  }
}

async function handleTenantListClick(event) {
  const editButton = event.target.closest("button.edit-tenant");
  if (editButton) {
    const slug = editButton.dataset.slug;
    const tenant = currentTenantBySlug(slug);
    if (tenant) {
      fillEditForm(tenant);
      editTenantForm.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    return;
  }

  const uploadButton = event.target.closest("button.upload-tenant-logo");
  if (uploadButton) {
    const slug = uploadButton.dataset.slug;
    if (!slug) {
      return;
    }
    const fileInput = Array.from(tenantList.querySelectorAll("input.tenant-logo-file")).find(
      (input) => input.dataset.slug === slug
    );
    const file = fileInput && fileInput.files && fileInput.files.length ? fileInput.files[0] : null;
    if (!file) {
      showToast("Choose a logo file first.");
      return;
    }
    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading...";
    try {
      const formData = new FormData();
      formData.append("logo", file);
      await api(`/platform/api/tenants/${slug}/logo`, {
        method: "POST",
        body: formData,
      });
      showToast(`Logo updated for /${slug}.`);
      await loadTenants();
    } catch (error) {
      showToast(error.message || "Unable to upload logo.");
    } finally {
      uploadButton.disabled = false;
      uploadButton.textContent = "Upload Logo";
    }
    return;
  }

  const button = event.target.closest("button.disable-tenant");
  if (!button) {
    return;
  }
  const slug = button.dataset.slug;
  if (!slug) {
    return;
  }
  const confirmed = window.confirm(`Disable /${slug}?`);
  if (!confirmed) {
    return;
  }
  try {
    await api(`/platform/api/tenants/${slug}`, { method: "DELETE" });
    await loadTenants();
    showToast(`Disabled /${slug}.`);
  } catch (error) {
    showToast(error.message || "Unable to disable organization.");
  }
}

function attachEvents() {
  loginForm.addEventListener("submit", handleLogin);
  logoutBtn.addEventListener("click", handleLogout);
  refreshBtn.addEventListener("click", loadTenants);
  createTenantForm.addEventListener("submit", handleCreateTenant);
  editTenantForm.addEventListener("submit", handleEditTenant);
  tenantList.addEventListener("click", handleTenantListClick);

  editTenantSlug.addEventListener("change", (event) => {
    const slug = String(event.target.value || "").trim();
    const tenant = currentTenantBySlug(slug);
    if (tenant) {
      fillEditForm(tenant);
    }
  });
}

function init() {
  renderCriteriaGrid(createCriteriaGrid, BASE_RATING_CRITERIA);
  renderCriteriaGrid(editCriteriaGrid, BASE_RATING_CRITERIA);
  attachEvents();
  ensureSession();
}

init();
