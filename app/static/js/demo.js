function cloneDemoSeed() {
  return [
    {
      id: 1,
      pnm_code: "AJM02162026",
      first_name: "Alex",
      last_name: "Morgan",
      class_year: "F",
      hometown: "Nashville, TN",
      instagram_handle: "@alex.morgan",
      stereotype: "Connector",
      interests: ["Leadership", "Sports", "Finance"],
      rating: {
        good_with_girls: 8,
        will_make_it: 9,
        personable: 9,
        alcohol_control: 8,
        instagram_marketability: 4,
      },
      lunches: [
        { date: "2026-02-10", time: "12:00", location: "Main Dining Hall", note: "Strong conversation" },
      ],
      trend: [
        { changed_at: "2026-02-04T18:00:00Z", total: 34, comment: "Initial assessment." },
        { changed_at: "2026-02-10T21:15:00Z", total: 38, comment: "Higher confidence after roundtable." },
      ],
    },
    {
      id: 2,
      pnm_code: "BTH02162026",
      first_name: "Brooks",
      last_name: "Thompson",
      class_year: "F",
      hometown: "Charlotte, NC",
      instagram_handle: "@brooks.th",
      stereotype: "Leader",
      interests: ["Outdoors", "Philanthropy"],
      rating: {
        good_with_girls: 7,
        will_make_it: 8,
        personable: 8,
        alcohol_control: 9,
        instagram_marketability: 3,
      },
      lunches: [
        { date: "2026-02-11", time: "13:00", location: "Student Center", note: "Consistent and reliable." },
      ],
      trend: [
        { changed_at: "2026-02-05T19:00:00Z", total: 32, comment: "Early positive read." },
        { changed_at: "2026-02-11T22:00:00Z", total: 35, comment: "Improved process confidence." },
      ],
    },
    {
      id: 3,
      pnm_code: "CRM02162026",
      first_name: "Carter",
      last_name: "Mills",
      class_year: "S",
      hometown: "Dallas, TX",
      instagram_handle: "@cartermills",
      stereotype: "Scholar",
      interests: ["Academics", "Music"],
      rating: {
        good_with_girls: 6,
        will_make_it: 7,
        personable: 7,
        alcohol_control: 8,
        instagram_marketability: 4,
      },
      lunches: [
        { date: "2026-02-12", time: "12:30", location: "Campus Cafe", note: "Great one-on-one depth." },
      ],
      trend: [
        { changed_at: "2026-02-06T20:00:00Z", total: 29, comment: "Steady first impression." },
        { changed_at: "2026-02-12T20:30:00Z", total: 32, comment: "More personable than expected." },
      ],
    },
    {
      id: 4,
      pnm_code: "DLS02162026",
      first_name: "Drew",
      last_name: "Sullivan",
      class_year: "F",
      hometown: "Birmingham, AL",
      instagram_handle: "@drewsul",
      stereotype: "Athlete",
      interests: ["Fitness", "Sports", "Travel"],
      rating: {
        good_with_girls: 9,
        will_make_it: 8,
        personable: 8,
        alcohol_control: 6,
        instagram_marketability: 5,
      },
      lunches: [],
      trend: [
        { changed_at: "2026-02-08T21:10:00Z", total: 33, comment: "Great event energy." },
        { changed_at: "2026-02-13T19:10:00Z", total: 36, comment: "High upside if consistency holds." },
      ],
    },
  ];
}

const state = {
  pnms: cloneDemoSeed(),
  selectedPnmId: null,
  toastTimer: null,
};

function scoreTotal(rating) {
  return (
    Number(rating.good_with_girls || 0) +
    Number(rating.will_make_it || 0) +
    Number(rating.personable || 0) +
    Number(rating.alcohol_control || 0) +
    Number(rating.instagram_marketability || 0)
  );
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
  const toast = document.getElementById("demoToast");
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.add("hidden"), 2500);
}

function selectedPnm() {
  return state.pnms.find((pnm) => pnm.id === state.selectedPnmId) || null;
}

