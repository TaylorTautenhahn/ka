const authSection = document.getElementById("platformAuth");
const consoleSection = document.getElementById("platformConsole");
const loginForm = document.getElementById("platformLoginForm");
const logoutBtn = document.getElementById("platformLogoutBtn");
const refreshBtn = document.getElementById("platformRefreshBtn");
const createTenantForm = document.getElementById("createTenantForm");
const tenantList = document.getElementById("tenantList");
const toastEl = document.getElementById("platformToast");
const sessionTitle = document.getElementById("platformSessionTitle");

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
  showToast.timer = setTimeout(() => toastEl.classList.add("hidden"), 2800);
}

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path, {
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

function setAuthView(isAuthed) {
  authSection.classList.toggle("hidden", isAuthed);
  consoleSection.classList.toggle("hidden", !isAuthed);
}

function renderTenantList(rows) {
  if (!rows.length) {
    tenantList.innerHTML = '<p class="muted">No organizations configured.</p>';
    return;
  }
  const tableRows = rows
    .map((tenant) => {
      const logo = tenant.logo_path ? `<img src="${escapeHtml(tenant.logo_path)}" class="mini-photo" alt="logo" />` : "No logo";
      const status = tenant.is_active ? "Active" : "Disabled";
      const path = `/${tenant.slug}`;
      return `
        <tr>
          <td>${logo}</td>
          <td><strong>${escapeHtml(tenant.display_name)}</strong><div class="muted">${escapeHtml(path)}</div></td>
          <td>${escapeHtml(tenant.chapter_name)}</td>
          <td>${escapeHtml(tenant.head_seed_username)}</td>
          <td>${escapeHtml(status)}</td>
          <td>
            <div class="action-row">
              <a class="quick-nav-link" href="${escapeHtml(path)}">Open</a>
              <div class="tenant-logo-upload">
                <input type="file" class="tenant-logo-file" data-slug="${escapeHtml(tenant.slug)}" accept="image/png,image/jpeg,image/webp" />
                <button type="button" class="secondary upload-tenant-logo" data-slug="${escapeHtml(tenant.slug)}">Upload Logo</button>
              </div>
              ${
                tenant.slug === "kappaalphaorder"
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
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

async function loadTenants() {
  const payload = await api("/platform/api/tenants");
  renderTenantList(payload.tenants || []);
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

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("platformUsername").value.trim();
  const accessCode = document.getElementById("platformAccessCode").value;
  try {
    await api("/platform/api/auth/login", {
      method: "POST",
      body: {
        username,
        access_code: accessCode,
      },
    });
    showToast("Signed in.");
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
    head_seed_access_code: document.getElementById("tenantHeadAccessCode").value,
    theme_primary: document.getElementById("tenantThemePrimary").value.trim() || null,
    theme_secondary: document.getElementById("tenantThemeSecondary").value.trim() || null,
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
    showToast(`Created ${payload.tenant.display_name}.`);
    await loadTenants();
  } catch (error) {
    showToast(error.message || "Unable to create organization.");
  }
}

async function handleTenantListClick(event) {
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
  tenantList.addEventListener("click", handleTenantListClick);
}

attachEvents();
ensureSession();
