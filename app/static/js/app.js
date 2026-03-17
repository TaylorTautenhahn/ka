function readAppConfig() {
  if (window.APP_CONFIG) {
    return window.APP_CONFIG;
  }
  const bodyValue = document.body ? document.body.dataset.appConfig : "";
  if (bodyValue) {
    try {
      return JSON.parse(bodyValue);
    } catch {
      // ignore malformed config and continue to fallback
    }
  }
  const node = document.getElementById("appConfig");
  if (!node) {
    return {};
  }
  try {
    return JSON.parse(node.textContent || "{}");
  } catch {
    return {};
  }
}

const APP_CONFIG = readAppConfig();
const BASE_PATH = (APP_CONFIG.base_path || "").replace(/\/$/, "");
const API_BASE = (APP_CONFIG.api_base || "/api").replace(/\/$/, "");
const MEETING_BASE = (APP_CONFIG.meeting_base || `${BASE_PATH}/meeting`).replace(/\/$/, "");
const TENANT_KEY = String(APP_CONFIG.tenant_slug || "default").trim() || "default";

function clampChannel(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function hexToRgb(hex) {
  const normalized = String(hex || "").trim();
  const match = normalized.match(/^#([0-9a-fA-F]{6})$/);
  if (!match) {
    return null;
  }
  const token = match[1];
  return {
    r: Number.parseInt(token.slice(0, 2), 16),
    g: Number.parseInt(token.slice(2, 4), 16),
    b: Number.parseInt(token.slice(4, 6), 16),
  };
}

function rgbToHex(rgb) {
  const toHex = (value) => clampChannel(value).toString(16).padStart(2, "0");
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

function mixRgb(base, target, ratio) {
  const t = Math.max(0, Math.min(1, ratio));
  return {
    r: clampChannel(base.r + (target.r - base.r) * t),
    g: clampChannel(base.g + (target.g - base.g) * t),
    b: clampChannel(base.b + (target.b - base.b) * t),
  };
}

function rgbTriplet(rgb) {
  return `${rgb.r}, ${rgb.g}, ${rgb.b}`;
}

function applyTenantTheme(config) {
  const root = document.documentElement;
  const accentBase = hexToRgb(config.theme_primary) || hexToRgb("#8a1538");
  const goldBase = hexToRgb(config.theme_secondary) || hexToRgb("#c99a2b");
  const tertiaryBase = hexToRgb(config.theme_tertiary) || hexToRgb("#1d7a4b");
  if (!accentBase || !goldBase || !tertiaryBase) {
    return;
  }

  const accentBright = mixRgb(accentBase, { r: 255, g: 255, b: 255 }, 0.16);
  const accentSoft = mixRgb(accentBase, { r: 255, g: 255, b: 255 }, 0.11);
  const accentDeep = mixRgb(accentBase, { r: 0, g: 0, b: 0 }, 0.34);
  const accentShadow = mixRgb(accentBase, { r: 0, g: 0, b: 0 }, 0.42);
  const heading = mixRgb(accentBase, { r: 36, g: 24, b: 31 }, 0.32);

  root.style.setProperty("--accent", rgbToHex(accentBase));
  root.style.setProperty("--accent-bright", rgbToHex(accentBright));
  root.style.setProperty("--gold", rgbToHex(goldBase));
  root.style.setProperty("--accent-rgb", rgbTriplet(accentBase));
  root.style.setProperty("--accent-soft-rgb", rgbTriplet(accentSoft));
  root.style.setProperty("--accent-deep-rgb", rgbTriplet(accentDeep));
  root.style.setProperty("--accent-shadow-rgb", rgbTriplet(accentShadow));
  root.style.setProperty("--gold-rgb", rgbTriplet(goldBase));
  root.style.setProperty("--heading", rgbToHex(heading));
  root.style.setProperty("--good", rgbToHex(tertiaryBase));
}

applyTenantTheme(APP_CONFIG);

const authShell = document.getElementById("authShell");
const authHero = document.getElementById("authHero");
const authSection = document.getElementById("authSection");
const appSection = document.getElementById("appSection");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const logoutBtn = document.getElementById("logoutBtn");
const installBtn = document.getElementById("installBtn");
const openTutorialBtn = document.getElementById("openTutorialBtn");
const loginRememberMe = document.getElementById("loginRememberMe");
const globalAddMenu = document.getElementById("globalAddMenu");
const appHelpMenu = document.getElementById("appHelpMenu");

const regEmoji = document.getElementById("regEmoji");

const workspaceEyebrow = document.getElementById("workspaceEyebrow");
const workspaceTitle = document.getElementById("workspaceTitle");
const workspaceSubtitle = document.getElementById("workspaceSubtitle");
const sessionTitle = document.getElementById("sessionTitle");
const sessionSubtitle = document.getElementById("sessionSubtitle");
const globalCommandBtn = document.getElementById("globalCommandBtn");
const globalSearchInput = document.getElementById("globalSearchInput");
const globalCommandPalette = document.getElementById("globalCommandPalette");
const commandPaletteInput = document.getElementById("commandPaletteInput");
const commandPaletteResults = document.getElementById("commandPaletteResults");
const commandPaletteCloseBtn = document.getElementById("commandPaletteCloseBtn");
const appNotificationsBtn = document.getElementById("appNotificationsBtn");
const appNotificationsBadge = document.getElementById("appNotificationsBadge");
const appNotificationsTray = document.getElementById("appNotificationsTray");
const appNotificationsList = document.getElementById("appNotificationsList");
const appNotificationsCloseBtn = document.getElementById("appNotificationsCloseBtn");
const toastEl = document.getElementById("toast");
const heroStats = document.getElementById("heroStats");
const heroPnmCount = document.getElementById("heroPnmCount");
const heroRatingCount = document.getElementById("heroRatingCount");
const heroLunchCount = document.getElementById("heroLunchCount");

const rusheeFilterInterest = document.getElementById("rusheeFilterInterest");
const rusheeFilterStereotype = document.getElementById("rusheeFilterStereotype");
const rusheeFilterState = document.getElementById("rusheeFilterState");
const matchingFilterInterest = document.getElementById("matchingFilterInterest");
const matchingFilterStereotype = document.getElementById("matchingFilterStereotype");
const matchingFilterState = document.getElementById("matchingFilterState");
const applyMatchingFiltersBtn = document.getElementById("applyMatchingFiltersBtn");
const memberFilterRole = document.getElementById("memberFilterRole");
const memberFilterState = document.getElementById("memberFilterState");
const memberFilterCity = document.getElementById("memberFilterCity");
const memberSortSelectDesktop = document.getElementById("memberSortSelectDesktop");
const interestHints = document.getElementById("interestHints");
const stereotypeFilterHints = document.getElementById("stereotypeFilterHints");
const stateFilterHints = document.getElementById("stateFilterHints");
const adminNavLink = document.getElementById("adminNavLink");

const pnmForm = document.getElementById("pnmForm");
const ratingForm = document.getElementById("ratingForm");
const photoForm = document.getElementById("photoForm");
const pnmPhotoInput = document.getElementById("pnmPhoto");
const selectedPnmPhotoFile = document.getElementById("selectedPnmPhotoFile");
const refreshInstagramPhotoBtn = document.getElementById("refreshInstagramPhotoBtn");
const selectedPnmPhoto = document.getElementById("selectedPnmPhoto");
const selectedPnmPhotoPlaceholder = document.getElementById("selectedPnmPhotoPlaceholder");

const pnmTable = document.getElementById("pnmTable");
const pnmBoard = document.getElementById("pnmBoard");
const pnmViewToggleTable = document.getElementById("pnmViewToggleTable");
const pnmViewToggleBoard = document.getElementById("pnmViewToggleBoard");
const memberTable = document.getElementById("memberTable");
const teamPulseCards = document.getElementById("teamPulseCards");
const teamOfficerLoads = document.getElementById("teamOfficerLoads");
const sameStatePnmsHeader = document.getElementById("sameStatePnmsHeader");
const sameStatePnmsList = document.getElementById("sameStatePnmsList");
const ratingList = document.getElementById("ratingList");
const lunchHistory = document.getElementById("lunchHistory");
const selectedPnmLabel = document.getElementById("selectedPnmLabel");
const openMeetingPageBtn = document.getElementById("openMeetingPageBtn");
const rusheeWatchToggleBtn = document.getElementById("rusheeWatchToggleBtn");
const rusheeScheduleTouchpointBtn = document.getElementById("rusheeScheduleTouchpointBtn");
const ratingPnm = document.getElementById("ratingPnm");
const assignPanel = document.getElementById("assignPanel");
const assignOfficerSelect = document.getElementById("assignOfficerSelect");
const assignOfficerBtn = document.getElementById("assignOfficerBtn");
const clearAssignBtn = document.getElementById("clearAssignBtn");
const packageDealPanel = document.getElementById("packageDealPanel");
const packagePartnerSelect = document.getElementById("packagePartnerSelect");
const packageLinkBtn = document.getElementById("packageLinkBtn");
const packageUnlinkBtn = document.getElementById("packageUnlinkBtn");
const packageDealSummary = document.getElementById("packageDealSummary");

const approvalsPanel = document.getElementById("approvalsPanel");
const pendingList = document.getElementById("pendingList");
const adminPanel = document.getElementById("adminPanel");
const adminPnmTable = document.getElementById("adminPnmTable");
const headAdminSummary = document.getElementById("headAdminSummary");
const officerMetricsTable = document.getElementById("officerMetricsTable");
const currentHeadsList = document.getElementById("currentHeadsList");
const promoteOfficerSelect = document.getElementById("promoteOfficerSelect");
const demoteExistingHeads = document.getElementById("demoteExistingHeads");
const promoteOfficerBtn = document.getElementById("promoteOfficerBtn");
const adminPnmEditorForm = document.getElementById("adminPnmEditorForm");
const adminEditPnmSelect = document.getElementById("adminEditPnmSelect");
const googleImportForm = document.getElementById("googleImportForm");
const googleImportFile = document.getElementById("googleImportFile");
const googleImportResult = document.getElementById("googleImportResult");
const googleImportBtn = document.getElementById("googleImportBtn");
const downloadGoogleImportTemplateBtn = document.getElementById("downloadGoogleImportTemplateBtn");
const seasonArchiveSummary = document.getElementById("seasonArchiveSummary");
const seasonArchivePhrase = document.getElementById("seasonArchivePhrase");
const seasonArchiveLabel = document.getElementById("seasonArchiveLabel");
const seasonHeadChairConfirm = document.getElementById("seasonHeadChairConfirm");
const seasonResetBtn = document.getElementById("seasonResetBtn");
const seasonArchiveDownloadBtn = document.getElementById("seasonArchiveDownloadBtn");
const adminTabBar = document.getElementById("adminTabBar");
const adminStorageDiagnostics = document.getElementById("adminStorageDiagnostics");

const analyticsCards = document.getElementById("analyticsCards");
const matchingPnms = document.getElementById("matchingPnms");
const matchingMembers = document.getElementById("matchingMembers");
const leaderboardTable = document.getElementById("leaderboardTable");
const commandCenterSection = document.getElementById("commandCenterSection");
const commandWindowLabel = document.getElementById("commandWindowLabel");
const commandQueueCount = document.getElementById("commandQueueCount");
const commandStaleCount = document.getElementById("commandStaleCount");
const commandRecentCount = document.getElementById("commandRecentCount");
const commandPendingCount = document.getElementById("commandPendingCount");
const commandNeedsHelpCount = document.getElementById("commandNeedsHelpCount");
const commandUnassignedCount = document.getElementById("commandUnassignedCount");
const commandCenterQueue = document.getElementById("commandCenterQueue");
const commandStaleList = document.getElementById("commandStaleList");
const commandRecentChanges = document.getElementById("commandRecentChanges");
const commandAttentionList = document.getElementById("commandAttentionList");
const commandTodayList = document.getElementById("commandTodayList");
const commandPulseCards = document.getElementById("commandPulseCards");
const commandSelectedPhoto = document.getElementById("commandSelectedPhoto");
const commandSelectedPhotoPlaceholder = document.getElementById("commandSelectedPhotoPlaceholder");
const commandSelectedName = document.getElementById("commandSelectedName");
const commandSelectedMeta = document.getElementById("commandSelectedMeta");
const commandSelectedSignal = document.getElementById("commandSelectedSignal");
const commandSelectedStats = document.getElementById("commandSelectedStats");
const commandOpenMeetingBtn = document.getElementById("commandOpenMeetingBtn");
const commandWatchToggleBtn = document.getElementById("commandWatchToggleBtn");
const commandScheduleTouchpointBtn = document.getElementById("commandScheduleTouchpointBtn");
const commandRatingForm = document.getElementById("commandRatingForm");
const commandSaveNextBtn = document.getElementById("commandSaveNextBtn");
const copyCalendarFeedBtn = document.getElementById("copyCalendarFeedBtn");
const openGoogleSubscribeBtn = document.getElementById("openGoogleSubscribeBtn");
const calendarFeedPreview = document.getElementById("calendarFeedPreview");
const lastLunchCalendarActions = document.getElementById("lastLunchCalendarActions");
const openLastLunchGoogleLink = document.getElementById("openLastLunchGoogleLink");
const refreshScheduledLunchesBtn = document.getElementById("refreshScheduledLunchesBtn");
const scheduledLunchesList = document.getElementById("scheduledLunchesList");
const touchpointDrawer = document.getElementById("touchpointDrawer");
const touchpointDrawerCloseBtn = document.getElementById("touchpointDrawerCloseBtn");
const touchpointDrawerForm = document.getElementById("touchpointDrawerForm");
const touchpointDrawerPnm = document.getElementById("touchpointDrawerPnm");
const touchpointDrawerDate = document.getElementById("touchpointDrawerDate");
const touchpointDrawerStartTime = document.getElementById("touchpointDrawerStartTime");
const touchpointDrawerEndTime = document.getElementById("touchpointDrawerEndTime");
const touchpointDrawerLocation = document.getElementById("touchpointDrawerLocation");
const touchpointDrawerNotes = document.getElementById("touchpointDrawerNotes");
const touchpointDrawerOpenGoogle = document.getElementById("touchpointDrawerOpenGoogle");
const touchpointDrawerLastGoogleLink = document.getElementById("touchpointDrawerLastGoogleLink");
const touchpointDrawerTitle = document.getElementById("touchpointDrawerTitle");
const touchpointDrawerSubtitle = document.getElementById("touchpointDrawerSubtitle");

const rushEventForm = document.getElementById("rushEventForm");
const rushEventTitle = document.getElementById("rushEventTitle");
const rushEventType = document.getElementById("rushEventType");
const rushEventDate = document.getElementById("rushEventDate");
const rushEventStartTime = document.getElementById("rushEventStartTime");
const rushEventEndTime = document.getElementById("rushEventEndTime");
const rushEventLocation = document.getElementById("rushEventLocation");
const rushEventDetails = document.getElementById("rushEventDetails");
const rushEventOfficial = document.getElementById("rushEventOfficial");
const rushEventPermissionNotice = document.getElementById("rushEventPermissionNotice");
const rushCalendarStats = document.getElementById("rushCalendarStats");
const rushCalendarTable = document.getElementById("rushCalendarTable");
const operationsSummaryCards = document.getElementById("operationsSummaryCards");
const operationsTabBar = document.getElementById("operationsTabBar");
const operationsScheduleTouchpointBtn = document.getElementById("operationsScheduleTouchpointBtn");
const copyRushCalendarFeedBtn = document.getElementById("copyRushCalendarFeedBtn");
const openRushGoogleSubscribeBtn = document.getElementById("openRushGoogleSubscribeBtn");
const rushCalendarFeedPreview = document.getElementById("rushCalendarFeedPreview");
const copyLunchOnlyFeedBtn = document.getElementById("copyLunchOnlyFeedBtn");
const lunchOnlyFeedPreview = document.getElementById("lunchOnlyFeedPreview");

const weeklyGoalForm = document.getElementById("weeklyGoalForm");
const weeklyGoalTitle = document.getElementById("weeklyGoalTitle");
const weeklyGoalDescription = document.getElementById("weeklyGoalDescription");
const weeklyGoalMetric = document.getElementById("weeklyGoalMetric");
const weeklyGoalTarget = document.getElementById("weeklyGoalTarget");
const weeklyGoalWeekStart = document.getElementById("weeklyGoalWeekStart");
const weeklyGoalWeekEnd = document.getElementById("weeklyGoalWeekEnd");
const weeklyGoalAssignedUser = document.getElementById("weeklyGoalAssignedUser");
const weeklyGoalSummary = document.getElementById("weeklyGoalSummary");
const weeklyGoalsList = document.getElementById("weeklyGoalsList");

const appNotificationsReadAllBtn = document.getElementById("appNotificationsReadAllBtn");
const officerChatForm = document.getElementById("officerChatForm");
const officerChatMessage = document.getElementById("officerChatMessage");
const officerChatTags = document.getElementById("officerChatTags");
const officerChatStats = document.getElementById("officerChatStats");
const officerChatList = document.getElementById("officerChatList");
const officerChatQuickTags = document.getElementById("officerChatQuickTags");

const desktopPageNav = document.getElementById("desktopPageNav");
const desktopPages = Array.from(document.querySelectorAll(".desktop-page[data-page]"));
const desktopPageLinks = Array.from(document.querySelectorAll(".desktop-page-link[data-page]"));
const operationsUnreadBadge = document.getElementById("operationsUnreadBadge");
const tutorialLayer = document.getElementById("tutorialLayer");
const tutorialModeCard = document.getElementById("tutorialModeCard");
const tutorialStepCard = document.getElementById("tutorialStepCard");
const tutorialModeTitle = document.getElementById("tutorialModeTitle");
const tutorialModeSubtitle = document.getElementById("tutorialModeSubtitle");
const tutorialRoleChecklist = document.getElementById("tutorialRoleChecklist");
const tutorialModeSkipBtn = document.getElementById("tutorialModeSkipBtn");
const tutorialStepMeta = document.getElementById("tutorialStepMeta");
const tutorialStepTitle = document.getElementById("tutorialStepTitle");
const tutorialStepBody = document.getElementById("tutorialStepBody");
const tutorialStepHint = document.getElementById("tutorialStepHint");
const tutorialProgressBar = document.getElementById("tutorialProgressBar");
const tutorialPrevBtn = document.getElementById("tutorialPrevBtn");
const tutorialNextBtn = document.getElementById("tutorialNextBtn");
const tutorialCloseBtn = document.getElementById("tutorialCloseBtn");

const assignedRushPanel = document.getElementById("assignedRushPanel");
const assignedRushTitle = document.getElementById("assignedRushTitle");
const assignedRushSubtitle = document.getElementById("assignedRushSubtitle");
const assignedRushTable = document.getElementById("assignedRushTable");
const assignedRushDownloadBtn = document.getElementById("assignedRushDownloadBtn");

const headAssignmentForm = document.getElementById("headAssignmentForm");
const headAssignPnmSelect = document.getElementById("headAssignPnmSelect");
const headAssignOfficerSelect = document.getElementById("headAssignOfficerSelect");
const headAssignClearBtn = document.getElementById("headAssignClearBtn");
const headAddAssigneeSelect = document.getElementById("headAddAssigneeSelect");
const headAddAssigneeBtn = document.getElementById("headAddAssigneeBtn");
const headAssigneeList = document.getElementById("headAssigneeList");
const headAssignmentTable = document.getElementById("headAssignmentTable");
const meetingsShortlist = document.getElementById("meetingsShortlist");
const meetingsAttentionList = document.getElementById("meetingsAttentionList");
const meetingsWatchlist = document.getElementById("meetingsWatchlist");
const meetingsCompareSelectA = document.getElementById("meetingsCompareSelectA");
const meetingsCompareSelectB = document.getElementById("meetingsCompareSelectB");
const meetingsCompareSummary = document.getElementById("meetingsCompareSummary");

const DEFAULT_DESKTOP_PAGE = "overview";
const ROLE_HEAD = "Head Rush Officer";
const ROLE_RUSH_OFFICER = "Rush Officer";
const ROLE_RUSHER = "Rusher";
const TUTORIAL_MODE_GUIDED = "guided";
const TUTORIAL_MODE_ADVANCED = "advanced";
const TUTORIAL_MODE_QUICK = "quick";
const TUTORIAL_VERSION = 1;
const BASE_DEFAULT_INTEREST_TAGS = [
  "Leadership",
  "Academics",
  "Career",
  "Community",
  "Culture",
  "Service",
  "Sports",
  "Fitness",
  "Finance",
  "Business",
  "Outdoors",
  "Music",
  "Technology",
  "Wellness",
  "Faith",
  "Philanthropy",
  "Gaming",
  "Travel",
  "Food",
  "Fashion",
  "Entrepreneurship",
];
const BASE_DEFAULT_STEREOTYPE_TAGS = [
  "Leader",
  "Connector",
  "Scholar",
  "Athlete",
  "Social",
  "Creative",
  "Mentor",
  "Builder",
];
const BASE_RATING_CRITERIA = [
  { field: "good_with_girls", label: "Good with girls", short_label: "Girls", max: 10 },
  { field: "will_make_it", label: "Will make it through process", short_label: "Process", max: 10 },
  { field: "personable", label: "Personable", short_label: "Personable", max: 10 },
  { field: "alcohol_control", label: "Alcohol control", short_label: "Alcohol", max: 10 },
  { field: "instagram_marketability", label: "Instagram marketability", short_label: "IG", max: 5 },
];
const RATING_FIELD_LIMITS = {
  good_with_girls: 10,
  will_make_it: 10,
  personable: 10,
  alcohol_control: 10,
  instagram_marketability: 5,
};
const PNM_AVG_FIELD_BY_RATING_FIELD = {
  good_with_girls: "avg_good_with_girls",
  will_make_it: "avg_will_make_it",
  personable: "avg_personable",
  alcohol_control: "avg_alcohol_control",
  instagram_marketability: "avg_instagram_marketability",
};

function toTitleCase(text) {
  return String(text || "")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function parseConfiguredTagList(raw, fallback) {
  if (!Array.isArray(raw)) {
    return [...fallback];
  }
  const out = [];
  const seen = new Set();
  raw.forEach((item) => {
    const token = toTitleCase(item);
    if (!token) {
      return;
    }
    const key = token.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    out.push(token);
  });
  return out.length ? out.slice(0, 20) : [...fallback];
}

function normalizeStateCodeToken(value) {
  const token = String(value || "").trim().toUpperCase();
  return /^[A-Z]{2}$/.test(token) ? token : "";
}

function parseStateOptions(raw) {
  if (!Array.isArray(raw)) {
    return [];
  }
  const out = [];
  const seen = new Set();
  raw.forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const code = normalizeStateCodeToken(item.code);
    const name = toTitleCase(item.name || "");
    if (!code || !name || seen.has(code)) {
      return;
    }
    seen.add(code);
    out.push({ code, name });
  });
  return out;
}

function parseRatingCriteria(raw) {
  const byField = new Map();
  if (Array.isArray(raw)) {
    raw.forEach((item) => {
      if (!item || typeof item !== "object" || !item.field) {
        return;
      }
      byField.set(String(item.field), item);
    });
  }
  return BASE_RATING_CRITERIA.map((base) => {
    const incoming = byField.get(base.field) || {};
    const limit = RATING_FIELD_LIMITS[base.field] || base.max;
    const parsedMax = Number.parseInt(String(incoming.max ?? base.max), 10);
    const max = Number.isFinite(parsedMax) ? Math.max(1, Math.min(limit, parsedMax)) : base.max;
    const label = String(incoming.label || base.label).trim() || base.label;
    const shortLabel = String(incoming.short_label || base.short_label).trim() || base.short_label;
    return {
      field: base.field,
      label,
      short_label: shortLabel,
      max,
    };
  });
}

const RATING_CRITERIA = parseRatingCriteria(APP_CONFIG.rating_criteria);
const RATING_CRITERIA_BY_FIELD = new Map(RATING_CRITERIA.map((item) => [item.field, item]));
const RATING_TOTAL_MAX =
  Number.isFinite(Number(APP_CONFIG.rating_total_max)) && Number(APP_CONFIG.rating_total_max) > 0
    ? Number(APP_CONFIG.rating_total_max)
    : RATING_CRITERIA.reduce((sum, item) => sum + Number(item.max || 0), 0);
const DEFAULT_INTEREST_TAGS = parseConfiguredTagList(APP_CONFIG.default_interest_tags, BASE_DEFAULT_INTEREST_TAGS);
const DEFAULT_STEREOTYPE_TAGS = parseConfiguredTagList(
  APP_CONFIG.default_stereotype_tags,
  BASE_DEFAULT_STEREOTYPE_TAGS
);
const STATE_OPTIONS = parseStateOptions(APP_CONFIG.state_options);

function storageKey(suffix) {
  return `bidboard:${TENANT_KEY}:${suffix}`;
}

function readStoredJson(suffix, fallback) {
  try {
    const raw = window.localStorage.getItem(storageKey(suffix));
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeStoredJson(suffix, value) {
  try {
    window.localStorage.setItem(storageKey(suffix), JSON.stringify(value));
  } catch {
    // ignore storage failures
  }
}

const state = {
  user: null,
  pnms: [],
  assignedRushRows: [],
  members: [],
  sameStatePnms: [],
  selectedPnmId: null,
  selectedMemberId: null,
  toastTimer: null,
  filterTimers: {
    rushees: null,
    members: null,
  },
  touchpoint: {
    source: "shell",
    pnmId: null,
    lastGoogleUrl: "",
  },
  rusheeFilters: {
    interest: "",
    stereotype: "",
    state: "",
  },
  matchingFilters: {
    interest: "",
    stereotype: "",
    state: "",
  },
  commandCenter: {
    queue: [],
    staleAlerts: [],
    recentChanges: [],
    summary: null,
    selectedQueuePnmId: null,
    windowHours: 72,
    limit: 30,
    error: "",
  },
  memberFilters: {
    role: "all",
    state: "",
    city: "",
    sort: "location",
  },
  heroStats: {
    pnmCount: 0,
    ratingCount: 0,
    lunchCount: 0,
  },
  calendarShare: null,
  activeDesktopPage: DEFAULT_DESKTOP_PAGE,
  liveRefreshTimer: null,
  liveRefreshInFlight: false,
  headAdmin: {
    summary: null,
    currentHeads: [],
    rushOfficers: [],
  },
  scheduledLunches: [],
  rushCalendarItems: [],
  rushCalendarStats: null,
  weeklyGoals: [],
  weeklyGoalSummary: null,
  weeklyGoalMetricOptions: [],
  notifications: [],
  unreadNotifications: 0,
  officerChatMessages: [],
  officerChatStats: null,
  adminEditPnmId: null,
  headAssignmentPnmId: null,
  packagePartnerId: null,
  seasonArchive: null,
  watchlist: readStoredJson("watchlist", []),
  viewPrefs: {
    pnmView: readStoredJson("pnm-view", "table"),
    operationsTab: readStoredJson("operations-tab", "timeline"),
    adminTab: readStoredJson("admin-tab", "leadership"),
  },
  commandWorkspace: {
    attention: [],
    today: [],
    teamPulse: null,
    watchCandidates: [],
    notifications: null,
  },
  teamWorkspace: {
    assignmentOverview: null,
    leadership: null,
  },
  operationsWorkspace: {
    notificationsDigest: null,
  },
  meetingsWorkspace: {
    shortlist: [],
    attention: [],
    candidates: [],
    compareDefaults: [],
    compareA: null,
    compareB: null,
    compareSummaryA: null,
    compareSummaryB: null,
  },
  adminOverview: {
    storage: null,
    assignments: null,
    leadership: null,
    pending: null,
  },
  searchResults: {
    query: "",
    pnms: [],
    members: [],
    commands: [],
  },
  tutorial: {
    active: false,
    mode: TUTORIAL_MODE_GUIDED,
    steps: [],
    index: 0,
    highlightedEl: null,
    completing: false,
  },
};

function ratingCriteriaForField(field) {
  return RATING_CRITERIA_BY_FIELD.get(field) || BASE_RATING_CRITERIA.find((item) => item.field === field);
}

function ratingLabelWithRange(field) {
  const criterion = ratingCriteriaForField(field);
  if (!criterion) {
    return `${field} (0-10)`;
  }
  return `${criterion.short_label} (0-${criterion.max})`;
}

function formatScoreBreakdown(row) {
  return RATING_CRITERIA.map((criterion) => {
    const value = Number(row[criterion.field] || 0);
    return `${criterion.short_label} ${value}`;
  }).join(" | ");
}


function normalizePackageGroupId(value) {
  const token = String(value || "").trim();
  return token || "";
}

function packageGroupLabel(groupId) {
  const token = normalizePackageGroupId(groupId);
  if (!token) {
    return "";
  }
  const raw = token.startsWith("pkg_") ? token.slice(4) : token;
  return `PKG-${raw.slice(0, 6).toUpperCase()}`;
}

function packageGroupIndex() {
  const map = new Map();
  state.pnms.forEach((pnm) => {
    const groupId = normalizePackageGroupId(pnm.package_group_id);
    if (!groupId) {
      return;
    }
    if (!map.has(groupId)) {
      map.set(groupId, []);
    }
    map.get(groupId).push(pnm);
  });
  return map;
}

function packageInfoForPnm(pnm, groups = null) {
  if (!pnm) {
    return { id: "", label: "Solo", count: 1, members: [] };
  }
  const groupId = normalizePackageGroupId(pnm.package_group_id);
  if (!groupId) {
    return { id: "", label: "Solo", count: 1, members: [pnm] };
  }
  const lookup = groups || packageGroupIndex();
  const members = lookup.get(groupId) || [pnm];
  return {
    id: groupId,
    label: packageGroupLabel(groupId) || "Package",
    count: members.length,
    members,
  };
}

function linkedRusheeNamesForPnm(pnm, groups = null) {
  const packageInfo = packageInfoForPnm(pnm, groups);
  if (!packageInfo.id) {
    return "None";
  }
  const linkedNames = packageInfo.members
    .filter((member) => Number(member.pnm_id) !== Number(pnm.pnm_id))
    .map((member) => `${member.first_name} ${member.last_name}`);
  return linkedNames.length ? linkedNames.join(", ") : "None";
}

function assignmentTeamForPnm(pnm) {
  if (!pnm || !Array.isArray(pnm.assigned_officers)) {
    return [];
  }
  return pnm.assigned_officers
    .filter((item) => item && Number(item.user_id || 0) > 0)
    .map((item) => ({
      user_id: Number(item.user_id),
      username: String(item.username || "Unknown"),
      emoji: item.emoji ? String(item.emoji) : "",
      is_primary: Boolean(item.is_primary),
      assigned_at: item.assigned_at || null,
    }));
}

function assignmentTeamLabel(officers) {
  if (!officers || !officers.length) {
    return "Unassigned";
  }
  return officers
    .map((officer) => {
      const emoji = officer.emoji ? `${officer.emoji} ` : "";
      return `${emoji}${officer.username}`;
    })
    .join(", ");
}

function primaryAssignmentLabel(pnm, officers = []) {
  const primary = officers.find((item) => item.is_primary) || null;
  if (primary && primary.username) {
    return primary.username;
  }
  if (pnm && pnm.assigned_officer && pnm.assigned_officer.username) {
    return pnm.assigned_officer.username;
  }
  return "Unassigned";
}

function applyRatingCriteriaUi() {
  const fields = [
    {
      field: "good_with_girls",
      targets: [
        { inputId: "rateGirls", labelId: "rateGirlsLabel" },
        { inputId: "commandRateGirls", labelId: "commandRateGirlsLabel" },
      ],
    },
    {
      field: "will_make_it",
      targets: [
        { inputId: "rateProcess", labelId: "rateProcessLabel" },
        { inputId: "commandRateProcess", labelId: "commandRateProcessLabel" },
      ],
    },
    {
      field: "personable",
      targets: [
        { inputId: "ratePersonable", labelId: "ratePersonableLabel" },
        { inputId: "commandRatePersonable", labelId: "commandRatePersonableLabel" },
      ],
    },
    {
      field: "alcohol_control",
      targets: [
        { inputId: "rateAlcohol", labelId: "rateAlcoholLabel" },
        { inputId: "commandRateAlcohol", labelId: "commandRateAlcoholLabel" },
      ],
    },
    {
      field: "instagram_marketability",
      targets: [
        { inputId: "rateIg", labelId: "rateIgLabel" },
        { inputId: "commandRateIg", labelId: "commandRateIgLabel" },
      ],
    },
  ];
  fields.forEach(({ field, targets }) => {
    const criterion = ratingCriteriaForField(field);
    (targets || []).forEach(({ inputId, labelId }) => {
      const input = document.getElementById(inputId);
      const label = document.getElementById(labelId);
      if (input && criterion) {
        input.min = "0";
        input.max = String(criterion.max);
      }
      if (label) {
        label.textContent = ratingLabelWithRange(field);
      }
    });
  });
}

function parseTagInput(raw) {
  return String(raw || "")
    .split(/[,;\n]+/)
    .map((value) => value.trim())
    .filter(Boolean);
}

function uniqueNormalized(values) {
  const out = [];
  const seen = new Set();
  values.forEach((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    out.push(value);
  });
  return out;
}

function renderTagPickerButtons(pickerEl, tags, selectedSet) {
  if (!pickerEl) {
    return;
  }
  pickerEl.innerHTML = tags
    .map((tag) => {
      const active = selectedSet.has(tag.toLowerCase()) ? " is-active" : "";
      const pressed = active ? "true" : "false";
      return `<span class="tag-pill${active}" data-tag="${escapeHtml(tag)}" role="button" tabindex="0" aria-pressed="${pressed}">${escapeHtml(tag)}</span>`;
    })
    .join("");
}

function syncInterestPickerFromInput(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker) {
    return;
  }
  const selected = new Set(parseTagInput(input.value).map((value) => value.toLowerCase()));
  renderTagPickerButtons(picker, DEFAULT_INTEREST_TAGS, selected);
}

function syncStereotypePickerFromInput(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker) {
    return;
  }
  const selected = new Set();
  const value = String(input.value || "").trim().toLowerCase();
  if (value) {
    selected.add(value);
  }
  renderTagPickerButtons(picker, DEFAULT_STEREOTYPE_TAGS, selected);
}

function bindInterestPicker(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker || picker.dataset.bound === "1") {
    return;
  }
  input.readOnly = true;
  picker.dataset.bound = "1";

  const applyTagToggle = (tag) => {
    if (!tag) {
      return;
    }
    const tokens = parseTagInput(input.value);
    const existing = new Set(tokens.map((value) => value.toLowerCase()));
    if (existing.has(tag.toLowerCase())) {
      input.value = tokens.filter((value) => value.toLowerCase() !== tag.toLowerCase()).join(",");
    } else {
      tokens.push(tag);
      input.value = uniqueNormalized(tokens).join(",");
    }
    syncInterestPickerFromInput(inputId, pickerId);
  };

  picker.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const tag = String(chip.dataset.tag || "").trim();
    applyTagToggle(tag);
  });

  picker.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    const tag = String(chip.dataset.tag || "").trim();
    applyTagToggle(tag);
  });

  input.addEventListener("input", () => syncInterestPickerFromInput(inputId, pickerId));
  syncInterestPickerFromInput(inputId, pickerId);
}

