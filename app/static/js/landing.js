(function () {
  "use strict";

  const campusImage = document.querySelector(".bb-campus-image img");
  if (campusImage) {
    campusImage.addEventListener("error", () => { campusImage.hidden = true; });
    if (campusImage.complete && !campusImage.naturalWidth) campusImage.hidden = true;
  }

  const navToggle = document.getElementById("bbNavToggle");
  const nav = document.getElementById("bbPrimaryNav");
  if (navToggle && nav) {
    const mobile = window.matchMedia("(max-width: 760px)");
    const label = navToggle.querySelector("[data-nav-label]");
    const setNavOpen = (open) => {
      document.body.classList.toggle("bb-nav-open", open);
      navToggle.setAttribute("aria-expanded", String(open));
      if (label) label.textContent = open ? "Close navigation" : "Open navigation";
    };
    navToggle.addEventListener("click", () => {
      setNavOpen(navToggle.getAttribute("aria-expanded") !== "true");
    });
    nav.addEventListener("click", (event) => {
      if (event.target.closest("a")) setNavOpen(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && navToggle.getAttribute("aria-expanded") === "true") {
        setNavOpen(false);
        navToggle.focus();
      }
    });
    const closeOutside = (event) => {
      if (!nav.contains(event.target) && !navToggle.contains(event.target)) setNavOpen(false);
    };
    document.addEventListener("click", closeOutside);
    document.addEventListener("focusin", closeOutside);
    mobile.addEventListener("change", () => {
      // Never leave keyboard focus inside navigation when a resize hides it.
      if (mobile.matches && nav.contains(document.activeElement)) navToggle.focus();
      if (!mobile.matches && document.activeElement === navToggle) nav.querySelector("a")?.focus();
      setNavOpen(false);
    });
    document.body.classList.add("bb-nav-ready");
    navToggle.hidden = false;
  }

  const orgSearch = document.getElementById("bbOrgSearchInput");
  const orgCount = document.getElementById("bbOrgSearchCount");
  const orgEmpty = document.getElementById("bbOrgNoResults");
  const orgClear = document.getElementById("bbOrgSearchClear");
  const orgCards = Array.from(document.querySelectorAll(".bb-org-card[data-org-search]"));
  if (orgSearch) {
    const normalize = (value) => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const searchableCards = orgCards.map((card) => ({ card, text: normalize(card.dataset.orgSearch || "") }));
    const filterOrganizations = () => {
      const terms = normalize(orgSearch.value).trim().split(/\s+/).filter(Boolean);
      let visible = 0;
      searchableCards.forEach(({ card, text }) => {
        const matches = terms.every((term) => text.includes(term));
        card.hidden = !matches;
        if (matches) visible += 1;
      });
      if (orgCount) orgCount.textContent = `${visible} organization${visible === 1 ? "" : "s"} ${terms.length ? "found" : "available"}`;
      if (orgEmpty) orgEmpty.hidden = visible > 0 || orgCards.length === 0;
    };
    orgSearch.addEventListener("input", filterOrganizations);
    orgClear?.addEventListener("click", () => {
      orgSearch.value = "";
      filterOrganizations();
      orgSearch.focus();
    });
    // Reconcile browser-restored search values with the server-rendered list.
    window.addEventListener("pageshow", filterOrganizations);
    filterOrganizations();
  }

  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (!motion.matches && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll(".bb-reveal").forEach((node) => observer.observe(node));
    motion.addEventListener("change", (event) => {
      if (event.matches) observer.disconnect();
    });
  }
})();
