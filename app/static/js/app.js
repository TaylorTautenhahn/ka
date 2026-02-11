const authSection = document.getElementById("authSection");
const appSection = document.getElementById("appSection");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const logoutBtn = document.getElementById("logoutBtn");
const installBtn = document.getElementById("installBtn");

const regRole = document.getElementById("regRole");
const regEmoji = document.getElementById("regEmoji");

const sessionTitle = document.getElementById("sessionTitle");
const sessionSubtitle = document.getElementById("sessionSubtitle");
const toastEl = document.getElementById("toast");
const heroPnmCount = document.getElementById("heroPnmCount");
const heroRatingCount = document.getElementById("heroRatingCount");
const heroLunchCount = document.getElementById("heroLunchCount");

const filterInterest = document.getElementById("filterInterest");
const filterStereotype = document.getElementById("filterStereotype");
const applyFiltersBtn = document.getElementById("applyFiltersBtn");
const interestHints = document.getElementById("interestHints");

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

const approvalsPanel = document.getElementById("approvalsPanel");
const pendingList = document.getElementById("pendingList");
const adminPanel = document.getElementById("adminPanel");
const adminPnmTable = document.getElementById("adminPnmTable");

const analyticsCards = document.getElementById("analyticsCards");
const matchingPnms = document.getElementById("matchingPnms");
const matchingMembers = document.getElementById("matchingMembers");

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
  liveRefreshTimer: null,
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

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(path, {
    method: options.method || "GET",
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

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json().catch(() => ({}));
  } else {
    payload = await response.text().catch(() => "");
  }

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? payload.detail
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }

  return payload;
}