function bindStereotypePicker(inputId, pickerId) {
  const input = document.getElementById(inputId);
  const picker = document.getElementById(pickerId);
  if (!input || !picker || picker.dataset.bound === "1") {
    return;
  }
  input.readOnly = true;
  picker.dataset.bound = "1";

  const applyStereotype = (tag) => {
    if (!tag) {
      return;
    }
    const current = String(input.value || "").trim().toLowerCase();
    input.value = current === tag.toLowerCase() ? "" : tag;
    syncStereotypePickerFromInput(inputId, pickerId);
  };

  picker.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const tag = String(chip.dataset.tag || "").trim();
    applyStereotype(tag);
  });

  picker.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    const chip = event.target.closest("[data-tag]");
    if (!chip) {
      return;
    }
    event.preventDefault();
    const tag = String(chip.dataset.tag || "").trim();
    applyStereotype(tag);
  });

  input.addEventListener("input", () => syncStereotypePickerFromInput(inputId, pickerId));
  syncStereotypePickerFromInput(inputId, pickerId);
}

function initializePresetTagPickers() {
  bindInterestPicker("pnmInterests", "pnmInterestTags");
  bindInterestPicker("adminEditInterests", "adminEditInterestTags");
  bindStereotypePicker("pnmStereotype", "pnmStereotypeTags");
  bindStereotypePicker("adminEditStereotype", "adminEditStereotypeTags");
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

function resolveApiPath(path) {
  if (path.startsWith("/api/")) {
    return `${API_BASE}${path.slice(4)}`;
  }
  if (path === "/api") {
    return API_BASE;
  }
  return path;
}

function resolveTenantPath(path) {
  const raw = String(path || "").trim();
  if (!raw) {
    return raw;
  }
  if (raw.startsWith("#")) {
    return raw;
  }
  if (/^[a-z][a-z0-9+.-]*:/i.test(raw) || raw.startsWith("//")) {
    return BASE_PATH || "/";
  }
  if (raw.startsWith("/") && BASE_PATH && !raw.startsWith(`${BASE_PATH}/`) && raw !== BASE_PATH) {
    return `${BASE_PATH}${raw}`;
  }
  if (raw.startsWith("/")) {
    return raw;
  }
  return BASE_PATH || "/";
}

function readCookie(name) {
  const needle = `${name}=`;
  const parts = document.cookie ? document.cookie.split(";") : [];
  for (const rawPart of parts) {
    const part = rawPart.trim();
    if (part.startsWith(needle)) {
      return decodeURIComponent(part.slice(needle.length));
    }
  }
  return "";
}

function csrfHeadersForMethod(method, headers) {
  const normalizedMethod = String(method || "GET").toUpperCase();
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(normalizedMethod)) {
    return headers;
  }
  const token = readCookie("bb_csrf_token");
  if (!token) {
    return headers;
  }
  return {
    ...headers,
    "X-CSRF-Token": token,
  };
}

async function api(path, options = {}) {
  const requestPath = resolveApiPath(path);
  const isFormData = options.body instanceof FormData;
  const method = String(options.method || "GET").toUpperCase();
  const headers = csrfHeadersForMethod(
    method,
    isFormData
      ? {
          ...(options.headers || {}),
        }
      : {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        }
  );
  let response;
  try {
    response = await fetch(requestPath, {
      method,
      credentials: "same-origin",
      headers,
      body: options.body ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined,
    });
  } catch (networkError) {
    const text = networkError instanceof Error ? networkError.message : "Network error";
    throw new Error(`Network error: ${text}`);
  }

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json().catch(() => ({}));
  } else {
    payload = await response.text().catch(() => "");
  }

  if (!response.ok) {
    let detail = "";
    if (typeof payload === "object" && payload !== null && "detail" in payload) {
      const rawDetail = payload.detail;
      if (Array.isArray(rawDetail)) {
        detail = rawDetail.map((item) => String(item?.msg || JSON.stringify(item))).join("; ");
      } else {
        detail = String(rawDetail || "");
      }
    } else if (typeof payload === "string") {
      detail = payload.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return payload;
}

async function downloadFile(url, fallbackFileName) {
  const response = await fetch(resolveApiPath(url), { method: "GET", credentials: "same-origin" });
  if (!response.ok) {
    const detail = await response.text().catch(() => "Download failed.");
    throw new Error(detail || "Download failed.");
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const fileNameMatch = disposition.match(/filename=\"?([^\";]+)\"?/i);
  const fileName = fileNameMatch ? fileNameMatch[1] : fallbackFileName;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function safeFileToken(value) {
  return String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
}

function setAuthView(isAuthenticated) {
  document.body.classList.toggle("desktop-product-auth", Boolean(isAuthenticated));
  if (authShell) {
    authShell.classList.toggle("hidden", isAuthenticated);
  } else {
    authSection.classList.toggle("hidden", isAuthenticated);
  }
  appSection.classList.toggle("hidden", !isAuthenticated);
  if (heroStats) {
    heroStats.classList.toggle("hidden", !isAuthenticated);
  }
  if (isAuthenticated) {
    setActiveDesktopPage(currentRequestedDesktopPage(), false);
  }
}

function availableDesktopPages() {
  return desktopPages.map((panel) => panel.dataset.page).filter(Boolean);
}

function mapDesktopRouteToPage(value) {
  const token = String(value || "").trim().toLowerCase();
  if (!token) {
    return "";
  }
  if (token === "dashboard" || token === "overview") {
    return "overview";
  }
  if (token === "calendar" || token === "operations") {
    return "operations";
  }
  if (token === "team" || token === "members") {
    return "members";
  }
  if (token === "rushees") {
    return "rushees";
  }
  if (token === "meetings") {
    return "meetings";
  }
  if (token === "admin") {
    return "admin";
  }
  return "";
}

function desktopRoutePathForPage(page) {
  const routeMap = APP_CONFIG.desktop_routes || {};
  if (page === "overview") {
    return routeMap.dashboard || `${BASE_PATH}/dashboard`;
  }
  if (page === "operations") {
    return routeMap.calendar || `${BASE_PATH}/calendar`;
  }
  if (page === "members") {
    return routeMap.team || `${BASE_PATH}/team`;
  }
  if (page === "rushees") {
    return routeMap.rushees || `${BASE_PATH}/rushees`;
  }
  if (page === "meetings") {
    return routeMap.meetings || `${BASE_PATH}/meetings`;
  }
  if (page === "admin") {
    return routeMap.admin || `${BASE_PATH}/admin`;
  }
  return routeMap.dashboard || `${BASE_PATH}/dashboard`;
}

function currentRequestedDesktopPage() {
  const fromConfig = mapDesktopRouteToPage(APP_CONFIG.desktop_page);
  if (fromConfig) {
    return fromConfig;
  }
  const viewRequested = mapDesktopRouteToPage(new URLSearchParams(window.location.search).get("view"));
  if (viewRequested) {
    return viewRequested;
  }
  const path = window.location.pathname || "";
  const segments = path.split("/").filter(Boolean);
  const maybeRoute = segments.length ? segments[segments.length - 1] : "";
  const fromPath = mapDesktopRouteToPage(maybeRoute);
  if (fromPath) {
    return fromPath;
  }
  return DEFAULT_DESKTOP_PAGE;
}

function setActiveDesktopPage(page, updateUrl = true) {
  if (!desktopPages.length) {
    return;
  }
  const available = new Set(availableDesktopPages());
  let target = available.has(page) ? page : DEFAULT_DESKTOP_PAGE;
  if (target === "admin" && !roleCanUseAdminPanel()) {
    target = DEFAULT_DESKTOP_PAGE;
  }
  state.activeDesktopPage = target;
  desktopPages.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.page === target);
  });
  desktopPageLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.page === target);
  });
  updateWorkspaceHeader();
  closeAppMenus();

  if (!updateUrl) {
    return;
  }
  const shouldRefresh = Boolean(state.user);
  const nextPath = desktopRoutePathForPage(target);
  const current = window.location.pathname;
  if (!nextPath || current === nextPath) {
    if (shouldRefresh) {
      refreshByActivePage().catch(() => {});
    }
    return;
  }
  window.history.replaceState({}, "", nextPath);
  if (shouldRefresh) {
    refreshByActivePage().catch(() => {});
  }
}

function updateTopbarActions() {
  const isHead = roleCanUseAdminPanel();
  if (openTutorialBtn) {
    openTutorialBtn.classList.toggle("hidden", !state.user);
  }
  if (installBtn) {
    installBtn.classList.toggle("hidden", !state.user);
  }
  if (adminNavLink) {
    adminNavLink.classList.toggle("hidden", !isHead);
  }
  if (!isHead && state.activeDesktopPage === "admin") {
    setActiveDesktopPage(DEFAULT_DESKTOP_PAGE);
  }
}

function workspaceMetaForPage(page) {
  if (page === "rushees") {
    return { eyebrow: "Workspace", title: "Rushees", subtitle: "Roster, inspector, ownership, and packet readiness." };
  }
  if (page === "meetings") {
    return { eyebrow: "Workspace", title: "Meetings", subtitle: "Shortlist, compare, and packet launch from one queue." };
  }
  if (page === "members") {
    return { eyebrow: "Workspace", title: "Team", subtitle: "Approvals, workload, assignment coverage, and member alignment." };
  }
  if (page === "operations") {
    return { eyebrow: "Workspace", title: "Operations", subtitle: "Timeline, goals, touchpoints, and officer chat." };
  }
  if (page === "admin") {
    return { eyebrow: "Workspace", title: "Admin", subtitle: "Leadership, season reset, imports, roster tools, and storage." };
  }
  return { eyebrow: "Workspace", title: "Command", subtitle: "Personal queue, exceptions, recent decisions, and team pulse." };
}

function updateWorkspaceHeader() {
  const meta = workspaceMetaForPage(state.activeDesktopPage || DEFAULT_DESKTOP_PAGE);
  if (workspaceEyebrow) {
    workspaceEyebrow.textContent = meta.eyebrow;
  }
  if (workspaceTitle) {
    workspaceTitle.textContent = meta.title;
  }
  if (workspaceSubtitle) {
    workspaceSubtitle.textContent = meta.subtitle;
  }
}

function refreshLoadersForActivePage() {
  const page = state.activeDesktopPage || DEFAULT_DESKTOP_PAGE;
  if (page === "operations") {
    return [loadOperationsWorkspace];
  }
  if (page === "rushees") {
    return [loadRusheesWorkspace];
  }
  if (page === "meetings") {
    return [loadMeetingsWorkspace];
  }
  if (page === "members") {
    return [loadTeamWorkspace];
  }
  if (page === "admin") {
    return [loadAdminWorkspace];
  }
  return [loadCommandWorkspace];
}

async function refreshByActivePage() {
  const loaders = refreshLoadersForActivePage();
  await Promise.all(loaders.map((loader) => loader()));
}

function startLiveRefresh() {
  if (state.liveRefreshTimer) {
    clearInterval(state.liveRefreshTimer);
  }
  state.liveRefreshTimer = setInterval(async () => {
    if (!state.user) {
      return;
    }
    if (state.liveRefreshInFlight) {
      return;
    }
    state.liveRefreshInFlight = true;
    try {
      await refreshByActivePage();
    } catch {
      // Passive sync should fail silently; explicit actions already report errors.
    } finally {
      state.liveRefreshInFlight = false;
    }
  }, 18000);
}

function stopLiveRefresh() {
  if (state.liveRefreshTimer) {
    clearInterval(state.liveRefreshTimer);
    state.liveRefreshTimer = null;
  }
  state.liveRefreshInFlight = false;
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

function closeAppMenus() {
  [globalAddMenu, appHelpMenu].forEach((menu) => {
    if (menu && menu.open) {
      menu.open = false;
    }
  });
}

function setTouchpointDrawerVisible(visible) {
  if (!touchpointDrawer) {
    return;
  }
  touchpointDrawer.classList.toggle("hidden", !visible);
  touchpointDrawer.setAttribute("aria-hidden", visible ? "false" : "true");
  if (!visible) {
    closeAppMenus();
  }
}

function showRouteNoticeFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const notice = String(params.get("notice") || "").trim().toLowerCase();
  if (!notice) {
    return;
  }
  if (notice === "admin-access-denied") {
    showToast("Admin access is limited to Head Rush Officers.");
  }
  params.delete("notice");
  const nextQuery = params.toString();
  const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash || ""}`;
  window.history.replaceState({}, "", nextUrl);
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

function roleCanApproveUsers() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanAssignOfficer() {
  return state.user && state.user.role === "Head Rush Officer";
}

function roleCanViewAssignedRushes() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanUseCommandCenter() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanManageOperations() {
  return state.user && (state.user.role === "Head Rush Officer" || state.user.role === "Rush Officer");
}

function roleCanManagePackages() {
  return Boolean(state.user);
}

function userOnboardingState() {
  if (!state.user || typeof state.user !== "object") {
    return {
      mode: TUTORIAL_MODE_GUIDED,
      completed_at: null,
      version: 0,
      required: false,
    };
  }
  const raw = state.user.onboarding && typeof state.user.onboarding === "object" ? state.user.onboarding : {};
  const mode = String(raw.mode || TUTORIAL_MODE_GUIDED).trim().toLowerCase();
  return {
    mode:
      mode === TUTORIAL_MODE_ADVANCED || mode === TUTORIAL_MODE_QUICK || mode === TUTORIAL_MODE_GUIDED
        ? mode
        : TUTORIAL_MODE_GUIDED,
    completed_at: raw.completed_at || null,
    version: Number.isFinite(Number(raw.version)) ? Number(raw.version) : 0,
    required: Boolean(raw.required),
  };
}

function tutorialRoleSummary(role) {
  if (role === ROLE_HEAD) {
    return [
      { title: "Leadership Controls", body: "Manage approvals, assignments, promotions, and season lifecycle safely." },
      { title: "Calendar Command", body: "Run events, goals, and live rush chat in one timeline workflow." },
      { title: "Decision Intelligence", body: "Move from live scoring to meeting packets with full audit context." },
    ];
  }
  if (role === ROLE_RUSH_OFFICER) {
    return [
      { title: "Daily Execution", body: "Add rushees, schedule touchpoints, and submit weighted rating updates quickly." },
      { title: "Team Coordination", body: "Track assignments, state coverage, goals, and chat in one system." },
      { title: "Meeting Readiness", body: "Use leaderboard and packets to keep decisions consistent and accountable." },
    ];
  }
  return [
    { title: "Member View", body: "Find priority rushees quickly and submit simplified ratings." },
    { title: "Participation", body: "Contribute feedback while officer-only analytics stay role-restricted." },
  ];
}

function tutorialBaseStepsForRole(role) {
  const commonOfficerSteps = [
    {
      page: "rushees",
      target: "#pnmForm",
      title: "Core Workflow: Add, Rate, Run Meeting",
      body: "Use the same three-step sequence every cycle: 1) Add + Select a rushee, 2) Rate + Log activity, 3) Run Meeting packets for final decisions.",
      hint: "Step 1 starts in Rushees form, Step 2 in the rating flow and touchpoint drawer, Step 3 from the packet links.",
      advanced:
        "Advanced workflow: keep this sequence strict after every event block so decisions stay consistent and auditable.",
    },
    {
      page: "overview",
      target: "#desktopPageNav",
      title: "Use Navigation As The Command Rail",
      body: "Move between Command, Rushees, Meetings, Operations, Team, and Admin from the left navigation rail.",
      hint: "Use the left rail as your default route system so rush-week work stays predictable.",
      advanced:
        "Advanced workflow: keep one tab on Calendar and one on Rushees during live events for faster execution.",
    },
    {
      page: "overview",
      target: "#globalSearchInput",
      title: "Use Command Search To Move Fast",
      body: "Use the top search to jump to rushees, members, and common actions without leaving your current workspace.",
      hint: "Start typing a first name, code, hometown, or command to open results instantly.",
      advanced:
        "Advanced workflow: use command search as the fastest way to jump between active rushees during events and meetings.",
    },
    {
      page: "rushees",
      target: "#rusheeFiltersSection",
      title: "Filter The Rushee Board By State",
      body: "Use page-local filters for interest, stereotype, and state to quickly narrow active targets.",
      hint: "State filtering is best for hometown outreach and assignment balancing.",
      advanced:
        "Advanced workflow: stack state + stereotype to find high-priority clusters before planning lunches.",
    },
    {
      page: "rushees",
      target: "#pnmForm",
      title: "Create Rushees With Complete Intake",
      body: "Capture contact info, interests, stereotype, notes, and photo so the chapter has one reliable record.",
      hint: "Use consistent interests so filters and matching stay clean.",
      advanced:
        "Advanced workflow: create intake standards for notes (strengths, concerns, context) to keep meeting packets consistent.",
    },
    {
      page: "rushees",
      target: "#ratingForm",
      title: "Submit Role-Weighted Ratings",
      body: "Each rating update immediately recalculates weighted totals and meeting analytics.",
      hint: "When updating an existing rating, include clear context in the comment.",
      advanced:
        "Advanced workflow: rate right after each event while context is fresh to improve historical trend quality.",
    },
    {
      page: "rushees",
      target: "#openMeetingPageBtn",
      title: "Open Meeting Packet From Rushee Detail",
      body: "Jump straight into the dedicated meeting view for deep analytics, trend history, and decision packets.",
      hint: "Use this after selecting a rushee so packet context stays aligned with live updates.",
      advanced:
        "Advanced workflow: keep meeting packets open during final discussions while officers continue logging updates.",
    },
    {
      page: "rushees",
      target: "#rusheeScheduleTouchpointBtn",
      title: "Schedule Touchpoints Directly In The Workflow",
      body: "Touchpoint scheduling updates member and rushee stats immediately and can open in Google Calendar.",
      hint: "Use the shared Schedule Touchpoint drawer so Command, Rushees, and Operations stay consistent.",
      advanced:
        "Advanced workflow: schedule lunches by assignment owner so accountability is clear before key decisions.",
    },
    {
      page: "operations",
      operationsTab: "timeline",
      target: "#rushCalendarTable",
      title: "Track One Shared Rush Timeline",
      body: "The calendar combines official rush events and touchpoints into a single operational timeline.",
      hint: "Use this view as the source of truth before each day starts.",
      advanced:
        "Advanced workflow: compare timeline density against rating activity to spot under-covered rushees quickly.",
    },
    {
      page: "operations",
      operationsTab: "goals",
      target: "#weeklyGoalsList",
      title: "Use Weekly Goals For Accountability",
      body: "Goals auto-track progress from real activity like ratings, lunches, and chat participation.",
      hint: "Create one team goal and one owner-specific goal each week.",
      advanced:
        "Advanced workflow: align goals to funnel stage movement so progress reflects recruiting outcomes, not just activity.",
    },
    {
      page: "operations",
      operationsTab: "comms",
      target: "#officerChatForm",
      title: "Coordinate In Live Officer Chat",
      body: "Use tags and mentions to run real-time coordination like a focused rush command channel.",
      hint: "Use tags like #priority and #followup to keep thread signal high.",
      advanced:
        "Advanced workflow: standardize tags by event type so chat stats become a reliable operations diagnostic.",
    },
    {
      page: "members",
      target: "#memberFiltersSection",
      title: "Filter Team Coverage By Role + Location",
      body: "Use Team filters to sort members by role, state, city, and location-first ordering.",
      hint: "This is the fastest way to verify member coverage by region.",
      advanced:
        "Advanced workflow: audit coverage by state before each round and rebalance assignments proactively.",
    },
    {
      page: "members",
      target: "#sameStatePnmsSection",
      title: "Use Same-State Discovery",
      body: "Select a member to instantly see rushees from the same state for stronger local connections.",
      hint: "If no results appear, confirm the member has a state set in their profile.",
      advanced:
        "Advanced workflow: use same-state lists to assign warm introductions before high-stakes events.",
    },
    {
      page: "members",
      target: "#assignedRushPanel",
      title: "Check Assigned Rushee Ownership",
      body: "Assignment visibility keeps outreach accountable and prevents coverage gaps.",
      hint: "Visit this page before events to confirm every key rushee has an owner.",
      advanced:
        "Advanced workflow: escalate any high-score unassigned rushee immediately from this panel.",
    },
  ];

  if (role === ROLE_HEAD) {
    return commonOfficerSteps.concat([
      {
        page: "admin",
        adminTab: "leadership",
        target: "#headAdminSummary",
        title: "Use Admin As Head Mission Control",
        body: "Head-only metrics summarize officer output, approvals, and chapter-level recruiting health.",
        hint: "Review this panel daily before assigning priorities.",
        advanced:
          "Advanced workflow: run a quick metrics review each morning to rebalance assignments before noon events.",
      },
      {
        page: "admin",
        adminTab: "roster",
        target: "#headAssignmentForm",
        title: "Assign Rushees Directly From Head Console",
        body: "Set or clear assignment ownership centrally so every rushee has accountable follow-through.",
        hint: "Assign by fit and current officer capacity, not just availability.",
        advanced:
          "Advanced workflow: pair assignment updates with funnel-stage updates to track movement quality over time.",
      },
      {
        page: "admin",
        adminTab: "season",
        target: "#seasonArchiveSummary",
        title: "Archive And Reset Safely",
        body: "Archive one full season snapshot before reset so leadership transitions keep historical context.",
        hint: "Use this only with explicit head-chair confirmation.",
        advanced:
          "Advanced workflow: export CSV + archive DB before reset for audit-grade redundancy.",
      },
    ]);
  }

  if (role === ROLE_RUSH_OFFICER) {
    return commonOfficerSteps.concat([
      {
        page: "members",
        target: "#approvalsPanel",
        title: "Approve New Team Accounts Quickly",
        body: "Rush Officers can approve pending users so new members can contribute quickly.",
        hint: "Approve only known accounts to keep data quality and security tight.",
        advanced:
          "Advanced workflow: review pending accounts at fixed windows each day so onboarding is fast but controlled.",
      },
    ]);
  }

  return [
    {
      page: "overview",
      target: "#leaderboardSection",
      title: "Track Priority Rushees",
      body: "Use leaderboard context to focus your feedback on top-priority candidates.",
      hint: "You will only see access-appropriate information for your role.",
      advanced: "Advanced workflow: submit ratings immediately after interactions to improve decision quality.",
    },
  ];
}

function buildTutorialSteps(role, mode) {
  const base = tutorialBaseStepsForRole(role);
  if (!base.length) {
    return [];
  }
  if (mode === TUTORIAL_MODE_QUICK) {
    const selectedIndices = [0, 4, 5, 6, base.length - 1];
    const seen = new Set();
    return selectedIndices
      .filter((index) => index >= 0 && index < base.length)
      .filter((index) => {
        if (seen.has(index)) {
          return false;
        }
        seen.add(index);
        return true;
      })
      .map((index) => ({
        ...base[index],
        hint: base[index].hint || base[index].advanced || "",
      }));
  }
  if (mode === TUTORIAL_MODE_ADVANCED) {
    return base.map((step) => ({
      ...step,
      hint: step.advanced || step.hint || "",
    }));
  }
  return base.map((step) => ({
    ...step,
    hint: step.hint || "",
  }));
}

function clearTutorialHighlight() {
  if (state.tutorial.highlightedEl) {
    state.tutorial.highlightedEl.classList.remove("tutorial-highlight");
    state.tutorial.highlightedEl = null;
  }
}

function setTutorialDock(side = "right") {
  if (!tutorialLayer) {
    return;
  }
  const resolved = side === "left" ? "left" : "right";
  tutorialLayer.dataset.dock = resolved;
  tutorialLayer.classList.toggle("tutorial-dock-left", resolved === "left");
  tutorialLayer.classList.toggle("tutorial-dock-right", resolved === "right");
}

function updateTutorialDockForTarget(target) {
  if (!target) {
    setTutorialDock("right");
    return;
  }
  const rect = target.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const targetCenterX = rect.left + rect.width / 2;
  setTutorialDock(targetCenterX > viewportWidth * 0.58 ? "left" : "right");
}

function setTutorialHighlight(selector) {
  clearTutorialHighlight();
  if (!selector) {
    updateTutorialDockForTarget(null);
    return null;
  }
  const target = document.querySelector(selector);
  if (!target) {
    updateTutorialDockForTarget(null);
    return null;
  }
  state.tutorial.highlightedEl = target;
  target.classList.add("tutorial-highlight");
  updateTutorialDockForTarget(target);
  if (typeof target.scrollIntoView === "function") {
    target.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
  }
  return target;
}

function setTutorialLayerVisible(visible) {
  if (!tutorialLayer) {
    return;
  }
  tutorialLayer.classList.toggle("hidden", !visible);
  tutorialLayer.setAttribute("aria-hidden", visible ? "false" : "true");
}

function closeTutorialOverlay(reset = true) {
  clearTutorialHighlight();
  setTutorialDock("right");
  setTutorialLayerVisible(false);
  if (tutorialModeCard) {
    tutorialModeCard.classList.add("hidden");
  }
  if (tutorialStepCard) {
    tutorialStepCard.classList.add("hidden");
  }
  state.tutorial.active = false;
  state.tutorial.completing = false;
  if (reset) {
    state.tutorial.mode = TUTORIAL_MODE_GUIDED;
    state.tutorial.steps = [];
    state.tutorial.index = 0;
  }
}

function renderTutorialModeCard() {
  if (!state.user || !tutorialModeCard || !tutorialModeTitle || !tutorialModeSubtitle || !tutorialRoleChecklist) {
    return;
  }
  const role = state.user.role || ROLE_RUSH_OFFICER;
  const roleCopy = role === ROLE_HEAD ? "Head Rush Officer" : role === ROLE_RUSH_OFFICER ? "Rush Officer" : "Member";
  tutorialModeTitle.textContent = `${roleCopy} Tutorial`;
  tutorialModeSubtitle.textContent = `Choose a mode to learn the ${roleCopy.toLowerCase()} workflow with in-app popups.`;
  tutorialRoleChecklist.innerHTML = tutorialRoleSummary(role)
    .map(
      (item) => `
        <div class="entry">
          <div class="entry-title"><strong>${escapeHtml(item.title)}</strong></div>
          <p class="muted">${escapeHtml(item.body)}</p>
        </div>
      `
    )
    .join("");
}

function openTutorialModeChooser() {
  if (!state.user || !tutorialLayer || !tutorialModeCard || !tutorialStepCard) {
    return;
  }
  state.tutorial.active = true;
  state.tutorial.steps = [];
  state.tutorial.index = 0;
  state.tutorial.completing = false;
  clearTutorialHighlight();
  setTutorialDock("right");
  renderTutorialModeCard();
  tutorialStepCard.classList.add("hidden");
  tutorialModeCard.classList.remove("hidden");
  setTutorialLayerVisible(true);
}

function renderTutorialStep() {
  if (!tutorialStepCard || !tutorialStepMeta || !tutorialStepTitle || !tutorialStepBody || !tutorialProgressBar) {
    return;
  }
  const steps = state.tutorial.steps;
  const safeIndex = Math.max(0, Math.min(state.tutorial.index, Math.max(steps.length - 1, 0)));
  state.tutorial.index = safeIndex;
  if (!steps.length) {
    closeTutorialOverlay();
    return;
  }

  const step = steps[safeIndex];
  if (step.page) {
    setActiveDesktopPage(step.page);
  }
  if (step.operationsTab) {
    setOperationsTab(step.operationsTab);
  }
  if (step.adminTab) {
    setAdminTab(step.adminTab);
  }
  window.setTimeout(() => {
    const highlighted = setTutorialHighlight(step.target);
    let hintText = step.hint || "";
    if (!highlighted && step.target) {
      hintText = hintText
        ? `${hintText} This target may be hidden by role permissions or current layout.`
        : "This target may be hidden by role permissions or current layout.";
    }
    if (tutorialStepHint) {
      tutorialStepHint.classList.toggle("hidden", !hintText);
      tutorialStepHint.textContent = hintText;
    }
  }, 70);

  tutorialStepMeta.textContent = `Step ${safeIndex + 1} of ${steps.length} • ${state.tutorial.mode.toUpperCase()} mode`;
  tutorialStepTitle.textContent = step.title;
  tutorialStepBody.textContent = step.body;
  tutorialProgressBar.style.width = `${Math.round(((safeIndex + 1) / steps.length) * 100)}%`;
  if (tutorialPrevBtn) {
    tutorialPrevBtn.disabled = safeIndex <= 0;
  }
  if (tutorialNextBtn) {
    tutorialNextBtn.textContent = safeIndex >= steps.length - 1 ? "Finish Tutorial" : "Next";
  }
}

function startTutorialMode(mode) {
  if (!state.user || !tutorialModeCard || !tutorialStepCard) {
    return;
  }
  const normalized = String(mode || "").trim().toLowerCase();
  const resolvedMode =
    normalized === TUTORIAL_MODE_ADVANCED || normalized === TUTORIAL_MODE_QUICK ? normalized : TUTORIAL_MODE_GUIDED;
  const steps = buildTutorialSteps(state.user.role || ROLE_RUSH_OFFICER, resolvedMode);
  if (!steps.length) {
    showToast("No tutorial steps are available for this role.");
    return;
  }
  state.tutorial.active = true;
  state.tutorial.mode = resolvedMode;
  state.tutorial.steps = steps;
  state.tutorial.index = 0;
  tutorialModeCard.classList.add("hidden");
  tutorialStepCard.classList.remove("hidden");
  setTutorialLayerVisible(true);
  renderTutorialStep();
}

function goTutorialStep(delta) {
  if (!state.tutorial.active || !state.tutorial.steps.length) {
    return;
  }
  const next = state.tutorial.index + delta;
  if (next < 0 || next >= state.tutorial.steps.length) {
    return;
  }
  state.tutorial.index = next;
  renderTutorialStep();
}

async function completeTutorialFlow() {
  if (state.tutorial.completing) {
    return;
  }
  state.tutorial.completing = true;
  if (tutorialNextBtn) {
    tutorialNextBtn.disabled = true;
    tutorialNextBtn.textContent = "Saving...";
  }
  try {
    const payload = await api("/api/auth/tutorial/complete", {
      method: "POST",
      body: {
        mode: state.tutorial.mode,
        version: TUTORIAL_VERSION,
      },
    });
    if (payload && payload.user) {
      state.user = payload.user;
      setSessionHeading();
    }
    closeTutorialOverlay();
    showToast("Tutorial completed. Reopen it anytime from Help → Open Tutorial.");
  } catch (error) {
    showToast(error.message || "Unable to save tutorial completion.");
  } finally {
    state.tutorial.completing = false;
    if (tutorialNextBtn) {
      tutorialNextBtn.disabled = false;
      tutorialNextBtn.textContent =
        state.tutorial.index >= state.tutorial.steps.length - 1 ? "Finish Tutorial" : "Next";
    }
  }
}

async function handleTutorialNext() {
  const isLastStep = state.tutorial.index >= state.tutorial.steps.length - 1;
  if (isLastStep) {
    await completeTutorialFlow();
    return;
  }
  goTutorialStep(1);
}

function maybeLaunchFirstRunTutorial() {
  if (!state.user || !tutorialLayer) {
    return;
  }
  // Keep onboarding available without blocking the first usable view.
  closeTutorialOverlay();
}

function handleTutorialShortcut() {
  if (!state.user) {
    return;
  }
  closeAppMenus();
  openTutorialModeChooser();
}

function handleTutorialKeydown(event) {
  if (!state.tutorial.active || !tutorialLayer || tutorialLayer.classList.contains("hidden")) {
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeTutorialOverlay();
    return;
  }
  if (tutorialModeCard && !tutorialModeCard.classList.contains("hidden")) {
    return;
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    goTutorialStep(-1);
    return;
  }
  if (event.key === "ArrowRight") {
    event.preventDefault();
    handleTutorialNext();
  }
}

function shouldPreferMobileUi() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("desktop") === "1") {
    return false;
  }
  if (window.matchMedia && window.matchMedia("(max-width: 900px)").matches) {
    return true;
  }
  const ua = navigator.userAgent.toLowerCase();
  return /iphone|ipad|ipod|android|mobile/.test(ua);
}

function shouldRedirectToMobileNow() {
  if (!APP_CONFIG.mobile_base || !shouldPreferMobileUi()) {
    return false;
  }
  const currentPath = window.location.pathname.replace(/\/$/, "");
  const mobilePath = APP_CONFIG.mobile_base.replace(/\/$/, "");
  if (!mobilePath) {
    return false;
  }
  if (currentPath === mobilePath || currentPath.startsWith(`${mobilePath}/`)) {
    return false;
  }
  return true;
}

function shouldRedirectToMemberPortal(user) {
  if (!user || user.role !== "Rusher" || !APP_CONFIG.member_base) {
    return false;
  }
  const currentPath = window.location.pathname.replace(/\/$/, "");
  const memberPath = APP_CONFIG.member_base.replace(/\/$/, "");
  if (!memberPath) {
    return false;
  }
  return currentPath !== memberPath;
}

function formatLunchWindow(row) {
  const timeRange =
    row.start_time && row.end_time
      ? `${row.start_time}-${row.end_time}`
      : row.start_time
        ? `${row.start_time}`
        : "";
  const parts = [timeRange, row.location || ""].filter(Boolean);
  return parts.join(" | ");
}

function formatTrendTimestamp(value) {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function renderTrendChart(points) {
  if (!points || points.length < 2) {
    return '<p class="muted">Trend chart appears after at least two rating updates.</p>';
  }
  const width = 760;
  const height = 220;
  const left = 40;
  const right = 14;
  const top = 14;
  const bottom = 26;
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const values = points.map((point) => Number(point.weighted_total || 0));
  let minY = Math.min(...values);
  let maxY = Math.max(...values);
  if (maxY - minY < 1) {
    minY = Math.max(0, minY - 0.5);
    maxY = Math.min(RATING_TOTAL_MAX, maxY + 0.5);
  }
  const yRange = Math.max(0.1, maxY - minY);
  const xStep = chartWidth / Math.max(1, points.length - 1);
  const toX = (index) => left + index * xStep;
  const toY = (value) => top + ((maxY - value) / yRange) * chartHeight;

  const polyline = points
    .map((point, index) => `${toX(index).toFixed(2)},${toY(Number(point.weighted_total || 0)).toFixed(2)}`)
    .join(" ");
  const areaPath = `M ${left},${height - bottom} L ${polyline.replaceAll(" ", " L ")} L ${left + chartWidth},${height - bottom} Z`;
  const horizontalGuides = [0, 1, 2, 3, 4]
    .map((step) => {
      const y = top + (chartHeight / 4) * step;
      return `<line x1="${left}" y1="${y.toFixed(2)}" x2="${(left + chartWidth).toFixed(2)}" y2="${y.toFixed(2)}" class="trend-grid"></line>`;
    })
    .join("");
  const markers = points
    .map((point, index) => {
      const x = toX(index);
      const y = toY(Number(point.weighted_total || 0));
      return `<circle cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="2.7" class="trend-point"></circle>`;
    })
    .join("");

  return `
    <div class="trend-chart-wrap">
      <svg class="trend-chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
        ${horizontalGuides}
        <path d="${areaPath}" class="trend-area"></path>
        <polyline points="${polyline}" class="trend-line"></polyline>
        ${markers}
      </svg>
      <div class="trend-axis">
        <span>${escapeHtml(formatTrendTimestamp(points[0].changed_at))}</span>
        <span>${escapeHtml(formatTrendTimestamp(points[points.length - 1].changed_at))}</span>
      </div>
    </div>
  `;
}

function renderScheduledLunches() {
  if (!scheduledLunchesList) {
    return;
  }
  const rows = state.scheduledLunches || [];
  if (!rows.length) {
    scheduledLunchesList.innerHTML = '<p class="muted">No scheduled touchpoints yet.</p>';
    return;
  }

  scheduledLunchesList.innerHTML = rows
    .map((row) => {
      const timing = formatLunchWindow(row);
      const timingText = timing || "All-day touchpoint";
      const assigned = row.assigned_officer_username ? `Assigned: ${row.assigned_officer_username}` : "Assigned: Unassigned";
      const notes = row.notes || "No notes";
      const calendarAction = row.google_calendar_url
        ? `<a class="quick-nav-link" href="${escapeHtml(row.google_calendar_url)}" target="_blank" rel="noopener">Open Event</a>`
        : "";
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(row.lunch_date)} | ${escapeHtml(row.pnm_code)} | ${escapeHtml(row.pnm_name)}</strong>
            <span>${escapeHtml(timingText)}</span>
          </div>
          <div class="muted">${escapeHtml(assigned)} | Scheduled by ${escapeHtml(row.scheduled_by_username)}</div>
          <div class="muted">${escapeHtml(notes)}</div>
          ${calendarAction ? `<div class="action-row">${calendarAction}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function formatCalendarWindow(item) {
  const start = item.start_time || "";
  const end = item.end_time || "";
  if (start && end) {
    return `${start}-${end}`;
  }
  if (start) {
    return start;
  }
  return "All day";
}