function sortAndFilterPnms() {
  const search = String(document.getElementById("demoSearch")?.value || "").trim().toLowerCase();
  const sort = String(document.getElementById("demoSort")?.value || "score");
  const filtered = state.pnms.filter((pnm) => {
    if (!search) {
      return true;
    }
    const haystack = [
      pnm.pnm_code,
      pnm.first_name,
      pnm.last_name,
      pnm.hometown,
      pnm.stereotype,
      pnm.instagram_handle,
      pnm.interests.join(" "),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });

  const sorted = [...filtered];
  if (sort === "name") {
    sorted.sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`));
  } else if (sort === "recent") {
    sorted.sort((a, b) => {
      const aTime = new Date(a.trend[a.trend.length - 1]?.changed_at || 0).getTime();
      const bTime = new Date(b.trend[b.trend.length - 1]?.changed_at || 0).getTime();
      return bTime - aTime;
    });
  } else {
    sorted.sort((a, b) => {
      const delta = scoreTotal(b.rating) - scoreTotal(a.rating);
      if (delta !== 0) {
        return delta;
      }
      return b.lunches.length - a.lunches.length;
    });
  }
  return sorted;
}

function renderKpis() {
  const pnmCount = state.pnms.length;
  const ratingCount = state.pnms.reduce((sum, pnm) => sum + pnm.trend.length, 0);
  const lunchCount = state.pnms.reduce((sum, pnm) => sum + pnm.lunches.length, 0);
  const avgScore =
    pnmCount > 0 ? state.pnms.reduce((sum, pnm) => sum + scoreTotal(pnm.rating), 0) / pnmCount : 0;

  document.getElementById("demoPnmCount").textContent = String(pnmCount);
  document.getElementById("demoRatingCount").textContent = String(ratingCount);
  document.getElementById("demoLunchCount").textContent = String(lunchCount);
  document.getElementById("demoAverageScore").textContent = avgScore.toFixed(1);
}

function renderPnmTable() {
  const rows = sortAndFilterPnms();
  document.getElementById("demoResultCount").textContent = `${rows.length} results`;

  if (!rows.length) {
    document.getElementById("demoPnmTable").innerHTML = '<p class="muted">No demo PNMs match that filter.</p>';
    return;
  }

  const tableRows = rows
    .map((pnm, index) => {
      const isActive = pnm.id === state.selectedPnmId ? " class=\"is-active\"" : "";
      return `
        <tr data-demo-pnm-id="${pnm.id}"${isActive}>
          <td>#${index + 1}</td>
          <td>${escapeHtml(pnm.pnm_code)}</td>
          <td>${escapeHtml(`${pnm.first_name} ${pnm.last_name}`)}</td>
          <td>${scoreTotal(pnm.rating)}</td>
          <td>${pnm.lunches.length}</td>
        </tr>
      `;
    })
    .join("");

  document.getElementById("demoPnmTable").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Code</th>
          <th>Name</th>
          <th>Total</th>
          <th>Lunches</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

function renderTrend(pnm) {
  const trend = pnm.trend
    .slice(-8)
    .map((entry) => {
      const dt = new Date(entry.changed_at);
      const stamp = Number.isNaN(dt.getTime()) ? entry.changed_at : dt.toLocaleString();
      return `<div class="entry"><strong>${entry.total}/45</strong><div class="muted">${escapeHtml(stamp)} | ${escapeHtml(entry.comment || "Updated")}</div></div>`;
    })
    .join("");
  document.getElementById("demoTrend").innerHTML = trend || '<p class="muted">No trend points yet.</p>';
}

function renderActivity(pnm) {
  const ratings = pnm.trend.map((entry) => ({
    stamp: entry.changed_at,
    text: `Rating update -> ${entry.total}/45`,
  }));
  const lunches = pnm.lunches.map((entry) => ({
    stamp: `${entry.date}T${entry.time || "12:00"}:00`,
    text: `Lunch scheduled ${entry.date}${entry.time ? ` ${entry.time}` : ""}${entry.location ? ` at ${entry.location}` : ""}`,
  }));
  const timeline = [...ratings, ...lunches].sort((a, b) => new Date(b.stamp).getTime() - new Date(a.stamp).getTime());
  if (!timeline.length) {
    document.getElementById("demoActivity").innerHTML = '<p class="muted">No activity yet.</p>';
    return;
  }
  document.getElementById("demoActivity").innerHTML = timeline
    .slice(0, 10)
    .map((entry) => `<div class="entry">${escapeHtml(entry.text)}</div>`)
    .join("");
}

function fillRatingForm(pnm) {
  document.getElementById("demoRateGirls").value = String(pnm.rating.good_with_girls);
  document.getElementById("demoRateProcess").value = String(pnm.rating.will_make_it);
  document.getElementById("demoRatePersonable").value = String(pnm.rating.personable);
  document.getElementById("demoRateAlcohol").value = String(pnm.rating.alcohol_control);
  document.getElementById("demoRateIg").value = String(pnm.rating.instagram_marketability);
}

function renderDetail() {
  const pnm = selectedPnm();
  const emptyState = document.getElementById("demoEmptyState");
  const detail = document.getElementById("demoDetail");
  if (!pnm) {
    emptyState.classList.remove("hidden");
    detail.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  detail.classList.remove("hidden");
  document.getElementById("demoSelectedCode").textContent = pnm.pnm_code;
  document.getElementById("demoSelectedName").textContent = `${pnm.first_name} ${pnm.last_name}`;
  document.getElementById("demoSelectedMeta").textContent = `${pnm.class_year} | ${pnm.hometown} | ${pnm.instagram_handle} | ${pnm.stereotype}`;
  fillRatingForm(pnm);
  renderTrend(pnm);
  renderActivity(pnm);
}

function refreshView() {
  renderKpis();
  renderPnmTable();
  renderDetail();
}

function validateRatingBounds(rating) {
  const checks = [
    [rating.good_with_girls, 10],
    [rating.will_make_it, 10],
    [rating.personable, 10],
    [rating.alcohol_control, 10],
    [rating.instagram_marketability, 5],
  ];
  return checks.every(([value, max]) => Number.isFinite(value) && value >= 0 && value <= max);
}

function handlePnmTableClick(event) {
  const row = event.target.closest("tr[data-demo-pnm-id]");
  if (!row) {
    return;
  }
  const id = Number(row.dataset.demoPnmId || 0);
  if (!id) {
    return;
  }
  state.selectedPnmId = id;
  refreshView();
}

function handleRatingSubmit(event) {
  event.preventDefault();
  const pnm = selectedPnm();
  if (!pnm) {
    showToast("Select a demo PNM first.");
    return;
  }

  const nextRating = {
    good_with_girls: Number(document.getElementById("demoRateGirls").value),
    will_make_it: Number(document.getElementById("demoRateProcess").value),
    personable: Number(document.getElementById("demoRatePersonable").value),
    alcohol_control: Number(document.getElementById("demoRateAlcohol").value),
    instagram_marketability: Number(document.getElementById("demoRateIg").value),
  };
  if (!validateRatingBounds(nextRating)) {
    showToast("Rating values are out of range.");
    return;
  }

  const comment = String(document.getElementById("demoRateComment").value || "").trim();
  pnm.rating = nextRating;
  pnm.trend.push({
    changed_at: new Date().toISOString(),
    total: scoreTotal(nextRating),
    comment: comment || "Demo update saved.",
  });
  document.getElementById("demoRateComment").value = "";
  refreshView();
  showToast("Demo rating saved.");
}

function toIsoDateToday() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function handleLunchSubmit(event) {
  event.preventDefault();
  const pnm = selectedPnm();
  if (!pnm) {
    showToast("Select a demo PNM first.");
    return;
  }
  const lunchDate = String(document.getElementById("demoLunchDate").value || "").trim();
  if (!lunchDate) {
    showToast("Lunch date is required.");
    return;
  }
  const lunchTime = String(document.getElementById("demoLunchTime").value || "").trim();
  const lunchLocation = String(document.getElementById("demoLunchLocation").value || "").trim();

  const duplicate = pnm.lunches.some((entry) => entry.date === lunchDate && entry.time === lunchTime);
  if (duplicate) {
    showToast("Duplicate lunch in demo data.");
    return;
  }

  pnm.lunches.push({
    date: lunchDate,
    time: lunchTime,
    location: lunchLocation,
    note: "Scheduled in live demo",
  });
  document.getElementById("demoLunchForm").reset();
  document.getElementById("demoLunchDate").value = toIsoDateToday();
  refreshView();
  showToast("Demo lunch added.");
}

function handleReset() {
  const confirmed = window.confirm("Reset all demo data to the original sample set?");
  if (!confirmed) {
    return;
  }
  state.pnms = cloneDemoSeed();
  state.selectedPnmId = state.pnms.length ? state.pnms[0].id : null;
  refreshView();
  showToast("Demo reset complete.");
}

function csvEscape(value) {
  const token = String(value ?? "");
  if (!/[",\n]/.test(token)) {
    return token;
  }
  return `"${token.replaceAll('"', '""')}"`;
}

function handleDownloadCsv() {
  const rows = [
    [
      "pnm_code",
      "name",
      "class_year",
      "hometown",
      "instagram_handle",
      "stereotype",
      "interests",
      "total_score",
      "lunch_count",
      "last_update",
    ],
  ];
  state.pnms.forEach((pnm) => {
    rows.push([
      pnm.pnm_code,
      `${pnm.first_name} ${pnm.last_name}`,
      pnm.class_year,
      pnm.hometown,
      pnm.instagram_handle,
      pnm.stereotype,
      pnm.interests.join("|"),
      String(scoreTotal(pnm.rating)),
      String(pnm.lunches.length),
      pnm.trend[pnm.trend.length - 1]?.changed_at || "",
    ]);
  });

  const csv = rows.map((row) => row.map(csvEscape).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "bidboard-demo-export.csv";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  showToast("Demo CSV downloaded.");
}

function init() {
  const table = document.getElementById("demoPnmTable");
  const ratingForm = document.getElementById("demoRatingForm");
  const lunchForm = document.getElementById("demoLunchForm");

  table.addEventListener("click", handlePnmTableClick);
  ratingForm.addEventListener("submit", handleRatingSubmit);
  lunchForm.addEventListener("submit", handleLunchSubmit);
  document.getElementById("demoSearch").addEventListener("input", renderPnmTable);
  document.getElementById("demoSort").addEventListener("change", renderPnmTable);
  document.getElementById("demoResetBtn").addEventListener("click", handleReset);
  document.getElementById("demoDownloadBtn").addEventListener("click", handleDownloadCsv);

  document.getElementById("demoLunchDate").value = toIsoDateToday();
  state.selectedPnmId = state.pnms.length ? state.pnms[0].id : null;
  refreshView();
}

document.addEventListener("DOMContentLoaded", init);
