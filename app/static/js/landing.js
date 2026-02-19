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
    const nodes = [
      { id: "r1", label: "Rushee A", type: "rushee", x: 0.16, y: 0.22, radius: 5.3, phase: 0.2, depth: 0.9 },
      { id: "r2", label: "Rushee B", type: "rushee", x: 0.14, y: 0.5, radius: 5.5, phase: 1.1, depth: 0.9 },
      { id: "r3", label: "Rushee C", type: "rushee", x: 0.18, y: 0.78, radius: 5.2, phase: 2.3, depth: 0.9 },
      { id: "off1", label: "Officer", type: "officer", x: 0.36, y: 0.18, radius: 4.4, phase: 0.9, depth: 0.75 },
      { id: "off2", label: "Officer", type: "officer", x: 0.34, y: 0.84, radius: 4.4, phase: 2.8, depth: 0.75 },
      { id: "hub", label: "Match Engine", type: "hub", x: 0.5, y: 0.5, radius: 7.6, phase: 1.5, depth: 1.2 },
      { id: "o1", label: "Org X", type: "org", x: 0.84, y: 0.24, radius: 5.3, phase: 0.4, depth: 0.92 },
      { id: "o2", label: "Org Y", type: "org", x: 0.86, y: 0.52, radius: 5.4, phase: 1.8, depth: 0.92 },
      { id: "o3", label: "Org Z", type: "org", x: 0.82, y: 0.8, radius: 5.1, phase: 2.7, depth: 0.92 },
    ];
    const edges = [
      ["r1", "hub"],
      ["r2", "hub"],
      ["r3", "hub"],
      ["off1", "hub"],
      ["off2", "hub"],
      ["hub", "o1"],
      ["hub", "o2"],
      ["hub", "o3"],
      ["r1", "off1"],
      ["r3", "off2"],
    ];
    const dust = Array.from({ length: 30 }, (_, idx) => ({
      x: Math.random(),
      y: Math.random(),
      vx: (Math.random() - 0.5) * 0.00012,
      vy: (Math.random() - 0.5) * 0.00012,
      phase: idx * 0.37,
      size: 0.8 + Math.random() * 1.3,
    }));
    const rusheeIds = nodes.filter((node) => node.type === "rushee").map((node) => node.id);
    const orgIds = nodes.filter((node) => node.type === "org").map((node) => node.id);
    let autoRouteIndex = 0;
    let lastRouteSwitchAt = 0;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(300, Math.round(rect.width * DPR));
      canvas.height = Math.max(220, Math.round(rect.height * DPR));
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    }

    function nodeScreenPosition(node, time) {
      const width = canvas.width / DPR;
      const height = canvas.height / DPR;
      const tiltX = (pointer.x - 0.5) * 26 * node.depth;
      const tiltY = (pointer.y - 0.5) * 20 * node.depth;
      const wobbleX = Math.sin(time * 0.00092 + node.phase * 2.2) * 0.01;
      const wobbleY = Math.cos(time * 0.00104 + node.phase * 1.6) * 0.012;
      return {
        id: node.id,
        label: node.label,
        type: node.type,
        x: (node.x + wobbleX) * width + tiltX,
        y: (node.y + wobbleY) * height + tiltY,
        radius: node.radius * (1 + Math.sin(time * 0.0015 + node.phase) * 0.06),
      };
    }

    function nearestNode(type, x, y, map) {
      let nearest = null;
      let best = Number.POSITIVE_INFINITY;
      for (const node of map.values()) {
        if (node.type !== type) {
          continue;
        }
        const distance = Math.hypot(node.x - x, node.y - y);
        if (distance < best) {
          best = distance;
          nearest = node;
        }
      }
      return nearest;
    }

    function drawNode(screen, color, glow, isActive) {
      ctx.beginPath();
      ctx.fillStyle = color;
      ctx.shadowBlur = isActive ? glow * 1.55 : glow;
      ctx.shadowColor = color;
      ctx.arc(screen.x, screen.y, screen.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    function drawLabel(screen, text) {
      ctx.save();
      ctx.fillStyle = "rgba(223, 236, 255, 0.92)";
      ctx.font = "700 11px Space Grotesk, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(text, screen.x, screen.y - (screen.radius + 10));
      ctx.restore();
    }

    function drawConnection(a, b, intensity, active) {
      const gradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      gradient.addColorStop(0, `rgba(69, 230, 184, ${0.08 + intensity * 0.35})`);
      gradient.addColorStop(0.52, `rgba(184, 214, 255, ${0.08 + intensity * 0.4})`);
      gradient.addColorStop(1, `rgba(53, 203, 255, ${0.1 + intensity * 0.45})`);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = active ? 2 + intensity * 2.2 : 0.9 + intensity * 1.15;
      ctx.shadowBlur = active ? 18 + intensity * 16 : 6 + intensity * 5;
      ctx.shadowColor = active ? "rgba(72, 190, 255, 0.66)" : "rgba(122, 167, 236, 0.24)";
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    function drawPulse(a, b, progress) {
      const x = a.x + (b.x - a.x) * progress;
      const y = a.y + (b.y - a.y) * progress;
      ctx.beginPath();
      ctx.fillStyle = "rgba(213, 233, 255, 0.95)";
      ctx.shadowBlur = 16;
      ctx.shadowColor = "rgba(125, 185, 255, 0.76)";
      ctx.arc(x, y, 2.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    function drawGrid(width, height) {
      const spacing = 36;
      ctx.strokeStyle = "rgba(94, 132, 194, 0.08)";
      ctx.lineWidth = 0.8;
      for (let x = spacing; x < width; x += spacing) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = spacing; y < height; y += spacing) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
    }

    function tick(time) {
      const width = canvas.width / DPR;
      const height = canvas.height / DPR;
      ctx.clearRect(0, 0, width, height);
      drawGrid(width, height);

      dust.forEach((point) => {
        point.x += point.vx;
        point.y += point.vy;
        if (point.x < 0.04 || point.x > 0.96) {
          point.vx *= -1;
        }
        if (point.y < 0.04 || point.y > 0.96) {
          point.vy *= -1;
        }
        const px = point.x * width;
        const py = point.y * height;
        const alpha = 0.18 + (Math.sin(time * 0.0012 + point.phase) + 1) * 0.12;
        ctx.beginPath();
        ctx.fillStyle = `rgba(154, 188, 243, ${alpha.toFixed(3)})`;
        ctx.arc(px, py, point.size, 0, Math.PI * 2);
        ctx.fill();
      });

      const projectedMap = new Map(nodes.map((node) => [node.id, nodeScreenPosition(node, time)]));
      const hub = projectedMap.get("hub");
      if (!hub) {
        window.requestAnimationFrame(tick);
        return;
      }

      let activeRushee = null;
      let activeOrg = null;
      if (pointer.active) {
        const pointerX = pointer.x * width;
        const pointerY = pointer.y * height;
        activeRushee = nearestNode("rushee", pointerX, pointerY, projectedMap);
        activeOrg = nearestNode("org", pointerX, pointerY, projectedMap);
      } else {
        if (time - lastRouteSwitchAt > 2600) {
          autoRouteIndex = (autoRouteIndex + 1) % rusheeIds.length;
          lastRouteSwitchAt = time;
        }
        activeRushee = projectedMap.get(rusheeIds[autoRouteIndex]) || null;
        activeOrg = projectedMap.get(orgIds[autoRouteIndex % orgIds.length]) || null;
      }

      const activeLinks = new Set();
      if (activeRushee && activeOrg) {
        activeLinks.add(`${activeRushee.id}->hub`);
        activeLinks.add(`hub->${activeOrg.id}`);
      }

      edges.forEach(([sourceId, targetId]) => {
        const source = projectedMap.get(sourceId);
        const target = projectedMap.get(targetId);
        if (!source || !target) {
          return;
        }
        const key = `${sourceId}->${targetId}`;
        const reverseKey = `${targetId}->${sourceId}`;
        const isActive = activeLinks.has(key) || activeLinks.has(reverseKey);
        drawConnection(source, target, isActive ? 0.68 : 0.3, isActive);
        if (isActive) {
          const progress = (time * 0.0007 + (sourceId.charCodeAt(0) % 4) * 0.19) % 1;
          drawPulse(source, target, progress);
        }
      });

      projectedMap.forEach((node) => {
        const isActive = (activeRushee && node.id === activeRushee.id) || (activeOrg && node.id === activeOrg.id) || node.id === "hub";
        if (node.type === "rushee") {
          drawNode(node, "rgba(69, 230, 184, 0.95)", 16, isActive);
        } else if (node.type === "org") {
          drawNode(node, "rgba(53, 203, 255, 0.95)", 16, isActive);
        } else if (node.type === "hub") {
          drawNode(node, "rgba(222, 236, 255, 0.96)", 18, true);
        } else {
          drawNode(node, "rgba(153, 183, 238, 0.9)", 10, false);
        }
      });

      if (activeRushee) {
        drawLabel(activeRushee, activeRushee.label);
      }
      drawLabel(hub, "Match Engine");
      if (activeOrg) {
        drawLabel(activeOrg, activeOrg.label);
      }

      if (pointer.active) {
        const pointerScreen = { x: pointer.x * width, y: pointer.y * height, radius: 3.2 };
        drawNode(pointerScreen, "rgba(214, 230, 255, 0.94)", 12, true);
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