function renderRushCalendar() {
  if (!rushCalendarTable || !rushCalendarStats) {
    return;
  }
  const canManageEvents = roleCanUseAdminPanel();
  if (rushEventForm) {
    rushEventForm.classList.toggle("hidden", !canManageEvents);
  }
  if (rushEventPermissionNotice) {
    rushEventPermissionNotice.classList.toggle("hidden", canManageEvents);
  }
  const items = state.rushCalendarItems || [];
  const stats = state.rushCalendarStats || { total_count: 0, official_event_count: 0, lunch_count: 0, this_week_count: 0 };
  rushCalendarStats.innerHTML = `
    <div class="card"><strong>${Number(stats.total_count || 0)}</strong><p>Total Timeline Items</p></div>
    <div class="card"><strong>${Number(stats.official_event_count || 0)}</strong><p>Official Rush Events</p></div>
    <div class="card"><strong>${Number(stats.lunch_count || 0)}</strong><p>Scheduled Touchpoints</p></div>
    <div class="card"><strong>${Number(stats.this_week_count || 0)}</strong><p>This Week</p></div>
  `;

  if (!items.length) {
    rushCalendarTable.innerHTML = '<p class="muted">No rush calendar items yet.</p>';
    return;
  }

  const rows = items
    .map((item) => {
      const isEvent = item.item_type === "rush_event";
      const typeLabel = isEvent ? (item.event_type || "event") : "lunch";
      const title = item.title || (item.pnm_name ? `Lunch with ${item.pnm_name}` : "Calendar Item");
      const creator = item.created_by_username || "-";
      const official = isEvent && item.is_official ? '<span class="pill">Official</span>' : "";
      const details = item.details || "-";
      const googleAction = item.google_calendar_url
        ? `<a class="quick-nav-link" href="${escapeHtml(item.google_calendar_url)}" target="_blank" rel="noopener">Open</a>`
        : "";
      const deleteAction = canManageEvents && isEvent
        ? `<button type="button" class="secondary calendar-remove-btn" data-rush-event-delete="${item.event_id}">Remove</button>`
        : "";
      return `
        <tr>
          <td><strong>${escapeHtml(item.event_date || "")}</strong></td>
          <td>${escapeHtml(formatCalendarWindow(item))}</td>
          <td><span class="pill">${escapeHtml(typeLabel)}</span> ${official}</td>
          <td>${escapeHtml(title)}</td>
          <td>${escapeHtml(item.location || "-")}</td>
          <td>${escapeHtml(details)}</td>
          <td>${escapeHtml(creator)}</td>
          <td>
            <div class="action-row">
              ${googleAction}
              ${deleteAction}
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  rushCalendarTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Time</th>
          <th>Type</th>
          <th>Title</th>
          <th>Location</th>
          <th>Details</th>
          <th>Created By</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderWeeklyGoalMetricOptions() {
  if (!weeklyGoalMetric) {
    return;
  }
  const options = (state.weeklyGoalMetricOptions || [])
    .map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`)
    .join("");
  weeklyGoalMetric.innerHTML = options || `
    <option value="manual">Manual Progress</option>
    <option value="ratings_submitted">Ratings Submitted</option>
    <option value="lunches_logged">Touchpoints Logged</option>
    <option value="pnms_created">PNMs Added</option>
    <option value="chat_messages">Chat Messages</option>
    <option value="rush_events_created">Rush Events Created</option>
  `;
}

function renderWeeklyGoalAssignedUsers() {
  if (!weeklyGoalAssignedUser) {
    return;
  }
  const options = ['<option value="">Team goal (unassigned)</option>'];
  const members = state.members || [];
  members
    .filter((member) => member && member.user_id && member.username)
    .forEach((member) => {
      const emoji = member.emoji ? `${member.emoji} ` : "";
      options.push(
        `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username} (${member.role})`)}</option>`
      );
    });
  weeklyGoalAssignedUser.innerHTML = options.join("");
}

function renderWeeklyGoals() {
  if (!weeklyGoalsList || !weeklyGoalSummary) {
    return;
  }
  if (weeklyGoalForm) {
    weeklyGoalForm.classList.toggle("hidden", !roleCanManageOperations());
  }
  const summary = state.weeklyGoalSummary || {
    total: 0,
    active: 0,
    completed: 0,
    overdue: 0,
    completion_rate: 0,
  };
  weeklyGoalSummary.innerHTML = `
    <div class="card"><strong>${Number(summary.total || 0)}</strong><p>Total Goals</p></div>
    <div class="card"><strong>${Number(summary.active || 0)}</strong><p>Active</p></div>
    <div class="card"><strong>${Number(summary.completed || 0)}</strong><p>Completed</p></div>
    <div class="card"><strong>${Number(summary.overdue || 0)}</strong><p>Overdue</p></div>
    <div class="card"><strong>${Number(summary.completion_rate || 0)}%</strong><p>Completion Rate</p></div>
  `;

  const goals = state.weeklyGoals || [];
  if (!goals.length) {
    weeklyGoalsList.innerHTML = '<p class="muted">No weekly goals created yet.</p>';
    return;
  }

  const canManage = roleCanManageOperations();
  const isHead = roleCanUseAdminPanel();
  weeklyGoalsList.innerHTML = goals
    .map((goal) => {
      const statusClass = goal.status === "completed" ? "good" : goal.status === "overdue" ? "bad" : "warn";
      const assignment = goal.assigned_username ? `Assigned: ${goal.assigned_username}` : "Team Goal";
      const weekWindow = `${goal.week_start} to ${goal.week_end}`;
      const actions = [];
      if (canManage && goal.metric_type === "manual" && !goal.is_completed && !goal.is_archived) {
        actions.push(`<button type="button" class="secondary" data-goal-progress="${goal.goal_id}">+1 Progress</button>`);
      }
      if (canManage && !goal.is_completed && !goal.is_archived) {
        actions.push(`<button type="button" class="secondary" data-goal-complete="${goal.goal_id}">Mark Complete</button>`);
      }
      if (isHead) {
        const label = goal.is_archived ? "Unarchive" : "Archive";
        actions.push(`<button type="button" class="secondary" data-goal-archive="${goal.goal_id}" data-goal-archived="${goal.is_archived ? "1" : "0"}">${label}</button>`);
      }
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(goal.title)}</strong>
            <span class="${statusClass}">${escapeHtml(goal.status)}</span>
          </div>
          <div class="muted">${escapeHtml(goal.metric_label)} | Target ${goal.target_count} | Progress ${goal.progress_count} (${goal.percent_complete}%)</div>
          <div class="muted">${escapeHtml(assignment)} | ${escapeHtml(weekWindow)}</div>
          ${goal.description ? `<div class="muted">${escapeHtml(goal.description)}</div>` : ""}
          ${actions.length ? `<div class="action-row">${actions.join("")}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function renderNotifications() {
  renderOperationsUnreadBadge();
  updateNotificationBell();
  renderGlobalNotificationsTray();
}

function renderOperationsUnreadBadge() {
  if (!operationsUnreadBadge) {
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  if (unread <= 0) {
    operationsUnreadBadge.classList.add("hidden");
    operationsUnreadBadge.textContent = "0";
    return;
  }
  operationsUnreadBadge.classList.remove("hidden");
  operationsUnreadBadge.textContent = unread > 99 ? "99+" : String(unread);
}

function renderOfficerChatStats() {
  if (!officerChatStats) {
    return;
  }
  if (!roleCanManageOperations()) {
    officerChatStats.innerHTML = '<p class="muted">Rush Officer access required.</p>';
    return;
  }
  const payload = state.officerChatStats;
  if (!payload || !payload.summary) {
    officerChatStats.innerHTML = '<p class="muted">Chat stats unavailable.</p>';
    return;
  }
  const summary = payload.summary;
  const topTag = payload.top_tags && payload.top_tags.length ? `#${payload.top_tags[0].tag}` : "None";
  const topSender = payload.top_senders && payload.top_senders.length ? payload.top_senders[0].username : "None";
  officerChatStats.innerHTML = `
    <div class="card"><strong>${Number(summary.total_messages || 0)}</strong><p>Total Messages</p></div>
    <div class="card"><strong>${Number(summary.messages_last_24h || 0)}</strong><p>Last 24h</p></div>
    <div class="card"><strong>${Number(summary.active_senders_7d || 0)}</strong><p>Active Senders (7d)</p></div>
    <div class="card"><strong>${escapeHtml(topTag)}</strong><p>Top Tag</p></div>
    <div class="card"><strong>${escapeHtml(topSender)}</strong><p>Top Contributor</p></div>
  `;
}

function formatChatClock(value) {
  if (!value) {
    return "--:--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--:--";
  }
  return parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatChatDayLabel(value) {
  if (!value) {
    return "Recent";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Recent";
  }
  const dayStart = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.round((dayStart.getTime() - todayStart.getTime()) / 86400000);
  if (diffDays === 0) {
    return "Today";
  }
  if (diffDays === -1) {
    return "Yesterday";
  }
  return parsed.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function chatRoleLabel(role) {
  if (role === "Head Rush Officer") {
    return "Head";
  }
  if (role === "Rush Officer") {
    return "Officer";
  }
  return "Member";
}

function shouldAutoScrollChatFeed() {
  if (!officerChatList) {
    return true;
  }
  const remaining = officerChatList.scrollHeight - officerChatList.scrollTop - officerChatList.clientHeight;
  return remaining <= 120;
}

function renderOfficerChat() {
  if (!officerChatList || !officerChatForm) {
    return;
  }
  const canUse = roleCanManageOperations();
  officerChatForm.classList.toggle("hidden", !canUse);
  if (!canUse) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>Rush Officer access required.</strong><p class="muted">Only approved Rush Officers and Head Rush Officers can access this thread.</p></div>';
    return;
  }

  const rows = state.officerChatMessages || [];
  if (!rows.length) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>No messages yet.</strong><p class="muted">Start the thread with a kickoff update, assignment, or concern.</p></div>';
    return;
  }

  const keepPinnedToBottom = shouldAutoScrollChatFeed();
  const parts = [];
  let lastDayKey = "";

  rows.forEach((message) => {
    const createdAt = message.created_at || "";
    const parsed = new Date(createdAt);
    if (!Number.isNaN(parsed.getTime())) {
      const nextDayKey = `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}`;
      if (nextDayKey !== lastDayKey) {
        parts.push(`<div class="chat-day-separator"><span>${escapeHtml(formatChatDayLabel(createdAt))}</span></div>`);
        lastDayKey = nextDayKey;
      }
    }

    const sender = message.sender || {};
    const username = sender.username || "Unknown";
    const emoji = sender.emoji ? String(sender.emoji).trim() : "";
    const avatarText = emoji || username.charAt(0).toUpperCase() || "?";
    const role = chatRoleLabel(sender.role);
    const classes = ["discord-message"];
    if (message.from_me) {
      classes.push("is-own");
    }
    if (message.mentions_me) {
      classes.push("is-mention");
    }
    const tags = (message.tags || [])
      .map((tag) => `<span class="pill chat-pill-tag">#${escapeHtml(tag)}</span>`)
      .join("");
    const mentions = (message.mentions || [])
      .map((item) => `<span class="pill chat-pill-mention">@${escapeHtml(item.username)}</span>`)
      .join("");
    const edited = message.edited_at ? '<span class="chat-edited">(edited)</span>' : "";
    const text = escapeHtml(message.message || "").replace(/\n/g, "<br />");
    const metadata = `${tags}${mentions}${edited}`;
    parts.push(`
      <article class="${classes.join(" ")}">
        <div class="chat-avatar${emoji ? "" : " is-fallback"}">${escapeHtml(avatarText)}</div>
        <div class="chat-bubble">
          <div class="chat-head-row">
            <strong class="chat-user">${escapeHtml(username)}</strong>
            <span class="chat-role-pill">${escapeHtml(role)}</span>
            <time class="chat-time" datetime="${escapeHtml(createdAt)}" title="${escapeHtml(formatLastSeen(createdAt))}">
              ${escapeHtml(formatChatClock(createdAt))}
            </time>
          </div>
          <p class="chat-message-body">${text}</p>
          ${metadata ? `<div class="chat-meta-row">${metadata}</div>` : ""}
        </div>
      </article>
    `);
  });

  officerChatList.innerHTML = parts.join("");
  if (keepPinnedToBottom || rows.length <= 12) {
    officerChatList.scrollTop = officerChatList.scrollHeight;
  }
}

function renderAssignedRushSection() {
  if (!assignedRushPanel || !assignedRushTable || !assignedRushTitle || !assignedRushSubtitle) {
    return;
  }
  if (!roleCanViewAssignedRushes()) {
    assignedRushPanel.classList.add("hidden");
    assignedRushTable.innerHTML = "";
    if (assignedRushDownloadBtn) {
      assignedRushDownloadBtn.classList.add("hidden");
      assignedRushDownloadBtn.disabled = true;
    }
    return;
  }

  assignedRushPanel.classList.remove("hidden");
  const isHead = state.user && state.user.role === "Head Rush Officer";
  const rows = Array.isArray(state.assignedRushRows) ? state.assignedRushRows : [];

  if (isHead) {
    assignedRushTitle.textContent = "Assignment Visibility";
    assignedRushSubtitle.textContent = "Live view of assignment teams and primary ownership.";
  } else {
    assignedRushTitle.textContent = "My Assigned Rushees";
    assignedRushSubtitle.textContent = `Rushees assigned to ${state.user.username} and your outreach team.`;
  }

  if (assignedRushDownloadBtn) {
    assignedRushDownloadBtn.classList.remove("hidden");
    assignedRushDownloadBtn.disabled = !rows.length;
  }

  if (!rows.length) {
    assignedRushTable.innerHTML = '<p class="muted">No assignments to display yet.</p>';
    return;
  }

  const groups = packageGroupIndex();
  const pnmsById = new Map((state.pnms || []).map((pnm) => [Number(pnm.pnm_id), pnm]));
  const tableRows = rows
    .map((entry) => {
      const pnm = pnmsById.get(Number(entry.pnm_id)) || null;
      const linkedDisplay = pnm ? linkedRusheeNamesForPnm(pnm, groups) : "None";
      const assignmentTeam = Array.isArray(entry.assigned_officers) ? entry.assigned_officers : [];
      const teamDisplay = assignmentTeamLabel(assignmentTeam);
      const primaryOfficer = primaryAssignmentLabel(entry, assignmentTeam);
      const assignedAt = entry.assigned_at ? formatLastSeen(entry.assigned_at) : "-";
      const officerCell = isHead ? `<td>${escapeHtml(primaryOfficer)}</td>` : "";
      const assignedAtCell = isHead ? `<td>${escapeHtml(assignedAt)}</td>` : "";
      return `
        <tr>
          <td><strong>${escapeHtml(entry.pnm_code || `PNM-${entry.pnm_id}`)}</strong></td>
          <td>${escapeHtml(entry.first_name)} ${escapeHtml(entry.last_name)}</td>
          <td>${escapeHtml(linkedDisplay)}</td>
          <td>${escapeHtml(teamDisplay)}</td>
          <td>${escapeHtml(entry.phone_number || "-")}</td>
          ${officerCell}
          ${assignedAtCell}
          <td>${Number(entry.weighted_total || 0).toFixed(2)}</td>
          <td>${Number(entry.total_lunches || 0)}</td>
          <td>
            <button
              type="button"
              class="secondary assigned-contact-btn"
              data-pnm-id="${Number(entry.pnm_id)}"
              data-pnm-code="${escapeHtml(entry.pnm_code || `pnm-${entry.pnm_id}`)}"
            >
              Add Contact
            </button>
          </td>
        </tr>
      `;
    })
    .join("");

  const officerHeader = isHead ? "<th>Assigned Officer</th><th>Assigned At</th>" : "";
  assignedRushTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th>Linked With</th>
          <th>Assignment Team</th>
          <th>Phone</th>
          ${officerHeader}
          <th>Weighted Total</th>
          <th>Touchpoints</th>
          <th>Contacts</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
}

function renderCalendarShareLinks(data) {
  state.calendarShare = data;
  if (calendarFeedPreview && openGoogleSubscribeBtn) {
    calendarFeedPreview.textContent = data.feed_url || "Calendar URL unavailable.";
    openGoogleSubscribeBtn.href = data.google_subscribe_url || "#";
    openGoogleSubscribeBtn.classList.toggle("hidden", !data.google_subscribe_url);
  }
  if (rushCalendarFeedPreview) {
    rushCalendarFeedPreview.textContent = data.rush_feed_url || data.feed_url || "Rush calendar URL unavailable.";
  }
  if (openRushGoogleSubscribeBtn) {
    openRushGoogleSubscribeBtn.href = data.google_subscribe_url || "#";
    openRushGoogleSubscribeBtn.classList.toggle("hidden", !data.google_subscribe_url);
  }
  if (lunchOnlyFeedPreview) {
    lunchOnlyFeedPreview.textContent = data.lunch_feed_url || "Touchpoint feed URL unavailable.";
  }
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
  const pnmEventDate = document.getElementById("pnmEventDate");
  if (pnmEventDate) {
    pnmEventDate.value = today;
  }
  if (touchpointDrawerDate) {
    touchpointDrawerDate.value = today;
  }
  if (rushEventDate) {
    rushEventDate.value = today;
  }
  if (weeklyGoalWeekStart && weeklyGoalWeekEnd) {
    const now = new Date();
    const dayIndex = now.getDay();
    const mondayOffset = dayIndex === 0 ? -6 : 1 - dayIndex;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    weeklyGoalWeekStart.value = monday.toISOString().slice(0, 10);
    weeklyGoalWeekEnd.value = sunday.toISOString().slice(0, 10);
  }
}

function setRoleEmojiRequirement() {
  regEmoji.required = false;
}

function rushOfficerMembers() {
  return state.members.filter((member) => member.role === "Rush Officer");
}

function renderAssignmentControls() {
  if (!assignPanel || !assignOfficerSelect) {
    return;
  }
  const canAssign = roleCanAssignOfficer();
  assignPanel.classList.toggle("hidden", !canAssign);
  if (!canAssign) {
    return;
  }

  const officers = rushOfficerMembers();
  const options =
    '<option value="">Unassigned</option>' +
    officers
      .map((member) => {
        const emoji = member.emoji ? `${member.emoji} ` : "";
        return `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username}`)}</option>`;
      })
      .join("");
  assignOfficerSelect.innerHTML = options;

  const selected = state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId);
  assignOfficerSelect.value = selected && selected.assigned_officer_id ? String(selected.assigned_officer_id) : "";
}

function renderInterestHints(interests) {
  if (!interestHints) {
    return;
  }
  interestHints.innerHTML = interests.map((interest) => `<option value="${escapeHtml(interest)}"></option>`).join("");
}

function renderStereotypeFilterHints(stereotypes) {
  if (!stereotypeFilterHints) {
    return;
  }
  stereotypeFilterHints.innerHTML = (stereotypes || [])
    .map((stereotype) => `<option value="${escapeHtml(stereotype)}"></option>`)
    .join("");
}

function renderStateFilterHints(options) {
  if (!stateFilterHints) {
    return;
  }
  const rows = [];
  const seen = new Set();
  (options || []).forEach((entry) => {
    const code = normalizeStateCodeToken(entry && entry.code);
    const name = toTitleCase(entry && entry.name ? entry.name : "");
    if (!code || !name) {
      return;
    }
    const keyCode = `code:${code}`;
    if (!seen.has(keyCode)) {
      rows.push(`<option value="${escapeHtml(code)}">${escapeHtml(name)}</option>`);
      seen.add(keyCode);
    }
    const keyName = `name:${name.toLowerCase()}`;
    if (!seen.has(keyName)) {
      rows.push(`<option value="${escapeHtml(name)}">${escapeHtml(code)}</option>`);
      seen.add(keyName);
    }
  });
  stateFilterHints.innerHTML = rows.join("");
}

function initializeFilterHintLists() {
  renderStereotypeFilterHints(DEFAULT_STEREOTYPE_TAGS);
  renderStateFilterHints(STATE_OPTIONS);
}

function renderPnmSelectOptions() {
  const combined = [];
  const seen = new Set();
  [...(state.pnms || []), ...(state.commandCenter.queue || []), ...(state.meetingsWorkspace.candidates || [])].forEach((pnm) => {
    const pnmId = Number(pnm && pnm.pnm_id ? pnm.pnm_id : 0);
    if (!pnmId || seen.has(pnmId)) {
      return;
    }
    seen.add(pnmId);
    combined.push(pnm);
  });
  const options =
    '<option value="">Select rushee</option>' +
    combined
      .map((pnm) => {
        const displayName =
          pnm.name ||
          [pnm.first_name, pnm.last_name].filter(Boolean).join(" ").trim() ||
          pnm.pnm_code ||
          "Unknown PNM";
        const label = `${pnm.pnm_code || "PNM"} | ${displayName}`;
        return `<option value="${pnm.pnm_id}">${escapeHtml(label)}</option>`;
      })
      .join("");
  if (ratingPnm) {
    ratingPnm.innerHTML = options;
  }
  if (touchpointDrawerPnm) {
    touchpointDrawerPnm.innerHTML = options;
  }

  if (state.selectedPnmId) {
    if (ratingPnm) {
      ratingPnm.value = String(state.selectedPnmId);
    }
    if (touchpointDrawerPnm) {
      touchpointDrawerPnm.value = String(state.selectedPnmId);
    }
  }
}

function syncOpenMeetingLink() {
  if (!openMeetingPageBtn) {
    return;
  }
  const selectedId = Number(state.selectedPnmId || 0);
  openMeetingPageBtn.href = selectedId ? `${MEETING_BASE}?pnm_id=${selectedId}` : MEETING_BASE;
}

function renderPnmTable() {
  if (!state.pnms.length) {
    pnmTable.innerHTML = '<p class="muted">No rushees match current filters.</p>';
    return;
  }

  const rows = state.pnms
    .map((pnm) => {
      const own = pnm.own_rating;
      const ownDisplay = own ? `${own.total_score}/${RATING_TOTAL_MAX}` : "Not rated";
      const assignedOfficer = pnm.assigned_officer ? pnm.assigned_officer.username : "Unassigned";
      const linkedDisplay = linkedRusheeNamesForPnm(pnm);
      const weightedPct = Math.max(0, Math.min(100, (Number(pnm.weighted_total) / RATING_TOTAL_MAX) * 100));
      const barWidth = Math.round((weightedPct / 100) * 58);
      const selectedClass = state.selectedPnmId === pnm.pnm_id ? "selected-row" : "";
      const categoryCells = RATING_CRITERIA.map((criterion) => {
        const avgField = PNM_AVG_FIELD_BY_RATING_FIELD[criterion.field];
        const value = Number(pnm[avgField] || 0);
        return `<td>${value.toFixed(2)}</td>`;
      }).join("");
      return `
        <tr class="${selectedClass}">
          <td>${smallPhotoCell(pnm)}</td>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
          <td>${escapeHtml(linkedDisplay)}</td>
          <td>${escapeHtml(pnm.phone_number || "-")}</td>
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
          ${categoryCells}
          <td>${pnm.total_lunches}</td>
          <td>${escapeHtml(assignedOfficer)}</td>
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
          <th>Linked With</th>
          <th>Phone</th>
          <th>Class</th>
          <th>Days Since Event</th>
          <th>Ratings</th>
          <th>Weighted Total</th>
          ${RATING_CRITERIA.map((criterion) => `<th>${escapeHtml(criterion.short_label)}</th>`).join("")}
          <th>Touchpoints</th>
          <th>Assigned Officer</th>
          <th>My Rating</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
  renderPnmBoard();
}

function renderMemberTable() {
  if (!state.members.length) {
    memberTable.innerHTML = '<p class="muted">No members match current filters.</p>';
    return;
  }

  const canDisapproveUsers = roleCanApproveUsers();
  const rows = state.members
    .map((member) => {
      const avgRating = member.avg_rating_given == null ? "Hidden" : member.avg_rating_given.toFixed(2);
      const ratingCount = member.rating_count == null ? "Hidden" : member.rating_count;
      const city = String(member.city || "").trim();
      const stateCode = String(member.state_code || "").trim();
      const selectedClass = Number(state.selectedMemberId) === Number(member.user_id) ? "selected-row" : "";
      const canDisapprove =
        canDisapproveUsers &&
        state.user &&
        member.user_id !== state.user.user_id &&
        member.role !== "Head Rush Officer";
      const disapproveAction = canDisapprove
        ? `<button type="button" class="secondary disapprove-user" data-user-id="${member.user_id}" data-username="${escapeHtml(member.username)}">Disapprove</button>`
        : "";
      return `
        <tr class="${selectedClass}">
          <td>${escapeHtml(member.username)}</td>
          <td>${escapeHtml(member.role)}</td>
          <td>${member.emoji ? escapeHtml(member.emoji) : "-"}</td>
          <td>${city ? escapeHtml(city) : "-"}</td>
          <td>${stateCode ? escapeHtml(stateCode) : "-"}</td>
          <td>${escapeHtml(member.stereotype)}</td>
          <td>${member.interests.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}</td>
          <td>${member.total_lunches}</td>
          <td>${member.lunches_per_week.toFixed(2)}</td>
          <td>${ratingCount}</td>
          <td>${avgRating}</td>
          <td>
            <div class="action-row">
              <button type="button" class="secondary select-member" data-user-id="${member.user_id}">Select</button>
              ${disapproveAction}
            </div>
          </td>
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
          <th>City</th>
          <th>State</th>
          <th>Stereotype</th>
          <th>Interests</th>
          <th>Total Touchpoints</th>
          <th>Touchpoints / Week</th>
          <th>Ratings Given</th>
          <th>Avg Rating Given</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

async function loadSameStatePnms() {
  if (!sameStatePnmsHeader || !sameStatePnmsList) {
    return;
  }
  const selectedMember = state.members.find((member) => Number(member.user_id) === Number(state.selectedMemberId)) || null;
  if (!selectedMember) {
    state.sameStatePnms = [];
    renderSameStatePnmsPanel();
    return;
  }
  const stateCode = String(selectedMember.state_code || "").trim();
  if (!stateCode) {
    state.sameStatePnms = [];
    renderSameStatePnmsPanel();
    return;
  }
  try {
    const payload = await api(`/api/pnms${toQuery({ state: stateCode })}`);
    state.sameStatePnms = payload.pnms || [];
  } catch {
    state.sameStatePnms = [];
  }
  renderSameStatePnmsPanel();
}

function renderSameStatePnmsPanel() {
  if (!sameStatePnmsHeader || !sameStatePnmsList) {
    return;
  }
  const selectedMember = state.members.find((member) => Number(member.user_id) === Number(state.selectedMemberId)) || null;
  if (!selectedMember) {
    sameStatePnmsHeader.textContent = "Select a member to view rushees from the same state.";
    sameStatePnmsList.innerHTML = '<p class="muted">No member selected.</p>';
    return;
  }
  const stateCode = String(selectedMember.state_code || "").trim();
  if (!stateCode) {
    sameStatePnmsHeader.textContent = `${selectedMember.username} has no state set.`;
    sameStatePnmsList.innerHTML = '<p class="muted">No state set for this member.</p>';
    return;
  }

  const rows = state.sameStatePnms || [];
  sameStatePnmsHeader.textContent = `${selectedMember.username} | ${stateCode} | ${rows.length} same-state rushees`;
  if (!rows.length) {
    sameStatePnmsList.innerHTML = '<p class="muted">No rushees found in this state.</p>';
    return;
  }
  sameStatePnmsList.innerHTML = rows
    .map((pnm) => {
      const meetingHref = `${MEETING_BASE}?pnm_id=${Number(pnm.pnm_id)}`;
      return `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</strong>
            <span>${Number(pnm.weighted_total || 0).toFixed(2)}</span>
          </div>
          <div class="muted">${escapeHtml(pnm.hometown || "-")}</div>
          <div class="action-row">
            <button type="button" class="secondary open-same-state-pnm" data-pnm-id="${Number(pnm.pnm_id)}" data-state="${escapeHtml(stateCode)}">Open In Rushees</button>
            <a class="quick-nav-link" href="${escapeHtml(meetingHref)}">Open Meeting Packet</a>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderAnalytics(overview) {
  if (!analyticsCards || !overview) {
    return;
  }
  const pnmCards = overview.top_pnms
    .slice(0, 5)
    .map(
      (pnm) => `
      <article class="card">
        <strong>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.name)}</strong>
        <p>Weighted Total: ${pnm.weighted_total.toFixed(2)} | Ratings: ${pnm.rating_count} | Touchpoints: ${pnm.total_lunches}</p>
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
        <p>Touchpoints: ${member.total_lunches} | Touchpoints/Week: ${member.lunches_per_week.toFixed(2)}</p>
      </article>
    `
    )
    .join("");

  analyticsCards.innerHTML = `${pnmCards}${memberCards}` || '<p class="muted">No analytics yet.</p>';
}

function renderLeaderboard(rows) {
  if (!leaderboardTable) {
    return;
  }
  if (!rows.length) {
    leaderboardTable.innerHTML = '<p class="muted">No rushee rankings available yet.</p>';
    return;
  }

  const rankBadge = (rank) => {
    if (rank === 1) {
      return '<span class="rank-chip rank-gold">#1</span>';
    }
    if (rank === 2) {
      return '<span class="rank-chip rank-silver">#2</span>';
    }
    if (rank === 3) {
      return '<span class="rank-chip rank-bronze">#3</span>';
    }
    return `<span class="rank-chip">#${rank}</span>`;
  };

  const tableRows = rows
    .map((item) => {
      const assigned = item.assigned_officer_username || "Unassigned";
      return `
        <tr>
          <td>${rankBadge(item.rank)}</td>
          <td><strong>${escapeHtml(item.pnm_code)}</strong></td>
          <td>${escapeHtml(item.name)}</td>
          <td>${item.weighted_total.toFixed(2)}</td>
          <td>${item.rating_count}</td>
          <td>${item.total_lunches}</td>
          <td>${item.days_since_first_event}</td>
          <td>${escapeHtml(assigned)}</td>
        </tr>
      `;
    })
    .join("");

  leaderboardTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Code</th>
          <th>Name</th>
          <th>Weighted Total</th>
          <th>Ratings</th>
          <th>Touchpoints</th>
          <th>Days</th>
          <th>Assigned Officer</th>
        </tr>
      </thead>
      <tbody>${tableRows}</tbody>
    </table>
  `;
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

function staleReasonLabel(value) {
  if (value === "never_rated") {
    return "Never Rated";
  }
  if (value === "rating_older_than_recent_touchpoint") {
    return "Behind Touchpoint";
  }
  if (value === "no_recent_rating") {
    return "No Recent Rating";
  }
  return "Needs Update";
}

function commandQueueSelectedItem() {
  const selectedId = Number(state.commandCenter.selectedQueuePnmId || 0);
  if (!selectedId) {
    return null;
  }
  return (
    (state.commandCenter.queue || []).find((item) => Number(item.pnm_id) === selectedId) ||
    null
  );
}

function syncCommandMeetingLink() {
  if (!commandOpenMeetingBtn) {
    return;
  }
  const selected = commandQueueSelectedItem();
  const selectedId = selected ? Number(selected.pnm_id || 0) : 0;
  commandOpenMeetingBtn.href = selectedId ? `${MEETING_BASE}?pnm_id=${selectedId}` : MEETING_BASE;
}

function touchpointDrawerSelectedPnmId() {
  const direct = Number(touchpointDrawerPnm && touchpointDrawerPnm.value ? touchpointDrawerPnm.value : 0);
  if (direct) {
    return direct;
  }
  return Number(state.touchpoint.pnmId || 0);
}

function syncTouchpointDrawerSelection() {
  if (!touchpointDrawerPnm) {
    return;
  }
  const preferredId = Number(state.touchpoint.pnmId || state.selectedPnmId || state.commandCenter.selectedQueuePnmId || 0);
  touchpointDrawerPnm.value = preferredId ? String(preferredId) : "";
}

function openTouchpointDrawer(options = {}) {
  if (!touchpointDrawer || !touchpointDrawerForm) {
    return;
  }
  const source = String(options.source || "shell").trim() || "shell";
  const fallbackPnmId =
    Number(options.pnmId || 0) ||
    Number(state.selectedPnmId || 0) ||
    Number(state.commandCenter.selectedQueuePnmId || 0) ||
    null;
  state.touchpoint.source = source;
  state.touchpoint.pnmId = fallbackPnmId;
  state.touchpoint.lastGoogleUrl = "";
  if (touchpointDrawerLastGoogleLink) {
    touchpointDrawerLastGoogleLink.classList.add("hidden");
    touchpointDrawerLastGoogleLink.href = "#";
  }
  if (touchpointDrawerTitle) {
    touchpointDrawerTitle.textContent = source === "operations" ? "Schedule Shared Touchpoint" : "Schedule Touchpoint";
  }
  if (touchpointDrawerSubtitle) {
    touchpointDrawerSubtitle.textContent =
      source === "operations"
        ? "Create a shared lunch or follow-up event without leaving operations."
        : "Create one shared touchpoint from the selected rushee context.";
  }
  renderPnmSelectOptions();
  if (touchpointDrawerDate && !touchpointDrawerDate.value) {
    touchpointDrawerDate.value = new Date().toISOString().slice(0, 10);
  }
  syncTouchpointDrawerSelection();
  setTouchpointDrawerVisible(true);
  const focusTarget = touchpointDrawerPnm && !touchpointDrawerPnm.value ? touchpointDrawerPnm : touchpointDrawerDate || touchpointDrawerPnm;
  if (focusTarget) {
    window.setTimeout(() => focusTarget.focus(), 30);
  }
}

function closeTouchpointDrawer() {
  setTouchpointDrawerVisible(false);
}

function renderCommandSelectedPhoto(item) {
  if (!commandSelectedPhoto || !commandSelectedPhotoPlaceholder) {
    return;
  }
  if (!item || !item.photo_url) {
    commandSelectedPhoto.classList.add("hidden");
    commandSelectedPhoto.removeAttribute("src");
    commandSelectedPhotoPlaceholder.classList.remove("hidden");
    return;
  }
  commandSelectedPhoto.src = item.photo_url;
  commandSelectedPhoto.alt = item.name || "Selected PNM";
  commandSelectedPhoto.classList.remove("hidden");
  commandSelectedPhotoPlaceholder.classList.add("hidden");
}

function applyCommandRatingFormForSelected() {
  if (!commandRatingForm) {
    return;
  }
  const selected = commandQueueSelectedItem();
  renderCommandSelectedPhoto(selected);
  if (!selected) {
    commandRatingForm.reset();
    if (commandSelectedName) {
      commandSelectedName.textContent = "Select a rushee from queue";
    }
    if (commandSelectedMeta) {
      commandSelectedMeta.textContent = "Queue details, assignment ownership, and latest touchpoint appear here.";
    }
    if (commandSelectedSignal) {
      commandSelectedSignal.textContent = "Pick a rushee to load assignment, freshness, and packet context.";
    }
    if (commandSelectedStats) {
      commandSelectedStats.innerHTML = "";
    }
    syncCommandMeetingLink();
    return;
  }

  const own = selected.own_rating || null;
  const girlsMax = ratingCriteriaForField("good_with_girls")?.max || 10;
  const processMax = ratingCriteriaForField("will_make_it")?.max || 10;
  const personableMax = ratingCriteriaForField("personable")?.max || 10;
  const alcoholMax = ratingCriteriaForField("alcohol_control")?.max || 10;
  const igMax = ratingCriteriaForField("instagram_marketability")?.max || 5;
  const assignedTeam = Array.isArray(selected.assigned_officers) ? selected.assigned_officers : [];
  const assignedLabel = assignedTeam.length
    ? assignedTeam
        .map((officer) => {
          const emoji = officer && officer.emoji ? `${officer.emoji} ` : "";
          return `${emoji}${officer && officer.username ? officer.username : "Unknown"}`;
        })
        .join(", ")
    : selected.assigned_officer_username || "Unassigned";
  const touchpointLabel = selected.last_touchpoint_at ? formatTrendTimestamp(selected.last_touchpoint_at) : "None";
  const mineLabel = selected.last_rating_by_me_at ? formatTrendTimestamp(selected.last_rating_by_me_at) : "Never";
  const staleLabel = selected.needs_rating_update ? staleReasonLabel(selected.stale_reason) : "Fresh";
  if (commandSelectedName) {
    commandSelectedName.textContent = `${selected.pnm_code} | ${selected.name}`;
  }
  if (commandSelectedMeta) {
    commandSelectedMeta.textContent =
      `Score ${Number(selected.weighted_total || 0).toFixed(2)} | Assigned: ${assignedLabel} | Touchpoint: ${touchpointLabel} | My Rating: ${mineLabel} | ${staleLabel}`;
  }
  if (commandSelectedSignal) {
    commandSelectedSignal.textContent =
      `${selected.needs_rating_update ? "Needs follow-up" : "Ready"} · ${assignedTeam.length ? `${assignedTeam.length} officer${assignedTeam.length === 1 ? "" : "s"} on coverage` : "No assignment team"} · Priority ${Number(selected.priority_score || 0).toFixed(0)}`;
  }
  if (commandSelectedStats) {
    commandSelectedStats.innerHTML = `
      <article class="command-stat-card">
        <span>Weighted Total</span>
        <strong>${Number(selected.weighted_total || 0).toFixed(2)}</strong>
      </article>
      <article class="command-stat-card">
        <span>Ratings</span>
        <strong>${Number(selected.rating_count || 0)}</strong>
      </article>
      <article class="command-stat-card">
        <span>Touchpoints</span>
        <strong>${Number(selected.total_lunches || 0)}</strong>
      </article>
      <article class="command-stat-card">
        <span>My Last Update</span>
        <strong>${escapeHtml(mineLabel)}</strong>
      </article>
    `;
  }
  const girlsInput = document.getElementById("commandRateGirls");
  const processInput = document.getElementById("commandRateProcess");
  const personableInput = document.getElementById("commandRatePersonable");
  const alcoholInput = document.getElementById("commandRateAlcohol");
  const igInput = document.getElementById("commandRateIg");
  const commentInput = document.getElementById("commandRateComment");
  if (girlsInput) {
    girlsInput.value = own ? Math.min(Number(own.good_with_girls || 0), girlsMax) : 0;
  }
  if (processInput) {
    processInput.value = own ? Math.min(Number(own.will_make_it || 0), processMax) : 0;
  }
  if (personableInput) {
    personableInput.value = own ? Math.min(Number(own.personable || 0), personableMax) : 0;
  }
  if (alcoholInput) {
    alcoholInput.value = own ? Math.min(Number(own.alcohol_control || 0), alcoholMax) : 0;
  }
  if (igInput) {
    igInput.value = own ? Math.min(Number(own.instagram_marketability || 0), igMax) : 0;
  }
  if (commentInput) {
    commentInput.value = own && own.comment ? own.comment : "";
  }
  syncWatchButtons();
  syncCommandMeetingLink();
}

function renderCommandCenter() {
  if (!commandCenterSection) {
    return;
  }
  const canUse = roleCanUseCommandCenter();
  commandCenterSection.classList.toggle("hidden", !canUse);
  if (!canUse) {
    return;
  }

  const summary = state.commandCenter.summary || {};
  if (commandQueueCount) {
    commandQueueCount.textContent = String(Number(summary.queue_count || 0));
  }
  if (commandStaleCount) {
    commandStaleCount.textContent = String(Number(summary.stale_count || 0));
  }
  if (commandRecentCount) {
    commandRecentCount.textContent = String(Number(summary.recent_change_count || 0));
  }
  if (commandWindowLabel) {
    commandWindowLabel.textContent = `Window: last ${Number(summary.window_hours || state.commandCenter.windowHours || 72)} hours`;
  }

  const queue = Array.isArray(state.commandCenter.queue) ? state.commandCenter.queue : [];
  if (!state.commandCenter.selectedQueuePnmId || !queue.some((item) => Number(item.pnm_id) === Number(state.commandCenter.selectedQueuePnmId))) {
    state.commandCenter.selectedQueuePnmId = queue.length ? Number(queue[0].pnm_id) : null;
  }

  if (commandCenterQueue) {
    if (!queue.length) {
      const detail = state.commandCenter.error || "No queue items available yet.";
      commandCenterQueue.innerHTML = `<p class="muted">${escapeHtml(detail)}</p>`;
    } else {
      commandCenterQueue.innerHTML = queue
        .map((item) => {
          const isSelected = Number(item.pnm_id) === Number(state.commandCenter.selectedQueuePnmId);
          const selectedClass = isSelected ? " selected-row" : "";
          const staleBadge = item.needs_rating_update
            ? `<span class="pill warn">${escapeHtml(staleReasonLabel(item.stale_reason))}</span>`
            : '<span class="pill good">Fresh</span>';
          const assignedBadge = item.is_assigned_to_me ? '<span class="pill">Assigned To Me</span>' : "";
          const touchpoint = item.last_touchpoint_at ? formatTrendTimestamp(item.last_touchpoint_at) : "No touchpoint";
          return `
            <div class="entry${selectedClass}">
              <button type="button" class="command-queue-btn" data-command-queue-pnm-id="${Number(item.pnm_id)}">
                <div class="entry-title">
                  <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</strong>
                  <span>${Number(item.weighted_total || 0).toFixed(2)}</span>
                </div>
                <div class="muted">Touchpoint: ${escapeHtml(touchpoint)}</div>
                <div class="muted">Assigned: ${escapeHtml(item.assigned_officer_username || "Unassigned")}</div>
                <div class="command-chip-row">${staleBadge}${assignedBadge}</div>
              </button>
            </div>
          `;
        })
        .join("");
    }
  }

  if (commandStaleList) {
    const staleRows = Array.isArray(state.commandCenter.staleAlerts) ? state.commandCenter.staleAlerts : [];
    if (!staleRows.length) {
      commandStaleList.innerHTML = '<p class="muted">No stale alerts in this window.</p>';
    } else {
      commandStaleList.innerHTML = staleRows
        .map(
          (item) => `
            <div class="entry">
              <div class="entry-title">
                <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</strong>
                <span>${escapeHtml(staleReasonLabel(item.stale_reason))}</span>
              </div>
              <div class="muted">Last touchpoint: ${escapeHtml(item.last_touchpoint_at ? formatTrendTimestamp(item.last_touchpoint_at) : "None")}</div>
            </div>
          `
        )
        .join("");
    }
  }

  if (commandRecentChanges) {
    const changes = Array.isArray(state.commandCenter.recentChanges) ? state.commandCenter.recentChanges : [];
    if (!changes.length) {
      commandRecentChanges.innerHTML = '<p class="muted">No rating changes in this window.</p>';
    } else {
      commandRecentChanges.innerHTML = changes
        .map((item) => {
          const delta = Number(item.delta_total || 0);
          const deltaClass = delta > 0 ? "good" : delta < 0 ? "bad" : "";
          const deltaLabel = delta > 0 ? `+${delta}` : `${delta}`;
          const changedBy = item.changed_by && item.changed_by.username ? item.changed_by.username : "Member";
          const comment = String(item.comment || "").trim();
          return `
            <div class="entry">
              <div class="entry-title">
                <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.pnm_name)}</strong>
                <span class="${deltaClass}">${escapeHtml(deltaLabel)}</span>
              </div>
              <div class="muted">${escapeHtml(changedBy)} | ${escapeHtml(formatTrendTimestamp(item.changed_at))}</div>
              <div class="muted">${escapeHtml(comment || "Rating update logged.")}</div>
            </div>
          `;
        })
        .join("");
    }
  }

  applyCommandRatingFormForSelected();
}

function setViewPreference(key, value) {
  state.viewPrefs[key] = value;
  writeStoredJson(key.replace(/[A-Z]/g, (char) => `-${char.toLowerCase()}`), value);
}

function currentWatchlistIds() {
  return Array.isArray(state.watchlist) ? state.watchlist.map((value) => Number(value)).filter((value) => value > 0) : [];
}

function isWatchedPnm(pnmId) {
  return currentWatchlistIds().includes(Number(pnmId));
}

function toggleWatchlistPnm(pnmId) {
  const target = Number(pnmId || 0);
  if (!target) {
    return false;
  }
  const next = new Set(currentWatchlistIds());
  if (next.has(target)) {
    next.delete(target);
  } else {
    next.add(target);
  }
  state.watchlist = Array.from(next);
  writeStoredJson("watchlist", state.watchlist);
  renderCommandWorkspaceExtras();
  renderMeetingsWorkspace();
  syncWatchButtons();
  return next.has(target);
}

function syncWatchButtons() {
  const selectedCommand = state.commandCenter.selectedQueuePnmId;
  if (commandWatchToggleBtn) {
    commandWatchToggleBtn.textContent = isWatchedPnm(selectedCommand) ? "Pinned for Meetings" : "Pin for Meetings";
  }
  if (rusheeWatchToggleBtn) {
    rusheeWatchToggleBtn.textContent = isWatchedPnm(state.selectedPnmId) ? "Pinned for Meetings" : "Pin for Meetings";
  }
}

function updateNotificationBell() {
  if (!appNotificationsBadge) {
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  appNotificationsBadge.textContent = String(unread);
  appNotificationsBadge.classList.toggle("hidden", unread <= 0);
}

function renderGlobalNotificationsTray() {
  if (!appNotificationsList) {
    return;
  }
  const unread = Number(state.unreadNotifications || 0);
  if (appNotificationsReadAllBtn) {
    appNotificationsReadAllBtn.textContent = unread > 0 ? `Mark All Read (${unread})` : "Mark All Read";
    appNotificationsReadAllBtn.disabled = unread <= 0;
  }
  if (!state.notifications.length) {
    appNotificationsList.innerHTML = '<p class="muted">No notifications right now.</p>';
    return;
  }
  appNotificationsList.innerHTML = state.notifications
    .slice(0, 20)
    .map(
      (item) => `
        <div class="entry${item.is_read ? "" : " notification-unread"}">
          <div class="entry-title">
            <strong>${escapeHtml(item.title || "Notification")}</strong>
            <span>${escapeHtml(formatLastSeen(item.created_at))}</span>
          </div>
          ${item.body ? `<div class="muted">${escapeHtml(item.body)}</div>` : ""}
          <div class="action-row">
            ${item.is_read ? "" : `<button type="button" class="secondary" data-notification-read="${item.notification_id}">Mark Read</button>`}
            ${item.link_path ? `<a class="quick-nav-link" href="${escapeHtml(resolveTenantPath(item.link_path))}">Open</a>` : ""}
          </div>
        </div>
      `
    )
    .join("");
}

function toggleNotificationsTray(forceOpen) {
  if (!appNotificationsTray) {
    return;
  }
  const next = forceOpen !== undefined ? Boolean(forceOpen) : appNotificationsTray.classList.contains("hidden");
  appNotificationsTray.classList.toggle("hidden", !next);
  appNotificationsTray.setAttribute("aria-hidden", next ? "false" : "true");
}

function renderCommandWorkspaceExtras() {
  if (commandPendingCount) {
    commandPendingCount.textContent = String(Number((state.commandWorkspace.teamPulse && state.commandWorkspace.teamPulse.pending_approvals) || 0));
  }
  if (commandNeedsHelpCount) {
    commandNeedsHelpCount.textContent = String(Number((state.commandWorkspace.teamPulse && state.commandWorkspace.teamPulse.needs_help) || 0));
  }
  if (commandUnassignedCount) {
    commandUnassignedCount.textContent = String(Number((state.commandWorkspace.teamPulse && state.commandWorkspace.teamPulse.unassigned_pnms) || 0));
  }
  if (commandAttentionList) {
    const rows = state.commandWorkspace.attention || [];
    commandAttentionList.innerHTML = rows.length
      ? rows
          .map(
            (item) => `
              <div class="entry">
                <div class="entry-title">
                  <strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</strong>
                  <span>${escapeHtml(item.label)}</span>
                </div>
                <div class="muted">${escapeHtml(item.detail || "")}</div>
                <div class="action-row">
                  <button type="button" class="secondary" data-open-pnm-id="${Number(item.pnm_id)}">Open Rushee</button>
                  <a class="quick-nav-link" href="${escapeHtml(`${MEETING_BASE}?pnm_id=${Number(item.pnm_id)}`)}">Packet</a>
                </div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No high-priority exceptions right now.</p>';
  }
  if (commandTodayList) {
    const rows = state.commandWorkspace.today || [];
    commandTodayList.innerHTML = rows.length
      ? rows
          .map(
            (item) => `
              <div class="entry">
                <div class="entry-title">
                  <strong>${escapeHtml(item.title || "")}</strong>
                  <span>${escapeHtml(item.start_time || item.event_date || "")}</span>
                </div>
                <div class="muted">${escapeHtml(item.location || "No location")} | ${escapeHtml(item.meta || "")}</div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No same-day actions queued.</p>';
  }
  if (commandPulseCards) {
    const pulse = state.commandWorkspace.teamPulse || {};
    const cards = [
      { label: "Pending Approvals", value: Number(pulse.pending_approvals || 0) },
      { label: "Unassigned Rushees", value: Number(pulse.unassigned_pnms || 0) },
      { label: "Needs Help", value: Number(pulse.needs_help || 0) },
      { label: "Over Capacity", value: Number(pulse.over_capacity_officers || 0) },
    ];
    commandPulseCards.innerHTML = cards
      .map((item) => `<article class="card"><p>${escapeHtml(item.label)}</p><strong>${item.value}</strong></article>`)
      .join("");
  }
  syncWatchButtons();
}

function renderPnmBoard() {
  if (!pnmBoard) {
    return;
  }
  const rows = state.pnms || [];
  pnmBoard.innerHTML = rows.length
    ? rows
        .map(
          (pnm) => `
            <article class="rushee-board-card">
              <h3>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</h3>
              <div class="rushee-board-meta">Weighted ${Number(pnm.weighted_total || 0).toFixed(2)} | Ratings ${Number(pnm.rating_count || 0)} | Touchpoints ${Number(pnm.total_lunches || 0)}</div>
              <div class="rushee-board-meta">Assigned: ${escapeHtml((pnm.assigned_officer && pnm.assigned_officer.username) || "Unassigned")}</div>
              <div class="action-row">
                <button type="button" class="secondary select-pnm" data-pnm-id="${Number(pnm.pnm_id)}">Inspect</button>
                <button type="button" class="secondary watch-toggle-btn" data-watch-pnm-id="${Number(pnm.pnm_id)}">${isWatchedPnm(pnm.pnm_id) ? "Pinned for Meetings" : "Pin for Meetings"}</button>
                <a class="quick-nav-link" href="${escapeHtml(`${MEETING_BASE}?pnm_id=${Number(pnm.pnm_id)}`)}">Packet</a>
              </div>
            </article>
          `
        )
        .join("")
    : '<p class="muted">No rushees match current filters.</p>';
  const useBoard = state.viewPrefs.pnmView === "board";
  pnmBoard.classList.toggle("hidden", !useBoard);
  if (pnmTable) {
    pnmTable.classList.toggle("hidden", useBoard);
  }
  if (pnmViewToggleBoard) {
    pnmViewToggleBoard.classList.toggle("is-active", useBoard);
  }
  if (pnmViewToggleTable) {
    pnmViewToggleTable.classList.toggle("is-active", !useBoard);
  }
}

function renderTeamWorkspaceExtras(pendingRows = []) {
  if (teamPulseCards) {
    const overview = state.teamWorkspace.assignmentOverview || {};
    const cards = [
      { label: "Members", value: state.members.length },
      { label: "Pending Approvals", value: pendingRows.length },
      { label: "Assignments", value: Number((overview.assignments || []).length || 0) },
      { label: "Escalations", value: Number((overview.escalations || []).length || 0) },
    ];
    teamPulseCards.innerHTML = cards
      .map((item) => `<article class="card"><p>${escapeHtml(item.label)}</p><strong>${item.value}</strong></article>`)
      .join("");
  }
  if (teamOfficerLoads) {
    const loads = (state.teamWorkspace.assignmentOverview && state.teamWorkspace.assignmentOverview.officer_loads) || [];
    teamOfficerLoads.innerHTML = loads.length
      ? loads
          .map(
            (row) => `
              <div class="team-load-card">
                <h3>${escapeHtml(row.username)}</h3>
                <div class="team-load-meta">Active ${Number(row.active_assignments || 0)} / Target ${Number(row.capacity_target || 0)}</div>
                <div class="team-load-meta">Remaining capacity ${Number(row.remaining_capacity || 0)} | Ratio ${Number(row.capacity_ratio || 0).toFixed(2)}</div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No officer load data available.</p>';
  }
}

function setOperationsTab(tab, persist = true) {
  const next = ["timeline", "goals", "comms"].includes(tab) ? tab : "timeline";
  if (persist) {
    setViewPreference("operationsTab", next);
  }
  document.querySelectorAll("[data-operations-tab]").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.operationsTab === next);
  });
  document.querySelectorAll(".operation-tab-btn[data-operations-tab]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.operationsTab === next);
  });
}

function renderOperationsSummary() {
  if (!operationsSummaryCards) {
    return;
  }
  const stats = state.rushCalendarStats || {};
  const notifications = state.operationsWorkspace.notificationsDigest || {};
  const goals = state.weeklyGoalSummary || {};
  const cards = [
    { label: "Timeline Items", value: Number(stats.total_count || 0) },
    { label: "This Week", value: Number(stats.this_week_count || 0) },
    { label: "Active Goals", value: Number(goals.active || 0) },
    { label: "Unread Alerts", value: Number(notifications.unread_count || 0) },
  ];
  operationsSummaryCards.innerHTML = cards
    .map((item) => `<article class="card"><p>${escapeHtml(item.label)}</p><strong>${item.value}</strong></article>`)
    .join("");
}

function setAdminTab(tab, persist = true) {
  const next = ["leadership", "season", "imports", "roster", "storage"].includes(tab) ? tab : "leadership";
  if (persist) {
    setViewPreference("adminTab", next);
  }
  document.querySelectorAll("[data-admin-tab]").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.adminTab === next);
  });
  document.querySelectorAll(".admin-tab-btn[data-admin-tab]").forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.adminTab === next);
  });
}