function setAuthView(isAuthenticated) {
  authSection.classList.toggle("hidden", isAuthenticated);
  appSection.classList.toggle("hidden", !isAuthenticated);
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
      await Promise.all([loadPnms(), loadMembers(), loadMatching(), loadAnalytics(), loadApprovals()]);
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
  const isRushOfficer = regRole.value === "Rush Officer";
  regEmoji.required = isRushOfficer;
  if (!isRushOfficer) {
    regEmoji.value = "";
  }
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
      const weightedPct = Math.max(0, Math.min(100, (Number(pnm.weighted_total) / 45) * 100));
      const barWidth = Math.round((weightedPct / 100) * 58);
      const selectedClass = state.selectedPnmId === pnm.pnm_id ? "selected-row" : "";
      return `
        <tr class="${selectedClass}">
          <td>${smallPhotoCell(pnm)}</td>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
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

function renderAdminPanel() {
  if (!roleCanUseAdminPanel()) {
    adminPanel.classList.add("hidden");
    adminPnmTable.innerHTML = "";
    return;
  }

  adminPanel.classList.remove("hidden");
  if (!state.pnms.length) {
    adminPnmTable.innerHTML = '<p class="muted">No PNMs to manage.</p>';
    return;
  }

  const rows = state.pnms
    .map(
      (pnm) => `
      <tr>
        <td>${smallPhotoCell(pnm)}</td>
        <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
        <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
        <td>${pnm.weighted_total.toFixed(2)}</td>
        <td>${pnm.rating_count}</td>
        <td><button type="button" class="delete-pnm" data-pnm-id="${pnm.pnm_id}">Remove Rushee</button></td>
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
          <th>Weighted Total</th>
          <th>Ratings</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function applyRatingFormForSelected() {
  if (!state.selectedPnmId) {
    ratingForm.reset();
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    return;
  }

  const selected = state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId);
  if (!selected) {
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    return;
  }

  selectedPnmLabel.textContent = `${selected.pnm_code} | ${selected.first_name} ${selected.last_name}`;
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
        <div class="muted">${escapeHtml(row.notes || "No notes")}</div>
      </div>
    `
    )
    .join("");
}

function renderMeetingView(payload) {
  const { pnm, summary, ratings, lunches, matches, can_view_rater_identity: canSeeRaters } = payload;
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
      .map((row) => `<li><strong>${escapeHtml(row.lunch_date)}</strong>: ${escapeHtml(row.username)} (${escapeHtml(row.role)})</li>`)
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
        <p class="muted">${escapeHtml(pnm.hometown)} | ${escapeHtml(pnm.class_year)} | ${escapeHtml(pnm.instagram_handle)}</p>
        <p class="muted">Interests: ${pnm.interests.map((item) => escapeHtml(item)).join(", ")} | Stereotype: ${escapeHtml(pnm.stereotype)}</p>
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
    meetingView.innerHTML = '<p class="muted">Select a PNM to load the meeting packet.</p>';
    renderSelectedPnmPhoto(null);
    return;
  }

  try {
    const [ratings, lunches] = await Promise.all([
      api(`/api/pnms/${pnmId}/ratings`),
      api(`/api/pnms/${pnmId}/lunches`),
    ]);
    renderRatingEntries(ratings);
    renderLunchEntries(lunches);
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
  applyRatingFormForSelected();
  await loadPnmDetail(state.selectedPnmId);
}

async function loadMembers() {
  const query = toQuery(state.filters);
  const payload = await api(`/api/users${query}`);
  state.members = payload.users || [];
  renderMemberTable();
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

async function loadApprovals() {
  if (!state.user || state.user.role !== "Head Rush Officer") {
    approvalsPanel.classList.add("hidden");
    return;
  }

  const payload = await api("/api/users/pending");
  renderPendingApprovals(payload);
}

async function refreshAll() {
  await Promise.all([loadInterestHints(), loadPnms(), loadMembers(), loadMatching(), loadAnalytics(), loadApprovals()]);
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    await refreshAll();
    startLiveRefresh();
  } catch {
    state.user = null;
    setAuthView(false);
    stopLiveRefresh();
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const accessCode = document.getElementById("loginAccessCode").value;

  if (!username || !accessCode) {
    showToast("Username and access code are required.");
    return;
  }

  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: {
        username,
        access_code: accessCode,
      },
    });
    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    showToast("Logged in.");
    await refreshAll();
    startLiveRefresh();
  } catch (error) {
    showToast(error.message || "Login failed.");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const accessCode = document.getElementById("regAccessCode").value;
  if (accessCode.length < 8 || !/[A-Za-z]/.test(accessCode) || !/[0-9]/.test(accessCode)) {
    showToast("Access code must be 8+ characters with letters and numbers.");
    return;
  }

  const body = {
    first_name: document.getElementById("regFirstName").value.trim(),
    last_name: document.getElementById("regLastName").value.trim(),
    pledge_class: document.getElementById("regPledgeClass").value.trim(),
    role: regRole.value,
    emoji: regEmoji.value.trim() || null,
    stereotype: document.getElementById("regStereotype").value.trim(),
    interests: document.getElementById("regInterests").value.trim(),
    access_code: accessCode,
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
  animateCounter(heroPnmCount, 0);
  animateCounter(heroRatingCount, 0);
  animateCounter(heroLunchCount, 0);
  meetingView.innerHTML = '<p class="muted">Select a PNM to load the meeting packet.</p>';
  renderSelectedPnmPhoto(null);
  renderAdminPanel();
  stopLiveRefresh();
  setAuthView(false);
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

  const body = {
    first_name: document.getElementById("pnmFirstName").value.trim(),
    last_name: document.getElementById("pnmLastName").value.trim(),
    class_year: document.getElementById("pnmClassYear").value,
    hometown: document.getElementById("pnmHometown").value.trim(),
    instagram_handle: document.getElementById("pnmInstagram").value.trim(),
    first_event_date: document.getElementById("pnmEventDate").value,
    interests: document.getElementById("pnmInterests").value.trim(),
    stereotype: document.getElementById("pnmStereotype").value.trim(),
    lunch_stats: document.getElementById("pnmLunchStats").value.trim(),
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
    notes: document.getElementById("lunchNotes").value.trim(),
  };

  try {
    await api("/api/lunches", {
      method: "POST",
      body,
    });
    document.getElementById("lunchNotes").value = "";
    showToast("Lunch logged.");
    state.selectedPnmId = selectedId;
    await refreshAll();
    await loadPnmDetail(selectedId);
  } catch (error) {
    showToast(error.message || "Unable to log lunch.");
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

async function handleAdminPanelClick(event) {
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

  regRole.addEventListener("change", setRoleEmojiRequirement);
  applyFiltersBtn.addEventListener("click", handleApplyFilters);

  pnmForm.addEventListener("submit", handlePnmCreate);
  ratingForm.addEventListener("submit", handleRatingSave);
  lunchForm.addEventListener("submit", handleLunchLog);
  photoForm.addEventListener("submit", handlePhotoUpload);

  pnmTable.addEventListener("click", handlePnmTableClick);
  pendingList.addEventListener("click", handlePendingClick);
  adminPnmTable.addEventListener("click", handleAdminPanelClick);

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
}

async function init() {
  setDefaultDates();
  setRoleEmojiRequirement();
  attachEvents();
  setupPwaInstall();
  await ensureSession();
}

init();
