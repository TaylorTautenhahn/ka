(function () {
  const revealNodes = Array.from(document.querySelectorAll(".bb-reveal"));

  if ("IntersectionObserver" in window && revealNodes.length) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const target = entry.target;
          const delay = Number(target.getAttribute("data-delay") || "0");
          if (delay > 0) {
            target.style.transitionDelay = `${delay}ms`;
          }
          target.classList.add("is-visible");
          observer.unobserve(target);
        });
      },
      {
        root: null,
        threshold: 0.14,
        rootMargin: "0px 0px -8% 0px",
      }
    );

    revealNodes.forEach((node) => revealObserver.observe(node));
  } else {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  }

  const counters = Array.from(document.querySelectorAll("[data-count]"));
  if (!counters.length) {
    return;
  }

  const animateCounter = (el) => {
    if (el.dataset.animated === "1") {
      return;
    }
    el.dataset.animated = "1";
    const end = Number(el.getAttribute("data-count") || "0");
    const safeEnd = Number.isFinite(end) && end >= 0 ? end : 0;
    const duration = 900;
    const start = performance.now();

    const tick = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(safeEnd * eased);
      el.textContent = String(value);
      if (progress < 1) {
        window.requestAnimationFrame(tick);
      }
    };

    window.requestAnimationFrame(tick);
  };

  if ("IntersectionObserver" in window) {
    const counterObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.5 }
    );

    counters.forEach((counter) => counterObserver.observe(counter));
  } else {
    counters.forEach((counter) => animateCounter(counter));
  }
})();