function renderAdminWorkspaceExtras() {
  if (!adminStorageDiagnostics) {
    return;
  }
  const payload = state.adminOverview.storage;
  if (!payload) {
    adminStorageDiagnostics.innerHTML = '<p class="muted">Storage diagnostics unavailable.</p>';
    return;
  }
  const tableCounts = payload.table_counts || {};
  adminStorageDiagnostics.innerHTML = `
    <div class="entry">
      <div class="entry-title"><strong>Persistent Paths OK</strong><span>${payload.persistent_paths_ok ? "Yes" : "No"}</span></div>
      <div class="muted">Users ${Number(tableCounts.users || 0)} | Rushees ${Number(tableCounts.pnms || 0)} | Ratings ${Number(tableCounts.ratings || 0)} | Touchpoints ${Number(tableCounts.lunches || 0)}</div>
    </div>
    <div class="entry">
      <div class="entry-title"><strong>Active Tenant DB</strong><span>${escapeHtml((payload.paths && payload.paths.ACTIVE_TENANT_DB_PATH) || "-")}</span></div>
      <div class="muted">${escapeHtml((payload.warnings || []).join(" | ") || "No warnings.")}</div>
    </div>
  `;
}

function renderMeetingCompareCard(payload, fallbackLabel) {
  if (!payload || !payload.pnm) {
    return `<article class="compare-candidate-card"><h3>${escapeHtml(fallbackLabel)}</h3><p class="muted">Select a candidate to compare.</p></article>`;
  }
  const pnm = payload.pnm;
  const metrics = payload.metrics || {};
  return `
    <article class="compare-candidate-card">
      <h3>${escapeHtml(pnm.pnm_code)} | ${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</h3>
      <div class="compare-candidate-meta">Weighted ${Number(pnm.weighted_total || 0).toFixed(2)} | Ratings ${Number(pnm.rating_count || 0)} | Touchpoints ${Number(pnm.total_lunches || 0)}</div>
      <div class="compare-candidate-meta">Assigned: ${escapeHtml((pnm.assigned_officer && pnm.assigned_officer.username) || "Unassigned")}</div>
      <div class="compare-candidate-meta">Rank ${metrics.weighted_rank || "-"} of ${metrics.cohort_size || "-"}</div>
      <div class="action-row">
        <a class="quick-nav-link" href="${escapeHtml(`${MEETING_BASE}?pnm_id=${Number(pnm.pnm_id)}`)}">Open Meeting Packet</a>
        <button type="button" class="secondary watch-toggle-btn" data-watch-pnm-id="${Number(pnm.pnm_id)}">${isWatchedPnm(pnm.pnm_id) ? "Pinned for Meetings" : "Pin for Meetings"}</button>
      </div>
    </article>
  `;
}

