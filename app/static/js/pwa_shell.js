(function () {
  function isStandaloneMode() {
    if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) {
      return true;
    }
    return window.navigator && window.navigator.standalone === true;
  }

  function safeNow() {
    return Date.now();
  }

  function readNumber(rawValue) {
    const parsed = Number(rawValue);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function safeGetStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function safeSetStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Ignore storage write failures.
    }
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) {
      return;
    }
    navigator.serviceWorker.register("/service-worker.js").catch(() => {
      // Registration errors should not block app usage.
    });
  }

  function dispatchInstallEvent(name) {
    try {
      document.dispatchEvent(new CustomEvent(name));
    } catch {
      // Ignore event dispatch failures in older browsers.
    }
  }

  function setupInstallPromptBridge() {
    window.addEventListener("beforeinstallprompt", (event) => {
      event.preventDefault();
      window.__bidboardDeferredInstallPrompt = event;
      dispatchInstallEvent("bidboard:install-ready");
    });

    window.addEventListener("appinstalled", () => {
      window.__bidboardDeferredInstallPrompt = null;
      dispatchInstallEvent("bidboard:installed");
    });
  }

  function getDeferredPrompt() {
    return window.__bidboardDeferredInstallPrompt || null;
  }

  async function promptInstall() {
    const promptEvent = getDeferredPrompt();
    if (!promptEvent) {
      return false;
    }
    promptEvent.prompt();
    try {
      await promptEvent.userChoice;
    } catch {
      // Ignore failures from dismissed install prompts.
    }
    window.__bidboardDeferredInstallPrompt = null;
    return true;
  }

  function initSplash() {
    const splash = document.getElementById("pwaSplash");
    if (!splash) {
      return;
    }

    if (!isStandaloneMode()) {
      splash.classList.add("hidden");
      return;
    }

    const key = `bidboard_splash_seen:${window.location.pathname}`;
    const lastSeen = readNumber(safeGetStorage(key));
    const showIntervalMs = 20 * 60 * 1000;
    const now = safeNow();
    if (now - lastSeen < showIntervalMs) {
      splash.classList.add("hidden");
      return;
    }

    safeSetStorage(key, String(now));
    splash.classList.remove("hidden");
    requestAnimationFrame(() => {
      splash.classList.add("is-visible");
    });

    window.setTimeout(() => {
      splash.classList.remove("is-visible");
      splash.classList.add("is-hidden");
      window.setTimeout(() => {
        splash.classList.add("hidden");
      }, 420);
    }, 1050);
  }

  if (isStandaloneMode()) {
    document.documentElement.classList.add("pwa-standalone");
  }
  document.documentElement.classList.add("pwa-capable");

  registerServiceWorker();
  setupInstallPromptBridge();

  window.BidBoardPwa = {
    isStandaloneMode,
    getDeferredPrompt,
    promptInstall,
  };

  window.addEventListener("DOMContentLoaded", () => {
    initSplash();
  });
})();
