(function () {
  const body = document.body;
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  document.documentElement.classList.add("bb-motion");

  const revealNodes = Array.from(document.querySelectorAll(".bb-reveal"));
  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  } else {
    const observer = new IntersectionObserver(
      (entries, instance) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          entry.target.classList.add("is-visible");
          instance.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -5%" }
    );
    revealNodes.forEach((node) => observer.observe(node));
  }

  const navToggle = document.getElementById("bbNavToggle");
  const nav = document.getElementById("bbPrimaryNav");
  const closeNav = () => {
    body.classList.remove("bb-nav-open");
    navToggle?.setAttribute("aria-expanded", "false");
  };

  navToggle?.addEventListener("click", () => {
    const open = !body.classList.contains("bb-nav-open");
    body.classList.toggle("bb-nav-open", open);
    navToggle.setAttribute("aria-expanded", String(open));
  });
  nav?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeNav));
  document.addEventListener("click", (event) => {
    if (!body.classList.contains("bb-nav-open") || nav?.contains(event.target) || navToggle?.contains(event.target)) {
      return;
    }
    closeNav();
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth > 900) {
      closeNav();
    }
  });

  const orgSearch = document.getElementById("bbOrgSearchInput");
  const orgCount = document.getElementById("bbOrgSearchCount");
  const orgCards = Array.from(document.querySelectorAll(".bb-org-card[data-org-search]"));
  orgSearch?.addEventListener("input", () => {
    const query = String(orgSearch.value || "").trim().toLowerCase();
    let visible = 0;
    orgCards.forEach((card) => {
      const matches = !query || String(card.dataset.orgSearch || "").includes(query);
      card.classList.toggle("hidden", !matches);
      visible += matches ? 1 : 0;
    });
    if (orgCount) {
      orgCount.textContent = `${visible} available`;
    }
  });
})();