async function loadMeetingCompareSummary(slot) {
  const key = slot === "B" ? "compareB" : "compareA";
  const targetId = Number(state.meetingsWorkspace[key] || 0);
  if (!targetId) {
    state.meetingsWorkspace[`compareSummary${slot}`] = null;
    renderMeetingsWorkspace();
    return;
  }
  try {
    const payload = await api(`/api/pnms/${targetId}/meeting`);
    state.meetingsWorkspace[`compareSummary${slot}`] = payload;
  } catch {
    state.meetingsWorkspace[`compareSummary${slot}`] = null;
  }
  renderMeetingsWorkspace();
}

function renderMeetingsWorkspace() {
  if (meetingsShortlist) {
    const rows = state.meetingsWorkspace.shortlist || [];
    meetingsShortlist.innerHTML = rows.length
      ? rows
          .map(
            (item) => `
              <div class="meetings-queue-card">
                <h3>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</h3>
                <div class="compare-candidate-meta">Ready ${Number(item.meeting_ready_score || 0)} | Weighted ${Number(item.weighted_total || 0).toFixed(2)} | Ratings ${Number(item.rating_count || 0)}</div>
                <div class="compare-candidate-meta">${escapeHtml(item.flags.join(" • ") || "Meeting-ready context in place")}</div>
                <div class="action-row">
                  <a class="quick-nav-link" href="${escapeHtml(`${MEETING_BASE}?pnm_id=${Number(item.pnm_id)}`)}">Packet</a>
                  <button type="button" class="secondary watch-toggle-btn" data-watch-pnm-id="${Number(item.pnm_id)}">${isWatchedPnm(item.pnm_id) ? "Pinned for Meetings" : "Pin for Meetings"}</button>
                </div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No meeting shortlist yet.</p>';
  }
  if (meetingsAttentionList) {
    const rows = state.meetingsWorkspace.attention || [];
    meetingsAttentionList.innerHTML = rows.length
      ? rows
          .map(
            (item) => `
              <div class="entry">
                <div class="entry-title"><strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name)}</strong><span>${escapeHtml(item.label)}</span></div>
                <div class="muted">${escapeHtml(item.detail || "")}</div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No meeting prep exceptions right now.</p>';
  }
  if (meetingsWatchlist) {
    const rows = currentWatchlistIds()
      .map(
        (pnmId) =>
          (state.meetingsWorkspace.candidates || []).find((item) => Number(item.pnm_id) === pnmId) ||
          (state.pnms || []).find((item) => Number(item.pnm_id) === pnmId) ||
          (state.commandCenter.queue || []).find((item) => Number(item.pnm_id) === pnmId)
      )
      .filter(Boolean);
    meetingsWatchlist.innerHTML = rows.length
      ? rows
          .map(
            (item) => `
        <div class="entry">
                <div class="entry-title"><strong>${escapeHtml(item.pnm_code)} | ${escapeHtml(item.name || `${item.first_name || ""} ${item.last_name || ""}`.trim())}</strong><span>${Number(item.weighted_total || 0).toFixed(2)}</span></div>
                <div class="action-row">
                  <button type="button" class="secondary watch-toggle-btn" data-watch-pnm-id="${Number(item.pnm_id)}">Remove from Meetings</button>
                  <a class="quick-nav-link" href="${escapeHtml(`${MEETING_BASE}?pnm_id=${Number(item.pnm_id)}`)}">Packet</a>
                </div>
              </div>
            `
          )
          .join("")
      : '<p class="muted">No pinned rushees yet.</p>';
  }
  if (meetingsCompareSelectA) {
    const options = '<option value=\"\">Select</option>' + (state.meetingsWorkspace.candidates || [])
      .map((item) => `<option value=\"${Number(item.pnm_id)}\">${escapeHtml(`${item.pnm_code} | ${item.name}`)}</option>`)
      .join("");
    meetingsCompareSelectA.innerHTML = options;
    meetingsCompareSelectA.value = state.meetingsWorkspace.compareA ? String(state.meetingsWorkspace.compareA) : "";
  }
  if (meetingsCompareSelectB) {
    const options = '<option value=\"\">Select</option>' + (state.meetingsWorkspace.candidates || [])
      .map((item) => `<option value=\"${Number(item.pnm_id)}\">${escapeHtml(`${item.pnm_code} | ${item.name}`)}</option>`)
      .join("");
    meetingsCompareSelectB.innerHTML = options;
    meetingsCompareSelectB.value = state.meetingsWorkspace.compareB ? String(state.meetingsWorkspace.compareB) : "";
  }
  if (meetingsCompareSummary) {
    meetingsCompareSummary.innerHTML = [
      renderMeetingCompareCard(state.meetingsWorkspace.compareSummaryA, "Candidate A"),
      renderMeetingCompareCard(state.meetingsWorkspace.compareSummaryB, "Candidate B"),
    ].join("");
  }
  syncWatchButtons();
}

function focusSoon(target) {
  if (!target) {
    return;
  }
  window.setTimeout(() => target.focus(), 40);
}

function openAdminStorageView() {
  setActiveDesktopPage("admin");
  setAdminTab("storage");
}

function localCommandResults(query, existing = []) {
  const token = String(query || "").trim().toLowerCase();
  const base = [];
  if (roleCanApproveUsers()) {
    base.push({ action: "add_rushee", label: "Add Rushee", command_id: "create new PNM record" });
  }
  if (state.user) {
    base.push({ action: "schedule_touchpoint", label: "Schedule Touchpoint", command_id: "open shared touchpoint drawer" });
    base.push({ action: "open_tutorial", label: "Open Tutorial", command_id: "relaunch role walkthrough" });
  }
  if (roleCanUseAdminPanel()) {
    base.push({ action: "create_event", label: "Create Event", command_id: "jump to Operations timeline" });
    base.push({ action: "backup_csv", label: "Backup CSV", command_id: "open admin data tools" });
  }
  if (roleCanUseCommandCenter()) {
    base.push({ action: "open_meetings", label: "Open Meetings Workspace", command_id: "review packet-ready rushees" });
  }
  const seen = new Set((existing || []).map((item) => String(item && item.action ? item.action : "").trim()).filter(Boolean));
  return base.filter((item) => item.label.toLowerCase().includes(token) && !seen.has(item.action));
}

function performCommandAction(action, context = null) {
  const resolvedAction = action === "create_lunch" ? "schedule_touchpoint" : action;
  closeAppMenus();
  if (resolvedAction === "add_rushee") {
    if (!roleCanApproveUsers()) {
      showToast("Only rush officers can add rushees.");
      return;
    }
    setActiveDesktopPage("rushees");
    focusSoon(document.getElementById("pnmFirstName"));
    return;
  }
  if (resolvedAction === "schedule_touchpoint") {
    if (!state.user) {
      return;
    }
    const selectedPnmId = Number(
      (context && context.pnm_id) ||
        state.selectedPnmId ||
        state.commandCenter.selectedQueuePnmId ||
        0
    );
    if (state.activeDesktopPage !== "operations" && !selectedPnmId) {
      setActiveDesktopPage("operations");
      setOperationsTab("timeline");
    }
    openTouchpointDrawer({
      source: state.activeDesktopPage === "operations" ? "operations" : "context",
      pnmId: selectedPnmId || null,
    });
    return;
  }
  if (resolvedAction === "create_event") {
    if (!roleCanUseAdminPanel()) {
      showToast("Only Head Rush Officers can create events from search.");
      return;
    }
    setActiveDesktopPage("operations");
    setOperationsTab("timeline");
    focusSoon(rushEventTitle);
    return;
  }
  if (resolvedAction === "backup_csv") {
    if (!roleCanUseAdminPanel()) {
      showToast("Backup tools are limited to Head Rush Officers.");
      return;
    }
    openAdminStorageView();
    handleCsvBackupDownload(context && context.button ? context.button : null).catch(() => {});
    return;
  }
  if (resolvedAction === "backup_db") {
    openAdminStorageView();
    handleDbBackupDownload(context && context.button ? context.button : null).catch(() => {});
    return;
  }
  if (resolvedAction === "open_tutorial") {
    handleTutorialShortcut();
    return;
  }
  if (resolvedAction === "open_meetings") {
    if (!roleCanUseCommandCenter()) {
      showToast("Meetings workspace is limited to rush officers.");
      return;
    }
    setActiveDesktopPage("meetings");
  }
}

function renderCommandPaletteResults() {
  if (!commandPaletteResults) {
    return;
  }
  const query = String(state.searchResults.query || "").trim();
  if (!query) {
    commandPaletteResults.innerHTML = '<p class="muted">Start typing to search rushees, members, or common actions.</p>';
    return;
  }
  const pnmMarkup = (state.searchResults.pnms || [])
    .map(
      (item) => `
        <button type="button" class="command-palette-result" data-command-open-pnm="${Number(item.pnm_id)}">
          <div class="command-palette-result-main">
            ${
              item.photo_url
                ? `<img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.name || item.pnm_code || "PNM")}" class="command-palette-avatar" loading="lazy" />`
                : '<div class="command-palette-avatar command-palette-avatar-empty">PNM</div>'
            }
            <div class="command-palette-result-copy">
              <strong>${escapeHtml(item.name || "Unknown PNM")}</strong>
              <div class="muted">${escapeHtml(item.pnm_code || "")}${item.hometown ? ` | ${escapeHtml(item.hometown)}` : ""}</div>
              <div class="muted">Weighted ${Number(item.weighted_total || 0).toFixed(2)}</div>
            </div>
          </div>
        </button>
      `
    )
    .join("");
  const memberMarkup = (state.searchResults.members || [])
    .map(
      (item) => `
        <button type="button" class="command-palette-result" data-command-open-member="${Number(item.user_id)}">
          <strong>${escapeHtml(item.username)}</strong>
          <div class="muted">${escapeHtml(item.role || "")}</div>
        </button>
      `
    )
    .join("");
  const commandMarkup = (state.searchResults.commands || [])
    .map(
      (item) => `
        <button type="button" class="command-palette-result" data-command-run="${escapeHtml(item.action)}">
          <strong>${escapeHtml(item.label)}</strong>
          <div class="muted">${escapeHtml(item.command_id || "")}</div>
        </button>
      `
    )
    .join("");
  commandPaletteResults.innerHTML = `
    <div class="command-palette-result-group">
      <h3>Rushees</h3>
      ${pnmMarkup || '<p class="muted">No rushee matches.</p>'}
    </div>
    <div class="command-palette-result-group">
      <h3>Members</h3>
      ${memberMarkup || '<p class="muted">No member matches.</p>'}
    </div>
    <div class="command-palette-result-group">
      <h3>Commands</h3>
      ${commandMarkup || '<p class="muted">No command matches.</p>'}
    </div>
  `;
}

async function loadGlobalSearch(query) {
  const token = String(query || "").trim();
  state.searchResults.query = token;
  if (!token) {
    state.searchResults.pnms = [];
    state.searchResults.members = [];
    state.searchResults.commands = [];
    renderCommandPaletteResults();
    return;
  }
  try {
    const payload = await api(`/api/search/global${toQuery({ q: token })}`);
    state.searchResults = {
      query: token,
      pnms: payload.pnms || [],
      members: payload.members || [],
      commands: [...(payload.commands || []), ...localCommandResults(token, payload.commands || [])],
    };
  } catch {
    state.searchResults = {
      query: token,
      pnms: [],
      members: [],
      commands: localCommandResults(token, []),
    };
  }
  renderCommandPaletteResults();
}

function openCommandPalette(seed = "") {
  if (!globalCommandPalette) {
    return;
  }
  globalCommandPalette.classList.remove("hidden");
  globalCommandPalette.setAttribute("aria-hidden", "false");
  if (commandPaletteInput) {
    commandPaletteInput.value = seed;
    commandPaletteInput.focus();
  }
  loadGlobalSearch(seed);
}

function closeCommandPalette() {
  if (!globalCommandPalette) {
    return;
  }
  globalCommandPalette.classList.add("hidden");
  globalCommandPalette.setAttribute("aria-hidden", "true");
}

function renderPendingApprovals(data) {
  if (!roleCanApproveUsers()) {
    approvalsPanel.classList.add("hidden");
    return;
  }

  approvalsPanel.classList.remove("hidden");

  if (!data.pending.length) {
    pendingList.innerHTML = '<p class="muted">No pending requests.</p>';
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

function formatLastSeen(value) {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Unknown";
  }
  return parsed.toLocaleString();
}

function renderHeadAdminSummary() {
  if (!headAdminSummary) {
    return;
  }
  const summary = state.headAdmin.summary;
  if (!summary) {
    headAdminSummary.innerHTML = '<p class="muted">Head admin metrics unavailable.</p>';
    return;
  }
  headAdminSummary.innerHTML = `
    <div class="card">
      <strong>${summary.head_count}</strong>
      <p>Current Head Rush Officers</p>
    </div>
    <div class="card">
      <strong>${summary.officer_count}</strong>
      <p>Active Rush Officers</p>
    </div>
    <div class="card">
      <strong>${summary.total_officer_ratings}</strong>
      <p>Total Officer Ratings</p>
    </div>
    <div class="card">
      <strong>${summary.total_officer_lunches}</strong>
      <p>Total Officer Touchpoints</p>
    </div>
    <div class="card">
      <strong>${Number(summary.avg_officer_score_given || 0).toFixed(2)}</strong>
      <p>Avg Officer Score Given</p>
    </div>
  `;
}

function renderCurrentHeadsList() {
  if (!currentHeadsList) {
    return;
  }
  const heads = state.headAdmin.currentHeads || [];
  if (!heads.length) {
    currentHeadsList.innerHTML = '<p class="muted">No head officers found.</p>';
    return;
  }
  currentHeadsList.innerHTML = heads
    .map(
      (head) => `
        <div class="entry">
          <div class="entry-title">
            <strong>${escapeHtml(head.username)}</strong>
            <span>${head.rating_count} ratings</span>
          </div>
          <div class="muted">Touchpoints: ${head.total_lunches} | Per week: ${Number(head.lunches_per_week || 0).toFixed(2)}</div>
          <div class="muted">Last login: ${escapeHtml(formatLastSeen(head.last_login_at))}</div>
        </div>
      `
    )
    .join("");
}

function renderPromotionControls() {
  if (!promoteOfficerSelect || !promoteOfficerBtn) {
    return;
  }
  const officers = state.headAdmin.rushOfficers || [];
  if (!officers.length) {
    promoteOfficerSelect.innerHTML = '<option value="">No rush officers available</option>';
    promoteOfficerSelect.disabled = true;
    promoteOfficerBtn.disabled = true;
    return;
  }
  const options = officers
    .map((officer) => {
      const emoji = officer.emoji ? `${officer.emoji} ` : "";
      return `<option value="${officer.user_id}">${escapeHtml(`${emoji}${officer.username}`)}</option>`;
    })
    .join("");
  promoteOfficerSelect.innerHTML = `<option value="">Select an officer</option>${options}`;
  promoteOfficerSelect.disabled = false;
  promoteOfficerBtn.disabled = false;
}

function renderOfficerMetrics() {
  if (!officerMetricsTable) {
    return;
  }
  const officers = state.headAdmin.rushOfficers || [];
  if (!officers.length) {
    officerMetricsTable.innerHTML = '<p class="muted">No Rush Officer metrics yet.</p>';
    return;
  }
  const rows = officers
    .map(
      (officer) => `
      <tr>
        <td><strong>${escapeHtml(officer.username)}</strong></td>
        <td>${escapeHtml(officer.emoji || "-")}</td>
        <td>${officer.rating_count}</td>
        <td>${Number(officer.avg_rating_given || 0).toFixed(2)}</td>
        <td>${Number(officer.avg_rating_total || 0).toFixed(2)}</td>
        <td>${officer.total_lunches}</td>
        <td>${Number(officer.lunches_per_week || 0).toFixed(2)}</td>
        <td>${officer.assigned_pnms_count}</td>
        <td>${Number(officer.participation_score || 0).toFixed(2)}</td>
        <td>${escapeHtml(formatLastSeen(officer.last_login_at))}</td>
      </tr>
    `
    )
    .join("");
  officerMetricsTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Officer</th>
          <th>Emoji</th>
          <th>Ratings</th>
          <th>Avg Given</th>
          <th>Avg Score</th>
          <th>Touchpoints</th>
          <th>Touchpoints/Week</th>
          <th>Assigned Rushees</th>
          <th>Participation</th>
          <th>Last Login</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderSeasonArchiveStatusPanel() {
  if (!seasonArchiveSummary || !seasonArchivePhrase || !seasonArchiveDownloadBtn) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    seasonArchiveSummary.innerHTML = '<p class="muted">Head Rush Officer access required.</p>';
    seasonArchiveDownloadBtn.classList.add("hidden");
    return;
  }
  const payload = state.seasonArchive;
  if (!payload) {
    seasonArchiveSummary.innerHTML = '<p class="muted">Loading season archive status...</p>';
    seasonArchiveDownloadBtn.classList.add("hidden");
    return;
  }

  const phrase = payload.confirmation_phrase || "RESET RUSH SEASON";
  seasonArchivePhrase.placeholder = `Type: ${phrase}`;

  const current = payload.current_counts || { pnm_count: 0, rating_count: 0, lunch_count: 0 };
  const archive = payload.archive || null;
  const archiveMeta = archive
    ? `
      <div class="entry">
        <div class="entry-title">
          <strong>Last Archive</strong>
          <span>${escapeHtml(archive.archive_label || "Season Archive")}</span>
        </div>
        <p class="muted">Created: ${escapeHtml(formatLastSeen(archive.archived_at))} by ${escapeHtml(archive.archived_by_username || "Unknown")}</p>
        <p class="muted">Archived counts: Rushees ${archive.pnm_count}, Ratings ${archive.rating_count}, Touchpoints ${archive.lunch_count}</p>
      </div>
    `
    : '<p class="muted">No archived season yet.</p>';

  seasonArchiveSummary.innerHTML = `
    <div class="entry">
      <div class="entry-title">
        <strong>Current Live Data</strong>
        <span>Before Reset</span>
      </div>
      <p class="muted">Rushees: ${current.pnm_count} | Ratings: ${current.rating_count} | Touchpoints: ${current.lunch_count}</p>
      <p class="muted">Confirmation phrase: <strong>${escapeHtml(phrase)}</strong></p>
    </div>
    ${archiveMeta}
  `;

  seasonArchiveDownloadBtn.classList.toggle("hidden", !payload.archive_download_path);
}

function renderAdminPnmEditorOptions() {
  if (!adminEditPnmSelect || !adminPnmEditorForm) {
    return;
  }
  if (!state.pnms.length) {
    adminEditPnmSelect.innerHTML = '<option value="">No rushees available</option>';
    adminPnmEditorForm.classList.add("hidden");
    state.adminEditPnmId = null;
    return;
  }

  const options = state.pnms
    .map((pnm) => `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}`)}</option>`)
    .join("");
  adminEditPnmSelect.innerHTML = options;
  adminPnmEditorForm.classList.remove("hidden");

  if (!state.adminEditPnmId || !state.pnms.some((pnm) => pnm.pnm_id === Number(state.adminEditPnmId))) {
    state.adminEditPnmId = state.selectedPnmId || state.pnms[0].pnm_id;
  }
  adminEditPnmSelect.value = String(state.adminEditPnmId);
  populateAdminPnmEditor(state.adminEditPnmId);
}

function populateAdminPnmEditor(pnmId) {
  const pnm = state.pnms.find((item) => item.pnm_id === Number(pnmId));
  if (!pnm) {
    return;
  }
  state.adminEditPnmId = pnm.pnm_id;
  document.getElementById("adminEditFirstName").value = pnm.first_name || "";
  document.getElementById("adminEditLastName").value = pnm.last_name || "";
  document.getElementById("adminEditClassYear").value = pnm.class_year || "F";
  document.getElementById("adminEditFirstEventDate").value = pnm.first_event_date || "";
  document.getElementById("adminEditHometown").value = pnm.hometown || "";
  document.getElementById("adminEditState").value = pnm.hometown_state_code || "";
  document.getElementById("adminEditPhoneNumber").value = pnm.phone_number || "";
  document.getElementById("adminEditInstagramHandle").value = pnm.instagram_handle || "";
  document.getElementById("adminEditInterests").value = (pnm.interests || []).join(",");
  document.getElementById("adminEditStereotype").value = pnm.stereotype || "";
  document.getElementById("adminEditLunchStats").value = pnm.lunch_stats || "";
  document.getElementById("adminEditNotes").value = pnm.notes || "";
  syncInterestPickerFromInput("adminEditInterests", "adminEditInterestTags");
  syncStereotypePickerFromInput("adminEditStereotype", "adminEditStereotypeTags");
}

function renderAdminPnmTable() {
  if (!adminPnmTable) {
    return;
  }
  if (!state.pnms.length) {
    adminPnmTable.innerHTML = '<p class="muted">No rushees to manage.</p>';
    return;
  }

  const rows = state.pnms
    .map(
      (pnm) => {
        const linkedDisplay = linkedRusheeNamesForPnm(pnm);
        return `
      <tr>
        <td>${smallPhotoCell(pnm)}</td>
        <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
        <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
        <td>${escapeHtml(linkedDisplay)}</td>
        <td>${escapeHtml(pnm.phone_number || "-")}</td>
        <td>${escapeHtml(pnm.instagram_handle)}</td>
        <td>${pnm.weighted_total.toFixed(2)}</td>
        <td>${pnm.rating_count}</td>
        <td>${pnm.total_lunches}</td>
        <td>
          <div class="action-row">
            <button type="button" class="secondary edit-pnm" data-pnm-id="${pnm.pnm_id}">Edit</button>
            <button type="button" class="delete-pnm" data-pnm-id="${pnm.pnm_id}">Remove</button>
          </div>
        </td>
      </tr>
    `;
      }
    )
    .join("");

  adminPnmTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Photo</th>
          <th>Code</th>
          <th>Name</th>
          <th>Linked With</th>
          <th>Phone</th>
          <th>Instagram</th>
          <th>Weighted Total</th>
          <th>Ratings</th>
          <th>Touchpoints</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function syncHeadAssignmentSelection() {
  if (!headAssignPnmSelect || !headAssignOfficerSelect) {
    return;
  }
  const pnmId = Number(headAssignPnmSelect.value || 0);
  if (!pnmId) {
    headAssignOfficerSelect.value = "";
    renderHeadAssigneeControls();
    return;
  }
  const pnm = state.pnms.find((item) => item.pnm_id === pnmId);
  if (!pnm || !pnm.assigned_officer_id) {
    headAssignOfficerSelect.value = "";
    renderHeadAssigneeControls();
    return;
  }
  headAssignOfficerSelect.value = String(pnm.assigned_officer_id);
  renderHeadAssigneeControls();
}

function renderHeadAssigneeControls() {
  if (!headAddAssigneeSelect || !headAssigneeList || !headAssignPnmSelect) {
    return;
  }
  const selectedPnmId = Number(headAssignPnmSelect.value || 0);
  const selected = state.pnms.find((pnm) => pnm.pnm_id === selectedPnmId) || null;
  if (!selected) {
    headAddAssigneeSelect.innerHTML = '<option value="">Select a rushee first</option>';
    headAssigneeList.innerHTML = '<p class="muted">Select a rushee to manage assignment team members.</p>';
    if (headAddAssigneeBtn) {
      headAddAssigneeBtn.disabled = true;
    }
    return;
  }

  const assignedTeam = assignmentTeamForPnm(selected);
  const assignedIds = new Set(assignedTeam.map((item) => Number(item.user_id)));
  const availableOfficers = rushOfficerMembers()
    .filter((member) => !assignedIds.has(Number(member.user_id)))
    .sort((a, b) => String(a.username || "").localeCompare(String(b.username || "")));

  const options = ['<option value="">Select Rush Officer</option>']
    .concat(
      availableOfficers.map((member) => {
        const emoji = member.emoji ? `${member.emoji} ` : "";
        return `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username}`)}</option>`;
      })
    )
    .join("");
  headAddAssigneeSelect.innerHTML = options;

  if (!assignedTeam.length) {
    headAssigneeList.innerHTML = '<p class="muted">No assignment team members yet.</p>';
  } else {
    headAssigneeList.innerHTML = assignedTeam
      .map((officer) => {
        const badge = officer.is_primary ? '<span class="pill">Primary</span>' : "";
        const removeButton =
          '<button type="button" class="secondary head-remove-assignee" data-user-id="' + officer.user_id + '">Remove</button>';
        const emoji = officer.emoji ? `${officer.emoji} ` : "";
        return `
          <div class="entry">
            <div class="entry-title">
              <strong>${escapeHtml(`${emoji}${officer.username}`)}</strong>
              ${badge}
            </div>
            <div class="action-row">${removeButton}</div>
          </div>
        `;
      })
      .join("");
  }

  if (headAddAssigneeBtn) {
    headAddAssigneeBtn.disabled = availableOfficers.length === 0;
  }
}

function renderPackageDealPanel() {
  if (!packageDealPanel || !packagePartnerSelect || !packageDealSummary) {
    return;
  }
  const canManage = roleCanManagePackages();
  packageDealPanel.classList.toggle("hidden", !canManage);
  if (!canManage) {
    packagePartnerSelect.innerHTML = "";
    packageDealSummary.textContent = "";
    return;
  }

  const selected = state.pnms.find((pnm) => pnm.pnm_id === Number(state.selectedPnmId)) || null;
  if (!selected) {
    packagePartnerSelect.innerHTML = '<option value="">Select a rushee first</option>';
    packageDealSummary.textContent = "No package deal linked for this rushee yet.";
    if (packageLinkBtn) {
      packageLinkBtn.disabled = true;
    }
    if (packageUnlinkBtn) {
      packageUnlinkBtn.disabled = true;
    }
    state.packagePartnerId = null;
    return;
  }

  const optionRows = ['<option value="">Select partner rushee</option>'];
  state.pnms
    .filter((pnm) => pnm.pnm_id !== selected.pnm_id)
    .sort((a, b) => `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`))
    .forEach((pnm) => {
      const info = packageInfoForPnm(pnm);
      const marker = info.id ? ` (${info.label})` : "";
      optionRows.push(
        `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}${marker}`)}</option>`
      );
    });
  packagePartnerSelect.innerHTML = optionRows.join("");

  const selectedPartnerExists = state.pnms.some((pnm) => pnm.pnm_id === Number(state.packagePartnerId));
  if (selectedPartnerExists) {
    packagePartnerSelect.value = String(state.packagePartnerId);
  } else {
    state.packagePartnerId = null;
  }

  const selectedInfo = packageInfoForPnm(selected);
  if (!selectedInfo.id) {
    packageDealSummary.textContent = "No package deal linked for this rushee yet.";
  } else {
    const members = selectedInfo.members.map((pnm) => `${pnm.first_name} ${pnm.last_name}`).join(", ");
    packageDealSummary.textContent = `${selectedInfo.label} includes ${selectedInfo.count} rushees: ${members}.`;
  }

  if (packageLinkBtn) {
    packageLinkBtn.disabled = !state.pnms.some((pnm) => pnm.pnm_id !== selected.pnm_id);
  }
  if (packageUnlinkBtn) {
    packageUnlinkBtn.disabled = !selectedInfo.id;
  }
}

