(function () {
  const doc = document.documentElement;
  const body = document.body;
  const prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const disableMotion = prefersReducedMotion || saveData;

  doc.classList.add("bb-motion");

  const revealNodes = Array.from(document.querySelectorAll(".bb-reveal"));
  if (disableMotion) {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  } else if ("IntersectionObserver" in window && revealNodes.length) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const delay = Number(entry.target.getAttribute("data-delay") || "0");
          if (delay > 0) {
            entry.target.style.transitionDelay = `${delay}ms`;
          }
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { root: null, threshold: 0.14, rootMargin: "0px 0px -6% 0px" }
    );
    revealNodes.forEach((node) => revealObserver.observe(node));
  } else {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
  }

  const themeToggle = document.getElementById("bbThemeToggle");
  const themeMeta = document.querySelector("meta[name='theme-color']");
  const THEME_KEY = "bb-theme";

  function applyTheme(theme) {
    const normalized = theme === "light" ? "light" : "dark";
    doc.setAttribute("data-theme", normalized);
    if (themeMeta) {
      themeMeta.setAttribute("content", normalized === "light" ? "#eef4ff" : "#090b14");
    }
  }

  const storedTheme = window.localStorage ? window.localStorage.getItem(THEME_KEY) : null;
  if (storedTheme === "light" || storedTheme === "dark") {
    applyTheme(storedTheme);
  } else {
    applyTheme("dark");
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = doc.getAttribute("data-theme") === "light" ? "light" : "dark";
      const next = current === "light" ? "dark" : "light";
      applyTheme(next);
      try {
        window.localStorage.setItem(THEME_KEY, next);
      } catch {
        // ignore storage failures
      }
    });
  }

  const cursorGlow = document.querySelector(".bb-cursor-glow");
  if (cursorGlow && !disableMotion) {
    let currentX = window.innerWidth * 0.5;
    let currentY = window.innerHeight * 0.3;
    let targetX = currentX;
    let targetY = currentY;

    function onPointerMove(event) {
      targetX = event.clientX;
      targetY = event.clientY;
      cursorGlow.style.opacity = "0.86";
    }

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerleave", () => {
      cursorGlow.style.opacity = "0";
    });

    const animateCursor = () => {
      currentX += (targetX - currentX) * 0.14;
      currentY += (targetY - currentY) * 0.14;
      doc.style.setProperty("--bb-cursor-x", `${currentX}px`);
      doc.style.setProperty("--bb-cursor-y", `${currentY}px`);
      window.requestAnimationFrame(animateCursor);
    };
    window.requestAnimationFrame(animateCursor);
  }

  const counters = Array.from(document.querySelectorAll("[data-count]"));
  function animateCounter(el) {
    if (el.dataset.animated === "1") {
      return;
    }
    el.dataset.animated = "1";
    const raw = Number(el.getAttribute("data-count") || "0");
    const target = Number.isFinite(raw) && raw >= 0 ? raw : 0;

    if (disableMotion) {
      el.textContent = String(Math.round(target));
      return;
    }

    const duration = 860;
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = String(Math.round(target * eased));
      if (progress < 1) {
        window.requestAnimationFrame(tick);
      }
    };
    window.requestAnimationFrame(tick);
  }

  if (counters.length) {
    if (disableMotion || !("IntersectionObserver" in window)) {
      counters.forEach((el) => animateCounter(el));
    } else {
      const observer = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) {
              return;
            }
            animateCounter(entry.target);
            obs.unobserve(entry.target);
          });
        },
        { threshold: 0.45 }
      );
      counters.forEach((el) => observer.observe(el));
    }
  }

  function initNetworkGraph() {
    const canvas = document.getElementById("bbNetworkCanvas");
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const DPR = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const pointer = { x: 0.5, y: 0.5, active: false };
    const points = [];
    const count = 34;

    function seedPoints() {
      points.length = 0;
      for (let i = 0; i < count; i += 1) {
        points.push({
          x: Math.random(),
          y: Math.random(),
          z: 0.18 + Math.random() * 0.9,
          vx: (Math.random() - 0.5) * 0.00024,
          vy: (Math.random() - 0.5) * 0.00024,
        });
      }
    }

    const rusheeNode = { x: 0.25, y: 0.62, z: 1.25, label: "Rushee" };
    const orgNode = { x: 0.75, y: 0.38, z: 1.25, label: "Organization" };

    function resize() {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(300, Math.round(rect.width * DPR));
      canvas.height = Math.max(220, Math.round(rect.height * DPR));
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    }

    function worldToScreen(point, t) {
      const width = canvas.width / DPR;
      const height = canvas.height / DPR;
      const tiltX = (pointer.x - 0.5) * 30;
      const tiltY = (pointer.y - 0.5) * 22;
      const wobble = Math.sin(t * 0.001 + point.z * 4.2) * 0.005;
      return {
        x: (point.x + wobble) * width + tiltX * point.z,
        y: (point.y - wobble) * height + tiltY * point.z,
        z: point.z,
      };
    }

    function drawNode(screen, radius, color, glow) {
      ctx.beginPath();
      ctx.fillStyle = color;
      ctx.shadowBlur = glow;
      ctx.shadowColor = color;
      ctx.arc(screen.x, screen.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    function drawLabel(screen, text) {
      ctx.save();
      ctx.fillStyle = "rgba(215, 232, 255, 0.95)";
      ctx.font = "700 12px Space Grotesk, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(text, screen.x, screen.y - 16);
      ctx.restore();
    }

    function drawConnection(a, b, intensity) {
      const gradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      gradient.addColorStop(0, `rgba(53, 203, 255, ${0.16 + intensity * 0.5})`);
      gradient.addColorStop(1, `rgba(132, 102, 255, ${0.12 + intensity * 0.5})`);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 1.2 + intensity * 1.5;
      ctx.shadowBlur = 14 + intensity * 12;
      ctx.shadowColor = "rgba(60, 167, 255, 0.55)";
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    function tick(time) {
      const width = canvas.width / DPR;
      const height = canvas.height / DPR;
      ctx.clearRect(0, 0, width, height);

      points.forEach((point) => {
        point.x += point.vx;
        point.y += point.vy;
        if (point.x <= 0.04 || point.x >= 0.96) {
          point.vx *= -1;
        }
        if (point.y <= 0.06 || point.y >= 0.94) {
          point.vy *= -1;
        }
      });

      const projected = points.map((point) => worldToScreen(point, time));

      for (let i = 0; i < projected.length; i += 1) {
        for (let j = i + 1; j < projected.length; j += 1) {
          const a = projected[i];
          const b = projected[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist > 130) {
            continue;
          }
          const alpha = Math.max(0.02, 1 - dist / 130) * 0.18;
          ctx.strokeStyle = `rgba(138, 173, 247, ${alpha.toFixed(3)})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      projected.forEach((point) => {
        const radius = 1.4 + point.z * 1.8;
        drawNode(point, radius, "rgba(174, 203, 255, 0.82)", 7);
      });

      const rusheeScreen = worldToScreen(rusheeNode, time);
      const orgScreen = worldToScreen(orgNode, time);
      drawNode(rusheeScreen, 5.2, "rgba(69, 230, 184, 0.96)", 14);
      drawNode(orgScreen, 5.2, "rgba(53, 203, 255, 0.96)", 14);
      drawLabel(rusheeScreen, rusheeNode.label);
      drawLabel(orgScreen, orgNode.label);

      const connectionIntensity = pointer.active
        ? Math.max(0.22, 1 - Math.hypot(pointer.x - 0.5, pointer.y - 0.5) * 1.35)
        : 0.18 + Math.sin(time * 0.002) * 0.08;
      drawConnection(rusheeScreen, orgScreen, connectionIntensity);

      if (pointer.active) {
        const pointerScreen = {
          x: pointer.x * width,
          y: pointer.y * height,
        };
        drawNode(pointerScreen, 3.6, "rgba(210, 220, 255, 0.95)", 12);
        drawConnection(pointerScreen, rusheeScreen, 0.34);
        drawConnection(pointerScreen, orgScreen, 0.34);
      }

      window.requestAnimationFrame(tick);
    }

    canvas.addEventListener(
      "pointermove",
      (event) => {
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return;
        }
        pointer.x = (event.clientX - rect.left) / rect.width;
        pointer.y = (event.clientY - rect.top) / rect.height;
        pointer.active = true;
      },
      { passive: true }
    );

    canvas.addEventListener("pointerleave", () => {
      pointer.active = false;
    });

    seedPoints();
    resize();
    window.addEventListener("resize", resize, { passive: true });
    window.requestAnimationFrame(tick);
  }

  function initSignalPanel() {
    const officer = document.getElementById("bbOfficerScore");
    const rusher = document.getElementById("bbRusherScore");
    const score = document.getElementById("bbSignalScore");
    const delta = document.getElementById("bbSignalDelta");
    const barFill = document.getElementById("bbSignalBarFill");
    const officerValue = document.getElementById("bbOfficerScoreValue");
    const rusherValue = document.getElementById("bbRusherScoreValue");

    if (!officer || !rusher || !score || !delta || !barFill || !officerValue || !rusherValue) {
      return;
    }

    const baseline = 32;
    function update() {
      const o = Number(officer.value || 0);
      const r = Number(rusher.value || 0);
      const weighted = o * 0.6 + r * 0.4;
      const weightedRounded = Math.round(weighted * 10) / 10;
      const change = Math.round((weightedRounded - baseline) * 10) / 10;
      const normalized = Math.max(0, Math.min(100, (weightedRounded / 45) * 100));

      score.textContent = weightedRounded.toFixed(1);
      officerValue.textContent = String(o);
      rusherValue.textContent = String(r);
      barFill.style.width = `${normalized}%`;

      if (change > 0) {
        delta.textContent = `+${change.toFixed(1)} vs baseline`;
        delta.style.color = "#6de9bd";
      } else if (change < 0) {
        delta.textContent = `${change.toFixed(1)} vs baseline`;
        delta.style.color = "#ff98bc";
      } else {
        delta.textContent = "+0.0 vs baseline";
        delta.style.color = "#92b6e8";
      }
    }

    officer.addEventListener("input", update);
    rusher.addEventListener("input", update);
    update();
  }

  function initJourney() {
    const steps = Array.from(document.querySelectorAll(".bb-journey-step"));
    const screen = document.getElementById("bbPhoneScreen");
    const title = document.getElementById("bbPhoneTitle");
    const badge = document.getElementById("bbPhoneBadge");
    const list = document.getElementById("bbPhoneList");
    const footer = document.getElementById("bbPhoneFooter");

    if (!steps.length || !screen || !title || !badge || !list || !footer) {
      return;
    }

    const states = {
      capture: {
        title: "Event Intake",
        badge: "New",
        items: [
          "First Name: Mason",
          "Last Name: Carter",
          "Class Year: Sophomore",
          "Instagram: @masoncarter",
        ],
        footer: "Synced to chapter board in 1.2s",
      },
      score: {
        title: "Scoring Live",
        badge: "Weighted",
        items: [
          "Officer Score: 34/45",
          "Member Score: 29/45",
          "Weighted Total: 32.0",
          "Trend: +3.2 this week",
        ],
        footer: "Leaderboard rank updated instantly",
      },
      coordinate: {
        title: "Officer Assignment",
        badge: "Scheduled",
        items: [
          "Owner: Jack M. 🔥",
          "Lunch: Tue 12:30 PM",
          "Event: Brotherhood Mixer",
          "Status: Touchpoint planned",
        ],
        footer: "Shared rush calendar auto-updated",
      },
      decide: {
        title: "Meeting Packet",
        badge: "Decision",
        items: [
          "Rating Trend: Upward",
          "Top Notes: Strong fit",
          "Officer Recommendation: Move forward",
          "Board Vote: Ready",
        ],
        footer: "Export packet PDF for chapter review",
      },
    };

    function applyState(key) {
      const state = states[key] || states.capture;
      screen.setAttribute("data-state", key);
      title.textContent = state.title;
      badge.textContent = state.badge;
      list.innerHTML = state.items.map((item) => `<li>${item}</li>`).join("");
      footer.textContent = state.footer;
      steps.forEach((step) => {
        step.classList.toggle("is-active", step.getAttribute("data-step") === key);
      });
    }

    if (disableMotion || !("IntersectionObserver" in window)) {
      applyState("capture");
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        let bestEntry = null;
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          if (!bestEntry || entry.intersectionRatio > bestEntry.intersectionRatio) {
            bestEntry = entry;
          }
        });
        if (!bestEntry) {
          return;
        }
        const step = bestEntry.target.getAttribute("data-step") || "capture";
        applyState(step);
      },
      { threshold: [0.35, 0.6, 0.8], rootMargin: "-10% 0px -30% 0px" }
    );

    steps.forEach((step) => observer.observe(step));
    applyState("capture");
  }

  initNetworkGraph();
  initSignalPanel();
  initJourney();
})();
