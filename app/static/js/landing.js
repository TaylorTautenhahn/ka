(function () {
  document.documentElement.classList.add("bb-motion");
  const revealNodes = Array.from(document.querySelectorAll(".bb-reveal"));
  const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const disableMotion = prefersReducedMotion || saveData;

  if (disableMotion) {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  } else if ("IntersectionObserver" in window && revealNodes.length) {
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    revealNodes.forEach((node) => {
      const rect = node.getBoundingClientRect();
      if (rect.top <= viewportHeight * 0.88) {
        node.classList.add("is-visible");
      }
    });

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

    revealNodes.forEach((node) => {
      if (!node.classList.contains("is-visible")) {
        revealObserver.observe(node);
      }
    });
  } else {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  }

  const cursorGlow = document.querySelector(".bb-cursor-glow");
  if (cursorGlow && !disableMotion) {
    let currentX = window.innerWidth * 0.5;
    let currentY = window.innerHeight * 0.34;
    let targetX = currentX;
    let targetY = currentY;

    const syncTarget = (event) => {
      targetX = event.clientX;
      targetY = event.clientY;
      cursorGlow.style.opacity = "0.85";
    };

    window.addEventListener("pointermove", syncTarget, { passive: true });
    window.addEventListener("pointerleave", () => {
      cursorGlow.style.opacity = "0";
    });
    window.addEventListener("pointerenter", () => {
      cursorGlow.style.opacity = "0.85";
    });

    const tickCursor = () => {
      currentX += (targetX - currentX) * 0.14;
      currentY += (targetY - currentY) * 0.14;
      document.documentElement.style.setProperty("--bb-cursor-x", `${currentX}px`);
      document.documentElement.style.setProperty("--bb-cursor-y", `${currentY}px`);
      window.requestAnimationFrame(tickCursor);
    };
    window.requestAnimationFrame(tickCursor);
  }

  const heroStage = document.querySelector(".bb-hero-stage");
  if (heroStage && !disableMotion) {
    heroStage.addEventListener("pointermove", (event) => {
      const rect = heroStage.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return;
      }
      const nx = (event.clientX - rect.left) / rect.width - 0.5;
      const ny = (event.clientY - rect.top) / rect.height - 0.5;
      const rotateY = nx * 5.5;
      const rotateX = -ny * 4.2;
      heroStage.style.transform = `perspective(960px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg)`;
    });

    heroStage.addEventListener("pointerleave", () => {
      heroStage.style.transform = "";
    });
  }

  const counters = Array.from(document.querySelectorAll("[data-count]"));
  if (!counters.length) {
    return;
  }

  if (disableMotion) {
    counters.forEach((counter) => {
      const raw = Number(counter.getAttribute("data-count") || "0");
      const value = Number.isFinite(raw) && raw >= 0 ? raw : 0;
      counter.textContent = String(Math.round(value));
    });
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