function renderHeadAssignmentTable() {
  if (!headAssignmentTable) {
    return;
  }
  if (!state.pnms.length) {
    headAssignmentTable.innerHTML = '<p class="muted">No rushees available for assignment.</p>';
    return;
  }

  const groups = packageGroupIndex();
  const rows = [...state.pnms]
    .sort((a, b) => {
      const aOfficer = (a.assigned_officer && a.assigned_officer.username) || "zzzz";
      const bOfficer = (b.assigned_officer && b.assigned_officer.username) || "zzzz";
      if (aOfficer !== bOfficer) {
        return aOfficer.localeCompare(bOfficer);
      }
      const aPackage = normalizePackageGroupId(a.package_group_id) || `solo-${a.pnm_id}`;
      const bPackage = normalizePackageGroupId(b.package_group_id) || `solo-${b.pnm_id}`;
      if (aPackage !== bPackage) {
        return aPackage.localeCompare(bPackage);
      }
      return `${a.last_name} ${a.first_name}`.localeCompare(`${b.last_name} ${b.first_name}`);
    })
    .map((pnm) => {
      const assignmentTeam = assignmentTeamForPnm(pnm);
      const assignedOfficer = primaryAssignmentLabel(pnm, assignmentTeam);
      const assignmentTeamText = assignmentTeamLabel(assignmentTeam);
      const assignedAt = pnm.assigned_at ? formatLastSeen(pnm.assigned_at) : "-";
      const packageInfo = packageInfoForPnm(pnm, groups);
      const packageMembers = packageInfo.members
        .map((member) => `${member.first_name} ${member.last_name}`)
        .join(", ");
      const packageText = packageInfo.id
        ? `${packageInfo.label} (${packageInfo.count})`
        : "Solo";
      return `
        <tr>
          <td><strong>${escapeHtml(pnm.pnm_code)}</strong></td>
          <td>${escapeHtml(pnm.first_name)} ${escapeHtml(pnm.last_name)}</td>
          <td>
            <strong>${escapeHtml(packageText)}</strong>
            ${packageInfo.id ? `<div class="muted">${escapeHtml(packageMembers)}</div>` : ""}
          </td>
          <td>${escapeHtml(assignmentTeamText)}</td>
          <td>${escapeHtml(assignedOfficer)}</td>
          <td>${escapeHtml(assignedAt)}</td>
          <td>${pnm.weighted_total.toFixed(2)}</td>
        </tr>
      `;
    })
    .join("");

  headAssignmentTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Code</th>
          <th>Rushee</th>
          <th>Package Deal</th>
          <th>Assignment Team</th>
          <th>Assigned Officer</th>
          <th>Assigned At</th>
          <th>Weighted Total</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderHeadAssignmentManager() {
  if (!headAssignmentForm || !headAssignPnmSelect || !headAssignOfficerSelect || !headAssignmentTable) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    headAssignmentForm.classList.add("hidden");
    headAssignmentTable.innerHTML = "";
    if (headAddAssigneeSelect) {
      headAddAssigneeSelect.innerHTML = "";
    }
    if (headAssigneeList) {
      headAssigneeList.innerHTML = "";
    }
    return;
  }

  headAssignmentForm.classList.remove("hidden");
  const pnmOptions = state.pnms
    .map((pnm) => {
      const packageInfo = packageInfoForPnm(pnm);
      const marker = packageInfo.id ? ` (${packageInfo.label})` : "";
      return `<option value="${pnm.pnm_id}">${escapeHtml(`${pnm.pnm_code} | ${pnm.first_name} ${pnm.last_name}${marker}`)}</option>`;
    })
    .join("");
  headAssignPnmSelect.innerHTML = pnmOptions || '<option value="">No rushees available</option>';

  const officers = rushOfficerMembers();
  const officerOptions =
    '<option value="">Unassigned</option>' +
    officers
      .map((member) => {
        const emoji = member.emoji ? `${member.emoji} ` : "";
        return `<option value="${member.user_id}">${escapeHtml(`${emoji}${member.username}`)}</option>`;
      })
      .join("");
  headAssignOfficerSelect.innerHTML = officerOptions;

  const hasActiveSelection = state.pnms.some((pnm) => pnm.pnm_id === Number(state.headAssignmentPnmId));
  if (!hasActiveSelection) {
    state.headAssignmentPnmId = state.selectedPnmId || (state.pnms.length ? state.pnms[0].pnm_id : null);
  }
  if (state.headAssignmentPnmId) {
    headAssignPnmSelect.value = String(state.headAssignmentPnmId);
  }
  syncHeadAssignmentSelection();
  renderHeadAssignmentTable();
  renderHeadAssigneeControls();
}

function renderAdminPanel() {
  if (!roleCanUseAdminPanel()) {
    adminPanel.classList.add("hidden");
    if (adminPnmTable) {
      adminPnmTable.innerHTML = "";
    }
    if (officerMetricsTable) {
      officerMetricsTable.innerHTML = "";
    }
    if (headAssignmentTable) {
      headAssignmentTable.innerHTML = "";
    }
    renderSeasonArchiveStatusPanel();
    return;
  }

  adminPanel.classList.remove("hidden");
  renderHeadAdminSummary();
  renderCurrentHeadsList();
  renderPromotionControls();
  renderSeasonArchiveStatusPanel();
  renderHeadAssignmentManager();
  renderOfficerMetrics();
  renderAdminPnmEditorOptions();
  renderAdminPnmTable();
  renderAdminWorkspaceExtras();
}

function applyRatingFormForSelected() {
  syncOpenMeetingLink();
  if (!state.selectedPnmId) {
    ratingForm.reset();
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    renderAssignmentControls();
    renderPackageDealPanel();
    return;
  }

  const selected = state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId);
  if (!selected) {
    renderSelectedPnmPhoto(null);
    photoForm.classList.toggle("hidden", !roleCanManagePhotos());
    renderAssignmentControls();
    renderPackageDealPanel();
    return;
  }

  const assignmentTeam = assignmentTeamForPnm(selected);
  const assigned = primaryAssignmentLabel(selected, assignmentTeam);
  const assignmentTeamText = assignmentTeamLabel(assignmentTeam);
  const packageInfo = packageInfoForPnm(selected);
  const packageText = packageInfo.id ? `${packageInfo.label} (${packageInfo.count})` : "Solo";
  const phone = selected.phone_number || "No phone";
  selectedPnmLabel.textContent = `${selected.pnm_code} | ${selected.first_name} ${selected.last_name} | ${phone} | Primary: ${assigned} | Team: ${assignmentTeamText} | Package: ${packageText}`;
  ratingPnm.value = String(selected.pnm_id);
  if (touchpointDrawerPnm) {
    touchpointDrawerPnm.value = String(selected.pnm_id);
  }

  const own = selected.own_rating;
  const girlsMax = ratingCriteriaForField("good_with_girls")?.max || 10;
  const processMax = ratingCriteriaForField("will_make_it")?.max || 10;
  const personableMax = ratingCriteriaForField("personable")?.max || 10;
  const alcoholMax = ratingCriteriaForField("alcohol_control")?.max || 10;
  const igMax = ratingCriteriaForField("instagram_marketability")?.max || 5;
  document.getElementById("rateGirls").value = own ? Math.min(Number(own.good_with_girls || 0), girlsMax) : 0;
  document.getElementById("rateProcess").value = own ? Math.min(Number(own.will_make_it || 0), processMax) : 0;
  document.getElementById("ratePersonable").value = own ? Math.min(Number(own.personable || 0), personableMax) : 0;
  document.getElementById("rateAlcohol").value = own ? Math.min(Number(own.alcohol_control || 0), alcoholMax) : 0;
  document.getElementById("rateIg").value = own ? Math.min(Number(own.instagram_marketability || 0), igMax) : 0;
  document.getElementById("rateComment").value = own ? own.comment || "" : "";
  renderSelectedPnmPhoto(selected);
  photoForm.classList.toggle("hidden", !roleCanManagePhotos());
  renderAssignmentControls();
  renderPackageDealPanel();
  syncWatchButtons();
  syncOpenMeetingLink();
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
            <span>Score ${row.total_score}/${RATING_TOTAL_MAX} ${deltaMarkup}</span>
          </div>
          <div class="muted">${escapeHtml(formatScoreBreakdown(row))}</div>
          ${comment}
          ${changeComment}
        </div>
      `;
    })
    .join("");
}

function renderLunchEntries(data) {
  if (!data.lunches.length) {
    lunchHistory.innerHTML = '<p class="muted">No touchpoints logged for this rushee.</p>';
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
        <div class="muted">${escapeHtml(formatLunchWindow(row) || "All-day touchpoint")}</div>
        <div class="muted">${escapeHtml(row.notes || "No notes")}</div>
      </div>
    `
    )
    .join("");
}

async function loadPnmDetail(pnmId) {
  if (!pnmId) {
    ratingList.innerHTML = '<p class="muted">Select a rushee to view rating entries.</p>';
    lunchHistory.innerHTML = '<p class="muted">Select a rushee to view touchpoint logs.</p>';
    renderSelectedPnmPhoto(null);
    syncOpenMeetingLink();
    renderAssignmentControls();
    return;
  }

  try {
    const [ratings, lunches] = await Promise.all([
      api(`/api/pnms/${pnmId}/ratings`),
      api(`/api/pnms/${pnmId}/lunches`),
    ]);
    renderRatingEntries(ratings);
    renderLunchEntries(lunches);
    renderAssignmentControls();
    syncOpenMeetingLink();
  } catch (error) {
    showToast(error.message || "Unable to load selected PNM details.");
  }
}

async function loadInterestHints() {
  try {
    const payload = await api("/api/interests");
    renderInterestHints(payload.interests || DEFAULT_INTEREST_TAGS);
  } catch {
    renderInterestHints(DEFAULT_INTEREST_TAGS);
  }
}

async function loadPnms(options = {}) {
  const includeDetail =
    options.includeDetail !== undefined
      ? Boolean(options.includeDetail)
      : state.activeDesktopPage === "rushees" || state.activeDesktopPage === "admin";
  const query = toQuery(state.rusheeFilters);
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
  renderPnmBoard();
  renderAdminPanel();
  renderAssignedRushSection();
  applyRatingFormForSelected();
  renderAssignmentControls();
  renderPackageDealPanel();
  renderSameStatePnmsPanel();
  if (includeDetail) {
    await loadPnmDetail(state.selectedPnmId);
  }
}

async function loadMembers(options = {}) {
  const includeSameState =
    options.includeSameState !== undefined ? Boolean(options.includeSameState) : state.activeDesktopPage === "members";
  const query = toQuery(state.memberFilters);
  const payload = await api(`/api/users${query}`);
  state.members = payload.users || [];
  if (!state.members.some((member) => Number(member.user_id) === Number(state.selectedMemberId))) {
    state.selectedMemberId = state.members.length ? Number(state.members[0].user_id) : null;
  }
  renderMemberTable();
  if (includeSameState) {
    await loadSameStatePnms();
  } else {
    renderSameStatePnmsPanel();
  }
  renderWeeklyGoalAssignedUsers();
  renderAssignmentControls();
  renderAdminPanel();
  renderAssignedRushSection();
  renderTeamWorkspaceExtras();
}

async function loadCommandCenter(options = {}) {
  const surfaceErrors = Boolean(options.surfaceErrors);
  if (!roleCanUseCommandCenter()) {
    state.commandCenter.queue = [];
    state.commandCenter.staleAlerts = [];
    state.commandCenter.recentChanges = [];
    state.commandCenter.summary = null;
    state.commandCenter.selectedQueuePnmId = null;
    state.commandCenter.error = "";
    renderCommandCenter();
    return;
  }
  const query = toQuery({
    window_hours: state.commandCenter.windowHours || 72,
    limit: state.commandCenter.limit || 30,
  });
  try {
    const payload = await api(`/api/dashboard/command-center${query}`);
    state.commandCenter.queue = Array.isArray(payload.queue) ? payload.queue : [];
    state.commandCenter.staleAlerts = Array.isArray(payload.stale_alerts) ? payload.stale_alerts : [];
    state.commandCenter.recentChanges = Array.isArray(payload.recent_rating_changes) ? payload.recent_rating_changes : [];
    state.commandCenter.summary = payload.summary || null;
    state.commandCenter.error = "";
  } catch (error) {
    state.commandCenter.queue = [];
    state.commandCenter.staleAlerts = [];
    state.commandCenter.recentChanges = [];
    state.commandCenter.summary = {
      window_hours: state.commandCenter.windowHours || 72,
      queue_count: 0,
      stale_count: 0,
      recent_change_count: 0,
    };
    state.commandCenter.selectedQueuePnmId = null;
    state.commandCenter.error = error.message || "Unable to load command center right now.";
    if (surfaceErrors) {
      throw error;
    }
  }

  if (!state.commandCenter.selectedQueuePnmId) {
    state.commandCenter.selectedQueuePnmId = state.commandCenter.queue.length
      ? Number(state.commandCenter.queue[0].pnm_id)
      : null;
  }
  renderCommandCenter();
}

async function loadMatching() {
  const query = toQuery(state.matchingFilters);
  const payload = await api(`/api/matching${query}`);
  renderMatching(payload);
}

async function loadAnalytics() {
  const payload = await api("/api/analytics/overview");
  renderAnalytics(payload);
}

async function loadLeaderboard() {
  const payload = await api("/api/leaderboard/pnms?limit=250");
  renderLeaderboard(payload.leaderboard || []);
}

async function loadCalendarShare() {
  try {
    const payload = await api("/api/calendar/share");
    renderCalendarShareLinks(payload);
  } catch {
    if (calendarFeedPreview) {
      calendarFeedPreview.textContent = "Unable to load shared calendar link right now.";
    }
    if (openGoogleSubscribeBtn) {
      openGoogleSubscribeBtn.href = "#";
      openGoogleSubscribeBtn.classList.add("hidden");
    }
    if (rushCalendarFeedPreview) {
      rushCalendarFeedPreview.textContent = "Unable to load rush calendar link right now.";
    }
    if (lunchOnlyFeedPreview) {
      lunchOnlyFeedPreview.textContent = "Unable to load lunch feed link right now.";
    }
    if (openRushGoogleSubscribeBtn) {
      openRushGoogleSubscribeBtn.href = "#";
      openRushGoogleSubscribeBtn.classList.add("hidden");
    }
  }
}

async function loadScheduledLunches() {
  try {
    const payload = await api("/api/lunches/scheduled?limit=200");
    state.scheduledLunches = payload.lunches || [];
    renderScheduledLunches();
  } catch {
    state.scheduledLunches = [];
    if (scheduledLunchesList) {
      scheduledLunchesList.innerHTML = '<p class="muted">Unable to load scheduled touchpoints right now.</p>';
    }
  }
}

async function loadRushCalendar() {
  try {
    const payload = await api("/api/rush-calendar?limit=600");
    state.rushCalendarItems = payload.items || [];
    state.rushCalendarStats = payload.stats || null;
    renderRushCalendar();
  } catch {
    state.rushCalendarItems = [];
    state.rushCalendarStats = null;
    if (rushCalendarTable) {
      rushCalendarTable.innerHTML = '<p class="muted">Unable to load rush calendar right now.</p>';
    }
    if (rushCalendarStats) {
      rushCalendarStats.innerHTML = '<p class="muted">Rush calendar metrics unavailable.</p>';
    }
  }
}

async function loadWeeklyGoals() {
  try {
    const payload = await api("/api/tasks/weekly");
    state.weeklyGoals = payload.goals || [];
    state.weeklyGoalSummary = payload.summary || null;
    state.weeklyGoalMetricOptions = payload.metric_options || [];
    renderWeeklyGoalMetricOptions();
    renderWeeklyGoals();
  } catch {
    state.weeklyGoals = [];
    state.weeklyGoalSummary = null;
    state.weeklyGoalMetricOptions = [];
    if (weeklyGoalsList) {
      weeklyGoalsList.innerHTML = '<p class="muted">Unable to load weekly goals right now.</p>';
    }
  }
}

async function loadNotifications() {
  try {
    const payload = await api("/api/notifications?limit=120");
    state.notifications = payload.notifications || [];
    state.unreadNotifications = Number(payload.unread_count || 0);
    renderNotifications();
  } catch {
    state.notifications = [];
    state.unreadNotifications = 0;
    if (appNotificationsList) {
      appNotificationsList.innerHTML = '<p class="muted">Unable to load notifications right now.</p>';
    }
    if (appNotificationsReadAllBtn) {
      appNotificationsReadAllBtn.disabled = true;
      appNotificationsReadAllBtn.textContent = "Mark All Read";
    }
    renderOperationsUnreadBadge();
    renderGlobalNotificationsTray();
    updateNotificationBell();
  }
}

async function loadOfficerChat() {
  if (!roleCanManageOperations()) {
    state.officerChatMessages = [];
    renderOfficerChat();
    return;
  }
  try {
    const payload = await api("/api/chat/officer?limit=220");
    state.officerChatMessages = payload.messages || [];
    renderOfficerChat();
  } catch {
    state.officerChatMessages = [];
    if (officerChatList) {
      officerChatList.innerHTML = '<p class="muted">Unable to load officer chat right now.</p>';
    }
  }
}

async function loadOfficerChatStats() {
  if (!roleCanManageOperations()) {
    state.officerChatStats = null;
    renderOfficerChatStats();
    return;
  }
  try {
    const payload = await api("/api/chat/officer/stats");
    state.officerChatStats = payload;
    renderOfficerChatStats();
  } catch {
    state.officerChatStats = null;
    if (officerChatStats) {
      officerChatStats.innerHTML = '<p class="muted">Unable to load chat stats right now.</p>';
    }
  }
}

async function loadApprovals() {
  if (!roleCanApproveUsers()) {
    approvalsPanel.classList.add("hidden");
    return;
  }

  const payload = await api("/api/users/pending");
  renderPendingApprovals(payload);
}

async function loadHeadAdminData() {
  if (!state.user || state.user.role !== "Head Rush Officer") {
    state.headAdmin = {
      summary: null,
      currentHeads: [],
      rushOfficers: [],
    };
    renderAdminPanel();
    return;
  }

  const payload = await api("/api/admin/rush-officers");
  state.headAdmin = {
    summary: payload.summary || null,
    currentHeads: payload.current_heads || [],
    rushOfficers: payload.rush_officers || [],
  };
  renderAdminPanel();
}

async function loadAssignedRushData() {
  if (!roleCanViewAssignedRushes()) {
    state.assignedRushRows = [];
    renderAssignedRushSection();
    return;
  }
  try {
    const payload = await api("/api/assignments/mine");
    state.assignedRushRows = payload.assignments || [];
  } catch {
    state.assignedRushRows = [];
  }
  renderAssignedRushSection();
}

async function loadSeasonArchiveStatus() {
  if (!roleCanUseAdminPanel()) {
    state.seasonArchive = null;
    renderSeasonArchiveStatusPanel();
    return;
  }
  try {
    const payload = await api("/api/admin/season/archive");
    state.seasonArchive = payload;
  } catch (error) {
    state.seasonArchive = {
      confirmation_phrase: "RESET RUSH SEASON",
      archive_download_path: null,
      archive: null,
      current_counts: { pnm_count: 0, rating_count: 0, lunch_count: 0 },
    };
    showToast(error.message || "Unable to load season archive status.");
  }
  renderSeasonArchiveStatusPanel();
}

async function loadCommandWorkspace() {
  const query = toQuery({
    window_hours: state.commandCenter.windowHours || 72,
    limit: state.commandCenter.limit || 30,
  });
  const payload = await api(`/api/workspace/command${query}`);
  const commandPayload = payload.command_center || {};
  state.commandCenter.queue = Array.isArray(commandPayload.queue) ? commandPayload.queue : [];
  state.commandCenter.staleAlerts = Array.isArray(commandPayload.stale_alerts) ? commandPayload.stale_alerts : [];
  state.commandCenter.recentChanges = Array.isArray(commandPayload.recent_rating_changes) ? commandPayload.recent_rating_changes : [];
  state.commandCenter.summary = commandPayload.summary || null;
  state.commandCenter.error = "";
  if (!state.commandCenter.selectedQueuePnmId) {
    state.commandCenter.selectedQueuePnmId = state.commandCenter.queue.length
      ? Number(state.commandCenter.queue[0].pnm_id)
      : null;
  }
  state.commandWorkspace.attention = payload.attention || [];
  state.commandWorkspace.today = payload.today || [];
  state.commandWorkspace.teamPulse = payload.team_pulse || null;
  state.commandWorkspace.watchCandidates = payload.watch_candidates || [];
  state.notifications = (payload.notifications && payload.notifications.notifications) || [];
  state.unreadNotifications = Number(payload.notifications && payload.notifications.unread_count ? payload.notifications.unread_count : 0);
  state.assignedRushRows = payload.assignments || [];
  renderPnmSelectOptions();
  renderCommandCenter();
  renderAssignedRushSection();
  renderGlobalNotificationsTray();
  updateNotificationBell();
  renderCommandWorkspaceExtras();
}

async function loadRusheesWorkspace() {
  const payload = await api(`/api/workspace/rushees${toQuery(state.rusheeFilters)}`);
  state.pnms = payload.pnms || [];
  state.calendarShare = payload.calendar_share || null;
  state.scheduledLunches = payload.scheduled_lunches || [];
  if (payload.analytics) {
    renderAnalytics(payload.analytics);
  }
  updateHeroStats();
  renderPnmSelectOptions();
  if (state.selectedPnmId && !state.pnms.find((pnm) => pnm.pnm_id === state.selectedPnmId)) {
    state.selectedPnmId = null;
  }
  if (!state.selectedPnmId && state.pnms.length) {
    state.selectedPnmId = state.pnms[0].pnm_id;
  }
  renderPnmTable();
  renderPnmBoard();
  renderAssignmentControls();
  renderPackageDealPanel();
  renderScheduledLunches();
  renderCalendarShareLinks(state.calendarShare);
  await loadPnmDetail(state.selectedPnmId);
}

async function loadTeamWorkspace() {
  const payload = await api(`/api/workspace/team${toQuery(state.memberFilters)}`);
  state.members = payload.users || [];
  state.assignedRushRows = (payload.assignments && payload.assignments.assignments) || [];
  state.teamWorkspace.assignmentOverview = payload.assignment_overview || null;
  state.teamWorkspace.leadership = payload.leadership || null;
  if (!state.members.some((member) => Number(member.user_id) === Number(state.selectedMemberId))) {
    state.selectedMemberId = state.members.length ? Number(state.members[0].user_id) : null;
  }
  renderMemberTable();
  await loadSameStatePnms();
  renderAssignedRushSection();
  renderTeamWorkspaceExtras(payload.pending || []);
  renderPendingApprovals({ pending: payload.pending || [] });
}

async function loadOperationsWorkspace() {
  const payload = await api("/api/workspace/operations");
  const calendar = payload.calendar || {};
  state.rushCalendarItems = calendar.items || [];
  state.rushCalendarStats = calendar.stats || null;
  state.scheduledLunches = payload.scheduled_lunches || [];
  state.calendarShare = payload.calendar_share || null;
  const goals = payload.goals || {};
  state.weeklyGoals = goals.goals || [];
  state.weeklyGoalSummary = goals.summary || null;
  state.weeklyGoalMetricOptions = goals.metric_options || [];
  const notifications = payload.notifications || {};
  state.notifications = notifications.notifications || [];
  state.unreadNotifications = Number(notifications.unread_count || 0);
  state.operationsWorkspace.notificationsDigest = notifications;
  state.officerChatMessages = (payload.chat && payload.chat.messages) || [];
  state.officerChatStats = payload.chat_stats || null;
  renderCalendarShareLinks(state.calendarShare);
  renderScheduledLunches();
  renderRushCalendar();
  renderWeeklyGoalMetricOptions();
  renderWeeklyGoals();
  renderNotifications();
  renderOfficerChat();
  renderOfficerChatStats();
  renderOperationsSummary();
  renderGlobalNotificationsTray();
  updateNotificationBell();
}

async function loadMeetingsWorkspace() {
  const payload = await api("/api/workspace/meetings");
  state.meetingsWorkspace.shortlist = payload.shortlist || [];
  state.meetingsWorkspace.attention = payload.attention || [];
  state.meetingsWorkspace.candidates = payload.candidates || [];
  state.meetingsWorkspace.compareDefaults = payload.compare_defaults || [];
  if (!state.meetingsWorkspace.compareA && state.meetingsWorkspace.compareDefaults[0]) {
    state.meetingsWorkspace.compareA = Number(state.meetingsWorkspace.compareDefaults[0]);
  }
  if (!state.meetingsWorkspace.compareB && state.meetingsWorkspace.compareDefaults[1]) {
    state.meetingsWorkspace.compareB = Number(state.meetingsWorkspace.compareDefaults[1]);
  }
  renderPnmSelectOptions();
  renderMeetingsWorkspace();
  await Promise.all([loadMeetingCompareSummary("A"), loadMeetingCompareSummary("B")]);
}

async function loadAdminWorkspace() {
  await Promise.all([
    loadPnms({ includeDetail: false }),
    loadMembers({ includeSameState: false }),
    loadHeadAdminData(),
    loadSeasonArchiveStatus(),
  ]);
  const payload = await api("/api/admin/overview");
  state.adminOverview = payload;
  state.teamWorkspace.assignmentOverview = payload.assignments || state.teamWorkspace.assignmentOverview;
  state.adminOverview.storage = payload.storage || null;
  state.adminOverview.pending = payload.pending || null;
  renderAdminWorkspaceExtras();
}

async function refreshAll() {
  await loadInterestHints();
  await refreshByActivePage();
}

async function ensureSession() {
  try {
    const payload = await api("/api/auth/me");
    if (!payload || !payload.authenticated || !payload.user) {
      state.user = null;
      closeTutorialOverlay();
      setAuthView(false);
      updateTopbarActions();
      stopLiveRefresh();
      return;
    }
    state.user = payload.user;
    const onboarding = state.user && state.user.onboarding ? state.user.onboarding : null;
    if (shouldRedirectToMemberPortal(state.user)) {
      window.location.replace(APP_CONFIG.member_base);
      return;
    }
    if (shouldRedirectToMobileNow() && !(onboarding && onboarding.required)) {
      window.location.replace(APP_CONFIG.mobile_base);
      return;
    }
    setAuthView(true);
    setSessionHeading();
    updateTopbarActions();
    await refreshAll();
    startLiveRefresh();
    maybeLaunchFirstRunTutorial();
  } catch {
    state.user = null;
    closeTutorialOverlay();
    setAuthView(false);
    updateTopbarActions();
    stopLiveRefresh();
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginAccessCode").value;
  const rememberMe = Boolean(loginRememberMe && loginRememberMe.checked);

  if (!username || !password) {
    showToast("Username and password are required.");
    return;
  }

  try {
    const payload = await api("/api/auth/login", {
      method: "POST",
      body: {
        username,
        password,
        remember_me: rememberMe,
      },
    });
    const onboarding = payload.user && payload.user.onboarding ? payload.user.onboarding : null;

    if (shouldRedirectToMemberPortal(payload.user)) {
      window.location.href = APP_CONFIG.member_base;
      return;
    }

    if (APP_CONFIG.mobile_base && shouldPreferMobileUi() && !(onboarding && onboarding.required)) {
      window.location.href = APP_CONFIG.mobile_base;
      return;
    }

    state.user = payload.user;
    setAuthView(true);
    setSessionHeading();
    updateTopbarActions();
    showToast("Logged in.");
    await refreshAll();
    startLiveRefresh();
    maybeLaunchFirstRunTutorial();
  } catch (error) {
    showToast(error.message || "Login failed.");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const username = document.getElementById("regUsername").value.trim();
  const password = document.getElementById("regAccessCode").value;
  const emoji = regEmoji.value.trim();
  const city = document.getElementById("regCity").value.trim();
  const stateCode = document.getElementById("regState").value.trim();
  if (!username) {
    showToast("Username is required.");
    return;
  }
  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
    showToast("Password must be 8+ characters with letters and numbers.");
    return;
  }

  const body = {
    username,
    emoji: emoji || null,
    password,
    city: city || null,
    state: stateCode || null,
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
  closeTouchpointDrawer();
  closeAppMenus();
  state.user = null;
  closeTutorialOverlay();
  state.selectedPnmId = null;
  state.pnms = [];
  state.assignedRushRows = [];
  state.members = [];
  state.sameStatePnms = [];
  state.selectedMemberId = null;
  state.commandCenter = {
    queue: [],
    staleAlerts: [],
    recentChanges: [],
    summary: null,
    selectedQueuePnmId: null,
    windowHours: 72,
    limit: 30,
    error: "",
  };
  state.calendarShare = null;
  state.scheduledLunches = [];
  state.rushCalendarItems = [];
  state.rushCalendarStats = null;
  state.weeklyGoals = [];
  state.weeklyGoalSummary = null;
  state.weeklyGoalMetricOptions = [];
  state.notifications = [];
  state.unreadNotifications = 0;
  state.officerChatMessages = [];
  state.officerChatStats = null;
  state.headAdmin = {
    summary: null,
    currentHeads: [],
    rushOfficers: [],
  };
  state.seasonArchive = null;
  state.adminEditPnmId = null;
  state.headAssignmentPnmId = null;
  state.packagePartnerId = null;
  animateCounter(heroPnmCount, 0);
  animateCounter(heroRatingCount, 0);
  animateCounter(heroLunchCount, 0);
  if (calendarFeedPreview) {
    calendarFeedPreview.textContent = "Sign in to load shared calendar link.";
  }
  if (rushCalendarFeedPreview) {
    rushCalendarFeedPreview.textContent = "Sign in to load rush calendar link.";
  }
  if (lunchOnlyFeedPreview) {
    lunchOnlyFeedPreview.textContent = "Sign in to load lunch feed link.";
  }
  if (scheduledLunchesList) {
    scheduledLunchesList.innerHTML = '<p class="muted">Sign in to view scheduled touchpoints.</p>';
  }
  if (rushCalendarTable) {
    rushCalendarTable.innerHTML = '<p class="muted">Sign in to view rush calendar items.</p>';
  }
  if (weeklyGoalsList) {
    weeklyGoalsList.innerHTML = '<p class="muted">Sign in to view weekly goals.</p>';
  }
  if (appNotificationsList) {
    appNotificationsList.innerHTML = '<p class="muted">Sign in to view notifications.</p>';
  }
  if (appNotificationsReadAllBtn) {
    appNotificationsReadAllBtn.disabled = true;
    appNotificationsReadAllBtn.textContent = "Mark All Read";
  }
  if (officerChatList) {
    officerChatList.innerHTML = '<div class="chat-welcome"><strong>Sign in to view officer chat.</strong><p class="muted">Rush Officer accounts can access the live thread after login.</p></div>';
  }
  if (openGoogleSubscribeBtn) {
    openGoogleSubscribeBtn.href = "#";
    openGoogleSubscribeBtn.classList.add("hidden");
  }
  if (openRushGoogleSubscribeBtn) {
    openRushGoogleSubscribeBtn.href = "#";
    openRushGoogleSubscribeBtn.classList.add("hidden");
  }
  if (lastLunchCalendarActions) {
    lastLunchCalendarActions.classList.add("hidden");
  }
  if (openLastLunchGoogleLink) {
    openLastLunchGoogleLink.href = "#";
  }
  if (sameStatePnmsHeader) {
    sameStatePnmsHeader.textContent = "Select a member to view PNMs from the same state.";
  }
  if (sameStatePnmsList) {
    sameStatePnmsList.innerHTML = '<p class="muted">No member selected.</p>';
  }
  if (seasonArchivePhrase) {
    seasonArchivePhrase.value = "";
  }
  if (seasonArchiveLabel) {
    seasonArchiveLabel.value = "";
  }
  if (seasonHeadChairConfirm) {
    seasonHeadChairConfirm.checked = false;
  }
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.classList.add("hidden");
  }
  renderOperationsUnreadBadge();
  renderGlobalNotificationsTray();
  updateNotificationBell();
  renderSelectedPnmPhoto(null);
  renderAdminPanel();
  renderAssignmentControls();
  renderAssignedRushSection();
  syncOpenMeetingLink();
  renderCommandCenter();
  renderGoogleImportResult(null);
  stopLiveRefresh();
  setAuthView(false);
  updateTopbarActions();
  showToast("Logged out.");
}

function getRusheeFilters() {
  return {
    interest: rusheeFilterInterest ? rusheeFilterInterest.value.trim() : "",
    stereotype: rusheeFilterStereotype ? rusheeFilterStereotype.value.trim() : "",
    state: rusheeFilterState ? rusheeFilterState.value.trim() : "",
  };
}

function getMatchingFilters() {
  return {
    interest: matchingFilterInterest ? matchingFilterInterest.value.trim() : "",
    stereotype: matchingFilterStereotype ? matchingFilterStereotype.value.trim() : "",
    state: matchingFilterState ? matchingFilterState.value.trim() : "",
  };
}

function getMemberFilters() {
  return {
    role: memberFilterRole ? memberFilterRole.value.trim() || "all" : "all",
    state: memberFilterState ? memberFilterState.value.trim() : "",
    city: memberFilterCity ? memberFilterCity.value.trim() : "",
    sort: memberSortSelectDesktop ? memberSortSelectDesktop.value.trim() || "location" : "location",
  };
}

function syncFilterInputsFromState() {
  if (rusheeFilterInterest) {
    rusheeFilterInterest.value = state.rusheeFilters.interest || "";
  }
  if (rusheeFilterStereotype) {
    rusheeFilterStereotype.value = state.rusheeFilters.stereotype || "";
  }
  if (rusheeFilterState) {
    rusheeFilterState.value = state.rusheeFilters.state || "";
  }
  if (matchingFilterInterest) {
    matchingFilterInterest.value = state.matchingFilters.interest || "";
  }
  if (matchingFilterStereotype) {
    matchingFilterStereotype.value = state.matchingFilters.stereotype || "";
  }
  if (matchingFilterState) {
    matchingFilterState.value = state.matchingFilters.state || "";
  }
  if (memberFilterRole) {
    memberFilterRole.value = state.memberFilters.role || "all";
  }
  if (memberFilterState) {
    memberFilterState.value = state.memberFilters.state || "";
  }
  if (memberFilterCity) {
    memberFilterCity.value = state.memberFilters.city || "";
  }
  if (memberSortSelectDesktop) {
    memberSortSelectDesktop.value = state.memberFilters.sort || "location";
  }
}

async function applyRusheeFilters(options = {}) {
  const silent = Boolean(options.silent);
  state.rusheeFilters = getRusheeFilters();
  try {
    if (state.activeDesktopPage === "rushees") {
      await loadRusheesWorkspace();
    } else {
      await loadPnms();
    }
    if (!silent) {
      showToast("Rushee filters applied.");
    }
  } catch (error) {
    showToast(error.message || "Unable to apply rushee filters.");
  }
}

async function handleApplyMatchingFilters() {
  state.matchingFilters = getMatchingFilters();
  try {
    await loadMatching();
    showToast("Matching filters applied.");
  } catch (error) {
    showToast(error.message || "Unable to apply matching filters.");
  }
}

async function applyMemberFilters(options = {}) {
  const silent = Boolean(options.silent);
  state.memberFilters = getMemberFilters();
  try {
    if (state.activeDesktopPage === "members") {
      await loadTeamWorkspace();
    } else {
      await loadMembers();
    }
    if (!silent) {
      showToast("Member filters applied.");
    }
  } catch (error) {
    showToast(error.message || "Unable to apply member filters.");
  }
}

function scheduleAutoApplyFilters(kind) {
  const timerMap = state.filterTimers || {};
  if (timerMap[kind]) {
    clearTimeout(timerMap[kind]);
  }
  timerMap[kind] = window.setTimeout(() => {
    if (kind === "members") {
      applyMemberFilters({ silent: true }).catch(() => {});
      return;
    }
    applyRusheeFilters({ silent: true }).catch(() => {});
  }, 240);
}

async function handlePnmCreate(event) {
  event.preventDefault();

  const interestsValue = document.getElementById("pnmInterests").value.trim();
  if (!interestsValue) {
    showToast("Select at least one approved interest tag.");
    return;
  }
  const stereotypeValue = document.getElementById("pnmStereotype").value.trim();
  if (!stereotypeValue) {
    showToast("Select one approved stereotype tag.");
    return;
  }
  const photoFile = pnmPhotoInput.files && pnmPhotoInput.files.length ? pnmPhotoInput.files[0] : null;
  const body = {
    first_name: document.getElementById("pnmFirstName").value.trim(),
    last_name: document.getElementById("pnmLastName").value.trim(),
    class_year: document.getElementById("pnmClassYear").value,
    hometown: document.getElementById("pnmHometown").value.trim(),
    state: document.getElementById("pnmState").value.trim(),
    phone_number: document.getElementById("pnmPhone").value.trim(),
    instagram_handle: document.getElementById("pnmInstagram").value.trim(),
    first_event_date: document.getElementById("pnmEventDate").value,
    interests: interestsValue,
    stereotype: stereotypeValue,
    lunch_stats: document.getElementById("pnmLunchStats").value.trim(),
    notes: document.getElementById("pnmNotes").value.trim(),
    auto_photo_from_instagram: !photoFile,
  };

  try {
    const payload = await api("/api/pnms", {
      method: "POST",
      body,
    });
    pnmForm.reset();
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
    syncInterestPickerFromInput("pnmInterests", "pnmInterestTags");
    syncStereotypePickerFromInput("pnmStereotype", "pnmStereotypeTags");
    showToast(`Rushee added: ${payload.pnm.pnm_code}`);
    await refreshAll();
    state.selectedPnmId = payload.pnm.pnm_id;
    applyRatingFormForSelected();
    await loadPnmDetail(state.selectedPnmId);
  } catch (error) {
    showToast(error.message || "Unable to create rushee.");
  }
}

async function handlePhotoUpload(event) {
  event.preventDefault();
  const selectedId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!selectedId) {
    showToast("Select a rushee before uploading a photo.");
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

async function handleRefreshInstagramPhoto() {
  const selectedId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!selectedId) {
    showToast("Select a rushee first.");
    return;
  }
  if (!roleCanManagePhotos()) {
    showToast("Only Rush Officers and Head Rush Officer can refresh photos.");
    return;
  }

  if (refreshInstagramPhotoBtn) {
    refreshInstagramPhotoBtn.disabled = true;
    refreshInstagramPhotoBtn.textContent = "Refreshing...";
  }

  try {
    await api(`/api/pnms/${selectedId}/photo/refresh-instagram`, {
      method: "POST",
    });
    await loadPnms();
    await loadPnmDetail(selectedId);
    showToast("Instagram photo refreshed.");
  } catch (error) {
    showToast(error.message || "Unable to refresh from Instagram right now.");
  } finally {
    if (refreshInstagramPhotoBtn) {
      refreshInstagramPhotoBtn.disabled = false;
      refreshInstagramPhotoBtn.textContent = "Pull From Instagram";
    }
  }
}

async function handleRatingSave(event) {
  event.preventDefault();
  const selectedId = Number(ratingPnm.value || state.selectedPnmId || 0);

  if (!selectedId) {
    showToast("Select a rushee before saving a rating.");
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
      showToast(`Rating increased to ${payload.change.new_total}/${RATING_TOTAL_MAX} (+${payload.change.delta_total}).`);
    } else {
      showToast("Rating saved.");
    }
  } catch (error) {
    showToast(error.message || "Unable to save rating.");
  }
}

function nextCommandQueuePnmId(previousId) {
  const rows = Array.isArray(state.commandCenter.queue) ? state.commandCenter.queue : [];
  if (!rows.length) {
    return null;
  }
  const safePrevious = Number(previousId || 0);
  if (!safePrevious) {
    return Number(rows[0].pnm_id);
  }
  const index = rows.findIndex((item) => Number(item.pnm_id) === safePrevious);
  if (index < 0) {
    return Number(rows[0].pnm_id);
  }
  if (rows[index + 1]) {
    return Number(rows[index + 1].pnm_id);
  }
  return Number(rows[0].pnm_id);
}

async function refreshCommandCenterDependencies() {
  await Promise.all([
    loadCommandCenter(),
    loadLeaderboard(),
    loadAnalytics(),
    loadPnms({ includeDetail: state.activeDesktopPage === "rushees" || state.activeDesktopPage === "admin" }),
    loadAssignedRushData(),
    loadNotifications(),
  ]);
}

async function submitCommandRating(options = {}) {
  const advance = Boolean(options.advance);
  if (!roleCanUseCommandCenter()) {
    showToast("Rush Officer access required.");
    return;
  }
  const selected = commandQueueSelectedItem();
  if (!selected) {
    showToast("Select a queue item first.");
    return;
  }
  const girlsInput = document.getElementById("commandRateGirls");
  const processInput = document.getElementById("commandRateProcess");
  const personableInput = document.getElementById("commandRatePersonable");
  const alcoholInput = document.getElementById("commandRateAlcohol");
  const igInput = document.getElementById("commandRateIg");
  const commentInput = document.getElementById("commandRateComment");
  if (!girlsInput || !processInput || !personableInput || !alcoholInput || !igInput || !commentInput) {
    showToast("Rating controls are unavailable.");
    return;
  }

  const selectedId = Number(selected.pnm_id || 0);
  if (!selectedId) {
    showToast("Invalid queue selection.");
    return;
  }

  const saveBtn = document.getElementById("commandSaveBtn");
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.textContent = advance ? "Saving + Advancing..." : "Saving...";
  }
  if (commandSaveNextBtn) {
    commandSaveNextBtn.disabled = true;
  }

  try {
    const payload = await api("/api/ratings", {
      method: "POST",
      body: {
        pnm_id: selectedId,
        good_with_girls: Number(girlsInput.value),
        will_make_it: Number(processInput.value),
        personable: Number(personableInput.value),
        alcohol_control: Number(alcoholInput.value),
        instagram_marketability: Number(igInput.value),
        comment: String(commentInput.value || "").trim(),
      },
    });
    const currentId = selectedId;
    await refreshCommandCenterDependencies();
    if (advance) {
      state.commandCenter.selectedQueuePnmId = nextCommandQueuePnmId(currentId);
      renderCommandCenter();
    }

    if (payload.change && Number(payload.change.delta_total) > 0) {
      spawnSuccessBurst();
      showToast(`Rating increased to ${payload.change.new_total}/${RATING_TOTAL_MAX} (+${payload.change.delta_total}).`);
    } else {
      showToast(advance ? "Rating saved. Advanced to next." : "Rating saved.");
    }
  } catch (error) {
    showToast(error.message || "Unable to save rating.");
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save Rating";
    }
    if (commandSaveNextBtn) {
      commandSaveNextBtn.disabled = false;
    }
  }
}

async function handleQuickRatingSave(event) {
  event.preventDefault();
  await submitCommandRating({ advance: false });
}

async function handleQuickRatingSaveNext() {
  await submitCommandRating({ advance: true });
}

async function submitTouchpointDrawer() {
  if (!touchpointDrawerForm || !touchpointDrawerPnm || !touchpointDrawerDate) {
    showToast("Touchpoint controls are unavailable.");
    return;
  }
  const selectedId = Number(touchpointDrawerPnm.value || state.touchpoint.pnmId || 0);
  if (!selectedId) {
    showToast("Select a rushee before scheduling a touchpoint.");
    return;
  }
  if (!String(touchpointDrawerDate.value || "").trim()) {
    showToast("Touchpoint date is required.");
    return;
  }
  const shouldAutoOpenGoogle = Boolean(touchpointDrawerOpenGoogle && touchpointDrawerOpenGoogle.checked);
  let pendingGoogleWindow = null;
  if (shouldAutoOpenGoogle) {
    try {
      pendingGoogleWindow = window.open("", "_blank");
    } catch {
      pendingGoogleWindow = null;
    }
  }

  const submitBtn = document.getElementById("touchpointDrawerSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Scheduling...";
  }

  try {
    const payload = await api("/api/lunches", {
      method: "POST",
      body: {
        pnm_id: selectedId,
        lunch_date: touchpointDrawerDate.value,
        start_time: touchpointDrawerStartTime && touchpointDrawerStartTime.value ? touchpointDrawerStartTime.value : null,
        end_time: touchpointDrawerEndTime && touchpointDrawerEndTime.value ? touchpointDrawerEndTime.value : null,
        location: touchpointDrawerLocation ? touchpointDrawerLocation.value.trim() : "",
        notes: touchpointDrawerNotes ? touchpointDrawerNotes.value.trim() : "",
      },
    });
    state.selectedPnmId = selectedId;
    state.touchpoint.pnmId = selectedId;
    state.touchpoint.lastGoogleUrl = payload.lunch && payload.lunch.google_calendar_url ? payload.lunch.google_calendar_url : "";
    if (touchpointDrawerLastGoogleLink) {
      const hasGoogleUrl = Boolean(state.touchpoint.lastGoogleUrl);
      touchpointDrawerLastGoogleLink.classList.toggle("hidden", !hasGoogleUrl);
      touchpointDrawerLastGoogleLink.href = hasGoogleUrl ? state.touchpoint.lastGoogleUrl : "#";
    }
    if (touchpointDrawerStartTime) {
      touchpointDrawerStartTime.value = "";
    }
    if (touchpointDrawerEndTime) {
      touchpointDrawerEndTime.value = "";
    }
    if (touchpointDrawerLocation) {
      touchpointDrawerLocation.value = "";
    }
    if (touchpointDrawerNotes) {
      touchpointDrawerNotes.value = "";
    }
    await Promise.all([
      refreshCommandCenterDependencies(),
      loadCalendarShare(),
      loadRushCalendar(),
      loadScheduledLunches(),
      loadWeeklyGoals(),
    ]);
    if (state.activeDesktopPage === "operations") {
      await loadOperationsWorkspace();
    } else if (state.activeDesktopPage === "meetings") {
      await loadMeetingsWorkspace();
    } else if (state.activeDesktopPage === "members") {
      await loadTeamWorkspace();
    }
    if (state.activeDesktopPage === "rushees" || state.activeDesktopPage === "admin") {
      await loadPnmDetail(selectedId);
    }
    if (payload.lunch && payload.lunch.google_calendar_url) {
      if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
        pendingGoogleWindow.location.href = payload.lunch.google_calendar_url;
      } else if (shouldAutoOpenGoogle) {
        window.location.assign(payload.lunch.google_calendar_url);
        return;
      }
    } else if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
      pendingGoogleWindow.close();
    }
    closeTouchpointDrawer();
    showToast("Touchpoint scheduled. Shared calendar updated.");
  } catch (error) {
    if (pendingGoogleWindow && !pendingGoogleWindow.closed) {
      pendingGoogleWindow.close();
    }
    showToast(error.message || "Unable to schedule touchpoint.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Schedule Touchpoint";
    }
  }
}

async function handleTouchpointDrawerSubmit(event) {
  event.preventDefault();
  await submitTouchpointDrawer();
}

function handleQueueSelect(event) {
  const button = event.target.closest("[data-command-queue-pnm-id]");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.commandQueuePnmId || 0);
  if (!pnmId) {
    return;
  }
  state.commandCenter.selectedQueuePnmId = pnmId;
  state.selectedPnmId = pnmId;
  renderPnmTable();
  applyRatingFormForSelected();
  renderCommandCenter();
}

async function handleHeadAssignmentSubmit(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  const officerUserId = headAssignOfficerSelect && headAssignOfficerSelect.value ? Number(headAssignOfficerSelect.value) : null;

  const saveButton = document.getElementById("headAssignSaveBtn");
  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: officerUserId },
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment saved from Head Console.");
  } catch (error) {
    showToast(error.message || "Unable to update assignment.");
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save Assignment";
    }
  }
}

async function handleHeadAssignmentClear() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  const clearButton = document.getElementById("headAssignClearBtn");
  if (clearButton) {
    clearButton.disabled = true;
    clearButton.textContent = "Clearing...";
  }
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: null },
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment cleared.");
  } catch (error) {
    showToast(error.message || "Unable to clear assignment.");
  } finally {
    if (clearButton) {
      clearButton.disabled = false;
      clearButton.textContent = "Clear Assignment";
    }
  }
}

async function handleHeadAddAssignee() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  const officerId = Number(headAddAssigneeSelect && headAddAssigneeSelect.value ? headAddAssigneeSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  if (!officerId) {
    showToast("Select a Rush Officer to add.");
    return;
  }

  const selected = state.pnms.find((pnm) => Number(pnm.pnm_id) === pnmId) || null;
  const includePackage = Boolean(selected && selected.package_group_id);
  if (headAddAssigneeBtn) {
    headAddAssigneeBtn.disabled = true;
    headAddAssigneeBtn.textContent = "Adding...";
  }
  try {
    const payload = await api(`/api/pnms/${pnmId}/assignees`, {
      method: "POST",
      body: {
        officer_user_id: officerId,
        include_package: includePackage,
        notify_officer: true,
      },
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast(payload.message || "Officer added to assignment team.");
  } catch (error) {
    showToast(error.message || "Unable to add assignment team member.");
  } finally {
    if (headAddAssigneeBtn) {
      headAddAssigneeBtn.disabled = false;
      headAddAssigneeBtn.textContent = "Add To Assignment Team";
    }
  }
}

async function handleHeadAssigneeListClick(event) {
  const button = event.target.closest("button.head-remove-assignee");
  if (!button) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(headAssignPnmSelect && headAssignPnmSelect.value ? headAssignPnmSelect.value : 0);
  const officerId = Number(button.dataset.userId || 0);
  if (!pnmId || !officerId) {
    return;
  }
  const selected = state.pnms.find((pnm) => Number(pnm.pnm_id) === pnmId) || null;
  const includePackage = Boolean(selected && selected.package_group_id);
  const officerName = button.closest(".entry")?.querySelector("strong")?.textContent?.trim() || "this officer";
  const confirmed = window.confirm(`Remove ${officerName} from this assignment team?`);
  if (!confirmed) {
    return;
  }

  button.disabled = true;
  try {
    const payload = await api(`/api/pnms/${pnmId}/assignees/${officerId}${includePackage ? "?include_package=1" : ""}`, {
      method: "DELETE",
    });
    state.headAssignmentPnmId = pnmId;
    state.selectedPnmId = pnmId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast(payload.message || "Officer removed from assignment team.");
  } catch (error) {
    showToast(error.message || "Unable to remove assignment team member.");
  } finally {
    button.disabled = false;
  }
}

async function handleAssignedContactsDownload() {
  if (!roleCanViewAssignedRushes()) {
    showToast("Rush Officer access required.");
    return;
  }
  if (assignedRushDownloadBtn) {
    assignedRushDownloadBtn.disabled = true;
    assignedRushDownloadBtn.textContent = "Preparing...";
  }
  try {
    await downloadFile(
      "/api/export/contacts-assigned.vcf",
      `assigned-rushees-${new Date().toISOString().slice(0, 10)}.vcf`
    );
    showToast("Assigned contacts downloaded.");
  } catch (error) {
    showToast(error.message || "Unable to download assigned contacts.");
  } finally {
    if (assignedRushDownloadBtn) {
      assignedRushDownloadBtn.disabled = false;
      assignedRushDownloadBtn.textContent = "Download Assigned Contacts (.vcf)";
    }
  }
}

async function handleAssignedRushTableClick(event) {
  const button = event.target.closest("button.assigned-contact-btn");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.pnmId || 0);
  if (!pnmId) {
    return;
  }
  const code = safeFileToken(button.dataset.pnmCode || `pnm-${pnmId}`) || `pnm-${pnmId}`;
  button.disabled = true;
  try {
    await downloadFile(`/api/export/contacts/${pnmId}.vcf`, `pnm-contact-${code}.vcf`);
    showToast("Contact downloaded.");
  } catch (error) {
    showToast(error.message || "Unable to download contact.");
  } finally {
    button.disabled = false;
  }
}

async function handlePackageDealLink() {
  if (!roleCanManagePackages()) {
    showToast("Sign in required.");
    return;
  }
  const primaryId = Number(state.selectedPnmId || 0);
  const partnerId = Number(packagePartnerSelect && packagePartnerSelect.value ? packagePartnerSelect.value : 0);
  if (!primaryId) {
    showToast("Select a rushee first.");
    return;
  }
  if (!partnerId || primaryId === partnerId) {
    showToast("Select a different rushee to link.");
    return;
  }
  const primaryPnm = state.pnms.find((pnm) => pnm.pnm_id === primaryId) || null;
  const partnerPnm = state.pnms.find((pnm) => pnm.pnm_id === partnerId) || null;
  if (!primaryPnm || !partnerPnm) {
    showToast("Could not find selected rushees.");
    return;
  }
  const primaryGroupId = normalizePackageGroupId(primaryPnm.package_group_id);
  const partnerGroupId = normalizePackageGroupId(partnerPnm.package_group_id);
  if (primaryGroupId && primaryGroupId === partnerGroupId) {
    showToast("These rushees are already linked in the same package deal.");
    return;
  }

  if (packageLinkBtn) {
    packageLinkBtn.disabled = true;
    packageLinkBtn.textContent = "Linking...";
  }
  try {
    const payload = await api("/api/pnms/package/link", {
      method: "POST",
      body: { pnm_ids: [primaryId, partnerId], sync_assignment: roleCanUseAdminPanel() },
    });
    state.packagePartnerId = partnerId;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(primaryId);
    showToast(payload.message || "Package deal linked.");
  } catch (error) {
    showToast(error.message || "Unable to link package deal.");
  } finally {
    if (packageLinkBtn) {
      packageLinkBtn.disabled = false;
      packageLinkBtn.textContent = "Link Package Deal";
    }
  }
}

async function handlePackageDealUnlink() {
  if (!roleCanManagePackages()) {
    showToast("Sign in required.");
    return;
  }
  const pnmId = Number(state.selectedPnmId || 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }

  if (packageUnlinkBtn) {
    packageUnlinkBtn.disabled = true;
    packageUnlinkBtn.textContent = "Unlinking...";
  }
  try {
    const payload = await api(`/api/pnms/${pnmId}/package/unlink`, {
      method: "POST",
    });
    state.packagePartnerId = null;
    await refreshAll();
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast(payload.message || "Package deal updated.");
  } catch (error) {
    showToast(error.message || "Unable to unlink package deal.");
  } finally {
    if (packageUnlinkBtn) {
      packageUnlinkBtn.disabled = false;
      packageUnlinkBtn.textContent = "Unlink Selected";
    }
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
  state.headAssignmentPnmId = pnmId;
  renderPnmTable();
  applyRatingFormForSelected();
  await loadPnmDetail(pnmId);
}

function handleWatchToggleClick(event) {
  const button = event.target.closest("[data-watch-pnm-id]");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.watchPnmId || 0);
  if (!pnmId) {
    return;
  }
  const watching = toggleWatchlistPnm(pnmId);
  showToast(watching ? "Pinned for Meetings." : "Removed from Meetings pins.");
}

async function handleGlobalOpenPnmClick(event) {
  const button = event.target.closest("[data-open-pnm-id]");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.openPnmId || 0);
  if (!pnmId) {
    return;
  }
  setActiveDesktopPage("rushees");
  state.selectedPnmId = pnmId;
  await loadRusheesWorkspace();
  state.selectedPnmId = pnmId;
  renderPnmTable();
  renderPnmBoard();
  applyRatingFormForSelected();
  await loadPnmDetail(pnmId);
}

function handleOperationsTabClick(event) {
  const button = event.target.closest(".operation-tab-btn[data-operations-tab]");
  if (!button) {
    return;
  }
  setOperationsTab(button.dataset.operationsTab || "timeline");
}

function handleAdminTabClick(event) {
  const button = event.target.closest(".admin-tab-btn[data-admin-tab]");
  if (!button) {
    return;
  }
  setAdminTab(button.dataset.adminTab || "leadership");
}

function handleCommandToolbarAction(event) {
  const button = event.target.closest("[data-command-action]");
  if (!button) {
    return;
  }
  performCommandAction(button.dataset.commandAction || "", { button });
}

function handleCommandPaletteResultsClick(event) {
  const openPnm = event.target.closest("[data-command-open-pnm]");
  if (openPnm) {
    const pnmId = Number(openPnm.dataset.commandOpenPnm || 0);
    if (pnmId) {
      closeCommandPalette();
      setActiveDesktopPage("rushees");
      state.selectedPnmId = pnmId;
      loadRusheesWorkspace()
        .then(() => {
          state.selectedPnmId = pnmId;
          renderPnmTable();
          renderPnmBoard();
          applyRatingFormForSelected();
          return loadPnmDetail(pnmId);
        })
        .catch(() => {});
    }
    return;
  }
  const openMember = event.target.closest("[data-command-open-member]");
  if (openMember) {
    const userId = Number(openMember.dataset.commandOpenMember || 0);
    if (userId) {
      closeCommandPalette();
      setActiveDesktopPage("members");
      state.selectedMemberId = userId;
      loadTeamWorkspace().catch(() => {});
    }
    return;
  }
  const runCommand = event.target.closest("[data-command-run]");
  if (!runCommand) {
    return;
  }
  closeCommandPalette();
  performCommandAction(runCommand.dataset.commandRun || "");
}

function handleMeetingsCompareChange(slot, value) {
  const nextId = Number(value || 0) || null;
  if (slot === "B") {
    state.meetingsWorkspace.compareB = nextId;
    loadMeetingCompareSummary("B").catch(() => {});
    return;
  }
  state.meetingsWorkspace.compareA = nextId;
  loadMeetingCompareSummary("A").catch(() => {});
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

async function handleMemberTableClick(event) {
  const selectButton = event.target.closest("button.select-member");
  if (selectButton) {
    const selectedUserId = Number(selectButton.dataset.userId || 0);
    if (!selectedUserId) {
      return;
    }
    state.selectedMemberId = selectedUserId;
    renderMemberTable();
    await loadSameStatePnms();
    return;
  }

  const button = event.target.closest("button.disapprove-user");
  if (!button) {
    return;
  }

  const userId = Number(button.dataset.userId || 0);
  if (!userId) {
    return;
  }
  const username = button.dataset.username || "this user";
  const confirmed = window.confirm(`Disapprove ${username}? They will be moved back to pending and signed out.`);
  if (!confirmed) {
    return;
  }

  try {
    await api(`/api/users/${userId}/disapprove`, {
      method: "POST",
    });
    showToast("User disapproved.");
    await Promise.all([loadApprovals(), loadMembers(), loadMatching(), loadHeadAdminData()]);
  } catch (error) {
    showToast(error.message || "Unable to disapprove user.");
  }
}

async function handlePromoteOfficer() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const officerId = Number(promoteOfficerSelect && promoteOfficerSelect.value ? promoteOfficerSelect.value : 0);
  if (!officerId) {
    showToast("Select a Rush Officer to promote.");
    return;
  }

  const officer = (state.headAdmin.rushOfficers || []).find((entry) => entry.user_id === officerId);
  const transferLeadership = Boolean(demoteExistingHeads && demoteExistingHeads.checked);
  const targetName = officer ? officer.username : "selected officer";
  const prompt = transferLeadership
    ? `Promote ${targetName} to Head Rush Officer and demote other heads to Rush Officer?`
    : `Promote ${targetName} to Head Rush Officer?`;
  const confirmed = window.confirm(prompt);
  if (!confirmed) {
    return;
  }

  promoteOfficerBtn.disabled = true;
  promoteOfficerBtn.textContent = "Promoting...";
  try {
    const payload = await api(`/api/admin/officers/${officerId}/promote-head`, {
      method: "POST",
      body: {
        demote_existing_heads: transferLeadership,
      },
    });
    showToast(payload.message || "Officer promoted.");
    await ensureSession();
  } catch (error) {
    showToast(error.message || "Unable to promote officer.");
  } finally {
    promoteOfficerBtn.disabled = false;
    promoteOfficerBtn.textContent = "Promote To Head";
  }
}

async function handleSameStatePnmsClick(event) {
  const button = event.target.closest("button.open-same-state-pnm");
  if (!button) {
    return;
  }
  const pnmId = Number(button.dataset.pnmId || 0);
  if (!pnmId) {
    return;
  }
  const preferredState = String(button.dataset.state || "").trim();
  if (preferredState) {
    state.rusheeFilters = {
      ...state.rusheeFilters,
      state: preferredState,
    };
  }
  syncFilterInputsFromState();
  await loadPnms();
  if (!state.pnms.some((pnm) => Number(pnm.pnm_id) === pnmId)) {
    showToast("Rushee not visible under current filters.");
    return;
  }
  state.selectedPnmId = pnmId;
  state.headAssignmentPnmId = pnmId;
  renderPnmTable();
  applyRatingFormForSelected();
  await loadPnmDetail(pnmId);
  setActiveDesktopPage("rushees");
}

async function handleAdminPnmEditorSubmit(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(adminEditPnmSelect && adminEditPnmSelect.value ? adminEditPnmSelect.value : 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }

  const interestsValue = document.getElementById("adminEditInterests").value.trim();
  if (!interestsValue) {
    showToast("Select at least one approved interest tag.");
    return;
  }
  const stereotypeValue = document.getElementById("adminEditStereotype").value.trim();
  if (!stereotypeValue) {
    showToast("Select one approved stereotype tag.");
    return;
  }
  const saveButton = document.getElementById("saveAdminPnmBtn");
  const body = {
    first_name: document.getElementById("adminEditFirstName").value.trim(),
    last_name: document.getElementById("adminEditLastName").value.trim(),
    class_year: document.getElementById("adminEditClassYear").value,
    first_event_date: document.getElementById("adminEditFirstEventDate").value,
    hometown: document.getElementById("adminEditHometown").value.trim(),
    state: document.getElementById("adminEditState").value.trim(),
    phone_number: document.getElementById("adminEditPhoneNumber").value.trim(),
    instagram_handle: document.getElementById("adminEditInstagramHandle").value.trim(),
    interests: interestsValue,
    stereotype: stereotypeValue,
    lunch_stats: document.getElementById("adminEditLunchStats").value.trim(),
    notes: document.getElementById("adminEditNotes").value.trim(),
  };

  if (saveButton) {
    saveButton.disabled = true;
    saveButton.textContent = "Saving...";
  }
  try {
    const payload = await api(`/api/pnms/${pnmId}`, {
      method: "PATCH",
      body,
    });
    state.selectedPnmId = pnmId;
    state.adminEditPnmId = pnmId;
    showToast(payload.message || "Rushee details saved.");
    await refreshAll();
    await loadPnmDetail(pnmId);
  } catch (error) {
    showToast(error.message || "Unable to update rushee details.");
  } finally {
    if (saveButton) {
      saveButton.disabled = false;
      saveButton.textContent = "Save Rushee Changes";
    }
  }
}

async function handleAdminPanelClick(event) {
  const editButton = event.target.closest("button.edit-pnm");
  if (editButton) {
    const pnmId = Number(editButton.dataset.pnmId || 0);
    if (!pnmId) {
      return;
    }
    state.adminEditPnmId = pnmId;
    if (adminEditPnmSelect) {
      adminEditPnmSelect.value = String(pnmId);
    }
    populateAdminPnmEditor(pnmId);
    setActiveDesktopPage("admin");
    showToast("Rushee loaded into editor.");
    return;
  }

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

async function handleAssignOfficer() {
  if (!roleCanAssignOfficer()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }

  const officerUserId = assignOfficerSelect.value ? Number(assignOfficerSelect.value) : null;
  assignOfficerBtn.disabled = true;
  assignOfficerBtn.textContent = "Saving...";
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: officerUserId },
    });
    state.headAssignmentPnmId = pnmId;
    await refreshAll();
    state.selectedPnmId = pnmId;
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment updated.");
  } catch (error) {
    showToast(error.message || "Unable to assign Rush Officer.");
  } finally {
    assignOfficerBtn.disabled = false;
    assignOfficerBtn.textContent = "Assign";
  }
}

async function handleClearAssignment() {
  if (!roleCanAssignOfficer()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const pnmId = Number(state.selectedPnmId || ratingPnm.value || 0);
  if (!pnmId) {
    showToast("Select a rushee first.");
    return;
  }
  clearAssignBtn.disabled = true;
  clearAssignBtn.textContent = "Clearing...";
  try {
    await api(`/api/pnms/${pnmId}/assign`, {
      method: "POST",
      body: { officer_user_id: null },
    });
    state.headAssignmentPnmId = pnmId;
    await refreshAll();
    state.selectedPnmId = pnmId;
    applyRatingFormForSelected();
    await loadPnmDetail(pnmId);
    showToast("Assignment cleared.");
  } catch (error) {
    showToast(error.message || "Unable to clear assignment.");
  } finally {
    clearAssignBtn.disabled = false;
    clearAssignBtn.textContent = "Clear";
  }
}

async function handleCsvBackupDownload(trigger = null) {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const button = trigger && trigger.nodeType === 1 ? trigger : null;
  const priorLabel = button ? button.textContent : "";
  if (button) {
    button.disabled = true;
    button.textContent = "Preparing...";
  }
  try {
    await downloadFile("/api/export/csv", "kao-rush-backup.zip");
    showToast("CSV backup downloaded.");
  } catch (error) {
    showToast(error.message || "CSV backup download failed.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = priorLabel || "Backup CSV";
    }
  }
}

async function handleDbBackupDownload(trigger = null) {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const button = trigger && trigger.nodeType === 1 ? trigger : null;
  const priorLabel = button ? button.textContent : "";
  if (button) {
    button.disabled = true;
    button.textContent = "Preparing...";
  }
  try {
    await downloadFile("/api/export/sqlite", "kao-rush-backup.sqlite");
    showToast("Database snapshot downloaded.");
  } catch (error) {
    showToast(error.message || "Database backup download failed.");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = priorLabel || "Backup DB";
    }
  }
}

async function handleSeasonArchiveDownload() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const downloadPath = (state.seasonArchive && state.seasonArchive.archive_download_path) || "/api/admin/season/archive/download";
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.disabled = true;
    seasonArchiveDownloadBtn.textContent = "Preparing...";
  }
  try {
    await downloadFile(downloadPath, "rush-season-archive.sqlite");
    showToast("Season archive downloaded.");
  } catch (error) {
    showToast(error.message || "Unable to download season archive.");
  } finally {
    if (seasonArchiveDownloadBtn) {
      seasonArchiveDownloadBtn.disabled = false;
      seasonArchiveDownloadBtn.textContent = "Download Archived Season";
    }
  }
}

async function handleSeasonReset() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const expectedPhrase = (state.seasonArchive && state.seasonArchive.confirmation_phrase) || "RESET RUSH SEASON";
  const typedPhrase = seasonArchivePhrase ? seasonArchivePhrase.value.trim() : "";
  if (!typedPhrase) {
    showToast(`Type the confirmation phrase: ${expectedPhrase}`);
    return;
  }
  if (typedPhrase.toUpperCase() !== expectedPhrase.toUpperCase()) {
    showToast(`Phrase mismatch. Type exactly: ${expectedPhrase}`);
    return;
  }
  if (!seasonHeadChairConfirm || !seasonHeadChairConfirm.checked) {
    showToast("Confirm that all head rush chairs approved before resetting.");
    return;
  }
  const confirmed = window.confirm(
    "Archive the current rush season and reset rushees, ratings, touchpoints, and participation counters for next season?"
  );
  if (!confirmed) {
    return;
  }

  if (seasonResetBtn) {
    seasonResetBtn.disabled = true;
    seasonResetBtn.textContent = "Archiving...";
  }
  try {
    const payload = await api("/api/admin/season/reset", {
      method: "POST",
      body: {
        confirm_phrase: typedPhrase,
        archive_label: seasonArchiveLabel && seasonArchiveLabel.value.trim() ? seasonArchiveLabel.value.trim() : null,
        head_chair_confirmation: true,
      },
    });
    if (seasonArchivePhrase) {
      seasonArchivePhrase.value = "";
    }
    if (seasonArchiveLabel) {
      seasonArchiveLabel.value = "";
    }
    if (seasonHeadChairConfirm) {
      seasonHeadChairConfirm.checked = false;
    }
    showToast(payload.message || "Season reset completed.");
    await refreshAll();
    setActiveDesktopPage("admin", false);
  } catch (error) {
    showToast(error.message || "Unable to reset rush season.");
  } finally {
    if (seasonResetBtn) {
      seasonResetBtn.disabled = false;
      seasonResetBtn.textContent = "Archive + Reset Season";
    }
  }
}

function renderGoogleImportResult(payload) {
  if (!googleImportResult) {
    return;
  }
  if (!payload) {
    googleImportResult.innerHTML = '<p class="muted">No imports yet.</p>';
    return;
  }
  const issues = (payload.errors || [])
    .map((item) => `<li>Row ${item.row}: ${escapeHtml(item.reason)}</li>`)
    .join("");
  const truncated = payload.errors_truncated ? '<p class="muted">Only the first set of errors are shown.</p>' : "";
  googleImportResult.innerHTML = `
    <div class="entry">
      <div class="entry-title">
        <strong>Last Import Result</strong>
        <span>${escapeHtml(payload.created_count || 0)} created</span>
      </div>
      <p class="muted">Rows processed: ${payload.rows_processed || 0} | Created: ${payload.created_count || 0} | Duplicates skipped: ${payload.skipped_duplicates || 0} | Errors: ${payload.error_count || 0}</p>
      <p class="muted">${escapeHtml(payload.message || "")}</p>
      ${issues ? `<ul class="import-error-list">${issues}</ul>${truncated}` : '<p class="muted">No row-level errors.</p>'}
    </div>
  `;
}

async function handleGoogleImport(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const file = googleImportFile && googleImportFile.files && googleImportFile.files.length ? googleImportFile.files[0] : null;
  if (!file) {
    showToast("Choose a Google Form CSV file first.");
    return;
  }

  if (googleImportBtn) {
    googleImportBtn.disabled = true;
    googleImportBtn.textContent = "Importing...";
  }
  try {
    const formData = new FormData();
    formData.append("file", file);
    const payload = await api("/api/admin/import/google-form", {
      method: "POST",
      body: formData,
    });
    renderGoogleImportResult(payload);
    if (googleImportForm) {
      googleImportForm.reset();
    }
    if (Number(payload.created_count || 0) > 0) {
      await refreshAll();
    }
    showToast(payload.message || "Google Form CSV imported.");
  } catch (error) {
    showToast(error.message || "Unable to import Google Form CSV.");
  } finally {
    if (googleImportBtn) {
      googleImportBtn.disabled = false;
      googleImportBtn.textContent = "Import Google Form CSV";
    }
  }
}

function handleDownloadGoogleImportTemplate() {
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  window.location.href = resolveApiPath("/api/admin/import/google-form/template");
}

async function copyTextToClipboard(value) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const input = document.createElement("input");
  input.value = value;
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

async function handleCopyCalendarFeed() {
  if (!state.calendarShare || !state.calendarShare.feed_url) {
    showToast("Shared calendar link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(state.calendarShare.feed_url);
    showToast("Shared calendar URL copied.");
  } catch {
    showToast("Unable to copy URL. Use the link shown below the button.");
  }
}

async function handleCopyRushCalendarFeed() {
  const value = state.calendarShare && (state.calendarShare.rush_feed_url || state.calendarShare.feed_url);
  if (!value) {
    showToast("Rush calendar link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(value);
    showToast("Rush calendar URL copied.");
  } catch {
    showToast("Unable to copy rush feed URL right now.");
  }
}

async function handleCopyLunchOnlyFeed() {
  const value = state.calendarShare && state.calendarShare.lunch_feed_url;
  if (!value) {
    showToast("Lunch-only feed link is not ready yet.");
    return;
  }
  try {
    await copyTextToClipboard(value);
    showToast("Lunch-only calendar URL copied.");
  } catch {
    showToast("Unable to copy lunch feed URL right now.");
  }
}

async function handleRushEventCreate(event) {
  event.preventDefault();
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const body = {
    title: rushEventTitle ? rushEventTitle.value.trim() : "",
    event_type: rushEventType ? rushEventType.value : "official",
    event_date: rushEventDate ? rushEventDate.value : "",
    start_time: rushEventStartTime && rushEventStartTime.value ? rushEventStartTime.value : null,
    end_time: rushEventEndTime && rushEventEndTime.value ? rushEventEndTime.value : null,
    location: rushEventLocation ? rushEventLocation.value.trim() : "",
    details: rushEventDetails ? rushEventDetails.value.trim() : "",
    is_official: rushEventOfficial ? Boolean(rushEventOfficial.checked) : true,
  };
  if (!body.title || !body.event_date) {
    showToast("Event title and date are required.");
    return;
  }
  const submitBtn = document.getElementById("rushEventSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
  }
  try {
    await api("/api/rush-events", { method: "POST", body });
    if (rushEventForm) {
      rushEventForm.reset();
    }
    setDefaultDates();
    if (rushEventOfficial) {
      rushEventOfficial.checked = true;
    }
    showToast("Rush event created.");
    await Promise.all([loadRushCalendar(), loadCalendarShare(), loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to create rush event.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Event";
    }
  }
}

async function handleRushCalendarTableClick(event) {
  const removeBtn = event.target.closest("[data-rush-event-delete]");
  if (!removeBtn) {
    return;
  }
  if (!roleCanUseAdminPanel()) {
    showToast("Head Rush Officer access required.");
    return;
  }
  const eventId = Number(removeBtn.dataset.rushEventDelete || 0);
  if (!eventId) {
    return;
  }
  const confirmed = window.confirm("Remove this rush event from the calendar?");
  if (!confirmed) {
    return;
  }
  removeBtn.disabled = true;
  try {
    await api(`/api/rush-events/${eventId}`, { method: "DELETE" });
    showToast("Rush event removed.");
    await Promise.all([loadRushCalendar(), loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to remove rush event.");
  } finally {
    removeBtn.disabled = false;
  }
}

async function handleWeeklyGoalCreate(event) {
  event.preventDefault();
  if (!roleCanManageOperations()) {
    showToast("Rush Officer access required.");
    return;
  }
  const body = {
    title: weeklyGoalTitle ? weeklyGoalTitle.value.trim() : "",
    description: weeklyGoalDescription ? weeklyGoalDescription.value.trim() : "",
    metric_type: weeklyGoalMetric ? weeklyGoalMetric.value : "manual",
    target_count: weeklyGoalTarget ? Number(weeklyGoalTarget.value || 0) : 0,
    week_start: weeklyGoalWeekStart && weeklyGoalWeekStart.value ? weeklyGoalWeekStart.value : null,
    week_end: weeklyGoalWeekEnd && weeklyGoalWeekEnd.value ? weeklyGoalWeekEnd.value : null,
    assigned_user_id: weeklyGoalAssignedUser && weeklyGoalAssignedUser.value ? Number(weeklyGoalAssignedUser.value) : null,
  };
  if (!body.title || !body.target_count) {
    showToast("Goal title and target are required.");
    return;
  }
  const submitBtn = document.getElementById("weeklyGoalSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating...";
  }
  try {
    await api("/api/tasks/weekly", { method: "POST", body });
    if (weeklyGoalForm) {
      weeklyGoalForm.reset();
    }
    setDefaultDates();
    renderWeeklyGoalMetricOptions();
    renderWeeklyGoalAssignedUsers();
    showToast("Weekly goal created.");
    await Promise.all([loadWeeklyGoals(), loadNotifications()]);
  } catch (error) {
    showToast(error.message || "Unable to create weekly goal.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Goal";
    }
  }
}

async function handleWeeklyGoalsActionClick(event) {
  const progressBtn = event.target.closest("[data-goal-progress]");
  if (progressBtn) {
    const goalId = Number(progressBtn.dataset.goalProgress || 0);
    if (!goalId) {
      return;
    }
    progressBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}/progress`, {
        method: "POST",
        body: { delta: 1 },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast("Goal progress updated.");
    } catch (error) {
      showToast(error.message || "Unable to update goal progress.");
    } finally {
      progressBtn.disabled = false;
    }
    return;
  }

  const completeBtn = event.target.closest("[data-goal-complete]");
  if (completeBtn) {
    const goalId = Number(completeBtn.dataset.goalComplete || 0);
    if (!goalId) {
      return;
    }
    completeBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}`, {
        method: "PATCH",
        body: { complete_now: true },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast("Goal marked complete.");
    } catch (error) {
      showToast(error.message || "Unable to mark goal complete.");
    } finally {
      completeBtn.disabled = false;
    }
    return;
  }

  const archiveBtn = event.target.closest("[data-goal-archive]");
  if (archiveBtn) {
    const goalId = Number(archiveBtn.dataset.goalArchive || 0);
    if (!goalId) {
      return;
    }
    const archived = archiveBtn.dataset.goalArchived === "1";
    archiveBtn.disabled = true;
    try {
      await api(`/api/tasks/weekly/${goalId}`, {
        method: "PATCH",
        body: { is_archived: !archived },
      });
      await Promise.all([loadWeeklyGoals(), loadNotifications()]);
      showToast(archived ? "Goal unarchived." : "Goal archived.");
    } catch (error) {
      showToast(error.message || "Unable to update goal archive state.");
    } finally {
      archiveBtn.disabled = false;
    }
  }
}

async function handleAppNotificationsClick(event) {
  const btn = event.target.closest("[data-notification-read]");
  if (!btn) {
    return;
  }
  const notificationId = Number(btn.dataset.notificationRead || 0);
  if (!notificationId) {
    return;
  }
  btn.disabled = true;
  try {
    await api(`/api/notifications/${notificationId}/read`, { method: "POST" });
    await loadNotifications();
  } catch (error) {
    showToast(error.message || "Unable to mark notification read.");
  } finally {
    btn.disabled = false;
  }
}

async function handleAppNotificationsReadAll() {
  if (!state.unreadNotifications) {
    return;
  }
  if (appNotificationsReadAllBtn) {
    appNotificationsReadAllBtn.disabled = true;
  }
  try {
    await api("/api/notifications/read-all", { method: "POST" });
    await loadNotifications();
    showToast("All notifications marked read.");
  } catch (error) {
    showToast(error.message || "Unable to mark notifications read.");
  } finally {
    if (appNotificationsReadAllBtn) {
      appNotificationsReadAllBtn.disabled = false;
    }
  }
}

function sanitizeChatTagToken(raw) {
  return String(raw || "")
    .trim()
    .replace(/^#+/, "")
    .replace(/[^a-zA-Z0-9_-]/g, "");
}

function appendQuickChatTag(rawTag) {
  if (!officerChatTags) {
    return;
  }
  const tag = sanitizeChatTagToken(rawTag);
  if (!tag) {
    return;
  }
  const tokens = parseTagInput(officerChatTags.value).map(sanitizeChatTagToken).filter(Boolean);
  tokens.push(tag);
  officerChatTags.value = uniqueNormalized(tokens).join(", ");
}

function handleOfficerChatQuickTagClick(event) {
  const button = event.target.closest("[data-chat-quick-tag]");
  if (!button) {
    return;
  }
  const tag = button.dataset.chatQuickTag || "";
  appendQuickChatTag(tag);
  button.classList.add("is-selected");
  clearTimeout(button._flashTimer);
  button._flashTimer = setTimeout(() => button.classList.remove("is-selected"), 520);
  if (officerChatMessage) {
    officerChatMessage.focus();
  }
}

function handleOfficerChatMessageKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  if (!officerChatForm) {
    return;
  }
  if (typeof officerChatForm.requestSubmit === "function") {
    officerChatForm.requestSubmit();
    return;
  }
  officerChatForm.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
}

async function handleOfficerChatSubmit(event) {
  event.preventDefault();
  if (!roleCanManageOperations()) {
    showToast("Rush Officer access required.");
    return;
  }
  const message = officerChatMessage ? officerChatMessage.value.trim() : "";
  const tags = officerChatTags ? officerChatTags.value.trim() : "";
  if (!message) {
    showToast("Enter a chat message first.");
    return;
  }
  const submitBtn = document.getElementById("officerChatSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending...";
  }
  try {
    await api("/api/chat/officer", {
      method: "POST",
      body: { message, tags: tags || null },
    });
    if (officerChatForm) {
      officerChatForm.reset();
    }
    if (officerChatMessage) {
      officerChatMessage.focus();
    }
    await Promise.all([loadOfficerChat(), loadOfficerChatStats(), loadWeeklyGoals(), loadNotifications()]);
    showToast("Message sent.");
  } catch (error) {
    showToast(error.message || "Unable to send chat message.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Send Message";
    }
  }
}

function setupPwaInstall() {
  if (!installBtn) {
    return;
  }
  const pwaApi = window.BidBoardPwa || null;
  const userAgent = (navigator.userAgent || "").toLowerCase();
  const isIosDevice = /iphone|ipad|ipod/.test(userAgent);
  const isStandalone =
    Boolean(pwaApi && typeof pwaApi.isStandaloneMode === "function" && pwaApi.isStandaloneMode()) ||
    window.navigator.standalone === true;
  const refreshInstallButton = () => {
    const hasPrompt = Boolean(pwaApi && typeof pwaApi.getDeferredPrompt === "function" && pwaApi.getDeferredPrompt());
    const showManualInstallHint = isIosDevice && !isStandalone;
    installBtn.classList.toggle("hidden", !(hasPrompt || showManualInstallHint));
  };
  refreshInstallButton();

  document.addEventListener("bidboard:install-ready", refreshInstallButton);
  document.addEventListener("bidboard:installed", () => {
    installBtn.classList.add("hidden");
  });

  installBtn.addEventListener("click", async () => {
    if (!pwaApi || typeof pwaApi.promptInstall !== "function") {
      showToast("Use Safari Share -> Add to Home Screen.");
      return;
    }
    const promptShown = await pwaApi.promptInstall();
    if (!promptShown) {
      showToast("Use Safari Share -> Add to Home Screen.");
      return;
    }
    refreshInstallButton();
  });
}

function attachEvents() {
  loginForm.addEventListener("submit", handleLogin);
  registerForm.addEventListener("submit", handleRegister);
  logoutBtn.addEventListener("click", handleLogout);
  if (openTutorialBtn) {
    openTutorialBtn.addEventListener("click", handleTutorialShortcut);
  }
  if (seasonResetBtn) {
    seasonResetBtn.addEventListener("click", handleSeasonReset);
  }
  if (seasonArchiveDownloadBtn) {
    seasonArchiveDownloadBtn.addEventListener("click", handleSeasonArchiveDownload);
  }
  if (googleImportForm) {
    googleImportForm.addEventListener("submit", handleGoogleImport);
  }
  if (downloadGoogleImportTemplateBtn) {
    downloadGoogleImportTemplateBtn.addEventListener("click", handleDownloadGoogleImportTemplate);
  }
  if (copyCalendarFeedBtn) {
    copyCalendarFeedBtn.addEventListener("click", handleCopyCalendarFeed);
  }
  if (copyRushCalendarFeedBtn) {
    copyRushCalendarFeedBtn.addEventListener("click", handleCopyRushCalendarFeed);
  }
  if (copyLunchOnlyFeedBtn) {
    copyLunchOnlyFeedBtn.addEventListener("click", handleCopyLunchOnlyFeed);
  }
  if (refreshScheduledLunchesBtn) {
    refreshScheduledLunchesBtn.addEventListener("click", async () => {
      try {
        await loadScheduledLunches();
        showToast("Scheduled lunches refreshed.");
      } catch (error) {
        showToast(error.message || "Unable to refresh scheduled touchpoints.");
      }
    });
  }
  if (assignOfficerBtn) {
    assignOfficerBtn.addEventListener("click", handleAssignOfficer);
  }
  if (clearAssignBtn) {
    clearAssignBtn.addEventListener("click", handleClearAssignment);
  }
  if (applyMatchingFiltersBtn) {
    applyMatchingFiltersBtn.addEventListener("click", handleApplyMatchingFilters);
  }
  if (commandRatingForm) {
    commandRatingForm.addEventListener("submit", handleQuickRatingSave);
  }
  if (commandSaveNextBtn) {
    commandSaveNextBtn.addEventListener("click", handleQuickRatingSaveNext);
  }
  if (commandCenterQueue) {
    commandCenterQueue.addEventListener("click", handleQueueSelect);
  }
  if (commandWatchToggleBtn) {
    commandWatchToggleBtn.addEventListener("click", () => {
      const selectedId = Number(state.commandCenter.selectedQueuePnmId || 0);
      if (!selectedId) {
        showToast("Select a queue item first.");
        return;
      }
      const watching = toggleWatchlistPnm(selectedId);
      showToast(watching ? "Pinned for Meetings." : "Removed from Meetings pins.");
    });
  }
  if (commandScheduleTouchpointBtn) {
    commandScheduleTouchpointBtn.addEventListener("click", () => {
      const selectedId = Number(state.commandCenter.selectedQueuePnmId || 0);
      if (!selectedId) {
        showToast("Select a queue item first.");
        return;
      }
      openTouchpointDrawer({ source: "command", pnmId: selectedId });
    });
  }
  if (rusheeWatchToggleBtn) {
    rusheeWatchToggleBtn.addEventListener("click", () => {
      const selectedId = Number(state.selectedPnmId || 0);
      if (!selectedId) {
        showToast("Select a rushee first.");
        return;
      }
      const watching = toggleWatchlistPnm(selectedId);
      showToast(watching ? "Pinned for Meetings." : "Removed from Meetings pins.");
    });
  }
  if (rusheeScheduleTouchpointBtn) {
    rusheeScheduleTouchpointBtn.addEventListener("click", () => {
      const selectedId = Number(state.selectedPnmId || 0);
      if (!selectedId) {
        showToast("Select a rushee first.");
        return;
      }
      openTouchpointDrawer({ source: "rushees", pnmId: selectedId });
    });
  }
  if (operationsScheduleTouchpointBtn) {
    operationsScheduleTouchpointBtn.addEventListener("click", () => {
      openTouchpointDrawer({ source: "operations", pnmId: Number(state.selectedPnmId || 0) || null });
    });
  }
  if (touchpointDrawerForm) {
    touchpointDrawerForm.addEventListener("submit", handleTouchpointDrawerSubmit);
  }
  if (touchpointDrawerPnm) {
    touchpointDrawerPnm.addEventListener("change", (event) => {
      state.touchpoint.pnmId = Number(event.target.value || 0) || null;
    });
  }
  if (touchpointDrawerCloseBtn) {
    touchpointDrawerCloseBtn.addEventListener("click", closeTouchpointDrawer);
  }
  if (touchpointDrawer) {
    touchpointDrawer.addEventListener("click", (event) => {
      if (event.target === touchpointDrawer || event.target.classList.contains("touchpoint-drawer-scrim")) {
        closeTouchpointDrawer();
      }
    });
  }
  [rusheeFilterInterest, rusheeFilterStereotype, rusheeFilterState].forEach((input) => {
    if (input) {
      input.addEventListener("input", () => scheduleAutoApplyFilters("rushees"));
      input.addEventListener("change", () => scheduleAutoApplyFilters("rushees"));
    }
  });
  [memberFilterRole, memberFilterState, memberFilterCity, memberSortSelectDesktop].forEach((input) => {
    if (input) {
      input.addEventListener("input", () => scheduleAutoApplyFilters("members"));
      input.addEventListener("change", () => scheduleAutoApplyFilters("members"));
    }
  });
  if (pnmViewToggleTable) {
    pnmViewToggleTable.addEventListener("click", () => {
      setViewPreference("pnmView", "table");
      renderPnmBoard();
    });
  }
  if (pnmViewToggleBoard) {
    pnmViewToggleBoard.addEventListener("click", () => {
      setViewPreference("pnmView", "board");
      renderPnmBoard();
    });
  }
  if (operationsTabBar) {
    operationsTabBar.addEventListener("click", handleOperationsTabClick);
  }
  if (adminTabBar) {
    adminTabBar.addEventListener("click", handleAdminTabClick);
  }
  if (globalCommandBtn) {
    globalCommandBtn.addEventListener("click", () => openCommandPalette(globalSearchInput ? globalSearchInput.value : ""));
  }
  if (globalSearchInput) {
    globalSearchInput.addEventListener("focus", () => openCommandPalette(globalSearchInput.value || ""));
    globalSearchInput.addEventListener("input", () => {
      if (commandPaletteInput) {
        commandPaletteInput.value = globalSearchInput.value || "";
      }
      loadGlobalSearch(globalSearchInput.value || "");
      if (globalCommandPalette && globalCommandPalette.classList.contains("hidden")) {
        openCommandPalette(globalSearchInput.value || "");
      }
    });
  }
  if (commandPaletteInput) {
    commandPaletteInput.addEventListener("input", () => loadGlobalSearch(commandPaletteInput.value || ""));
  }
  if (commandPaletteCloseBtn) {
    commandPaletteCloseBtn.addEventListener("click", closeCommandPalette);
  }
  if (commandPaletteResults) {
    commandPaletteResults.addEventListener("click", handleCommandPaletteResultsClick);
  }
  if (globalCommandPalette) {
    globalCommandPalette.addEventListener("click", (event) => {
      if (event.target === globalCommandPalette || event.target.classList.contains("command-palette-scrim")) {
        closeCommandPalette();
      }
    });
  }
  if (appNotificationsBtn) {
    appNotificationsBtn.addEventListener("click", () => toggleNotificationsTray());
  }
  if (appNotificationsCloseBtn) {
    appNotificationsCloseBtn.addEventListener("click", () => toggleNotificationsTray(false));
  }
  if (appNotificationsReadAllBtn) {
    appNotificationsReadAllBtn.addEventListener("click", handleAppNotificationsReadAll);
  }
  if (appNotificationsList) {
    appNotificationsList.addEventListener("click", handleAppNotificationsClick);
  }
  if (appNotificationsTray) {
    appNotificationsTray.addEventListener("click", (event) => {
      if (event.target === appNotificationsTray || event.target.classList.contains("notifications-tray-scrim")) {
        toggleNotificationsTray(false);
      }
    });
  }

  pnmForm.addEventListener("submit", handlePnmCreate);
  ratingForm.addEventListener("submit", handleRatingSave);
  photoForm.addEventListener("submit", handlePhotoUpload);
  if (rushEventForm) {
    rushEventForm.addEventListener("submit", handleRushEventCreate);
  }
  if (rushCalendarTable) {
    rushCalendarTable.addEventListener("click", handleRushCalendarTableClick);
  }
  if (weeklyGoalForm) {
    weeklyGoalForm.addEventListener("submit", handleWeeklyGoalCreate);
  }
  if (weeklyGoalsList) {
    weeklyGoalsList.addEventListener("click", handleWeeklyGoalsActionClick);
  }
  if (officerChatForm) {
    officerChatForm.addEventListener("submit", handleOfficerChatSubmit);
  }
  if (officerChatQuickTags) {
    officerChatQuickTags.addEventListener("click", handleOfficerChatQuickTagClick);
  }
  if (officerChatMessage) {
    officerChatMessage.addEventListener("keydown", handleOfficerChatMessageKeydown);
  }
  if (refreshInstagramPhotoBtn) {
    refreshInstagramPhotoBtn.addEventListener("click", handleRefreshInstagramPhoto);
  }

  pnmTable.addEventListener("click", handlePnmTableClick);
  if (pnmBoard) {
    pnmBoard.addEventListener("click", handlePnmTableClick);
    pnmBoard.addEventListener("click", handleWatchToggleClick);
  }
  pendingList.addEventListener("click", handlePendingClick);
  memberTable.addEventListener("click", handleMemberTableClick);
  adminPnmTable.addEventListener("click", handleAdminPanelClick);
  if (promoteOfficerBtn) {
    promoteOfficerBtn.addEventListener("click", handlePromoteOfficer);
  }
  if (adminPnmEditorForm) {
    adminPnmEditorForm.addEventListener("submit", handleAdminPnmEditorSubmit);
  }
  if (adminEditPnmSelect) {
    adminEditPnmSelect.addEventListener("change", (event) => {
      const nextId = Number(event.target.value || 0);
      if (!nextId) {
        return;
      }
      populateAdminPnmEditor(nextId);
    });
  }
  if (headAssignmentForm) {
    headAssignmentForm.addEventListener("submit", handleHeadAssignmentSubmit);
  }
  if (headAssignPnmSelect) {
    headAssignPnmSelect.addEventListener("change", () => {
      state.headAssignmentPnmId = Number(headAssignPnmSelect.value || 0) || null;
      syncHeadAssignmentSelection();
    });
  }
  if (headAssignClearBtn) {
    headAssignClearBtn.addEventListener("click", handleHeadAssignmentClear);
  }
  if (headAddAssigneeBtn) {
    headAddAssigneeBtn.addEventListener("click", handleHeadAddAssignee);
  }
  if (headAssigneeList) {
    headAssigneeList.addEventListener("click", handleHeadAssigneeListClick);
  }
  if (packagePartnerSelect) {
    packagePartnerSelect.addEventListener("change", () => {
      state.packagePartnerId = Number(packagePartnerSelect.value || 0) || null;
    });
  }
  if (packageLinkBtn) {
    packageLinkBtn.addEventListener("click", handlePackageDealLink);
  }
  if (packageUnlinkBtn) {
    packageUnlinkBtn.addEventListener("click", handlePackageDealUnlink);
  }
  if (assignedRushDownloadBtn) {
    assignedRushDownloadBtn.addEventListener("click", handleAssignedContactsDownload);
  }
  if (assignedRushTable) {
    assignedRushTable.addEventListener("click", handleAssignedRushTableClick);
  }
  if (sameStatePnmsList) {
    sameStatePnmsList.addEventListener("click", handleSameStatePnmsClick);
  }
  document.addEventListener("click", handleWatchToggleClick);
  document.addEventListener("click", (event) => {
    handleGlobalOpenPnmClick(event).catch(() => {});
  });
  document.addEventListener("click", handleCommandToolbarAction);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".app-menu")) {
      closeAppMenus();
    }
  });
  if (meetingsCompareSelectA) {
    meetingsCompareSelectA.addEventListener("change", (event) => handleMeetingsCompareChange("A", event.target.value));
  }
  if (meetingsCompareSelectB) {
    meetingsCompareSelectB.addEventListener("change", (event) => handleMeetingsCompareChange("B", event.target.value));
  }

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

  if (desktopPageNav) {
    desktopPageNav.addEventListener("click", (event) => {
      const link = event.target.closest(".desktop-page-link[data-page]");
      if (!link) {
        return;
      }
      setActiveDesktopPage((link.dataset.page || DEFAULT_DESKTOP_PAGE).toLowerCase(), false);
    });
  }

  window.addEventListener("popstate", () => {
    setActiveDesktopPage(currentRequestedDesktopPage(), false);
  });

  if (tutorialLayer) {
    tutorialLayer.addEventListener("click", (event) => {
      const target = event.target;
      if (target === tutorialLayer || (target && target.classList && target.classList.contains("tutorial-scrim"))) {
        closeTutorialOverlay();
      }
    });
  }
  if (tutorialModeCard) {
    tutorialModeCard.addEventListener("click", (event) => {
      const button = event.target.closest("[data-tutorial-mode]");
      if (!button) {
        return;
      }
      event.preventDefault();
      startTutorialMode(button.dataset.tutorialMode || TUTORIAL_MODE_GUIDED);
    });
  }
  if (tutorialModeSkipBtn) {
    tutorialModeSkipBtn.addEventListener("click", () => {
      closeTutorialOverlay();
      showToast("Tutorial skipped. Use Help → Open Tutorial any time.");
    });
  }
  if (tutorialPrevBtn) {
    tutorialPrevBtn.addEventListener("click", () => goTutorialStep(-1));
  }
  if (tutorialNextBtn) {
    tutorialNextBtn.addEventListener("click", () => {
      handleTutorialNext();
    });
  }
  if (tutorialCloseBtn) {
    tutorialCloseBtn.addEventListener("click", () => closeTutorialOverlay());
  }
  document.addEventListener("keydown", handleTutorialKeydown);
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommandPalette(globalSearchInput ? globalSearchInput.value : "");
    }
    if (event.key === "Escape") {
      closeCommandPalette();
      toggleNotificationsTray(false);
      closeTouchpointDrawer();
      closeAppMenus();
    }
  });
}

async function init() {
  setDefaultDates();
  applyRatingCriteriaUi();
  setRoleEmojiRequirement();
  initializePresetTagPickers();
  initializeFilterHintLists();
  syncFilterInputsFromState();
  syncOpenMeetingLink();
  attachEvents();
  setActiveDesktopPage(currentRequestedDesktopPage(), false);
  updateTopbarActions();
  renderWeeklyGoalMetricOptions();
  renderWeeklyGoalAssignedUsers();
  renderWeeklyGoals();
  renderNotifications();
  renderOfficerChat();
  renderOfficerChatStats();
  renderRushCalendar();
  setOperationsTab(state.viewPrefs.operationsTab || "timeline", false);
  setAdminTab(state.viewPrefs.adminTab || "leadership", false);
  renderPnmBoard();
  updateWorkspaceHeader();
  updateNotificationBell();
  setupPwaInstall();
  await ensureSession();
  showRouteNoticeFromQuery();
}

init();
