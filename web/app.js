const $ = (id) => document.getElementById(id);
const SVG_ICONS = {
  settings: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  power: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>`,
  refresh: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/></svg>`,
  start: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
  stop: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12"/></svg>`,
  eject: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V3m0 0L5 10m7-7l7 7M3 21h18"/></svg>`,
  bolt: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  plus: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>`,
};
const ICON_TEXT = (svg) => `<span class="icon-text" aria-hidden="true">${svg}</span>`;
let devices = [];
let deviceDiscoveryError = "";
const deviceStates = new Map();
const deviceErrors = new Map();
const runningPaths = new Set();
let quarantinedPaths = new Set();
let batchTotal = 0;
let batchDone = 0;
let autoStartTimer = null;
let currentCaseMedia = [];
let currentMediaId = null;
let currentDecision = null;
let currentIsPhone = false;
let confirmedOnlineSerials = new Set();
let devicePresenceInitialized = false;
let decisionQueueTimer = null;
let decisionQueueDeferred = false;
let returnToDecisionQueue = false;
let inventoryTreeMediaId = null;
let inventoryListState = null;
let mediaViewRevision = 0;
let inventoryViewRevision = 0;
let caseLoadRevision = 0;
const inventoryRequests = new WeakMap();
let caseHistorySignature = "";
let knownCases = [];
let activeCaseNumber = null;
let deleteTargetCaseNumber = null;
let activeOperator = "";
let profileKeywords = [];
let selectedKeywords = new Set();
let profileReady = false;
let availableProfiles = [];
const profileDetails = new Map();
const selectedByProfile = new Map();
let activeProfileIds = new Set();
let profilesInitialized = false;
let keywordDraft = [];
let draftSelectedKeywords = new Set();
let profileEditorId = "default";
let profileDetailId = null;
let profileDetailDraft = [];
let profileDetailSelected = new Set();
let profileDetailDirty = false;
let catalogState = null;
let catalogDefaults = null;
let catalogBusy = false;
let catalogDirty = false;
let settingsRevision = 0;
let cryptoState = null;
let bundledCryptoRules = { app_rules: [], file_rules: [], backup_rules: [] };
let cryptoDirty = false;
let cryptoBusy = false;
let detectionState = null;
let detectionDirty = false;
let detectionBusy = false;
let detectionSection = "crypto";
let detectionSelectedRuleId = null;
let detectionEditedRule = null;
let detectionDeletedRuleIds = new Set();
let detectionPendingEditorRule = null;
const detectionSectionLabels = {
  crypto: "KRYPTO-APPS",
  banking: "BANKING & FINANZEN",
  backups: "GERÄTE-BACKUPS",
  files: "DATEIHINWEISE",
};
const detectionKindForSection = {
  crypto: "app_rules",
  banking: "app_rules",
  backups: "backup_rules",
  files: "file_rules",
};

// Tooltip registry: maps help text to the trigger element and global tooltip layer.
let activeTooltipTrigger = null;
let activeTooltipText = "";

function showTooltip(trigger, text) {
  activeTooltipTrigger = trigger;
  activeTooltipText = text;
  const layer = $("settingsTooltipLayer");
  if (!layer) return;
  layer.textContent = text;
  layer.classList.add("visible");
  positionTooltip();
  layer.setAttribute("aria-hidden", "false");
}

function hideTooltip() {
  activeTooltipTrigger = null;
  activeTooltipText = "";
  const layer = $("settingsTooltipLayer");
  if (!layer) return;
  layer.classList.remove("visible");
  layer.setAttribute("aria-hidden", "true");
}

function positionTooltip() {
  const layer = $("settingsTooltipLayer");
  if (!layer || !activeTooltipTrigger) return;
  const rect = activeTooltipTrigger.getBoundingClientRect();
  const layerRect = layer.getBoundingClientRect();
  const margin = 8;
  let top = rect.top - layerRect.height - margin;
  let below = false;
  if (top < margin) {
    top = rect.bottom + margin;
    below = true;
  }
  let left = rect.left + rect.width / 2 - layerRect.width / 2;
  left = Math.max(margin, Math.min(left, window.innerWidth - layerRect.width - margin));
  layer.style.top = `${top}px`;
  layer.style.left = `${left}px`;
  layer.classList.toggle("tooltip-below", below);
}

function tooltip(text) {
  return `<button type="button" class="info-tooltip" aria-label="Hilfe" data-tooltip="${escapeHtml(text)}">?</button>`;
}

function initTooltips(root) {
  for (const trigger of root.querySelectorAll("[data-tooltip]")) {
    trigger.addEventListener("mouseenter", () => showTooltip(trigger, trigger.dataset.tooltip));
    trigger.addEventListener("mouseleave", hideTooltip);
    trigger.addEventListener("focus", () => showTooltip(trigger, trigger.dataset.tooltip));
    trigger.addEventListener("blur", hideTooltip);
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (activeTooltipTrigger === trigger) {
        hideTooltip();
      } else {
        showTooltip(trigger, trigger.dataset.tooltip);
      }
    });
  }
}
const appCategoryLabels = {
  wallet: "SELF-CUSTODY WALLETS", hardware_wallet: "HARDWARE-WALLETS",
  exchange: "KRYPTOBÖRSEN / BROKER", portfolio: "STEUER / PORTFOLIO",
  payment: "KRYPTO-ZAHLUNGSDIENSTE", market: "KURSE / MARKT",
  messenger: "MESSENGER", cloud: "CLOUDSPEICHER", banking: "BANKING / FINANZEN",
  other: "SONSTIGE APPS",
};
const cryptoCategories = new Set(["wallet", "hardware_wallet", "exchange", "portfolio", "payment", "market"]);
let updateState = { state: "unknown", message: "UPDATE NOCH NICHT GEPRÜFT" };
let updateActionInProgress = null;
const UPDATE_DIALOG_RESTORE_KEY = "triagebox-update-dialog";
let powerState = { state: "unknown", label: "STROMSTATUS UNBEKANNT" };
let pendingPowerAction = null;
let powerActionInProgress = false;
let serverActiveCase = null;
let caseSessionTransition = false;
let startOverlayReady = false;
const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
const rememberUpdateDialog = () => sessionStorage.setItem(UPDATE_DIALOG_RESTORE_KEY, "1");
const forgetUpdateDialog = () => sessionStorage.removeItem(UPDATE_DIALOG_RESTORE_KEY);
const isUpdateBusy = () => Boolean(updateActionInProgress) || ["checking", "installing"].includes(updateState.state);
const formatReleaseVersion = (value) => {
  const match = String(value || "").match(/^(\d+\.\d+\.\d+)a(\d+)$/);
  return match ? `v${match[1]}-alpha.${match[2]}` : String(value || "—");
};
const formatBytes = (bytes) => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes || 0), unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toLocaleString("de-AT", { maximumFractionDigits: 1 })} ${units[unit]}`;
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[char]));

function setSystemState(text, state = activeCaseNumber ? "ready" : "locked") {
  $("systemState").textContent = text;
  $("systemStatus").classList.remove("locked", "error", "busy");
  if (state !== "ready") $("systemStatus").classList.add(state);
}

function updateStartOverlay() {
  const overlay = $("startOverlay");
  if (!overlay) return;
  const hasCase = Boolean(activeCaseNumber || serverActiveCase?.case_number);
  if (hasCase) {
    startOverlayReady = true;
    overlay.hidden = true;
    return;
  }
  // Wait until the first server status has been loaded so the overlay does not
  // flash briefly when the page reloads with an active case on the server.
  overlay.hidden = !startOverlayReady;
}

function powerBlockedReason() {
  const activeCase = activeCaseNumber || serverActiveCase?.case_number;
  if (runningPaths.size) return "LAUFENDEN SCAN ZUERST ABSCHLIESSEN";
  if (updateActionInProgress || ["checking", "installing"].includes(updateState.state)) return "LAUFENDES UPDATE ZUERST ABSCHLIESSEN";
  if (activeCase) return `FALL ${activeCase} ZUERST BEENDEN`;
  return "";
}

function renderPowerState(value = {}) {
  powerState = { ...powerState, ...value };
  const state = ["ok", "warning", "danger"].includes(powerState.state) ? powerState.state : "unknown";
  const label = powerState.label || "STROMSTATUS UNBEKANNT";
  const health = $("powerHealth");
  health.className = `power-health ${state}`;
  health.hidden = !["warning", "danger"].includes(state);
  health.innerHTML = SVG_ICONS.bolt;
  health.title = state === "danger"
    ? `${label} · Stromversorgung jetzt prüfen`
    : `${label} · seit dem letzten Systemstart gespeichert`;
  health.setAttribute("aria-label", `Warnung Stromversorgung: ${health.title}`);
  const blocked = powerBlockedReason();
  for (const button of $("powerActions").querySelectorAll("button")) button.disabled = Boolean(blocked) || powerActionInProgress;
  if (!pendingPowerAction && !powerActionInProgress) $("powerMessage").textContent = blocked;
}

function openPowerDialog() {
  pendingPowerAction = null;
  $("powerConfirmation").hidden = true;
  $("powerActions").hidden = false;
  renderPowerState(powerState);
  if (!$("powerModal").open) $("powerModal").showModal();
}

function choosePowerAction(action) {
  const blocked = powerBlockedReason();
  if (blocked || powerActionInProgress) {
    $("powerMessage").textContent = blocked;
    return;
  }
  pendingPowerAction = action;
  const shutdown = action === "poweroff";
  $("powerConfirmation").classList.toggle("shutdown", shutdown);
  $("powerConfirmationText").textContent = shutdown
    ? "TRIAGE//BOX WIRKLICH HERUNTERFAHREN?"
    : "TRIAGE//BOX WIRKLICH NEU STARTEN?";
  $("confirmPowerAction").textContent = shutdown ? "JA, HERUNTERFAHREN" : "JA, NEU STARTEN";
  $("powerActions").hidden = true;
  $("powerConfirmation").hidden = false;
  $("powerMessage").textContent = "";
}

async function confirmPowerAction() {
  if (!pendingPowerAction || powerActionInProgress) return;
  const action = pendingPowerAction;
  powerActionInProgress = true;
  $("confirmPowerAction").disabled = true;
  $("cancelPowerAction").disabled = true;
  $("powerMessage").textContent = action === "poweroff"
    ? "SYSTEM WIRD SICHER HERUNTERGEFAHREN …"
    : "SYSTEM WIRD NEU GESTARTET …";
  try {
    const response = await fetch("/api/system/power", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Systemaktion nicht möglich");
    $("powerConfirmation").hidden = true;
    $("powerMessage").textContent = action === "poweroff"
      ? "HERUNTERFAHREN GESTARTET · NACH DEM ABSCHALTEN KANN DIE STROMVERSORGUNG GETRENNT WERDEN"
      : "NEUSTART GESTARTET · OBERFLÄCHE IST GLEICH KURZ NICHT ERREICHBAR";
  } catch (error) {
    powerActionInProgress = false;
    pendingPowerAction = null;
    $("confirmPowerAction").disabled = false;
    $("cancelPowerAction").disabled = false;
    $("powerConfirmation").hidden = true;
    $("powerActions").hidden = false;
    $("powerMessage").textContent = `FEHLER: ${error.message}`;
    renderPowerState(powerState);
  }
}

function renderUpdateState(value = {}) {
  updateState = { ...updateState, ...value };
  const state = updateState.state || "unknown";
  const available = updateState.available_version || "";
  const statusLabels = {
    current: "KEIN UPDATE VERFÜGBAR",
    installed: "UPDATE ERFOLGREICH INSTALLIERT",
    available: "UPDATE VERFÜGBAR",
    checking: "PRÜFUNG LÄUFT …",
    installing: "INSTALLATION LÄUFT …",
    unknown: "NOCH NICHT GEPRÜFT",
  };
  $("updateStatus").textContent = statusLabels[state] || updateState.message || "NOCH NICHT GEPRÜFT";
  $("updateCurrentVersion").textContent = formatReleaseVersion(updateState.current_version);
  $("systemVersion").textContent = formatReleaseVersion(updateState.current_version);
  $("updateCheckedAt").textContent = updateState.updated_at
    ? new Date(updateState.updated_at).toLocaleString("de-AT")
    : "—";
  $("updateSuccessNotice").hidden = state !== "installed";
  $("updateSuccessNotice").textContent = `✓ UPDATE ERFOLGREICH ABGESCHLOSSEN · ${formatReleaseVersion(updateState.current_version)}`;
  $("settingsUpdatesTab").classList.toggle("update-available", state === "available");
  $("updateInstall").hidden = state !== "available";
  $("updateInstall").textContent = available ? `${available.toUpperCase()} INSTALLIEREN` : "UPDATE INSTALLIEREN";
  const activeCase = activeCaseNumber || serverActiveCase?.case_number;
  const actionRunning = isUpdateBusy();
  $("updateModal").classList.toggle("update-busy", actionRunning);
  $("closeSettings").disabled = actionRunning || catalogBusy;
  $("updateProgress").hidden = !actionRunning;
  $("updateProgress").classList.toggle("checking", state === "checking");
  $("updateProgressLabel").textContent = state === "checking" ? "FREIGEGEBENE VERSION WIRD GEPRÜFT …"
    : updateActionInProgress === "offline" ? "PAKET WIRD ÜBERTRAGEN UND GEPRÜFT …" : "UPDATE WIRD VORBEREITET UND GETESTET …";
  $("updateInstall").disabled = Boolean(activeCase) || runningPaths.size > 0 || actionRunning || caseSessionTransition;
  $("updateStopCase").hidden = !activeCase && !caseSessionTransition;
  $("updateStopCase").disabled = runningPaths.size > 0 || actionRunning || caseSessionTransition;
  $("updateStopCase").textContent = caseSessionTransition ? "FALL WIRD BEENDET …" : `FALL ${activeCase || ""} BEENDEN`;
  $("updateCheck").disabled = actionRunning;
  $("offlineUpdateFile").disabled = Boolean(activeCase) || runningPaths.size > 0 || actionRunning || caseSessionTransition;
  $("offlineUpdateInstall").disabled = $("offlineUpdateFile").disabled || !$("offlineUpdateFile").files.length;
  if (["installed", "current"].includes(state) && $("offlineUpdateMessage").textContent.startsWith("FEHLER:")) {
    $("offlineUpdateMessage").textContent = "";
  }
  if (!updateActionInProgress) {
    if (caseSessionTransition) {
      $("updateActionMessage").textContent = "FALL WIRD BEENDET …";
    } else if (activeCase && runningPaths.size > 0) {
      $("updateActionMessage").textContent = "FALL KANN NACH ABSCHLUSS DES LAUFENDEN SCANS BEENDET WERDEN";
    } else if (state === "available" && activeCase) {
      $("updateActionMessage").textContent = `FALL ${activeCase} ZUERST BEENDEN`;
    } else if (state === "available" && runningPaths.size > 0) {
      $("updateActionMessage").textContent = "LAUFENDEN SCAN ZUERST ABSCHLIESSEN";
    } else {
      $("updateActionMessage").textContent = "";
    }
  }
}

async function waitForUpdateResult(action) {
  const startedAt = Date.now();
  const timeout = action === "check" ? 30000 : 15 * 60 * 1000;
  let workerObserved = false;
  while (Date.now() - startedAt < timeout) {
    await wait(action === "check" ? 700 : 1000);
    try {
      const response = await fetch("/api/updates", { cache: "no-store" });
      if (!response.ok) continue;
      const data = await response.json();
      const state = data.update?.state || "unknown";
      const workerRunning = Boolean(data.jobs?.[action]);
      const stateRunning = state === "checking" || state === "installing";
      workerObserved ||= workerRunning || stateRunning;
      if (workerRunning || stateRunning) {
        renderUpdateState(data.update || {});
        $("updateActionMessage").textContent = action === "check"
          ? "FREIGEGEBENE VERSION WIRD GEPRÜFT …"
          : "UPDATE WIRD SICHER VORBEREITET · DIENSTSTART ABWARTEN …";
        continue;
      }
      // systemctl starts asynchronously. Do not accept a stale previous result
      // before the worker has had a chance to write its new state.
      if (!workerObserved && Date.now() - startedAt < 2500) continue;
      renderUpdateState(data.update || {});
      $("updateActionMessage").textContent = "";
      return state;
    } catch (_) {
      // During installation the web service restarts briefly. Keep polling.
    }
  }
  throw new Error(action === "check"
    ? "PRÜFUNG DAUERT LÄNGER ALS 30 SEKUNDEN"
    : "INSTALLATION HAT INNERHALB VON 15 MINUTEN KEIN ERGEBNIS GELIEFERT");
}

async function requestUpdate(action) {
  if (updateActionInProgress || caseSessionTransition) return;
  const activeCase = activeCaseNumber || serverActiveCase?.case_number;
  if (action === "install" && activeCase) {
    $("updateActionMessage").textContent = `FALL ${activeCase} ZUERST BEENDEN`;
    return;
  }
  if (action === "install" && runningPaths.size > 0) {
    $("updateActionMessage").textContent = "LAUFENDEN SCAN ZUERST ABSCHLIESSEN";
    return;
  }
  if (action === "install" && !window.confirm("Update jetzt installieren? Der Dienst wird kurz neu gestartet.")) return;
  if (action === "install") rememberUpdateDialog();
  const previousUpdateState = { ...updateState };
  updateActionInProgress = action;
  renderUpdateState({
    state: action === "check" ? "checking" : "installing",
    message: action === "check" ? "UPDATE WIRD GEPRÜFT" : "UPDATE WIRD VORBEREITET",
  });
  $("updateActionMessage").textContent = action === "check"
    ? "PRÜFUNG WIRD GESTARTET …"
    : "INSTALLATION WIRD GESTARTET …";
  try {
    const response = await fetch(`/api/updates/${action}`, { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Update-Aktion nicht möglich");
    const result = await waitForUpdateResult(action);
    if (action === "install" && result === "installed") {
      $("updateActionMessage").textContent = "UPDATE INSTALLIERT · OBERFLÄCHE WIRD NEU GELADEN …";
      await wait(1000);
      window.location.reload();
    }
  } catch (error) {
    if (action === "install") forgetUpdateDialog();
    renderUpdateState(previousUpdateState);
    $("updateActionMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    updateActionInProgress = null;
    renderUpdateState(updateState);
  }
}

function uploadOfflinePackage(file) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/updates/offline");
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
      $("offlineUpdateMessage").textContent = `PAKET WIRD ÜBERTRAGEN · ${percent} %`;
      $("updateProgressLabel").textContent = `PAKET WIRD ÜBERTRAGEN · ${percent} %`;
    });
    request.addEventListener("load", () => {
      let data = {};
      try { data = JSON.parse(request.responseText || "{}"); } catch (_) { /* handled below */ }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(data.error || `UPLOAD FEHLGESCHLAGEN (${request.status})`));
      } else {
        resolve(data);
      }
    });
    request.addEventListener("error", () => reject(new Error("VERBINDUNG BEIM UPLOAD UNTERBROCHEN")));
    request.addEventListener("abort", () => reject(new Error("UPLOAD ABGEBROCHEN")));
    request.send(file);
  });
}

async function installOfflineUpdate() {
  if (updateActionInProgress || caseSessionTransition) return;
  const file = $("offlineUpdateFile").files[0];
  const activeCase = activeCaseNumber || serverActiveCase?.case_number;
  if (!file) return;
  if (activeCase) { $("offlineUpdateMessage").textContent = `FALL ${activeCase} ZUERST BEENDEN`; return; }
  if (runningPaths.size) { $("offlineUpdateMessage").textContent = "LAUFENDEN SCAN ZUERST ABSCHLIESSEN"; return; }
  if (!file.name.toLowerCase().endsWith(".tbu")) {
    $("offlineUpdateMessage").textContent = "BITTE EIN .TBU-UPDATEPAKET AUSWÄHLEN";
    return;
  }
  if (!window.confirm("Signiertes Offline-Update hochladen und installieren? Der Dienst wird kurz neu gestartet.")) return;
  rememberUpdateDialog();
  const previousUpdateState = { ...updateState };
  updateActionInProgress = "offline";
  renderUpdateState({ state: "installing", message: "OFFLINE-UPDATE WIRD ÜBERTRAGEN" });
  $("offlineUpdateMessage").textContent = "PAKET WIRD ÜBERTRAGEN · 0 %";
  try {
    await uploadOfflinePackage(file);
    $("offlineUpdateMessage").textContent = "SIGNATUR, VERSION UND SELBSTTEST WERDEN GEPRÜFT …";
    const result = await waitForUpdateResult("offline");
    if (result !== "installed") throw new Error(updateState.message || "OFFLINE-UPDATE NICHT INSTALLIERT");
    $("offlineUpdateMessage").textContent = "OFFLINE-UPDATE INSTALLIERT · OBERFLÄCHE WIRD NEU GELADEN …";
    await wait(1000);
    window.location.reload();
  } catch (error) {
    forgetUpdateDialog();
    renderUpdateState(previousUpdateState);
    $("offlineUpdateMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    updateActionInProgress = null;
    renderUpdateState(updateState);
  }
}

function openAuftrag() {
  if (!$("auftragModal").open) $("auftragModal").showModal();
}

const nestedAuftragDialogs = ["caseArchiveModal", "deleteModal"];

function syncAuftragBackdrop() {
  const nestedOpen = nestedAuftragDialogs.some((id) => $(id).open);
  $("auftragModal").classList.toggle("nested-open", $("auftragModal").open && nestedOpen);
  $("caseArchiveModal").classList.toggle("nested-open", $("caseArchiveModal").open && $("deleteModal").open);
  $("settingsModal").classList.toggle("nested-open", false);
}

function openNestedAuftragDialog(id) {
  const dialog = $(id);
  if (!dialog.open) dialog.showModal();
  syncAuftragBackdrop();
}

function updateKeywordSummary() {
  const uniqueKeywords = (values) => {
    const seen = new Set();
    return values.filter((value) => {
      const key = value.toLocaleLowerCase("de");
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  profileKeywords = uniqueKeywords([...activeProfileIds].flatMap((id) => profileDetails.get(id)?.keywords || []));
  selectedKeywords = new Set(uniqueKeywords([...activeProfileIds].flatMap((id) => [...(selectedByProfile.get(id) || new Set(profileDetails.get(id)?.keywords || []))])));
  $("keywordSelectionCount").textContent = `${selectedKeywords.size} AKTIV`;
  $("dockKeywordCount").textContent = `${selectedKeywords.size} STICHWÖRTER`;
  const names = [...activeProfileIds].map((id) => profileDetails.get(id)?.name).filter(Boolean);
  $("dockProfiles").textContent = names.length ? names.join(" + ").toUpperCase() : "KEIN SUCHPROFIL";
}

function renderKeywordOptions(container = $("profileDetailOptions")) {
  if (!container) return;
  container.innerHTML = keywordDraft.map((keyword) => `<label class="keyword-option">
    <input type="checkbox" value="${escapeHtml(keyword)}" ${draftSelectedKeywords.has(keyword) ? "checked" : ""} />
    <span>${escapeHtml(keyword.toUpperCase())}</span>
    <button class="keyword-remove" type="button" data-remove-keyword="${escapeHtml(keyword)}" aria-label="${escapeHtml(keyword)} entfernen">×</button>
  </label>`).join("");
}

function updateProfileDetailCount() {
  const count = keywordDraft.length;
  $("profileDetailCount").textContent = `${count} STICHWORT${count === 1 ? "" : "ER"}`;
}

function renderProfileList() {
  $("profileList").innerHTML = availableProfiles.map((profile) => `<label class="profile-list-item">
    <input type="checkbox" value="${escapeHtml(profile.id)}" ${activeProfileIds.has(profile.id) ? "checked" : ""} />
    <span class="profile-list-copy"><strong>${escapeHtml(profile.name.toUpperCase())}</strong><small>V${escapeHtml(profile.version)} · ${Number(profile.keyword_count)} STICHWÖRTER</small></span>
  </label>`).join("");
  $("settingsProfilesList").innerHTML = availableProfiles.map((profile) => {
    const selected = profileDetailId && profile.id === profileDetailId;
    return `<button type="button" class="settings-profile-row${selected ? " selected" : ""}" data-select-profile="${escapeHtml(profile.id)}">
      <span class="profile-row-name">${escapeHtml(profile.name)}</span>
      <span class="profile-row-meta">${Number(profile.keyword_count)}</span>
      <span class="profile-row-meta profile-row-version">${escapeHtml(profile.version)}</span>
    </button>`;
  }).join("") || '<p class="settings-empty-row">Noch keine Profile vorhanden.</p>';
}

function selectSettingsPane(pane = "profiles") {
  for (const name of ["Profiles", "Filetypes", "Crypto", "Updates"]) {
    const active = name.toLowerCase() === pane.toLowerCase();
    $(`settings${name}Pane`).hidden = !active;
    $(`settings${name}Tab`).setAttribute("aria-pressed", String(active));
  }
}

async function openSettings(initialPane = "profiles") {
  if ($("auftragModal").open) $("auftragModal").close();
  if (!$("settingsModal").open) $("settingsModal").showModal();
  selectSettingsPane(initialPane);
  resetProfileDetail();
  const revision = ++settingsRevision;
  catalogState = null; catalogDirty = false;
  $("catalogRows").innerHTML = "";
  $("catalogSave").disabled = true;
  $("catalogReset").disabled = true;
  $("catalogAddCategory").disabled = true;
  $("catalogMessage").textContent = "DATEITYPEN WERDEN GELADEN …";
  $("detectionMessage").textContent = "REGELN WERDEN GELADEN …";
  loadProfiles();
  loadDetectionRules(revision);
  try {
    const response = await fetch("/api/settings/filetypes");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Katalog nicht verfügbar");
    if (revision !== settingsRevision || !$("settingsModal").open) return;
    catalogState = data.catalog; catalogDefaults = data.defaults;
    $("catalogSearch").value = "";
    renderCatalog(catalogState.categories);
    $("catalogVersion").textContent = `KATALOG V${catalogState.version}`;
    $("catalogMessage").textContent = "";
    $("catalogReset").disabled = false;
    $("catalogAddCategory").disabled = false;
  } catch (error) {
    if (revision === settingsRevision) $("catalogMessage").textContent = `FEHLER: ${error.message}`;
  }
}

function renderCatalog(categories) {
  $("catalogRows").innerHTML = Object.entries(categories).map(([name, extensions], index) => `<div class="catalog-row" data-category="${escapeHtml(name)}">
    <div class="catalog-category"><label for="catalogExtensions${index}">${escapeHtml(name)}<small>${extensions.length} Endungen</small></label><button type="button" class="catalog-remove" aria-label="Kategorie ${escapeHtml(name)} entfernen">×</button></div>
    <textarea id="catalogExtensions${index}" aria-label="Endungen für ${escapeHtml(name)}" rows="2" spellcheck="false">${escapeHtml(extensions.join(", "))}</textarea>
  </div>`).join("");
  filterCatalog();
}

function catalogDraft() {
  return Object.fromEntries([...$("catalogRows").querySelectorAll(".catalog-row")].map(row => [row.dataset.category,
    row.querySelector("textarea").value.split(/[,;\s]+/).map(value => value.replace(/^\./, "").toLowerCase()).filter(Boolean)]));
}

function filterCatalog() {
  const search = $("catalogSearch").value.trim().toLocaleLowerCase("de").replace(/^\./, "");
  for (const row of $("catalogRows").children) {
    row.hidden = !`${row.dataset.category} ${row.querySelector("textarea").value}`.toLocaleLowerCase("de").includes(search);
  }
}

function markCatalogDirty() {
  catalogDirty = true;
  $("catalogSave").disabled = catalogBusy || !catalogState;
  $("catalogMessage").textContent = "UNGESPEICHERTE ÄNDERUNGEN";
}

async function saveCatalog() {
  if (!catalogState || catalogBusy) return;
  const categories = catalogDraft();
  catalogBusy = true;
  $("catalogSave").disabled = true;
  $("closeSettings").disabled = true;
  for (const element of $("settingsFiletypesPane").querySelectorAll("input, textarea, button")) element.disabled = true;
  $("catalogMessage").textContent = "KATALOG WIRD GESPEICHERT …";
  try {
    const response = await fetch("/api/settings/filetypes", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categories, base_sha256: catalogState.sha256 }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Speichern fehlgeschlagen");
    catalogState = data.catalog; catalogDirty = false;
    renderCatalog(catalogState.categories);
    $("catalogVersion").textContent = `KATALOG V${catalogState.version}`;
    $("catalogMessage").textContent = "GESPEICHERT · GILT FÜR NEUE SCANS";
  } catch (error) {
    $("catalogMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    catalogBusy = false;
    $("closeSettings").disabled = isUpdateBusy();
    for (const element of $("settingsFiletypesPane").querySelectorAll("input, textarea, button")) element.disabled = false;
    $("catalogSave").disabled = !catalogDirty;
  }
}

function splitList(value) {
  return String(value || "").split(/[,;\n]+/).map(item => item.trim()).filter(Boolean);
}

function joinList(value) {
  return (value || []).join(", ");
}

function platformIdStatus(rule, platform, ids) {
  const stored = rule[`${platform}_id_status`];
  if (["verified", "unverified", "not_applicable"].includes(stored)) return stored;
  return ids.length && rule.verified ? "verified" : "unverified";
}

function platformStatusTooltip(rule, platform, ids, status) {
  const label = platform === "ios" ? "IOS" : "ANDROID";
  const idLabel = platform === "ios" ? "Bundle-ID" : "Package-ID";
  const note = rule[`${platform}_id_note`] ? `\n\nNotiz: ${rule[`${platform}_id_note`]}` : "";
  if (status === "verified") {
    const source = rule.source ? `\nQuelle: ${rule.source}` : "";
    const checked = rule.last_verified ? `\nGeprüft: ${rule.last_verified.split("-").reverse().join(".")}` : "";
    return `${label} · ID VERIFIZIERT\n\n${idLabel}:\n${ids.join("\n")}${source}${checked}${note}`;
  }
  if (status === "not_applicable") {
    return `${label} · NICHT ANWENDBAR\n\nFür diese Regel ist keine ${label === "IOS" ? "iOS" : "Android"}-App vorgesehen.${note}`;
  }
  return `${label} · ID NICHT VERIFIZIERT\n\nFür diese App ist derzeit keine verlässlich geprüfte ${platform === "ios" ? "iOS Bundle-ID" : "Android Package-ID"} im Katalog hinterlegt.\n\nDas bedeutet nicht, dass keine ${platform === "ios" ? "iOS" : "Android"}-App existiert. Erkennung erfolgt derzeit über Name/Alias, soweit die Regel dies vorsieht.${note}`;
}

function platformStatusSymbol(status) {
  return status === "verified" ? "✓" : status === "not_applicable" ? "—" : "?";
}

function platformStatusLabel(status) {
  return status === "verified" ? "ID verifiziert" : status === "not_applicable" ? "nicht anwendbar" : "ID noch nicht verifiziert";
}

function platformStatusEditor(rule, platform, ids) {
  const isIos = platform === "ios";
  const status = platformIdStatus(rule, platform, ids);
  const idLabel = isIos ? "IOS BUNDLE-IDS" : "ANDROID PACKAGE-IDS";
  const idField = isIos ? "ios_bundle_ids" : "android_package_ids";
  const idHelp = isIos
    ? "Eindeutige technische Kennung einer iPhone-/iPad-App. Nur aus überprüfbarer Quelle übernehmen."
    : "Eindeutige technische Kennung einer Android-App. Im offiziellen Google-Play-Eintrag häufig in der URL hinter id=. Nicht raten.";
  const statusText = status === "verified" ? "ID VERIFIZIERT" : status === "not_applicable" ? "NICHT ANWENDBAR" : "ID NOCH NICHT VERIFIZIERT";
  const explanation = status === "verified"
    ? `Technische ${isIos ? "Bundle" : "Package"}-ID ist anhand der angegebenen Quelle geprüft.`
    : status === "not_applicable"
      ? "Nur wählen, wenn zuverlässig belegt ist, dass diese Regel für die Plattform nicht zutrifft."
      : `Für diese Plattform ist derzeit keine verlässlich geprüfte ${isIos ? "Bundle" : "Package"}-ID hinterlegt. Das bedeutet nicht, dass dort keine App existiert.`;
  return `<section class="platform-id-editor" data-platform="${platform}">
    <label>${idLabel}${tooltip(idHelp)}<textarea data-field="${idField}" data-platform-ids="${platform}" rows="2" spellcheck="false">${escapeHtml(joinList(ids))}</textarea></label>
    <label>PLATTFORMSTATUS<select data-field="${platform}_id_status">
      <option value="verified" ${status === "verified" ? "selected" : ""}>VERIFIZIERT</option>
      <option value="unverified" ${status === "unverified" ? "selected" : ""}>NOCH NICHT VERIFIZIERT</option>
      <option value="not_applicable" ${status === "not_applicable" ? "selected" : ""}>NICHT ANWENDBAR</option>
    </select></label>
    <p class="platform-id-explanation"><strong>STATUS: ${statusText}</strong>${escapeHtml(explanation)}</p>
    <label class="platform-id-note">PLATTFORMSPEZIFISCHE NOTIZ<textarea data-field="${platform}_id_note" rows="2" maxlength="500" spellcheck="false">${escapeHtml(rule[`${platform}_id_note`] || "")}</textarea></label>
  </section>`;
}

function selectDetectionSection(section) {
  detectionSection = section;
  for (const [key, label] of Object.entries(detectionSectionLabels)) {
    const tab = $(`detection${key[0].toUpperCase()}${key.slice(1)}Tab`);
    if (tab) tab.setAttribute("aria-pressed", String(key === section));
  }
  detectionSelectedRuleId = null;
  detectionEditedRule = null;
  renderDetectionRules();
}

function rulesForSection() {
  if (!detectionState) return [];
  const kind = detectionKindForSection[detectionSection];
  let rules = detectionState[kind] || [];
  if (detectionSection === "crypto") {
    rules = rules.filter(rule => cryptoCategories.has(rule.category));
  } else if (detectionSection === "banking") {
    rules = rules.filter(rule => rule.category === "banking" || rule.category === "messenger" || rule.category === "cloud");
  }
  return rules;
}

function filterDetectionRules() {
  const query = $("detectionSearch").value.trim().toLocaleLowerCase("de");
  const filter = $("detectionFilter").value;
  const rows = $("detectionRows");
  if (!rows) return;
  let visible = 0;
  for (const row of rows.children) {
    const rule = row.dataset;
    const haystack = `${rule.name} ${rule.category} ${rule.aliases} ${rule.ios} ${rule.android}`.toLocaleLowerCase("de");
    const matchesQuery = !query || haystack.includes(query);
    let matchesFilter = true;
    if (filter === "active") matchesFilter = rule.enabled === "true";
    if (filter === "inactive") matchesFilter = rule.enabled === "false";
    if (filter === "legacy") matchesFilter = rule.status === "legacy";
    if (filter === "verified") matchesFilter = rule.verified === "true";
    if (filter === "unverified") matchesFilter = rule.verified === "false";
    if (filter === "missing_ios") matchesFilter = rule.ios === "";
    if (filter === "missing_android") matchesFilter = rule.android === "";
    row.hidden = !(matchesQuery && matchesFilter);
    if (!row.hidden) visible += 1;
  }
  $("detectionCount").textContent = `${visible} REGELN`;
}

function sortDetectionRules() {
  const sort = $("detectionSort").value;
  const rows = $("detectionRows");
  if (!rows) return;
  const items = [...rows.children];
  items.sort((a, b) => {
    if (sort === "name") return (a.dataset.name || "").localeCompare(b.dataset.name || "", "de", { sensitivity: "base" });
    if (sort === "category") return (a.dataset.category || "").localeCompare(b.dataset.category || "", "de");
    if (sort === "status") return (a.dataset.status || "").localeCompare(b.dataset.status || "");
    return 0;
  });
  rows.append(...items);
}

function renderDetectionStats() {
  if (!detectionState) return;
  const total = (detectionState.app_rules?.length || 0) + (detectionState.file_rules?.length || 0) + (detectionState.backup_rules?.length || 0);
  const defaults = bundledCryptoRules;
  const defaultIds = new Set(defaults ? [
    ...defaults.app_rules.map(r => r.id),
    ...defaults.file_rules.map(r => r.id),
    ...defaults.backup_rules.map(r => r.id),
  ] : []);
  const ownRules = total - [...defaultIds].filter(id =>
    detectionState.app_rules?.some(r => r.id === id) ||
    detectionState.file_rules?.some(r => r.id === id) ||
    detectionState.backup_rules?.some(r => r.id === id)
  ).length;
  const changed = [...(detectionState.app_rules || []), ...(detectionState.file_rules || []), ...(detectionState.backup_rules || [])]
    .filter(rule => defaultIds.has(rule.id)).length;
  $("detectionStats").textContent = `GESAMT ${total} · STANDARD ${defaultIds.size} · EIGEN ${Math.max(0, ownRules)}`;
}

function renderDetectionRules() {
  if (!detectionState) return;
  $("detectionVersion").textContent = `REGELSTAND V${detectionState.version}`;
  renderDetectionStats();
  const rules = rulesForSection();
  const kind = detectionKindForSection[detectionSection];
  $("detectionRows").innerHTML = rules.map(rule => {
    const isApp = kind === "app_rules";
    const iosIds = isApp ? (rule.ios_bundle_ids?.length ? rule.ios_bundle_ids : rule.bundle_ids || []) : [];
    const androidIds = isApp ? (rule.android_package_ids || []) : [];
    const iosStatus = isApp ? platformIdStatus(rule, "ios", iosIds) : "";
    const androidStatus = isApp ? platformIdStatus(rule, "android", androidIds) : "";
    const category = appCategoryLabels[rule.category] || rule.category || "—";
    const statusClass = rule.status === "legacy" ? "status-legacy" : "status-active";
    const statusText = rule.status === "legacy" ? "LEGACY" : (rule.enabled ? "AKTIV" : "INAKTIV");
    return `<tr data-id="${escapeHtml(rule.id)}" data-name="${escapeHtml(rule.name)}" data-category="${escapeHtml(category)}" data-status="${escapeHtml(rule.status || "active")}" data-enabled="${rule.enabled}" data-verified="${rule.verified || false}" data-ios="${escapeHtml(isApp ? (iosIds.join(",") || "") : "")}" data-android="${escapeHtml(isApp ? (androidIds.join(",") || "") : "")}" data-aliases="${escapeHtml((rule.aliases || []).concat(rule.former_names || []).join(","))}">
      <td>${escapeHtml(rule.name || rule.id)}</td>
      <td>${escapeHtml(category)}</td>
      <td class="platform-status-cell">${isApp ? `<button type="button" class="platform-id-status info-tooltip status-${iosStatus}" aria-label="iOS: ${platformStatusLabel(iosStatus)}" data-tooltip="${escapeHtml(platformStatusTooltip(rule, "ios", iosIds, iosStatus))}">${platformStatusSymbol(iosStatus)}</button>` : ""}</td>
      <td class="platform-status-cell">${isApp ? `<button type="button" class="platform-id-status info-tooltip status-${androidStatus}" aria-label="Android: ${platformStatusLabel(androidStatus)}" data-tooltip="${escapeHtml(platformStatusTooltip(rule, "android", androidIds, androidStatus))}">${platformStatusSymbol(androidStatus)}</button>` : ""}</td>
      <td class="${statusClass}">${escapeHtml(statusText)}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="5" class="iphone-empty">KEINE REGELN IN DIESEM BEREICH</td></tr>`;
  initTooltips($("detectionRows"));
  filterDetectionRules();
  sortDetectionRules();
  $("detectionRows").querySelectorAll("tr").forEach(row => row.classList.toggle("active", row.dataset.id === detectionSelectedRuleId));
  renderDetectionEditor();
}

function getRuleById(id) {
  for (const kind of ["app_rules", "file_rules", "backup_rules"]) {
    const found = detectionState[kind]?.find(rule => rule.id === id);
    if (found) return { rule: found, kind };
  }
  return null;
}

function cloneRule(rule) {
  return JSON.parse(JSON.stringify(rule));
}

function renderDetectionEditor() {
  const empty = $("detectionEditorEmpty");
  const form = $("detectionEditorForm");
  if (!empty || !form) return;
  if (!detectionEditedRule) {
    empty.hidden = false;
    form.hidden = true;
    return;
  }
  const rule = detectionEditedRule;
  const kind = detectionKindForSection[detectionSection];
  const isApp = kind === "app_rules";
  const isFile = kind === "file_rules";
  const isBackup = kind === "backup_rules";
  $("detectionEditorTitle").textContent = rule.id ? rule.name || rule.id : "NEUE REGEL";
  let fields = `
    <div class="field-row">
      <label>REGEL-ID${tooltip("Eindeutige interne Kennung: Kleinbuchstaben, Zahlen, Bindestrich, Unterstrich. Wird in Scan-Nachweisen protokolliert.")}<input data-field="id" value="${escapeHtml(rule.id || "")}" autocomplete="off" spellcheck="false" /></label>
      <label>NAME${tooltip("Anzeigename der Regel. Bei App-Regeln ist dies der exakte App-Name, über den ebenfalls erkannt wird.")}<input data-field="name" value="${escapeHtml(rule.name || "")}" autocomplete="off" spellcheck="false" /></label>
    </div>
  `;
  if (isApp || isFile) {
    fields += `<div class="field-row">
      <label>KATEGORIE${tooltip("Kategorie des Treffers. Banking, Messenger und Cloud sind immer neutral und erzeugen keinen Krypto-Hinweis.")}<select data-field="category">${Object.entries(appCategoryLabels).filter(([id]) => id !== "other").map(([id, label]) => `<option value="${id}" ${rule.category === id ? "selected" : ""}>${label}</option>`).join("")}</select></label>
      <label>HINWEISSTÄRKE${tooltip("HOCH = Wallet/Börse; MITTEL = Portfolio/Steuer/Zahlung; NIEDRIG = vage Hinweise; NEUTRAL = kein Krypto-Hinweis.")}<select data-field="relevance">${[["high","HOCH"],["medium","MITTEL"],["low","NIEDRIG"],["neutral","NEUTRAL"]].map(([id,label])=>`<option value="${id}" ${rule.relevance===id?"selected":""}>${label}</option>`).join("")}</select></label>
    </div>`;
  }
  if (isApp) {
    const iosIds = rule.ios_bundle_ids || rule.bundle_ids || [];
    const androidIds = rule.android_package_ids || [];
    fields += `
      ${platformStatusEditor(rule, "ios", iosIds)}
      ${platformStatusEditor(rule, "android", androidIds)}
      <label>ALIASSE${tooltip("Alternativer oder früherer Name derselben App. Beispiel: Xumm als früherer Name von Xaman. Quelle: Herstellerseite, Store oder dokumentierte Umbenennung.")}<textarea data-field="aliases" rows="2" spellcheck="false">${escapeHtml(joinList(rule.aliases))}</textarea></label>
      <label>FRÜHERE NAMEN${tooltip("Ehemalige Markennamen derselben App, z. B. BitKeep vor der Umbenennung in Bitget Wallet.")}<textarea data-field="former_names" rows="2" spellcheck="false">${escapeHtml(joinList(rule.former_names))}</textarea></label>
      <label>VORSICHTIGE SUCHBEGRIFFE${tooltip("Zusätzlicher Begriff für eine vorsichtige Erkennung, falls keine eindeutige App-ID greift. Beispiel: metamask. Unscharfe Suchbegriffe können Fehlalarme erzeugen.")}<textarea data-field="terms" rows="2" spellcheck="false">${escapeHtml(joinList(rule.terms))}</textarea></label>
      <div class="field-row">
        <label>STATUS<select data-field="status">${[["active","AKTIV"],["legacy","LEGACY"]].map(([id,label])=>`<option value="${id}" ${(rule.status||"active")===id?"selected":""}>${label}</option>`).join("")}</select></label>
        <label class="checkbox-row"><input data-field="enabled" type="checkbox" ${rule.enabled ? "checked" : ""} /> AKTIV ${tooltip("Nur aktive Regeln werden für neue Scans verwendet.")}</label>
      </div>
      <label>QUELLE DER ID-PRÜFUNG<input data-field="source" value="${escapeHtml(rule.source || "")}" autocomplete="off" /></label>
      <div class="field-row">
        <label>PRÜFDATUM (YYYY-MM-DD)<input data-field="last_verified" value="${escapeHtml(rule.last_verified || "")}" autocomplete="off" /></label>
        <label>REGIONEN (kommagetrennt, z. B. AT,DE)<input data-field="regions" value="${escapeHtml(joinList(rule.regions))}" autocomplete="off" /></label>
      </div>
    `;
  } else if (isFile) {
    fields += `
      <label>EXAKTE DATEINAMEN${tooltip("Dateinamen, die exakt so vorkommen müssen.")}<textarea data-field="filename_equals" rows="2" spellcheck="false">${escapeHtml(joinList(rule.filename_equals))}</textarea></label>
      <label>BEGRIFFE IN NAME / PFAD${tooltip("Begriffe, die im Datei- oder Ordnerpfad vorkommen müssen.")}<textarea data-field="terms" rows="2" spellcheck="false">${escapeHtml(joinList(rule.terms))}</textarea></label>
      <label>ZUSÄTZLICHER KONTEXT (ODER)${tooltip("Wenn angegeben, muss mindestens einer dieser Begriffe ebenfalls im Pfad vorkommen.")}<textarea data-field="context_terms" rows="2" spellcheck="false">${escapeHtml(joinList(rule.context_terms))}</textarea></label>
      <label>ENDUNGEN (LEER = BELIEBIG)${tooltip("Auf diese Endungen einschränken. Leer lassen, um alle Endungen zu prüfen.")}<textarea data-field="extensions" rows="2" spellcheck="false">${escapeHtml(joinList(rule.extensions))}</textarea></label>
      <div class="field-row">
        <label>STATUS<select data-field="status">${[["active","AKTIV"],["legacy","LEGACY"]].map(([id,label])=>`<option value="${id}" ${(rule.status||"active")===id?"selected":""}>${label}</option>`).join("")}</select></label>
        <label class="checkbox-row"><input data-field="enabled" type="checkbox" ${rule.enabled ? "checked" : ""} /> AKTIV</label>
      </div>
    `;
  } else if (isBackup) {
    fields += `
      <label>PLATTFORM${tooltip("Betriebssystem oder Hersteller, auf den sich die Regel bezieht.")}<input data-field="platform" value="${escapeHtml(rule.platform || "")}" autocomplete="off" /></label>
      <label>ERKENNUNGSSICHERHEIT<select data-field="confidence">${[["high","HOCH"],["medium","MITTEL"],["low","NIEDRIG"]].map(([id,label])=>`<option value="${id}" ${(rule.confidence||"medium")===id?"selected":""}>${label}</option>`).join("")}</select></label>
      <label>ERFORDERLICHE PFADE / ORDNER${tooltip("Pfad-Merkmale, die zusammen auftreten müssen. Beispiel: MobileSync/Backup.")}<textarea data-field="required_paths" rows="2" spellcheck="false">${escapeHtml(joinList(rule.required_paths))}</textarea></label>
      <label>ERFORDERLICHE DATEIEN${tooltip("Dateinamen, deren Vorhandensein die Erkennung stützt. Beispiel: Manifest.db, Info.plist.")}<textarea data-field="required_files" rows="2" spellcheck="false">${escapeHtml(joinList(rule.required_files))}</textarea></label>
      <label>ERFORDERLICHE ENDUNGEN${tooltip("Dateiendungen, die zusätzlich vorkommen müssen.")}<textarea data-field="required_extensions" rows="2" spellcheck="false">${escapeHtml(joinList(rule.required_extensions))}</textarea></label>
      <label>TYPISCHE PFADE${tooltip("Beispielpfade zur Orientierung; werden nicht direkt geprüft.")}<textarea data-field="typical_paths" rows="2" spellcheck="false">${escapeHtml(joinList(rule.typical_paths))}</textarea></label>
      <div class="field-row">
        <label>STATUS<select data-field="status">${[["active","AKTIV"],["legacy","LEGACY"]].map(([id,label])=>`<option value="${id}" ${(rule.status||"active")===id?"selected":""}>${label}</option>`).join("")}</select></label>
        <label class="checkbox-row"><input data-field="enabled" type="checkbox" ${rule.enabled ? "checked" : ""} /> AKTIV</label>
      </div>
      <div class="field-row">
        <label>QUELLE<input data-field="source" value="${escapeHtml(rule.source || "")}" autocomplete="off" /></label>
        <label>PRÜFDATUM (YYYY-MM-DD)<input data-field="last_verified" value="${escapeHtml(rule.last_verified || "")}" autocomplete="off" /></label>
      </div>
    `;
  }
  fields += `<label>KOMMENTAR<textarea data-field="comment" rows="2" spellcheck="false">${escapeHtml(rule.comment || "")}</textarea></label>`;
  $("detectionEditorFields").innerHTML = fields;
  initTooltips($("detectionEditorFields"));
  empty.hidden = true;
  form.hidden = false;
  $("detectionApply").disabled = false;
  $("detectionEditorMessage").textContent = "";
}

function readDetectionEditor() {
  if (!detectionEditedRule) return null;
  const rule = { ...detectionEditedRule };
  const kind = detectionKindForSection[detectionSection];
  for (const element of $("detectionEditorFields").querySelectorAll("[data-field]")) {
    const key = element.dataset.field;
    const isCheckbox = element.type === "checkbox";
    const value = isCheckbox ? element.checked : element.value;
    const listFields = ["ios_bundle_ids", "android_package_ids", "aliases", "former_names", "terms", "filename_equals", "context_terms", "extensions", "required_paths", "required_files", "required_extensions", "typical_paths", "regions"];
    if (listFields.includes(key)) {
      rule[key] = splitList(value);
    } else if (["enabled", "verified"].includes(key)) {
      rule[key] = Boolean(value);
    } else {
      rule[key] = value;
    }
  }
  if (kind === "app_rules") {
    rule.bundle_ids = rule.ios_bundle_ids;
    if (!rule.ios_bundle_ids.length && rule.ios_id_status === "verified") rule.ios_id_status = "unverified";
    if (rule.ios_bundle_ids.length && rule.ios_id_status === "not_applicable") rule.ios_id_status = "unverified";
    if (!rule.android_package_ids.length && rule.android_id_status === "verified") rule.android_id_status = "unverified";
    if (rule.android_package_ids.length && rule.android_id_status === "not_applicable") rule.android_id_status = "unverified";
    rule.verified = rule.ios_id_status === "verified" || rule.android_id_status === "verified";
  }
  return rule;
}

function applyDetectionEditor() {
  if (!detectionEditedRule || !detectionState) return;
  const kind = detectionKindForSection[detectionSection];
  const updated = readDetectionEditor();
  if (!updated) return;
  const oldId = detectionSelectedRuleId;
  const idChanged = oldId && updated.id !== oldId;
  detectionState[kind] = detectionState[kind].map(rule => rule.id === oldId ? updated : rule);
  if (idChanged) {
    // Remove old id from tombstones if it was there; new id is treated as user intent.
    detectionDeletedRuleIds.delete(oldId);
    detectionSelectedRuleId = updated.id;
  }
  detectionEditedRule = cloneRule(updated);
  markDetectionDirty();
  renderDetectionRules();
  $("detectionEditorMessage").textContent = "IN ENTWURF ÜBERNOMMEN";
}

function cancelDetectionEditor() {
  detectionEditedRule = null;
  detectionSelectedRuleId = null;
  renderDetectionRules();
}

function detectionDraft() {
  if (!detectionState) return null;
  const draft = {
    app_rules: [...detectionState.app_rules],
    file_rules: [...detectionState.file_rules],
    backup_rules: [...(detectionState.backup_rules || [])],
    deleted_default_rule_ids: [...detectionDeletedRuleIds],
  };
  return draft;
}

function markDetectionDirty() {
  detectionDirty = true;
  $("detectionApply").disabled = false;
  $("detectionSaveAll").disabled = detectionBusy || !detectionState;
  $("detectionStatus").textContent = "UNGESPEICHERTE ÄNDERUNGEN";
  $("detectionEditorMessage").textContent = "UNGESPEICHERTE ÄNDERUNGEN";
}

async function loadDetectionRules(revision) {
  try {
    const response = await fetch("/api/settings/crypto");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Regeln nicht verfügbar");
    if (revision !== settingsRevision || !$("settingsModal").open) return;
    detectionState = data.rules;
    cryptoState = data.rules;
    bundledCryptoRules = data.defaults || bundledCryptoRules;
    detectionDirty = false;
    detectionSelectedRuleId = null;
    detectionEditedRule = null;
    detectionDeletedRuleIds = new Set(data.rules.deleted_default_rule_ids || []);
    selectDetectionSection(detectionSection);
    $("detectionMessage").textContent = "";
    $("detectionStatus").textContent = "";
    $("detectionSaveAll").disabled = true;
  } catch (error) {
    if (revision === settingsRevision) $("detectionMessage").textContent = `FEHLER: ${error.message}`;
  }
}

async function saveDetectionRules() {
  if (!detectionState || detectionBusy) return;
  detectionBusy = true;
  $("detectionApply").disabled = true;
  $("detectionSaveAll").disabled = true;
  $("closeSettings").disabled = true;
  $("detectionMessage").textContent = "REGELN WERDEN GESPEICHERT …";
  try {
    const response = await fetch("/api/settings/crypto", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rules: detectionDraft(), base_sha256: detectionState.sha256 }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Speichern fehlgeschlagen");
    detectionState = data.rules;
    cryptoState = data.rules;
    bundledCryptoRules = data.defaults || bundledCryptoRules;
    detectionDirty = false;
    detectionSelectedRuleId = null;
    detectionEditedRule = null;
    detectionDeletedRuleIds = new Set(data.rules.deleted_default_rule_ids || []);
    selectDetectionSection(detectionSection);
    $("detectionMessage").textContent = "GESPEICHERT · GILT FÜR NEUE SICHTUNGEN";
    $("detectionStatus").textContent = "";
  } catch (error) {
    $("detectionMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    detectionBusy = false;
    $("closeSettings").disabled = isUpdateBusy();
    $("detectionApply").disabled = false;
    $("detectionSaveAll").disabled = !detectionDirty;
  }
}

async function loadCryptoRules(revision) {
  await loadDetectionRules(revision);
}

function openDetectionGlossary() {
  const dialog = $("detectionGlossaryDialog");
  if (!dialog) return;
  if (dialog.showModal) dialog.showModal();
  else dialog.open = true;
}

function closeDetectionGlossary() {
  const dialog = $("detectionGlossaryDialog");
  if (!dialog) return;
  if (dialog.close) dialog.close();
  else dialog.open = false;
}

function closeSettings() {
  if (catalogBusy || detectionBusy || isUpdateBusy()) return;
  if (catalogDirty && !window.confirm("Ungespeicherte Änderungen am Dateityp-Katalog verwerfen?")) return;
  if (detectionDirty && !window.confirm("Ungespeicherte Änderungen an den Erkennungsregeln verwerfen?")) return;
  if (profileDetailDirty && !window.confirm("Ungespeicherte Änderungen am Profil verwerfen?")) return;
  ++settingsRevision;
  $("settingsModal").close();
  resetProfileDetail();
}

async function loadProfiles(preferredIds = activeProfileIds) {
  try {
    const response = await fetch("/api/profiles");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Profile nicht verfügbar");
    availableProfiles = data.profiles || [];
    const details = await Promise.all(availableProfiles.map(async (profile) => {
      const detailResponse = await fetch(`/api/profile?id=${encodeURIComponent(profile.id)}`);
      const detail = await detailResponse.json();
      if (!detailResponse.ok) throw new Error(detail.error || "Profil nicht verfügbar");
      return detail;
    }));
    profileDetails.clear();
    for (const detail of details) {
      profileDetails.set(detail.id, detail);
      if (!selectedByProfile.has(detail.id)) selectedByProfile.set(detail.id, new Set(detail.keywords));
    }
    const validIds = new Set(availableProfiles.map((profile) => profile.id));
    activeProfileIds = profilesInitialized
      ? new Set([...preferredIds].filter((id) => validIds.has(id)))
      : new Set(validIds);
    profilesInitialized = true;
    if (!activeProfileIds.size && availableProfiles[0]) activeProfileIds.add(availableProfiles[0].id);
    profileReady = activeProfileIds.size > 0;
    renderProfileList();
    $("createProfile").disabled = false;
    updateKeywordSummary();
    updateCaseSessionUi();
    if (profileDetailId && !profileDetailDirty) {
      const detail = profileDetails.get(profileDetailId);
      if (detail) {
        keywordDraft = [...detail.keywords];
        draftSelectedKeywords = new Set(selectedByProfile.get(profileDetailId) || keywordDraft);
        $("profileDetailName").value = detail.name;
        renderKeywordOptions();
        updateProfileDetailCount();
      }
    }
  } catch (error) {
    $("profileList").innerHTML = '<p class="case-start-message warning">PROFILE NICHT VERFÜGBAR</p>';
    $("keywordSelectionCount").textContent = "FEHLER";
    $("createProfile").disabled = true;
    profileReady = false;
    updateCaseSessionUi("SCAN-PROFIL NICHT VERFÜGBAR");
  }
}

function renderResults(summary, hits = {}) {
  const catalog = summary.filetype_catalog;
  $("archiveFiletypeCatalog").textContent = catalog
    ? `V${catalog.version} · SHA-256 ${catalog.sha256} · filetype-catalog.json`
    : "Bei dieser älteren Sichtung noch nicht separat gespeichert";
  $("resultEvidence").textContent = summary.evidence || "SICHTUNG";
  $("resultDuration").textContent = `${Number(summary.duration_seconds || 0).toLocaleString("de-AT")} s`;
  $("fileCount").textContent = Number(summary.file_count || 0).toLocaleString("de-AT");
  $("directoryCount").textContent = Number(summary.directory_count || 0).toLocaleString("de-AT");
  $("keywordMatches").textContent = Number(summary.keyword_matches || 0).toLocaleString("de-AT");
  $("totalBytes").textContent = formatBytes(summary.total_file_bytes);
  const categories = Object.entries(summary.categories_by_count || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...categories.map(([, count]) => count), 1);
  const archiveEncryption = summary.archive_encryption || {};
  $("categories").innerHTML = categories.map(([name, count]) => {
    return `<button class="bar-row result-filter" type="button" data-inventory-category="${escapeHtml(name)}" aria-pressed="false" title="${escapeHtml(name)} im Dateiverzeichnis anzeigen"><span class="bar-value">${Number(count)}</span><span class="bar-name">${escapeHtml(name.toUpperCase())}</span><span class="bar-track"><span class="bar-fill" style="width:${(count / max) * 100}%"></span></span></button>`;
  }).join("");
  $("archiveStatus").hidden = !Number(archiveEncryption.total || 0);
  $("archiveEncryptedCount").textContent = Number(archiveEncryption.encrypted || 0).toLocaleString("de-AT");
  $("archiveUnknownCount").textContent = Number(archiveEncryption.unknown || 0).toLocaleString("de-AT");
  for (const button of $("archiveStatus").querySelectorAll("button")) {
    button.disabled = !Number(archiveEncryption[button.dataset.inventoryArchiveStatus] || 0);
  }
  $("keywords").innerHTML = Object.entries(hits).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]).map(([word, count]) => `
    <button class="keyword-row result-filter" type="button" data-inventory-keyword="${escapeHtml(word)}" aria-pressed="false" title="Trefferpfade für ${escapeHtml(word)} anzeigen"><span>${escapeHtml(word.toUpperCase())}</span><b>${Number(count)}</b></button>
  `).join("");
  $("largestFiles").innerHTML = (summary.largest_files || []).map((file) => {
    const path = String(file.path || "");
    const separator = path.lastIndexOf("/");
    const name = path.slice(separator + 1);
    const folder = separator >= 0 ? path.slice(0, separator) : "Stammverzeichnis";
    return `<tr><td class="largest-size">${formatBytes(file.size)}</td><td><button class="largest-file-link" type="button" data-inventory-file="${escapeHtml(path)}" title="Im Dateiverzeichnis anzeigen: ${escapeHtml(path)}" aria-label="Im Dateiverzeichnis anzeigen: ${escapeHtml(path)}"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(folder)}</small><span aria-hidden="true"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M17 7H7M17 7V17"/></svg></span></button></td></tr>`;
  }).join("") || '<tr><td colspan="2">KEINE DATEIEN ERFASST</td></tr>';
  $("results").hidden = false;
}

function renderArchive(archive) {
  if (!archive) { $("documentationGrid").hidden = true; return; }
  $("documentationGrid").hidden = false;
  $("archiveCasePath").textContent = archive.case_path || "—";
  $("archiveInventory").textContent = archive.result_path ? `${archive.result_path}/files.csv` : "files.csv";
  $("archiveContainerIndex").textContent = archive.result_path ? `${archive.result_path}/container-index.json` : "container-index.json";
  $("archiveRegister").textContent = archive.media_register || "media-register.csv";
  $("archivePdfReport").textContent = archive.pdf_report || "case-report.pdf";
  $("archiveReport").textContent = archive.case_report || "case-report.txt";
  $("archiveAudit").textContent = archive.audit_log || "audit.log";
  $("archiveManifestCount").textContent = Number(archive.manifest_entries || 0).toLocaleString("de-AT");
}

function renderDeviceEvidence(media = {}, storedDevice = {}) {
  const liveDevice = devices.find((device) => deviceMatchesMedium(device, media)) || {};
  const device = { ...liveDevice, ...storedDevice };
  const model = [media.vendor || device.vendor, media.model || device.model].filter(Boolean).join(" ") || "UNBEKANNT";
  const isIphone = device.media_type === "iphone" || String(media.device_path || "").startsWith("iphone:");
  const isAndroid = device.media_type === "android" || String(media.device_path || "").startsWith("android:");
  const isPhone = isIphone || isAndroid;
  const isOptical = device.type === "rom" || device.media_type === "optical" || String(media.device_path || "").startsWith("/dev/sr");
  const readOnly = isPhone
    ? `${isAndroid ? "ANDROID-PAKETMETADATEN" : "APPLE-APP-METADATEN"} · KEINE DATEISICHTUNG`
    : device.read_only_verified === true
    ? "BEIM SCAN VERIFIZIERT"
    : (device.read_only || device.ro ? "AKTIV" : "NICHT DOKUMENTIERT");
  $("evidenceDeviceModel").textContent = model;
  $("evidenceDeviceSerial").textContent = media.serial || device.serial || "NICHT GEMELDET";
  $("evidenceDeviceCapacity").textContent = Number(media.size || device.size || 0) > 0
    ? formatBytes(media.size || device.size)
    : "NICHT GEMELDET";
  $("evidenceDeviceType").textContent = isIphone ? "IPHONE (APPLE USB-DIENSTE)" : isAndroid ? "ANDROID (FREIGEGEBENE APP-METADATEN)" : isOptical ? "CD/DVD (USB)" : "USB-DATENTRÄGER";
  $("evidenceDevicePath").textContent = media.device_path || device.path || "—";
  $("evidenceDeviceReadOnly").textContent = readOnly;
}

function renderIphoneSummary(phone) {
  $("iphoneSummary").hidden = !phone;
  if (!phone) return;
  const device = phone.device || {};
  const platform = phone.platform || (device.android_version ? "android" : "ios");
  const appHints = phone.app_hints || [];
  const apps = phone.apps || [];
  $("iphoneDevice").textContent = [device.device_name, device.vendor, device.model].filter(Boolean).filter((value, index, all) => all.indexOf(value) === index).join(" · ") || "TELEFON";
  const os = platform === "android" ? `ANDROID ${device.android_version || "UNBEKANNT"}` : `IOS ${device.ios_version || "UNBEKANNT"}`;
  $("iphoneSystem").textContent = `${os} · ${platform === "android" ? "VERBINDUNG FREIGEGEBEN" : device.connection_state === "paired" ? "GEKOPPELT" : String(device.connection_state || "STATUS UNBEKANNT").toUpperCase()}`;
  $("iphoneSerial").textContent = device.serial || "NICHT GEMELDET";
  $("iphoneUdid").textContent = device.udid || device.adb_serial || device.serial || "NICHT GEMELDET";
  $("iphoneHardware").textContent = platform === "android" ? `BUILD ${device.build_version || "NICHT GEMELDET"}` : `MODELLKENNUNG ${device.model_number || device.hardware_model || "NICHT GEMELDET"}`;
  $("iphoneAccessibleFiles").textContent = "NUR APP-LISTE";
  $("iphoneFileStatus").textContent = "KEINE DATEI-, FOTO- ODER MEDIENSICHTUNG";
  const appsComplete = phone.apps_complete ?? phone.apps_status === "complete";
  const uniqueAppHints = [...new Map(appHints.map(item => [item.package_id || item.bundle_id || item.name, item])).values()];
  const highSignals = uniqueAppHints.filter(item => item.relevance === "high").length;
  const triageLevel = uniqueAppHints.length >= 2 || highSignals >= 1 ? "DEUTLICHER KRYPTO-HINWEIS"
    : uniqueAppHints.length ? "KRYPTO-HINWEIS ERKANNT"
      : appsComplete ? "KEIN KRYPTO-HINWEIS IN DER APP-LISTE" : "KEINE VERLÄSSLICHE AUSSAGE";
  const triageText = uniqueAppHints.length
    ? `${uniqueAppHints.length} relevante ${uniqueAppHints.length === 1 ? "App" : "Apps"} erkannt. Für die weitere Beurteilung eine Fachperson hinzuziehen.`
    : appsComplete
      ? "Keine Krypto-Apps in der erfassten Benutzer-App-Liste erkannt. Das schließt Krypto auf dem Telefon nicht aus."
      : "Die App-Liste oder mindestens ein Profil konnte nicht vollständig geprüft werden. Kein verlässlicher Negativbefund.";
  $("iphoneTriageLevel").textContent = triageLevel;
  $("iphoneTriageText").textContent = triageText;
  $("iphoneHintSummary").classList.toggle("has-hints", Boolean(uniqueAppHints.length));
  $("iphoneTriageApps").innerHTML = uniqueAppHints.map(item => `<span>${escapeHtml(item.name || item.package_id || item.bundle_id || "APP")}</span>`).join("");
  $("iphoneAssessment").textContent = phone.assessment || "—";
  $("iphoneCompleteness").textContent = appsComplete ? `${apps.length.toLocaleString("de-AT")} ${apps.length === 1 ? "APP" : "APPS"} ERFASST` : "APP-LISTE UNVOLLSTÄNDIG";
  $("iphoneCompleteness").classList.toggle("incomplete", !appsComplete);
  const incompleteCoverage = (phone.coverage || []).filter(area => area.status !== "complete").length;
  $("iphoneCoverageBrief").textContent = appsComplete && !incompleteCoverage
    ? "BENUTZER-APP-LISTE GEPRÜFT"
    : `${incompleteCoverage || 1} BEREICH${incompleteCoverage === 1 ? "" : "E"} NICHT VOLLSTÄNDIG PRÜFBAR`;
  $("iphoneNotice").textContent = `${phone.notice || ""} APP-LISTE: ${String(phone.apps_status || "unbekannt").toUpperCase()}`;
  const grouped = new Map();
  for (const app of apps) {
    const category = app.matches?.[0]?.category || "other";
    if (platform === "android" && !cryptoCategories.has(category)) continue;
    if (!grouped.has(category)) grouped.set(category, []);
    grouped.get(category).push(app);
  }
  const sortedGroups = [...grouped.entries()].sort((a, b) => Number(a[0] === "other") - Number(b[0] === "other") || b[1].length - a[1].length);
  $("iphoneCategories").innerHTML = sortedGroups.map(([category, entries]) => {
    const label = escapeHtml(appCategoryLabels[category] || "WEITERE APPS");
    const list = `<ul>${entries.map(app => `<li>${escapeHtml(app.name || app.bundle_id || "UNBEKANNT")}</li>`).join("")}</ul>`;
    if (category === "other") return `<details class="iphone-category iphone-category-other"><summary><span>${label}</span><b>${entries.length}</b><em>+ APPS ANZEIGEN</em></summary><div class="iphone-other-body"><label for="iphoneOtherSearch">SONSTIGE APPS DURCHSUCHEN</label><input id="iphoneOtherSearch" type="search" placeholder="APP-NAME SUCHEN …" autocomplete="off" />${list}<p id="iphoneOtherEmpty" hidden>KEINE PASSENDE APP</p></div></details>`;
    return `<details class="iphone-category ${cryptoCategories.has(category) ? "crypto" : ""}"><summary><span>${label}</span><b>${entries.length}</b><em>+ APPS ANZEIGEN</em></summary>${list}</details>`;
  }).join("") || '<p class="iphone-empty">KEINE BENUTZER-APPS ERFASST · NICHT ALS „KEINE INSTALLIERT“ WERTEN</p>';
  $("iphoneOtherSearch")?.addEventListener("input", (event) => {
    const query = event.target.value.trim().toLocaleLowerCase("de");
    let visible = 0;
    for (const row of event.target.parentElement.querySelectorAll("li")) {
      row.hidden = !row.textContent.toLocaleLowerCase("de").includes(query);
      if (!row.hidden) visible += 1;
    }
    $("iphoneOtherEmpty").hidden = visible > 0;
  });
  $("iphoneApps").innerHTML = apps.map((app) => {
    const matches = (app.matches || []).map((match) => `${match.category} (${match.id})`).join(" · ") || "—";
    const context = [app.profile_name, matches].filter(Boolean).join(" · ") || "—";
    return `<tr><td>${escapeHtml(app.name || "—")}</td><td><code>${escapeHtml(app.package_id || app.bundle_id || "—")}</code></td><td>${escapeHtml(app.version || "—")}</td><td>${escapeHtml(context)}</td></tr>`;
  }).join("") || '<tr><td colspan="4">APP-LISTE NICHT VERFÜGBAR ODER LEER</td></tr>';
  $("phoneCoverage").innerHTML = (phone.coverage || []).map((area) => `<div class="iphone-area ${escapeHtml(area.status || "unknown")}"><strong>${area.status === "complete" ? "✓" : "△"} ${escapeHtml(area.label || "BEREICH")}</strong><span>${escapeHtml(area.status === "complete" ? "GEPRÜFT" : "NICHT VOLLSTÄNDIG PRÜFBAR")}</span><small>${escapeHtml(area.message || "")}</small></div>`).join("");
}

function renderCryptoFindings(crypto, isPhone) {
  $("cryptoFindings").hidden = !crypto || isPhone;
  if (!crypto) return;
  const apps = crypto.app_hints || [];
  const files = crypto.file_hints || [];
  $("cryptoRulesVersion").textContent = crypto.rules?.version ? `REGELSTAND V${crypto.rules.version}` : "ÄLTERE SICHTUNG";
  $("cryptoScope").textContent = isPhone
    ? "Hinweise aus Apps und zugänglichen Dateinamen · keine Inhaltsanalyse."
    : "Hinweise nur aus Dateinamen und Pfaden des Grobindex. Keine Inhaltsanalyse und kein Nachweis für Krypto-Vermögenswerte.";
  const appRows = apps.slice(0, 100).map(item => `<li><strong>${escapeHtml(item.name || "APP")}</strong><span>${escapeHtml(appCategoryLabels[item.category] || item.category || "HINWEIS")} · ${escapeHtml(item.reason || item.id || "REGELTREFFER")}</span></li>`);
  const fileRows = files.slice(0, 100).map(item => {
    const matches = item.matches || [item];
    return `<li><button class="crypto-file-link" type="button" data-inventory-file="${escapeHtml(item.path || "")}" title="Im Dateiverzeichnis anzeigen"><strong>${escapeHtml(item.path || "DATEI")}</strong><span>${escapeHtml(matches.map(match => `${appCategoryLabels[match.category] || match.category}: ${match.reason || match.id}`).join(" · "))}</span></button></li>`;
  });
  $("cryptoHintList").innerHTML = appRows.length || fileRows.length
    ? `<ul class="crypto-hint-list">${appRows.join("")}${fileRows.join("")}</ul>${apps.length > 100 || files.length > 100 ? `<p class="iphone-empty">ANZEIGE AUF 100 APP- UND 100 DATEIHINWEISE BEGRENZT · VOLLSTÄNDIGE LISTE IN DER FALLAKTE</p>` : ""}`
    : '<p class="iphone-empty">KEINE KRYPTO-HINWEISE IN DEN ERFASSTEN METADATEN · KEINE AUSSAGE ÜBER NICHT ZUGÄNGLICHE BEREICHE</p>';
}

function renderBackupFindings(backup) {
  const container = $("backupFindings");
  if (!container) return;
  const hints = backup?.backup_hints || [];
  container.hidden = !hints.length;
  if (!hints.length) return;
  const items = hints.slice(0, 50).map(hit => `
    <div class="backup-hint">
      <div class="backup-hint-name">${escapeHtml(hit.name || hit.id || "BACKUP")}</div>
      <div class="backup-hint-path">${escapeHtml(hit.path || "—")}</div>
      <div class="backup-hint-confidence ${escapeHtml(hit.confidence || "medium")}">ERKENNUNGSSICHERHEIT: ${escapeHtml((hit.confidence || "medium").toUpperCase())}</div>
      <small>${escapeHtml((hit.matched_indicators || []).join(" · "))} · Inhalt wurde nicht analysiert.</small>
    </div>
  `).join("");
  container.innerHTML = `<h3><span>↗</span>GERÄTE-BACKUPS · ${hints.length}</h3>${items}${hints.length > 50 ? '<p class="iphone-empty">ANZEIGE AUF 50 HINWEISE BEGRENZT · VOLLSTÄNDIGE LISTE IN DER FALLAKTE</p>' : ""}`;
}

const decisionLabels = {
  open: "ENTSCHEIDUNG OFFEN",
  secure: "ZUR SICHERUNG AUSGEWÄHLT",
  not_selected: "NICHT ZUR SICHERUNG AUSGEWÄHLT",
  specialist_consulted: "FACHPERSON HINZUGEZOGEN",
  specialist_not_consulted: "KEINE FACHPERSON HINZUGEZOGEN",
  review: "ENTSCHEIDUNG OFFEN · ALTER STATUS",
};

function renderDecision(media) {
  if (!media) return;
  currentMediaId = media.id;
  const allowed = currentIsPhone ? ["specialist_consulted", "specialist_not_consulted"] : ["secure", "not_selected"];
  currentDecision = allowed.includes(media.decision) ? media.decision : null;
  $("decisionState").textContent = decisionLabels[media.decision] || decisionLabels.open;
  $("decisionEvidence").value = media.evidence_number || "";
  $("decisionSpecialist").value = media.specialist_name || "";
  updateDecisionFields();
  $("decisionReason").value = media.reason_code || "";
  $("decisionNote").value = media.reason_note || "";
  for (const button of document.querySelectorAll("[data-decision]")) {
    button.classList.toggle("active", button.dataset.decision === currentDecision);
  }
  updateDecisionAvailability();
}

function updateDecisionFields() {
  const secure = currentDecision === "secure";
  const consulted = currentDecision === "specialist_consulted";
  $("decisionEvidenceWrap").hidden = currentIsPhone || !secure;
  $("decisionSpecialistWrap").hidden = !currentIsPhone || !consulted;
  $("decisionReasonWrap").hidden = currentIsPhone || secure;
  $("decisionNoteWrap").hidden = currentIsPhone || secure;
  $("decisionHelp").hidden = !currentIsPhone && secure;
}

function renderRecord(record) {
  renderResults(record.summary, record.hits);
  const phone = record.phone || record.iphone || record.android || null;
  const isPhone = Boolean(phone);
  currentIsPhone = isPhone;
  $("inventoryTitle").textContent = isPhone ? "TECHNISCHE DATEIDETAILS" : "DATEIEN DIESES MEDIUMS";
  $("decisionTitle").textContent = isPhone ? "FACHPERSON DOKUMENTIEREN" : "ENTSCHEIDUNG ZUM DATENTRÄGER";
  $("decisionHelp").innerHTML = isPhone
    ? "Dokumentieren Sie, ob nach dem Krypto-Schnellscan eine <b>Fachperson hinzugezogen</b> wurde. Bei Ja ist deren Name oder Dienststelle erforderlich."
    : "Wählen Sie <b>„Sichern“</b> oder <b>„Nicht sichern“</b>. Eine Beweismittelnummer ist nur bei Sicherung erforderlich; eine Nicht-Sicherung muss nachvollziehbar begründet werden.";
  $("decisionPrimary").dataset.decision = isPhone ? "specialist_consulted" : "secure";
  $("decisionPrimary").textContent = isPhone ? "FACHPERSON HINZUGEZOGEN" : "SICHERN";
  $("decisionSecondary").dataset.decision = isPhone ? "specialist_not_consulted" : "not_selected";
  $("decisionSecondary").textContent = isPhone ? "KEINE FACHPERSON HINZUGEZOGEN" : "NICHT SICHERN";
  $("documentationGrid").classList.toggle("phone-view", isPhone);
  $("classicHome").hidden = isPhone;
  if (isPhone && $("inventoryPanel").dataset.mediaId !== String(record.media?.id ?? "")) $("inventoryPanel").open = false;
  $("inventoryPanel").dataset.mediaId = String(record.media?.id ?? "");
  if (isPhone) {
    $("iphoneSummary").after($("cryptoFindings"));
    $("cryptoFindings").after($("backupFindings"));
  } else {
    $("classicHome").after($("cryptoFindings"));
    $("cryptoFindings").after($("backupFindings"));
  }
  renderIphoneSummary(phone);
  renderCryptoFindings(record.crypto || null, isPhone);
  renderBackupFindings(record.backup || null);
  if (record.media) {
    clearInventoryView();
    const connected = devices.some((device) => deviceMatchesMedium(device, record.media));
    $("detailConnectionState").textContent = deviceDiscoveryError ? "STATUS UNBEKANNT" : connected ? "● ONLINE" : "○ OFFLINE";
    $("detailConnectionState").className = connected && !deviceDiscoveryError ? "connected" : "disconnected";
    renderDeviceEvidence(record.media, record.device);
    renderArchive(record.archive);
    renderDecision(record.media);
    loadCase(record.media.case_number);
    $("inventoryPanel").hidden = isPhone;
    if (!isPhone && $("inventoryPanel").open) loadInventoryTree();
  }
}

function statusTag(decision) {
  return `<span class="status-tag status-${decision}">${decisionLabels[decision] || decisionLabels.open}</span>`;
}

function setCaseDownloads(caseNumber = null) {
  const downloads = [
    [$("caseReportDownload"), caseNumber ? `/api/cases/${encodeURIComponent(caseNumber)}/report.pdf` : "#"],
    [$("caseDownload"), caseNumber ? `/api/cases/${encodeURIComponent(caseNumber)}/export.zip` : "#"],
  ];
  for (const [link, href] of downloads) {
    link.classList.toggle("disabled", !caseNumber);
    link.setAttribute("aria-disabled", caseNumber ? "false" : "true");
    link.href = href;
  }
}

async function loadCase(caseNumber) {
  const revision = ++caseLoadRevision;
  if (!caseNumber) {
    currentCaseMedia = [];
    renderMediaCards([]);
    $("casePanel").hidden = true;
    setCaseDownloads();
    return;
  }
  try {
    const response = await fetch(`/api/cases/${encodeURIComponent(caseNumber)}`);
    const data = await response.json();
    if (revision !== caseLoadRevision) return;
    if (response.status === 404) {
      currentCaseMedia = [];
      renderMediaCards([]);
      $("casePanel").hidden = true;
      setCaseDownloads();
      return;
    }
    if (!response.ok) throw new Error(data.error || "Fallakte nicht verfügbar");
    currentCaseMedia = sortedSightings(data.media || []);
    renderMediaCards(currentCaseMedia);
    renderDevices(devices);
    $("casePanel").hidden = false;
    $("casePanelNumber").textContent = data.case.case_number;
    setCaseDownloads(data.case.case_number);
    $("caseMedia").innerHTML = currentCaseMedia.map((medium) => `
      <tr data-media-id="${Number(medium.id)}"><td>${escapeHtml(medium.sighting_number)}</td><td>${escapeHtml(medium.evidence_number || "—")}</td><td>${escapeHtml([medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path)}</td><td>${Number(medium.file_count).toLocaleString("de-AT")}</td><td>${Number(medium.keyword_matches).toLocaleString("de-AT")}</td><td>${statusTag(medium.decision)}</td></tr>
    `).join("");
  } catch (error) {
    if (revision !== caseLoadRevision) return;
    $("decisionMessage").textContent = error.message;
  }
}

function sortedSightings(media) {
  return [...media].sort((left, right) =>
    String(left.sighting_number || "").localeCompare(String(right.sighting_number || ""), "de", { numeric: true })
    || Number(left.id) - Number(right.id));
}

function decisionIsOpen(medium) {
  return !["secure", "not_selected", "specialist_consulted", "specialist_not_consulted"].includes(medium?.decision);
}

function presenceKey(item) {
  const path = String(item?.device_path || item?.path || "");
  return path.startsWith("iphone:") ? path : String(item?.serial || path);
}

function deviceMatchesMedium(device, medium) {
  const path = String(medium?.device_path || "");
  if (path.startsWith("iphone:")) return device.path === path;
  return Boolean(device.serial && medium.serial && device.serial === medium.serial)
    || Boolean(device.path && device.path === path);
}

function pendingOfflineMedia() {
  return sortedSightings(currentCaseMedia.filter((medium) => decisionIsOpen(medium) && !devices.some(device => deviceMatchesMedium(device, medium))));
}

function renderPendingDecisionState(pending = pendingOfflineMedia()) {
  const count = pending.length;
  $("pendingDecisionBanner").hidden = count === 0;
  $("pendingDecisionCount").textContent = `${count} ${count === 1 ? "ENTSCHEIDUNG" : "ENTSCHEIDUNGEN"} OFFEN`;
  if (!count) {
    returnToDecisionQueue = false;
    if ($("decisionQueueModal").open) $("decisionQueueModal").close();
    return;
  }
  $("decisionQueueTitle").textContent = `${count} ${count === 1 ? "ENTSCHEIDUNG" : "ENTSCHEIDUNGEN"} OFFEN`;
  $("decisionQueueSummary").textContent = `${count} ABGEZOGENE ${count === 1 ? "SICHTUNG" : "SICHTUNGEN"} OHNE ENTSCHEIDUNG`;
  $("decisionQueueList").innerHTML = pending.map((medium, index) => {
    const model = [medium.vendor, medium.model].filter(Boolean).join(" ") || "USB-DATENTRÄGER";
    const isIphone = String(medium.device_path || "").startsWith("iphone:");
    const serial = (isIphone ? String(medium.device_path).slice(7) : medium.serial) || "NICHT GEMELDET";
    const capacity = Number(medium.size || 0) > 0 ? formatBytes(medium.size) : "GRÖSSE NICHT GEMELDET";
    return `<button type="button" class="decision-queue-item" data-queue-media-id="${Number(medium.id)}">
      <span class="decision-queue-position">${index + 1} / ${count}</span>
      <strong>${escapeHtml(medium.sighting_number || `SICHT-${medium.id}`)}</strong>
      <span class="decision-queue-model">${escapeHtml(model)}</span>
      <code title="${escapeHtml(serial)}">${isIphone ? "UDID" : "SERIAL"} ${escapeHtml(serial)}</code>
      <small>${escapeHtml(capacity)} · ${Number(medium.file_count || 0).toLocaleString("de-AT")} DATEIEN · ${Number(medium.keyword_matches || 0).toLocaleString("de-AT")} TREFFER</small>
      <em>SICHTUNG &amp; ENTSCHEIDUNG ÖFFNEN →</em>
    </button>`;
  }).join("");
}

function otherDialogIsOpen() {
  return [...document.querySelectorAll("dialog[open]")].some((dialog) => dialog.id !== "decisionQueueModal");
}

function openDecisionQueue() {
  renderPendingDecisionState();
  if (!pendingOfflineMedia().length || decisionQueueDeferred || otherDialogIsOpen()) return false;
  if (!$("decisionQueueModal").open) $("decisionQueueModal").showModal();
  return true;
}

function scheduleDecisionQueue(delay = 1200) {
  clearTimeout(decisionQueueTimer);
  decisionQueueTimer = setTimeout(() => {
    if (!openDecisionQueue() && !decisionQueueDeferred && pendingOfflineMedia().length) scheduleDecisionQueue(700);
  }, delay);
}

function observeConfirmedDevicePresence(items) {
  if (deviceDiscoveryError) return;
  const nextSerials = new Set((items || []).map(presenceKey).filter(Boolean));
  if (devicePresenceInitialized) {
    const removed = [...confirmedOnlineSerials].filter((serial) => !nextSerials.has(serial));
    const requiresDecision = removed.some((serial) => currentCaseMedia.some((medium) => presenceKey(medium) === serial && decisionIsOpen(medium)));
    if (requiresDecision) {
      decisionQueueDeferred = false;
      scheduleDecisionQueue();
    }
  }
  confirmedOnlineSerials = nextSerials;
  devicePresenceInitialized = true;
}

function renderMediaCards(media) {
  media = sortedSightings(media);
  for (const device of devices) {
    const alreadyRecorded = media.some((medium) => deviceMatchesMedium(device, medium));
    if (alreadyRecorded && deviceStates.get(device.path) === "ready") deviceStates.set(device.path, "complete");
  }
  const renderCard = (medium, connected) => {
    const isIphone = String(medium.device_path || "").startsWith("iphone:");
    const evidenceLabel = medium.evidence_number
      ? `<b>${escapeHtml(medium.evidence_number)}</b>`
      : "";
    const model = [medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path;
    const ejectLabel = String(medium.device_path || "").startsWith("/dev/sr")
      ? `${ICON_TEXT(SVG_ICONS.eject)} CD/DVD AUSWERFEN`
      : `${ICON_TEXT(SVG_ICONS.eject)} SICHER AUSWERFEN`;
    return `<div class="media-card-shell${connected ? " online" : " offline"}"><button class="media-card complete${connected ? " online" : " offline"}${Number(medium.id) === currentMediaId ? " active" : ""}" type="button" data-media-id="${Number(medium.id)}">
      <span class="media-card-top">${evidenceLabel}${statusTag(medium.decision)}</span>
      <strong>${escapeHtml(medium.sighting_number)}</strong>
      <small>${escapeHtml(model)}</small>
      <span class="media-card-metrics"><i>${Number(medium.file_count).toLocaleString("de-AT")} DATEIEN</i><i>${Number(medium.keyword_matches).toLocaleString("de-AT")} TREFFER</i></span>
      <span class="connection-badge ${connected && !deviceDiscoveryError ? "connected" : "disconnected"}">${deviceDiscoveryError ? "STATUS UNBEKANNT" : connected ? "● ONLINE" : "○ OFFLINE"}</span>
      <em>DETAILS ÖFFNEN →</em>
    </button>${connected && !isIphone ? `<button class="media-eject" type="button" data-eject-device="${escapeHtml(medium.device_path)}" ${deviceDiscoveryError ? "disabled" : ""}>${ejectLabel}</button>` : ""}</div>`;
  };
  const onlineMedia = media.filter((medium) => devices.some((device) => deviceMatchesMedium(device, medium)));
  const offlineMedia = media.filter((medium) => !devices.some((device) => deviceMatchesMedium(device, medium)));
  const pendingOffline = offlineMedia.filter(decisionIsOpen);
  const offlineHistory = offlineMedia.filter((medium) => !decisionIsOpen(medium));
  $("mediaCards").innerHTML = onlineMedia.map((medium) => renderCard(medium, true)).join("");
  $("offlineMediaCards").innerHTML = offlineHistory.map((medium) => renderCard(medium, false)).join("");
  $("offlineMediaPanel").hidden = offlineHistory.length === 0;
  $("offlineMediaCount").textContent = `${offlineHistory.length} ${offlineHistory.length === 1 ? "MEDIUM" : "MEDIEN"}`;
  renderPendingDecisionState(pendingOffline);
  updateDashboardState();
}

function updateDashboardState() {
  const online = devices.length;
  if (deviceDiscoveryError) {
    $("deviceCount").textContent = "ERKENNUNG GESTÖRT · LETZTER STAND";
    $("deviceEmptyTitle").textContent = "VERBINDUNG PRÜFEN";
    $("deviceEmptyCopy").textContent = "Geräteerkennung derzeit nicht verfügbar. Bitte aktualisieren.";
    $("deviceEmpty").hidden = online > 0;
    return;
  }
  if (!activeCaseNumber) {
    $("deviceCount").textContent = `${online} ONLINE · WARTET AUF FALL`;
    $("deviceEmptyTitle").textContent = "KEIN FALL AKTIV";
    $("deviceEmptyCopy").textContent = "Fallnummer und Kürzel eingeben, dann „Fall starten“. Erst danach ist Auto-Scan freigeschaltet.";
    $("deviceEmpty").hidden = false;
    return;
  }
  const pending = pendingOfflineMedia().length;
  const offline = currentCaseMedia.filter((medium) => !devices.some((device) => deviceMatchesMedium(device, medium)) && !decisionIsOpen(medium)).length;
  $("deviceCount").textContent = `${online} ONLINE · ${pending} OFFEN · ${offline} OFFLINE`;
  $("deviceEmptyTitle").textContent = "NOCH KEIN MEDIUM IN DIESEM FALL";
  $("deviceEmptyCopy").textContent = "USB-Medium einstecken. Auto-Scan übernimmt die geschützte Grobsichtung.";
  $("deviceEmpty").hidden = online > 0;
}

function updateOrderSummary() {
  $("openAuftragModal").textContent = activeCaseNumber ? "FALL VERWALTEN" : "＋ FALL ANLEGEN / ÖFFNEN";
  $("openAuftragModal").classList.toggle("active-case", Boolean(activeCaseNumber));
  $("autoScanToggle").nextElementSibling.textContent = $("autoScanToggle").checked ? "AUTO-SCAN EIN" : "AUTO-SCAN AUS";
}

function updateCaseSessionUi(message = "") {
  const draftCase = $("caseNumber").value.trim().toUpperCase();
  const draftOperator = $("operator").value.trim().toUpperCase();
  const openRequirements = [];
  if (!draftCase) openRequirements.push("FALLNUMMER FEHLT");
  if (!draftOperator) openRequirements.push("BEARBEITERKÜRZEL FEHLT");
  if (!profileReady) openRequirements.push("SUCHPROFIL FEHLT");
  if (runningPaths.size) openRequirements.push("SCAN LÄUFT");
  const ready = openRequirements.length === 0;
  const sameSession = activeCaseNumber === draftCase && activeOperator === draftOperator;
  $("caseStart").disabled = !ready || sameSession;
  const caseStartLabel = activeCaseNumber && !sameSession ? " ANDEREN FALL STARTEN" : " FALL STARTEN";
  const caseStartText = $("caseStart").lastChild;
  if (caseStartText && caseStartText.nodeType === Node.TEXT_NODE) caseStartText.textContent = caseStartLabel;
  else $("caseStart").append(caseStartLabel);
  $("caseStop").disabled = !activeCaseNumber || runningPaths.size > 0;
  $("activeCaseDisplay").classList.toggle("locked", !activeCaseNumber);
  $("activeCaseNumber").textContent = activeCaseNumber || "KEIN FALL";
  $("activeCaseOperator").textContent = activeCaseNumber ? `| ${activeOperator}` : "";
  if (message) {
    $("caseStartMessage").textContent = message;
  } else if (openRequirements.length) {
    $("caseStartMessage").textContent = `OFFEN: ${openRequirements.join(" · ")}`;
  } else if (sameSession) {
    $("caseStartMessage").textContent = "DIESER FALL IST AKTIV";
  } else if (activeCaseNumber) {
    $("caseStartMessage").textContent = `${activeCaseNumber} BLEIBT AKTIV, BIS DER WECHSEL BESTÄTIGT WIRD`;
  } else {
    $("caseStartMessage").textContent = "BEREIT — FALL MUSS AUSDRÜCKLICH GESTARTET WERDEN";
  }
  $("caseStartMessage").className = `case-start-message${openRequirements.length || (ready && !sameSession) ? " warning" : activeCaseNumber ? " ready" : ""}`;
  updateOrderSummary();
  updateScanAvailability();
  updateDecisionAvailability();
  renderUpdateState(updateState);
}

const stateLabels = {
  ready: "BEREIT", scanning: "SCAN LÄUFT", complete: "FERTIG", error: "PRÜFEN",
  timeout: "MEDIUM ANTWORTET NICHT", unavailable: "NICHT BEREIT",
};

function resetDeviceStatesForCase() {
  for (const device of devices) {
    const recorded = activeCaseNumber && currentCaseMedia.some((medium) => deviceMatchesMedium(device, medium));
    if (runningPaths.has(device.path)) deviceStates.set(device.path, "scanning");
    else if (quarantinedPaths.has(device.path)) deviceStates.set(device.path, "timeout");
    else if (recorded) deviceStates.set(device.path, "complete");
    else deviceStates.set(device.path, device.scan_supported ? "ready" : "unavailable");
  }
}

function renderDevices(items, activePaths = [], blockedPaths = null) {
  observeConfirmedDevicePresence(items);
  devices = items || [];
  if (blockedPaths !== null) quarantinedPaths = new Set(blockedPaths);
  const active = new Set(activePaths);
  const presentPaths = new Set(devices.map((device) => device.path));
  for (const path of deviceStates.keys()) if (!presentPaths.has(path)) deviceStates.delete(path);
  for (const path of deviceErrors.keys()) if (!presentPaths.has(path)) deviceErrors.delete(path);
  for (const device of devices) {
    if (active.has(device.path)) deviceStates.set(device.path, "scanning");
    else if (quarantinedPaths.has(device.path)) deviceStates.set(device.path, "timeout");
    else if (!device.scan_supported) deviceStates.set(device.path, "unavailable");
    else if (deviceStates.get(device.path) === "unavailable") deviceStates.set(device.path, "ready");
    else if (!deviceStates.has(device.path)) deviceStates.set(device.path, device.scan_supported ? "ready" : "unavailable");
  }
  const visibleDevices = devices.filter((device) => !(
    currentCaseMedia.some((medium) => deviceMatchesMedium(device, medium))
  ));
  const dashboardDevices = activeCaseNumber
    ? visibleDevices
    : visibleDevices.filter((device) => device.media_type === "optical");
  $("deviceList").innerHTML = dashboardDevices.map((device) => {
    const state = deviceStates.get(device.path) || "ready";
    const iphone = device.media_type === "iphone";
    const android = device.media_type === "android";
    const phone = iphone || android;
    const model = iphone
      ? [device.device_name, device.model].filter(Boolean).join(" · ") || "Apple iPhone"
      : [device.vendor, device.model].filter(Boolean).join(" ") || (device.media_type === "optical" ? "CD/DVD-Laufwerk" : "USB-Datenträger");
    const serial = (iphone ? device.udid : device.serial) || "NICHT GEMELDET";
    const type = iphone ? `IPHONE · IOS ${device.ios_version || "?"}` : android ? "ANDROID-TELEFON" : device.media_type === "optical" ? "CD/DVD" : "USB";
    const disabled = deviceDiscoveryError || !device.scan_supported || state === "scanning" || state === "timeout";
    const stateReason = state === "timeout"
      ? "ABZIEHEN UND NEU VERBINDEN"
      : (deviceErrors.get(device.path) || device.unavailable_reason || "");
    const optical = device.media_type === "optical";
    const visibleState = iphone && state === "ready" && device.connection_state !== "paired"
      ? "IPHONE ENTSPERREN / VERTRAUEN"
      : android && !device.scan_supported
        ? (device.connection_state === "authorization_required" ? "VERBINDUNG AM TELEFON BESTÄTIGEN" : "TELEFON VORBEREITEN")
      : stateLabels[state];
    const guidance = android && !device.scan_supported ? `<div class="android-guidance"><strong>ANDROID-TELEFON ERKANNT</strong><p>Für die Krypto-App-Prüfung einmalig am Telefon:</p><ol>${(device.guidance || []).map(step => `<li>${escapeHtml(step)}</li>`).join("")}</ol><small>TRIAGE//BOX wartet automatisch. Nach der Bestätigung startet der Scan bei aktivem Fall.</small></div>` : "";
    const ejectDisabled = deviceDiscoveryError || ["scanning", "timeout"].includes(state) || device.mounted;
    return `<article class="device-card" data-state="${state}">
      <span class="device-card-top"><i class="device-led" title="${escapeHtml(visibleState)}"></i><b>${phone ? `${android ? "ANDROID" : "IPHONE"} ERKANNT` : optical ? "CD/DVD-LAUFWERK" : "NEUES MEDIUM"}</b><em>${deviceDiscoveryError ? "STATUS UNBEKANNT" : "● ONLINE"}</em></span>
      <div class="device-copy"><strong>${escapeHtml(model)}</strong><span>${escapeHtml(device.path)}${phone ? "" : ` · ${formatBytes(device.size)}`} · ${type}</span><code title="${escapeHtml(serial)}">${phone ? "GERÄTE-ID" : "SERIAL"} ${escapeHtml(serial.length > 22 ? `${serial.slice(0, 22)}…` : serial)}</code></div>
      <div class="device-state"><b>${escapeHtml(visibleState)}</b><small title="${escapeHtml(stateReason)}">${escapeHtml(stateReason)}</small></div>
      ${guidance}
      <div class="device-progress" aria-label="Scanfortschritt"><i></i></div>
      <div class="device-card-actions${optical ? " optical" : ""}">
        <button type="button" data-scan-device="${escapeHtml(device.path)}" ${disabled ? "disabled" : ""}>${state === "complete" ? "ERNEUT SCANNEN" : "SCANNEN"}</button>
        ${optical ? `<button class="device-eject" type="button" data-eject-device="${escapeHtml(device.path)}" ${ejectDisabled ? "disabled" : ""}>${ICON_TEXT(SVG_ICONS.eject)} CD/DVD AUSWERFEN</button>` : ""}
      </div>
    </article>`;
  }).join("");
  if (!activeCaseNumber) {
    $("mediaCards").innerHTML = "";
    $("offlineMediaPanel").hidden = true;
  }
  renderMediaCards(currentCaseMedia);
  const detailMedium = currentCaseMedia.find((medium) => Number(medium.id) === currentMediaId);
  if (detailMedium) {
    const connected = devices.some((device) => deviceMatchesMedium(device, detailMedium));
    $("detailConnectionState").textContent = deviceDiscoveryError ? "STATUS UNBEKANNT" : connected ? "● ONLINE" : "○ OFFLINE";
    $("detailConnectionState").className = connected && !deviceDiscoveryError ? "connected" : "disconnected";
  }
  updateDashboardState();
  updateScanAvailability();
  scheduleAutoScan(400);
}

function updateScanAvailability() {
  for (const button of document.querySelectorAll("[data-scan-device]")) {
    const device = devices.find((item) => item.path === button.dataset.scanDevice);
    button.disabled = Boolean(deviceDiscoveryError) || !device?.scan_supported || ["scanning", "timeout"].includes(deviceStates.get(device.path)) || !activeCaseNumber || !activeOperator;
  }
}

function updateDecisionAvailability() {
  const reasonRequired = currentDecision === "not_selected";
  const hasReason = $("decisionReason").value.length > 0;
  const hasEvidence = $("decisionEvidence").value.trim().length > 0;
  const hasSpecialist = $("decisionSpecialist").value.trim().length > 0;
  $("saveDecision").disabled = !currentMediaId || !currentDecision || (reasonRequired && !hasReason) || (currentDecision === "secure" && !hasEvidence) || (currentDecision === "specialist_consulted" && !hasSpecialist) || !activeOperator;
}

function renderCaseHistory(cases) {
  knownCases = cases || [];
  const selected = $("caseNumber").value.trim().toUpperCase();
  const signature = JSON.stringify({ selected, activeCaseNumber, cases: knownCases.map((item) => [item.case_number, item.media_count, item.open_count]) });
  if (signature === caseHistorySignature) return;
  caseHistorySignature = signature;
  $("caseListCount").textContent = `${knownCases.length} ${knownCases.length === 1 ? "FALLAKTE" : "FALLAKTEN"}`;
  $("caseList").innerHTML = knownCases.map((item) => {
    const isActive = item.case_number === activeCaseNumber;
    return `<div class="case-list-item${isActive ? " active" : item.case_number === selected ? " selected" : ""}">
      <div class="case-list-copy">
        <strong>${escapeHtml(item.case_number)}</strong><span>${Number(item.media_count)} MEDIEN</span><span class="open-count">${Number(item.open_count)} OFFEN</span>
      </div>
      <button type="button" class="case-list-open" data-case-number="${escapeHtml(item.case_number)}">ÖFFNEN</button>
      <button type="button" class="case-list-delete" data-delete-case="${escapeHtml(item.case_number)}"${isActive ? " disabled title=\"Aktiven Fall zuerst beenden\"" : ""}>LÖSCHEN</button>
    </div>`;
  }).join("") || "<p>NOCH KEINE FÄLLE VORHANDEN</p>";
}

async function syncCaseSessionFromServer(session) {
  if (caseSessionTransition) return;
  const serverCaseNumber = String(session?.case_number || "");
  const serverOperator = String(session?.operator || "");
  serverActiveCase = session || null;
  if (!serverCaseNumber) {
    if (!activeCaseNumber) { updateStartOverlay(); return; }
    invalidateMediaView();
    activeCaseNumber = null;
    activeOperator = "";
    currentCaseMedia = [];
    currentMediaId = null;
    currentDecision = null;
    inventoryTreeMediaId = null;
    $("caseNumber").value = "";
    $("operator").value = "";
    $("casePanel").hidden = true;
    $("results").hidden = true;
    $("dashboardView").hidden = false;
    setCaseDownloads();
    caseHistorySignature = "";
    resetDeviceStatesForCase();
    updateCaseSessionUi("FALL AUF DEM GERÄT BEENDET · SCANS GESPERRT");
    setSystemState("GESPERRT", "locked");
    updateStartOverlay();
    return;
  }
  if (activeCaseNumber === serverCaseNumber && activeOperator === serverOperator) { updateStartOverlay(); return; }
  invalidateMediaView();
  activeCaseNumber = serverCaseNumber;
  activeOperator = serverOperator;
  $("caseNumber").value = activeCaseNumber;
  $("operator").value = activeOperator;
  currentMediaId = null;
  currentDecision = null;
  inventoryTreeMediaId = null;
  caseHistorySignature = "";
  await loadCase(activeCaseNumber);
  resetDeviceStatesForCase();
  updateCaseSessionUi(`FALL ${activeCaseNumber} AKTIV · GERÄTESTATUS ÜBERNOMMEN`);
  setSystemState("BEREIT", "ready");
  updateStartOverlay();
}

async function refresh(loadLatest = false) {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("offline");
    const data = await response.json();
    const previousDeviceError = deviceDiscoveryError;
    deviceDiscoveryError = data.device_error || "";
    await syncCaseSessionFromServer(data.active_case || null);
    renderDevices(data.devices || [], data.active_devices || [], data.quarantined_devices || []);
    renderCaseHistory(data.cases || []);
    if (data.device_error) setSystemState("DATENTRÄGERERKENNUNG PRÜFEN", "error");
    else if (previousDeviceError) setSystemState(activeCaseNumber ? "BEREIT" : "GESPERRT");
    if (!updateActionInProgress) renderUpdateState(data.update || {});
    renderPowerState(data.power || {});
    if (loadLatest && data.latest) renderRecord(data.latest);
    startOverlayReady = true;
    updateStartOverlay();
  } catch (_) {
    deviceDiscoveryError = "Verbindung zur Geräteerkennung unterbrochen";
    renderDevices(devices);
    setSystemState("VERBINDUNG PRÜFEN", "error");
  }
}

async function refreshMediaDevices() {
  $("deviceRefresh").disabled = true;
  setSystemState("DATENTRÄGER WERDEN NEU EINGELESEN", "busy");
  try {
    const response = await fetch("/api/devices/refresh", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Datenträger konnten nicht aktualisiert werden");
    deviceDiscoveryError = data.device_error || "";
    renderDevices(data.devices || [], data.active_devices || [], data.quarantined_devices || []);
    const restored = Number(data.reactivated?.length || 0);
    if (data.device_error) {
      setSystemState("DATENTRÄGERERKENNUNG PRÜFEN", "error");
    } else {
      setSystemState(restored ? `${restored} DATENTRÄGER REAKTIVIERT` : (activeCaseNumber ? "DATENTRÄGER AKTUELL" : "GESPERRT"));
    }
  } catch (error) {
    setSystemState(`FEHLER: ${error.message}`, "error");
  } finally {
    $("deviceRefresh").disabled = false;
  }
}

function updateProgress() {
  $("progressPanel").hidden = true;
  const percent = batchTotal ? Math.round((batchDone / batchTotal) * 100) : 0;
  $("progressValue").textContent = `${percent}%`;
  $("progressBar").style.width = `${Math.max(runningPaths.size ? 8 : 0, percent)}%`;
  if (runningPaths.size) $("progressLabel").textContent = `${runningPaths.size} Grobsichtung${runningPaths.size === 1 ? "" : "en"} parallel …`;
  else if (batchDone === batchTotal) $("progressLabel").textContent = "Sichtungslauf abgeschlossen";
  $("progressLog").textContent = runningPaths.size ? `$ Geschützte Metadaten-Inventarisierung: ${[...runningPaths].join(" · ")}` : "$ Protokolle und Prüfsummen aktualisiert";
}

async function runScan(devicePath, standalone = true) {
  if (deviceDiscoveryError) return;
  if (!activeCaseNumber || !activeOperator) {
    setSystemState("GESPERRT", "locked");
    openAuftrag();
    return;
  }
  if (standalone) { batchTotal = 1; batchDone = 0; }
  deviceErrors.delete(devicePath);
  runningPaths.add(devicePath);
  deviceStates.set(devicePath, "scanning");
  renderDevices(devices);
  updateProgress();
  try {
    const response = await fetch("/api/scans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        case_number: activeCaseNumber,
        operator: activeOperator,
        device_path: devicePath,
        profiles: [...activeProfileIds],
        keywords: [...selectedKeywords],
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan fehlgeschlagen");
    deviceStates.set(devicePath, "complete");
    deviceErrors.delete(devicePath);
    await loadCase(data.media.case_number);
    $("results").hidden = true;
  } catch (error) {
    $("progressLabel").textContent = `FEHLER: ${error.message}`;
    deviceErrors.set(devicePath, error.message);
    deviceStates.set(devicePath, error.message.includes("Zeitlimit") ? "timeout" : "error");
    setSystemState("SCAN FEHLGESCHLAGEN", "error");
  } finally {
    runningPaths.delete(devicePath);
    batchDone += 1;
    renderDevices(devices);
    updateProgress();
    updateScanAvailability();
  }
}

async function runReadyScans() {
  if (deviceDiscoveryError) return;
  const paths = devices
    .filter((device) => device.scan_supported && deviceStates.get(device.path) === "ready")
    .map((device) => device.path);
  if (!paths.length) return;
  batchTotal = paths.length;
  batchDone = 0;
  await Promise.allSettled(paths.map((path) => runScan(path, false)));
  await refresh(false);
}

function maybeAutoScan() {
  if (deviceDiscoveryError) return;
  if (!$("autoScanToggle").checked) return;
  if (!activeCaseNumber || !activeOperator) return;
  const ready = devices.some((device) => device.scan_supported && deviceStates.get(device.path) === "ready");
  if (ready) runReadyScans();
}

function scheduleAutoScan(delay = 700) {
  clearTimeout(autoStartTimer);
  autoStartTimer = setTimeout(maybeAutoScan, delay);
}

async function saveDecision() {
  if (!currentMediaId || !currentDecision) return;
  const mediaId = currentMediaId;
  const revision = mediaViewRevision;
  $("saveDecision").disabled = true;
  $("decisionMessage").textContent = "Wird protokolliert …";
  try {
    const response = await fetch(`/api/media/${mediaId}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: currentDecision,
        evidence_number: currentDecision === "secure" ? $("decisionEvidence").value.trim().toUpperCase().replace(/[^A-Z0-9._-]/g, "-").slice(0, 80) : null,
        reason_code: currentDecision === "secure" ? null : ($("decisionReason").value || null),
        reason_note: currentDecision === "secure" ? "" : $("decisionNote").value,
        specialist_name: currentDecision === "specialist_consulted" ? $("decisionSpecialist").value.trim() : null,
        operator: activeOperator,
      }),
    });
    const data = await response.json();
    if (revision !== mediaViewRevision || mediaId !== currentMediaId) return;
    if (!response.ok) throw new Error(data.error || "Entscheidung konnte nicht gespeichert werden");
    if (data.media) currentCaseMedia = currentCaseMedia.map((medium) => Number(medium.id) === Number(data.media.id) ? data.media : medium);
    const continueQueue = returnToDecisionQueue;
    renderRecord(data);
    $("decisionMessage").textContent = "ENTSCHEIDUNG MIT ZEITSTEMPEL PROTOKOLLIERT";
    if (continueQueue) {
      returnToDecisionQueue = false;
      decisionQueueDeferred = false;
      showDashboard();
      if (pendingOfflineMedia().length) openDecisionQueue();
      else setSystemState("ALLE ENTSCHEIDUNGEN DOKUMENTIERT", "ready");
    }
  } catch (error) {
    if (revision !== mediaViewRevision || mediaId !== currentMediaId) return;
    $("decisionMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    updateDecisionAvailability();
  }
}

function archiveStatusMark(file) {
  if (file.source === "container_index") return "";
  if (file.archive_encryption === "encrypted") return '<span class="archive-mark encrypted">VERSCHLÜSSELT</span>';
  if (file.archive_encryption === "unknown") return '<span class="archive-mark unknown" title="Verschlüsselungsstatus nicht geklärt; nicht gleichbedeutend mit unverschlüsselt">UNGEPRÜFT</span>';
  return "";
}

function treeEntriesHtml(entries, containerPath = "") {
  return entries.map((entry) => {
    if (entry.kind === "directory") {
      const sizeLabel = entry.size_known === false ? "GRÖSSE NICHT INDEXIERT" : formatBytes(entry.size);
      return `<details class="tree-folder" data-loaded="false">
        <summary ${containerPath ? `data-container-path="${escapeHtml(containerPath)}" data-container-prefix="${escapeHtml(entry.path)}"` : `data-tree-prefix="${escapeHtml(entry.path)}"`}><span class="tree-arrow">▶</span><b>${escapeHtml(entry.name)}</b><small>${Number(entry.file_count).toLocaleString("de-AT")} DATEIEN · ${sizeLabel}</small></summary>
        <div class="tree-children"><p class="tree-loading">ORDNER ÖFFNEN …</p></div>
      </details>`;
    }
    if (entry.kind === "container") {
      const format = String(entry.container_format || "CONTAINER").toUpperCase();
      const stateLabels = {
        invalid_or_unsupported: "NICHT LESBAR",
        encrypted_headers: "NAMEN NICHT SICHTBAR",
        incomplete: "UNVOLLSTÄNDIG",
        tool_unavailable: "WERKZEUG FEHLT",
      };
      const state = stateLabels[entry.container_status]
        || (entry.truncated ? `${Number(entry.entry_count).toLocaleString("de-AT")} EINTRÄGE · LIMIT`
          : `${Number(entry.entry_count).toLocaleString("de-AT")} EINTRÄGE`);
      const marker = archiveStatusMark(entry);
      const encryptionState = !marker && entry.encrypted ? " · VERSCHLÜSSELT" : "";
      return `<details class="tree-folder tree-container" data-loaded="false" data-archive-state="${escapeHtml(entry.archive_encryption || "")}">
        <summary data-container-path="${escapeHtml(entry.container_id || entry.path)}" data-container-prefix=""><span class="tree-arrow">▶</span><b>${escapeHtml(entry.name)}</b><small>${marker}${escapeHtml(state + encryptionState)}</small></summary>
        <div class="tree-children"><p class="tree-loading">${escapeHtml(format)}-VERZEICHNIS ÖFFNEN …</p></div>
      </details>`;
    }
    return `<div class="tree-file"><span>·</span><b>${escapeHtml(entry.name)}</b><small>${archiveStatusMark(entry)}${escapeHtml(entry.category)} · ${entry.size_known === false ? "GRÖSSE NICHT INDEXIERT" : formatBytes(entry.size)}</small></div>`;
  }).join("") || '<p class="tree-loading">ORDNER IST LEER</p>';
}

function inventoryRowsHtml(files) {
  return files.map((file) => {
    const path = escapeHtml(file.path);
    const pathCell = file.container_id
      ? `<button class="inventory-container-toggle" type="button" data-container-path="${escapeHtml(file.container_id)}" aria-expanded="false"><span>▶</span><b>${path}</b></button>`
      : path;
    const inside = file.source === "container_index";
    const location = inside ? `IM ${String(file.container_format || "ARCHIV").toUpperCase()}` : "AUF DEM MEDIUM";
    const nested = inside && ["Archive", "Datenträger-/Backup-Images"].includes(file.category);
    const note = nested ? '<small class="inventory-entry-note">VERSCHACHTELT · NICHT WEITER GEÖFFNET</small>' : "";
    const matchNote = file.match_source && (!inside || !file.match_source.endsWith("-INHALT") || file.match_source.includes(" · "))
      ? `<small class="inventory-entry-note">${escapeHtml(file.match_source)}</small>` : "";
    const marker = archiveStatusMark(file);
    const statusNote = marker ? `<small class="inventory-archive-state">${marker}</small>` : "";
    const row = `<tr${inside ? ' class="inventory-inner-file"' : ""}><td title="${path}">${pathCell}${statusNote}${note}</td><td><span class="inventory-location">${escapeHtml(location)}</span>${matchNote}</td><td>${escapeHtml(file.category)}</td><td>${escapeHtml(file.extension || "—")}</td><td>${file.size_known === false ? "—" : formatBytes(file.size)}</td></tr>`;
    if (!file.container_id) return row;
    return `${row}<tr class="inventory-container-detail" hidden><td colspan="5"><div class="tree-children"><p class="tree-loading">ARCHIVVERZEICHNIS ÖFFNEN …</p></div></td></tr>`;
  }).join("") || '<tr class="inventory-empty"><td colspan="5">KEINE PASSENDEN DATEIEN GEFUNDEN</td></tr>';
}

function clearInventoryView() {
  inventoryViewRevision += 1;
  inventoryTreeMediaId = null;
  inventoryListState = null;
  clearInventoryFilterState();
  $("inventoryTree").innerHTML = "";
  $("inventoryTree").hidden = false;
  $("inventoryFiles").innerHTML = "";
  $("inventorySearchResults").hidden = true;
  $("inventoryFilterBar").hidden = true;
  $("inventoryReset").hidden = true;
  $("inventoryMore").hidden = true;
  $("inventorySearch").value = "";
  $("inventoryCount").textContent = "—";
}

function invalidateMediaView() {
  mediaViewRevision += 1;
  caseLoadRevision += 1;
  currentMediaId = null;
  currentDecision = null;
  clearInventoryView();
  updateDecisionAvailability();
}

function beginInventoryRequest(target) {
  // Bind responses to the view incarnation, not just an ID: A → B → A must
  // also reject the first A's response. Per-target tokens keep sibling folders independent.
  const request = { mediaId: currentMediaId, mediaRevision: mediaViewRevision, inventoryRevision: inventoryViewRevision };
  inventoryRequests.set(target, request);
  return request;
}

function inventoryRequestIsCurrent(target, request) {
  return target.isConnected && inventoryRequests.get(target) === request
    && currentMediaId === request.mediaId && mediaViewRevision === request.mediaRevision
    && inventoryViewRevision === request.inventoryRevision;
}

async function loadInventoryTree(prefix = "", target = $("inventoryTree"), offset = 0) {
  if (!currentMediaId) return;
  const request = beginInventoryRequest(target);
  const moreButton = target.querySelector(":scope > .tree-more");
  if (offset === 0) target.innerHTML = '<p class="tree-loading">VERZEICHNIS WIRD GELADEN …</p>';
  else if (moreButton) moreButton.disabled = true;
  target.querySelector(":scope > .tree-page-error")?.remove();
  try {
    const response = await fetch(`/api/media/${request.mediaId}/tree?prefix=${encodeURIComponent(prefix)}&limit=300&offset=${offset}`);
    const data = await response.json();
    if (!inventoryRequestIsCurrent(target, request)) return;
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    const entries = treeEntriesHtml(data.entries || []);
    if (offset === 0) target.innerHTML = entries;
    else { moreButton?.remove(); target.insertAdjacentHTML("beforeend", entries); }
    if (data.has_more) target.insertAdjacentHTML("beforeend", `<button class="tree-more" type="button" data-tree-prefix="${escapeHtml(prefix)}" data-tree-offset="${Number(data.next_offset)}">WEITERE EINTRÄGE LADEN</button>`);
    const folderOwner = target.closest(".tree-folder");
    if (folderOwner) folderOwner.dataset.loaded = "true";
    if (target === $("inventoryTree")) {
      inventoryTreeMediaId = request.mediaId;
      $("inventoryCount").textContent = `${data.total} EINTRÄGE AUF DIESER EBENE`;
    }
    if (prefix === "" && offset === 0 && data.entries?.length === 1 && data.entries[0].kind === "directory") {
      const folder = target.querySelector(":scope > .tree-folder");
      if (folder) {
        folder.open = true;
        await loadInventoryTree(data.entries[0].path, folder.querySelector(".tree-children"));
      }
    }
  } catch (error) {
    if (!inventoryRequestIsCurrent(target, request)) return;
    const message = `<p class="tree-loading error tree-page-error">FEHLER: ${escapeHtml(error.message)}</p>`;
    if (offset === 0) target.innerHTML = message;
    else { target.insertAdjacentHTML("beforeend", message); if (moreButton) moreButton.disabled = false; }
  }
}

async function loadContainerTree(containerPath, prefix = "", target, offset = 0) {
  if (!currentMediaId || !target) return;
  const request = beginInventoryRequest(target);
  const moreButton = target.querySelector(":scope > .tree-more");
  if (offset === 0) target.innerHTML = '<p class="tree-loading">CONTAINER-VERZEICHNIS WIRD GELADEN …</p>';
  else if (moreButton) moreButton.disabled = true;
  target.querySelector(":scope > .tree-page-error")?.remove();
  try {
    const parameters = new URLSearchParams({ path: containerPath, prefix, limit: "300", offset: String(offset) });
    const response = await fetch(`/api/media/${request.mediaId}/container?${parameters}`);
    const data = await response.json();
    if (!inventoryRequestIsCurrent(target, request)) return;
    if (!response.ok) throw new Error(data.error || "Container-Verzeichnis nicht verfügbar");
    let entries = treeEntriesHtml(data.entries || [], containerPath);
    if (!(data.entries || []).length) {
      const emptyLabels = {
        invalid_or_unsupported: "VERZEICHNIS NICHT LESBAR ODER NICHT UNTERSTÜTZT",
        encrypted_headers: "DATEINAMEN VERSCHLÜSSELT · KEIN PASSWORTVERSUCH",
        incomplete: "ARCHIV UNVOLLSTÄNDIG ODER TEILVOLUME FEHLT",
        tool_unavailable: "7ZIP-WERKZEUG NICHT INSTALLIERT",
        limit_reached: "ZEIT- ODER MENGENLIMIT ERREICHT",
      };
      entries = emptyLabels[data.container_status]
        ? `<p class="tree-loading error">${emptyLabels[data.container_status]}</p>`
        : '<p class="tree-loading">CONTAINER IST LEER</p>';
    }
    if (offset === 0) target.innerHTML = entries;
    else { moreButton?.remove(); target.insertAdjacentHTML("beforeend", entries); }
    if (data.has_more) target.insertAdjacentHTML("beforeend", `<button class="tree-more" type="button" data-container-path="${escapeHtml(containerPath)}" data-container-prefix="${escapeHtml(prefix)}" data-container-offset="${Number(data.next_offset)}">WEITERE EINTRÄGE LADEN</button>`);
    if (data.truncated && offset === 0) target.insertAdjacentHTML("beforeend", '<p class="tree-loading warning">SCHNELLINDEX-LIMIT ERREICHT · VERZEICHNIS IST UNVOLLSTÄNDIG</p>');
    const owner = target.closest(".tree-folder, .inventory-container-detail");
    if (owner) owner.dataset.loaded = "true";
  } catch (error) {
    if (!inventoryRequestIsCurrent(target, request)) return;
    const message = `<p class="tree-loading error tree-page-error">FEHLER: ${escapeHtml(error.message)}</p>`;
    if (offset === 0) target.innerHTML = message;
    else { target.insertAdjacentHTML("beforeend", message); if (moreButton) moreButton.disabled = false; }
  }
}

function clearInventoryFilterState() {
  for (const button of document.querySelectorAll(".result-filter")) {
    button.classList.remove("active");
    button.setAttribute("aria-pressed", "false");
  }
}

async function resetInventoryView() {
  clearInventoryView();
  await loadInventoryTree();
}

async function loadInventory({ category = "", keyword = "", search = null, exactPath = null, archiveStatus = "", offset = 0 } = {}) {
  if (!currentMediaId) return;
  const searchText = search === null ? $("inventorySearch").value.trim() : search;
  if (!searchText && !category && !keyword && exactPath === null && !archiveStatus) {
    $("inventorySearch").focus();
    return;
  }
  if (exactPath !== null || (searchText && !category && !keyword && !archiveStatus)) clearInventoryFilterState();
  if (offset === 0) {
    inventoryViewRevision += 1;
    inventoryListState = { category, keyword, search: searchText, exactPath, archiveStatus, nextOffset: 0 };
    $("inventoryFiles").innerHTML = '<tr><td colspan="5">FUNDSTELLEN WERDEN GELADEN …</td></tr>';
  }
  const target = $("inventoryFiles");
  const request = beginInventoryRequest(target);
  $("inventoryTree").hidden = true;
  $("inventorySearchResults").hidden = false;
  const filterLabel = archiveStatus ? `ARCHIVE: ${archiveStatus === "encrypted" ? "VERSCHLÜSSELT" : "UNGEPRÜFT"}` : exactPath !== null ? `DATEI: ${exactPath}` : category ? `DATEITYP: ${category}` : keyword ? `STICHWORT: ${keyword}` : `SUCHE: ${searchText}`;
  $("inventoryFilterLabel").textContent = filterLabel.toUpperCase();
  $("inventoryFilterLabel").title = filterLabel;
  $("inventoryFilterDescription").textContent = archiveStatus
    ? "Nur Archivdateien auf dem Medium. Ungeprüft = Verschlüsselungsstatus nicht geklärt."
    : "Auf dem Medium und in lesbaren Archivverzeichnissen. Inhalte werden nicht zusätzlich zur Dateizahl gezählt.";
  $("inventoryFilterBar").hidden = false;
  $("inventoryReset").hidden = false;
  $("inventoryMore").hidden = true;
  $("inventoryCount").textContent = "LÄDT …";
  try {
    const parameters = new URLSearchParams({ limit: "250", offset: String(offset) });
    if (searchText) parameters.set("q", searchText);
    if (category) parameters.set("category", category);
    if (keyword) parameters.set("keyword", keyword);
    if (exactPath !== null) parameters.set("exact_path", exactPath);
    if (archiveStatus) parameters.set("archive_status", archiveStatus);
    const response = await fetch(`/api/media/${request.mediaId}/files?${parameters}`);
    const data = await response.json();
    if (!inventoryRequestIsCurrent(target, request)) return;
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    const visible = Number(data.offset || 0) + Number(data.shown || 0);
    $("inventoryCount").textContent = `${visible} / ${data.total} FUNDSTELLEN`;
    const rows = inventoryRowsHtml(data.files);
    if (offset === 0) $("inventoryFiles").innerHTML = rows;
    else $("inventoryFiles").insertAdjacentHTML("beforeend", rows);
    inventoryListState = { category, keyword, search: searchText, exactPath, archiveStatus, nextOffset: Number(data.next_offset || visible) };
    $("inventoryMore").hidden = !data.has_more;
  } catch (error) {
    if (!inventoryRequestIsCurrent(target, request)) return;
    $("inventoryCount").textContent = `FEHLER: ${error.message}`;
    if (offset === 0) target.innerHTML = `<tr><td colspan="5">FEHLER: ${escapeHtml(error.message)}</td></tr>`;
    else $("inventoryMore").hidden = false;
  }
}

async function startCaseSession() {
  const caseNumber = $("caseNumber").value.trim().toUpperCase().replace(/[^A-Z0-9._-]/g, "-").slice(0, 80);
  const operator = $("operator").value.trim().toUpperCase();
  if (!caseNumber) { $("caseNumber").focus(); return; }
  if (!operator) { $("operator").focus(); return; }
  if (runningPaths.size) {
    updateCaseSessionUi("FALLWECHSEL WÄHREND EINES SCANS GESPERRT");
    return;
  }
  $("caseStart").disabled = true;
  $("caseStartMessage").textContent = "FALL WIRD GESTARTET …";
  caseSessionTransition = true;
  try {
    const response = await fetch("/api/cases/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_number: caseNumber, operator }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Fall konnte nicht gestartet werden");
    activeCaseNumber = data.case.case_number;
    invalidateMediaView();
    activeOperator = operator;
    serverActiveCase = { case_number: activeCaseNumber, operator: activeOperator };
    $("caseNumber").value = activeCaseNumber;
    currentMediaId = null;
    currentCaseMedia = [];
    caseHistorySignature = "";
    await loadCase(activeCaseNumber);
    resetDeviceStatesForCase();
    renderDevices(devices);
    updateCaseSessionUi(`FALL ${activeCaseNumber} AKTIV · SCANS FREIGEGEBEN`);
    setSystemState("BEREIT", "ready");
    $("auftragModal").close();
    updateStartOverlay();
    await refresh(false);
    scheduleAutoScan(150);
  } catch (error) {
    $("caseStartMessage").textContent = `FEHLER: ${error.message}`;
    $("caseStartMessage").className = "case-start-message warning";
    updateCaseSessionUi($("caseStartMessage").textContent);
  } finally {
    caseSessionTransition = false;
  }
}

async function stopCaseSession({ keepUpdateOpen = false } = {}) {
  if (runningPaths.size || caseSessionTransition) return false;
  invalidateMediaView();
  caseSessionTransition = true;
  clearTimeout(autoStartTimer);
  if (activeCaseNumber && !serverActiveCase) serverActiveCase = { case_number: activeCaseNumber, operator: activeOperator };
  activeCaseNumber = null;
  activeOperator = "";
  currentCaseMedia = [];
  currentMediaId = null;
  currentDecision = null;
  inventoryTreeMediaId = null;
  $("caseNumber").value = "";
  $("operator").value = "";
  $("casePanel").hidden = true;
  $("results").hidden = true;
  $("dashboardView").hidden = false;
  setCaseDownloads();
  caseHistorySignature = "";
  resetDeviceStatesForCase();
  renderDevices(devices);
  renderCaseHistory(knownCases);
  updateCaseSessionUi("FALL BEENDET · SCANS GESPERRT");
  setSystemState("GESPERRT", "locked");
  updateStartOverlay();
  if (!keepUpdateOpen) openAuftrag();
  try {
    const response = await fetch("/api/cases/stop", { method: "POST" });
    if (!response.ok) throw new Error("Fall konnte am Gerät nicht beendet werden");
    serverActiveCase = null;
    updateStartOverlay();
    renderUpdateState(updateState);
  } catch (error) {
    $("caseStartMessage").textContent = `FEHLER: ${error.message}`;
    caseSessionTransition = false;
    await refresh(false);
    return false;
  } finally {
    caseSessionTransition = false;
    renderUpdateState(updateState);
  }
  return true;
}

async function deleteCurrentCase() {
  const caseNumber = deleteTargetCaseNumber;
  if (!caseNumber || caseNumber === activeCaseNumber) return;
  if (!$("deleteConfirmed").checked) {
    $("deleteMessage").textContent = "BITTE DAS ENTFERNEN DIESES FALLS AUSDRÜCKLICH BESTÄTIGEN.";
    return;
  }
  $("deleteMessage").textContent = "FALL WIRD ENTFERNT …";
  try {
    const response = await fetch(`/api/cases/${encodeURIComponent(caseNumber)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: caseNumber }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Fall konnte nicht gelöscht werden");
    $("deleteModal").close();
    $("deleteConfirmed").checked = false;
    $("confirmDelete").disabled = true;
    if ($("caseNumber").value.trim().toUpperCase() === caseNumber) $("caseNumber").value = "";
    deleteTargetCaseNumber = null;
    caseHistorySignature = "";
    await refresh(false);
    updateCaseSessionUi(`FALL ${caseNumber} AUS DEM ARCHIV ENTFERNT`);
  } catch (error) {
    $("deleteMessage").textContent = `FEHLER: ${error.message}`;
  }
}

async function ejectDevice(devicePath) {
  if (deviceDiscoveryError) return;
  setSystemState("DATENTRÄGER WIRD AUSGEWORFEN …", "busy");
  try {
    const response = await fetch("/api/devices/eject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_path: devicePath }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Auswerfen fehlgeschlagen");
    setSystemState(
      data.media_type === "optical" ? "CD/DVD-LAUFWERK GEÖFFNET" : "DATENTRÄGER KANN ABGEZOGEN WERDEN",
      "ready",
    );
    await refresh(false);
  } catch (error) {
    setSystemState(`FEHLER: ${error.message}`, "error");
  }
}

async function openMedia(mediaId) {
  invalidateMediaView();
  const revision = mediaViewRevision;
  $("results").hidden = true;
  $("dashboardView").hidden = false;
  setSystemState("SICHTUNG LÄDT …", "busy");
  try {
    const response = await fetch(`/api/media/${mediaId}`);
    const data = await response.json();
    if (revision !== mediaViewRevision) return;
    if (!response.ok) throw new Error(data.error || "Medienakte nicht verfügbar");
    renderRecord(data);
    renderMediaCards(currentCaseMedia);
    $("dashboardView").hidden = true;
    $("results").hidden = false;
    $("results").scrollIntoView({ behavior: "smooth", block: "start" });
    setSystemState(activeCaseNumber ? "BEREIT" : "GESPERRT");
  } catch (error) {
    if (revision !== mediaViewRevision) return;
    setSystemState(`FEHLER: ${error.message}`, "error");
  }
}

function showDashboard() {
  const reopenDecisionQueue = returnToDecisionQueue;
  returnToDecisionQueue = false;
  invalidateMediaView();
  if ($("evidenceModal").open) $("evidenceModal").close();
  if ($("deleteModal").open) $("deleteModal").close();
  if ($("caseArchiveModal").open) $("caseArchiveModal").close();
  if ($("auftragModal").open) $("auftragModal").close();
  $("results").hidden = true;
  $("dashboardView").hidden = false;
  currentMediaId = null;
  renderMediaCards(currentCaseMedia);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (reopenDecisionQueue) {
    decisionQueueDeferred = false;
    openDecisionQueue();
  }
}

function openProfileEditor(profileId = null, duplicate = false) {
  const createNew = profileId === null || duplicate;
  const detail = profileDetails.get(profileId);
  profileEditorId = createNew ? null : profileId;
  profileDetailId = profileEditorId;
  keywordDraft = [...(detail?.keywords || [])];
  draftSelectedKeywords = new Set(duplicate ? keywordDraft : selectedByProfile.get(profileId) || keywordDraft);
  $("profileDetailName").value = duplicate ? `${(detail?.name || "Profil").slice(0, 34)} Kopie` : detail?.name || "";
  $("profileDetailTitle").textContent = createNew ? "NEUES PROFIL" : "PROFIL BEARBEITEN";
  $("profileDetailNewInput").value = "";
  $("profileDetailMessage").textContent = "";
  $("profileDetailApply").hidden = createNew;
  profileDetailDirty = false;
  $("profileDetailEmpty").hidden = true;
  $("profileDetailForm").hidden = false;
  renderKeywordOptions();
  updateProfileDetailCount();
  renderProfileList();
  if (!$("settingsModal").open) $("settingsModal").showModal();
  selectSettingsPane("profiles");
  if (createNew) $("profileDetailName").focus();
}

function addKeywordFromInput() {
  const input = $("profileDetailNewInput");
  const keyword = input.value.trim();
  if (!keyword) return;
  if (keywordDraft.some((item) => item.toLocaleLowerCase("de") === keyword.toLocaleLowerCase("de"))) {
    $("profileDetailMessage").textContent = "DIESES STICHWORT IST BEREITS VORHANDEN";
    return;
  }
  keywordDraft.push(keyword);
  draftSelectedKeywords.add(keyword);
  input.value = "";
  $("profileDetailMessage").textContent = "";
  profileDetailDirty = true;
  renderKeywordOptions();
  updateProfileDetailCount();
  input.focus();
}

function selectedDraftFromControls() {
  return new Set([...$("profileDetailOptions").querySelectorAll("input:checked")].map((input) => input.value));
}

function markProfileDetailDirty() {
  profileDetailDirty = true;
  $("profileDetailMessage").textContent = "UNGESPEICHERTE ÄNDERUNGEN";
}

async function saveProfileEditor() {
  const name = $("profileDetailName").value.trim();
  if (!name) { $("profileDetailName").focus(); $("profileDetailMessage").textContent = "PROFILNAME ERFORDERLICH"; return; }
  draftSelectedKeywords = selectedDraftFromControls();
  $("profileDetailSave").disabled = true;
  $("profileDetailMessage").textContent = "PROFIL WIRD GESPEICHERT …";
  try {
    const response = await fetch("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: profileEditorId, name, keywords: keywordDraft }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Profil konnte nicht gespeichert werden");
    const savedSelection = new Set([...draftSelectedKeywords].filter((word) => data.profile.keywords.includes(word)));
    selectedByProfile.set(data.profile.id, savedSelection);
    profileEditorId = data.profile.id;
    profileDetailId = data.profile.id;
    await loadProfiles(activeProfileIds);
    updateKeywordSummary();
    profileDetailDirty = false;
    $("profileDetailMessage").textContent = "GESPEICHERT";
    $("profileDetailTitle").textContent = "PROFIL BEARBEITEN";
    renderProfileList();
    setSystemState(`PROFIL ${data.profile.name.toUpperCase()} GESPEICHERT`, "ready");
  } catch (error) {
    $("profileDetailMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    $("profileDetailSave").disabled = false;
  }
}

function applyProfileSelection() {
  if (profileEditorId) {
    const selected = selectedDraftFromControls();
    selectedByProfile.set(profileEditorId, selected);
    updateKeywordSummary();
    updateCaseSessionUi();
    $("profileDetailMessage").textContent = "AUSWAHL FÜR NÄCHSTE SCANS ÜBERNOMMEN";
  }
}

function canSwitchProfileDetail() {
  if (!profileDetailDirty) return true;
  return window.confirm("Ungespeicherte Änderungen am Profil verwerfen?");
}

function resetProfileDetail() {
  $("profileDetailEmpty").hidden = false;
  $("profileDetailForm").hidden = true;
  profileDetailId = null;
  profileEditorId = null;
  profileDetailDirty = false;
  keywordDraft = [];
  draftSelectedKeywords = new Set();
  renderProfileList();
}

const clockFormatter = new Intl.DateTimeFormat("de-AT", {
  hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
});
function updateClock() { $("clock").textContent = `LOKAL ${clockFormatter.format(new Date())}`; }
updateClock();
setInterval(updateClock, 1000);
$("autoScanToggle").addEventListener("change", () => {
  updateOrderSummary();
  if (!activeCaseNumber) setSystemState("GESPERRT", "locked");
  scheduleAutoScan(100);
});
$("deviceRefresh").addEventListener("click", refreshMediaDevices);
$("deviceList").addEventListener("click", (event) => {
  const eject = event.target.closest("button[data-eject-device]");
  if (eject) { ejectDevice(eject.dataset.ejectDevice); return; }
  const button = event.target.closest("button[data-scan-device]");
  if (button) runScan(button.dataset.scanDevice);
});
$("mediaCards").addEventListener("click", (event) => {
  const eject = event.target.closest("button[data-eject-device]");
  if (eject) { ejectDevice(eject.dataset.ejectDevice); return; }
  const card = event.target.closest("button[data-media-id]");
  if (card) openMedia(Number(card.dataset.mediaId));
});
$("offlineMediaCards").addEventListener("click", (event) => {
  const card = event.target.closest("button[data-media-id]");
  if (card) openMedia(Number(card.dataset.mediaId));
});
$("pendingDecisionBanner").addEventListener("click", () => {
  decisionQueueDeferred = false;
  openDecisionQueue();
});
$("decisionQueueList").addEventListener("click", (event) => {
  const item = event.target.closest("button[data-queue-media-id]");
  if (!item) return;
  returnToDecisionQueue = true;
  $("decisionQueueModal").close();
  openMedia(Number(item.dataset.queueMediaId));
});
$("closeDecisionQueue").addEventListener("click", () => {
  decisionQueueDeferred = true;
  returnToDecisionQueue = false;
  $("decisionQueueModal").close();
});
$("decisionQueueModal").addEventListener("cancel", (event) => {
  event.preventDefault();
  decisionQueueDeferred = true;
  returnToDecisionQueue = false;
  $("decisionQueueModal").close();
});
$("decisionQueueModal").addEventListener("click", (event) => {
  if (event.target !== $("decisionQueueModal")) return;
  decisionQueueDeferred = true;
  returnToDecisionQueue = false;
  $("decisionQueueModal").close();
});
$("homeLogo").addEventListener("click", showDashboard);
$("openPowerModal").addEventListener("click", openPowerDialog);
$("closePowerModal").addEventListener("click", () => $("powerModal").close());
$("powerModal").addEventListener("cancel", (event) => {
  if (powerActionInProgress) event.preventDefault();
});
$("powerModal").addEventListener("close", () => {
  if (powerActionInProgress) return;
  pendingPowerAction = null;
  $("powerConfirmation").hidden = true;
  $("powerActions").hidden = false;
});
$("powerActions").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-power-action]");
  if (button) choosePowerAction(button.dataset.powerAction);
});
$("cancelPowerAction").addEventListener("click", () => {
  pendingPowerAction = null;
  $("powerConfirmation").hidden = true;
  $("powerActions").hidden = false;
  renderPowerState(powerState);
});
$("confirmPowerAction").addEventListener("click", confirmPowerAction);
$("openAuftragModal").addEventListener("click", openAuftrag);
$("startOpenCase").addEventListener("click", openAuftrag);
$("startOverlaySettings").addEventListener("click", () => openSettings());
$("startOverlayPower").addEventListener("click", () => openPowerDialog());
$("openSettings").addEventListener("click", () => openSettings());
$("closeSettings").addEventListener("click", closeSettings);
$("settingsModal").addEventListener("cancel", (event) => { event.preventDefault(); closeSettings(); });
$("settingsModal").addEventListener("click", (event) => { if (event.target === $("settingsModal")) closeSettings(); });
$("settingsProfilesTab").addEventListener("click", () => selectSettingsPane("profiles"));
$("settingsFiletypesTab").addEventListener("click", () => selectSettingsPane("filetypes"));
$("settingsCryptoTab").addEventListener("click", () => selectSettingsPane("crypto"));
$("settingsUpdatesTab").addEventListener("click", () => selectSettingsPane("updates"));
for (const [key] of Object.entries(detectionSectionLabels)) {
  const tab = $(`detection${key[0].toUpperCase()}${key.slice(1)}Tab`);
  if (tab) tab.addEventListener("click", () => selectDetectionSection(key));
}
$("detectionSearch").addEventListener("input", () => { filterDetectionRules(); sortDetectionRules(); });
$("detectionFilter").addEventListener("change", () => { filterDetectionRules(); sortDetectionRules(); });
$("detectionSort").addEventListener("change", sortDetectionRules);
$("detectionRows").addEventListener("click", event => {
  const row = event.target.closest("tr[data-id]");
  if (!row || !detectionState) return;
  const id = row.dataset.id;
  const found = getRuleById(id);
  if (!found) return;
  detectionSelectedRuleId = id;
  detectionEditedRule = cloneRule(found.rule);
  $("detectionRows").querySelectorAll("tr").forEach(r => r.classList.toggle("active", r.dataset.id === id));
  renderDetectionEditor();
});
$("detectionAdd").addEventListener("click", () => {
  if (!detectionState || detectionBusy) return;
  const kind = detectionKindForSection[detectionSection];
  const baseId = `neu-${detectionSection}-${Date.now().toString(36)}`;
  let newRule;
  if (kind === "app_rules") {
    const category = detectionSection === "banking" ? "banking" : "wallet";
    const relevance = detectionSection === "banking" ? "neutral" : "high";
    newRule = { id: baseId, name: "Neue Regel", category, relevance, enabled: true, ios_bundle_ids: [], android_package_ids: [], ios_id_status: "unverified", android_id_status: "unverified", ios_id_note: "", android_id_note: "", aliases: [], former_names: [], terms: [], comment: "", status: "active", verified: false, source: "", last_verified: "", regions: [] };
  } else if (kind === "file_rules") {
    newRule = { id: baseId, name: "Neue Dateiregel", category: "portfolio", relevance: "medium", enabled: true, filename_equals: [], terms: [], context_terms: [], extensions: [], comment: "", status: "active", verified: false, source: "", last_verified: "", regions: [] };
  } else {
    newRule = { id: baseId, name: "Neue Backup-Regel", platform: "", status: "active", confidence: "medium", enabled: true, required_paths: [], required_files: [], required_extensions: [], typical_paths: [], source: "", last_verified: "", comment: "" };
  }
  // If a previously deleted default rule is re-added under the same id, clear tombstone.
  detectionDeletedRuleIds.delete(newRule.id);
  const kindKey = kind;
  detectionState[kindKey] = [...detectionState[kindKey], newRule];
  detectionSelectedRuleId = newRule.id;
  detectionEditedRule = cloneRule(newRule);
  markDetectionDirty();
  renderDetectionRules();
  renderDetectionEditor();
});
$("detectionDuplicate").addEventListener("click", () => {
  if (!detectionEditedRule || detectionBusy) return;
  const kind = detectionKindForSection[detectionSection];
  const copy = cloneRule(detectionEditedRule);
  copy.id = `${copy.id}-kopie-${Date.now().toString(36)}`;
  copy.name = `${copy.name} (Kopie)`;
  detectionState[kind] = [...detectionState[kind], copy];
  detectionSelectedRuleId = copy.id;
  detectionEditedRule = cloneRule(copy);
  markDetectionDirty();
  renderDetectionRules();
  renderDetectionEditor();
});
$("detectionDelete").addEventListener("click", () => {
  if (!detectionEditedRule || detectionBusy) return;
  if (!window.confirm(`Regel „${detectionEditedRule.name || detectionEditedRule.id}" wirklich löschen?`)) return;
  const kind = detectionKindForSection[detectionSection];
  const deletedId = detectionEditedRule.id;
  const defaults = bundledCryptoRules;
  const defaultIds = defaults ? new Set([...defaults.app_rules.map(r => r.id), ...defaults.file_rules.map(r => r.id), ...defaults.backup_rules.map(r => r.id)]) : new Set();
  if (defaultIds.has(deletedId)) {
    detectionDeletedRuleIds.add(deletedId);
  }
  detectionState[kind] = detectionState[kind].filter(rule => rule.id !== deletedId);
  detectionSelectedRuleId = null;
  detectionEditedRule = null;
  markDetectionDirty();
  renderDetectionRules();
});
$("detectionCancel").addEventListener("click", cancelDetectionEditor);
$("detectionApply").addEventListener("click", applyDetectionEditor);
$("detectionSaveAll").addEventListener("click", saveDetectionRules);
$("detectionEditorFields").addEventListener("input", () => {
  const updated = readDetectionEditor();
  if (updated) {
    detectionEditedRule = updated;
    markDetectionDirty();
  }
});
$("detectionEditorFields").addEventListener("scroll", hideTooltip);
$("detectionTableWrap")?.addEventListener("scroll", hideTooltip);
$("detectionGlossaryButton")?.addEventListener("click", openDetectionGlossary);
$("detectionGlossaryClose")?.addEventListener("click", closeDetectionGlossary);
$("detectionGlossaryDialog")?.addEventListener("cancel", closeDetectionGlossary);
$("detectionGlossaryDialog")?.addEventListener("click", event => {
  if (event.target === $("detectionGlossaryDialog")) closeDetectionGlossary();
});
$("detectionExport").addEventListener("click", () => {
  if (!detectionState) return;
  const blob = new Blob([JSON.stringify({ version: detectionState.version, ...detectionDraft() }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a"); link.href = url; link.download = "triagebox-erkennungsregeln.json"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$("detectionImport").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file || !detectionState) return;
  try {
    if (file.size > 786432) throw new Error("Datei zu groß (maximal 768 KB).");
    const imported = JSON.parse(await file.text());
    if (!Array.isArray(imported.app_rules) || !Array.isArray(imported.file_rules)) throw new Error("Keine gültige Regelsammlung.");
    detectionState = {
      ...detectionState,
      app_rules: imported.app_rules,
      file_rules: imported.file_rules,
      backup_rules: imported.backup_rules || detectionState.backup_rules || [],
    };
    if (Array.isArray(imported.deleted_default_rule_ids)) {
      detectionDeletedRuleIds = new Set(imported.deleted_default_rule_ids);
    }
    markDetectionDirty();
    selectDetectionSection(detectionSection);
    $("detectionMessage").textContent = "IMPORTIERT · BITTE PRÜFEN UND SPEICHERN";
  } catch (error) {
    $("detectionMessage").textContent = `IMPORT FEHLGESCHLAGEN: ${error.message}`;
  } finally { event.target.value = ""; }
});
document.addEventListener("click", event => {
  if (!event.target.closest(".info-tooltip") && !event.target.closest(".global-tooltip")) hideTooltip();
});
document.addEventListener("scroll", () => hideTooltip(), true);
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && activeTooltipTrigger) hideTooltip();
});
initTooltips(document);
$("catalogSearch").addEventListener("input", filterCatalog);
$("catalogRows").addEventListener("click", (event) => {
  const remove = event.target.closest(".catalog-remove");
  if (!remove || catalogBusy) return;
  remove.closest(".catalog-row").remove(); markCatalogDirty();
});
$("catalogRows").addEventListener("input", (event) => {
  const row = event.target.closest(".catalog-row");
  if (row) row.querySelector("small").textContent = `${catalogDraft()[row.dataset.category].length} Endungen`;
  markCatalogDirty();
});
$("catalogAddCategory").addEventListener("click", () => {
  const name = $("catalogNewCategory").value.trim();
  const draft = catalogDraft();
  if (!name || name.toLocaleLowerCase("de") === "unbekannt" || Object.keys(draft).some(value => value.toLocaleLowerCase("de") === name.toLocaleLowerCase("de"))) {
    $("catalogMessage").textContent = "BITTE EINEN NEUEN, EINDEUTIGEN KATEGORIENAMEN EINGEBEN"; return;
  }
  $("catalogSearch").value = "";
  renderCatalog({ ...draft, [name]: [] });
  $("catalogNewCategory").value = "";
  markCatalogDirty();
  $("catalogRows").lastElementChild.querySelector("textarea").focus();
});
$("catalogReset").addEventListener("click", () => {
  if (!catalogDefaults || catalogBusy) return;
  $("catalogSearch").value = "";
  renderCatalog(catalogDefaults.categories); markCatalogDirty();
  $("catalogMessage").textContent = "STANDARD GELADEN · ZUM ÜBERNEHMEN SPEICHERN";
});
$("catalogSave").addEventListener("click", saveCatalog);
$("closeAuftragModal").addEventListener("click", () => $("auftragModal").close());
$("auftragModal").addEventListener("click", (event) => { if (event.target === $("auftragModal")) $("auftragModal").close(); });
$("openCaseArchive").addEventListener("click", () => openNestedAuftragDialog("caseArchiveModal"));
$("closeCaseArchive").addEventListener("click", () => $("caseArchiveModal").close());
$("caseArchiveModal").addEventListener("click", (event) => { if (event.target === $("caseArchiveModal")) $("caseArchiveModal").close(); });
$("openEvidenceModal").addEventListener("click", () => $("evidenceModal").showModal());
$("closeEvidenceModal").addEventListener("click", () => $("evidenceModal").close());
$("evidenceModal").addEventListener("click", (event) => {
  if (event.target === $("evidenceModal")) $("evidenceModal").close();
});
$("createProfile").addEventListener("click", () => { if (!canSwitchProfileDetail()) return; openProfileEditor(null); });
$("settingsProfilesList").addEventListener("click", (event) => {
  const row = event.target.closest("[data-select-profile]");
  if (!row) return;
  if (!canSwitchProfileDetail()) return;
  openProfileEditor(row.dataset.selectProfile);
});
$("profileDetailDuplicate").addEventListener("click", () => {
  if (!profileDetailId) return;
  if (!canSwitchProfileDetail()) return;
  openProfileEditor(profileDetailId, true);
});
$("profileDetailSelectAll").addEventListener("click", () => {
  for (const checkbox of $("profileDetailOptions").querySelectorAll("input")) checkbox.checked = true;
  profileDetailDirty = true;
});
$("profileDetailClearAll").addEventListener("click", () => {
  for (const checkbox of $("profileDetailOptions").querySelectorAll("input")) checkbox.checked = false;
  profileDetailDirty = true;
});
$("profileDetailApply").addEventListener("click", applyProfileSelection);
$("profileDetailAddKeyword").addEventListener("click", addKeywordFromInput);
$("profileDetailNewInput").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); addKeywordFromInput(); } });
$("profileDetailOptions").addEventListener("click", (event) => {
  const remove = event.target.closest("button[data-remove-keyword]");
  if (!remove) return;
  event.preventDefault();
  event.stopPropagation();
  const keyword = remove.dataset.removeKeyword;
  draftSelectedKeywords = selectedDraftFromControls();
  draftSelectedKeywords.delete(keyword);
  keywordDraft = keywordDraft.filter((item) => item !== keyword);
  profileDetailDirty = true;
  renderKeywordOptions();
  updateProfileDetailCount();
});
$("profileDetailName").addEventListener("input", markProfileDetailDirty);
$("profileDetailSave").addEventListener("click", saveProfileEditor);
$("profileList").addEventListener("change", (event) => {
  const checkbox = event.target.closest('input[type="checkbox"]');
  if (!checkbox) return;
  if (checkbox.checked) activeProfileIds.add(checkbox.value);
  else activeProfileIds.delete(checkbox.value);
  if (!activeProfileIds.size) {
    checkbox.checked = true;
    activeProfileIds.add(checkbox.value);
    setSystemState("MINDESTENS EIN SUCHPROFIL ERFORDERLICH", "busy");
  }
  profileReady = activeProfileIds.size > 0;
  renderProfileList();
  updateKeywordSummary();
  updateCaseSessionUi();
});
$("profileList").addEventListener("click", (event) => {
  const edit = event.target.closest("button[data-edit-profile]");
  if (!edit) return;
  event.preventDefault();
  event.stopPropagation();
  openProfileEditor(edit.dataset.editProfile);
});
$("caseList").addEventListener("click", (event) => {
  const remove = event.target.closest("button[data-delete-case]");
  if (remove) {
    const caseNumber = remove.dataset.deleteCase;
    if (!caseNumber || caseNumber === activeCaseNumber) return;
    deleteTargetCaseNumber = caseNumber;
    $("deleteCaseNumber").textContent = caseNumber;
    $("deleteConfirmCaseNumber").textContent = caseNumber;
    $("deleteConfirmed").checked = false;
    $("confirmDelete").disabled = true;
    $("deleteMessage").textContent = "";
    openNestedAuftragDialog("deleteModal");
    $("deleteConfirmed").focus();
    return;
  }
  const item = event.target.closest("button[data-case-number]");
  if (!item) return;
  $("caseNumber").value = item.dataset.caseNumber;
  caseHistorySignature = "";
  renderCaseHistory(knownCases);
  updateCaseSessionUi();
  $("caseArchiveModal").close();
});
$("caseStart").addEventListener("click", startCaseSession);
$("caseStop").addEventListener("click", stopCaseSession);
$("updateStopCase").addEventListener("click", async () => {
  if ($("updateStopCase").disabled) return;
  const stopped = await stopCaseSession({ keepUpdateOpen: true });
  $("updateActionMessage").textContent = stopped
    ? "FALL BEENDET · UPDATE KANN JETZT SEPARAT INSTALLIERT WERDEN"
    : "FALL KONNTE NICHT BEENDET WERDEN · BITTE STATUS PRÜFEN";
});
$("cancelDelete").addEventListener("click", () => $("deleteModal").close());
$("deleteConfirmed").addEventListener("change", () => {
  $("confirmDelete").disabled = !$("deleteConfirmed").checked;
  if ($("deleteConfirmed").checked) $("deleteMessage").textContent = "";
});
for (const id of nestedAuftragDialogs) $(id).addEventListener("close", syncAuftragBackdrop);
$("auftragModal").addEventListener("close", () => {
  $("auftragModal").classList.remove("nested-open");
  $("caseArchiveModal").classList.remove("nested-open");
});
$("deleteForm").addEventListener("submit", (event) => { event.preventDefault(); deleteCurrentCase(); });
$("refreshButton").addEventListener("click", () => refresh(false));
$("saveDecision").addEventListener("click", saveDecision);
$("inventoryLoad").addEventListener("click", () => loadInventory());
$("inventoryReset").addEventListener("click", resetInventoryView);
$("inventoryMore").addEventListener("click", () => {
  if (inventoryListState) loadInventory({ ...inventoryListState, offset: inventoryListState.nextOffset });
});
$("inventorySearch").addEventListener("keydown", (event) => { if (event.key === "Enter") loadInventory(); });
$("largestFiles").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-inventory-file]");
  if (!button || !currentMediaId) return;
  $("inventoryPanel").open = true;
  $("inventorySearch").value = button.dataset.inventoryFile;
  loadInventory({ exactPath: button.dataset.inventoryFile, search: "" });
  $("inventoryPanel").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("cryptoHintList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-inventory-file]");
  if (!button || !currentMediaId) return;
  $("inventoryPanel").open = true;
  $("inventorySearch").value = button.dataset.inventoryFile;
  loadInventory({ exactPath: button.dataset.inventoryFile, search: "" });
  $("inventoryPanel").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("inventoryFiles").addEventListener("click", (event) => {
  const button = event.target.closest("button.inventory-container-toggle");
  if (!button) return;
  const detail = button.closest("tr")?.nextElementSibling;
  if (!detail?.classList.contains("inventory-container-detail")) return;
  const opening = detail.hidden;
  detail.hidden = !opening;
  button.setAttribute("aria-expanded", String(opening));
  if (opening && detail.dataset.loaded !== "true") {
    loadContainerTree(button.dataset.containerPath, "", detail.querySelector(".tree-children"));
  }
});
$("categories").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-inventory-category]");
  if (!button) return;
  if (button.classList.contains("active")) {
    resetInventoryView();
    return;
  }
  clearInventoryFilterState();
  button.classList.add("active");
  button.setAttribute("aria-pressed", "true");
  $("inventorySearch").value = "";
  $("inventoryPanel").open = true;
  loadInventory({ category: button.dataset.inventoryCategory });
  $("inventoryPanel").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("archiveStatus").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-inventory-archive-status]");
  if (!button || button.disabled) return;
  if (button.classList.contains("active")) {
    resetInventoryView();
    return;
  }
  clearInventoryFilterState();
  button.classList.add("active");
  button.setAttribute("aria-pressed", "true");
  $("inventorySearch").value = "";
  $("inventoryPanel").open = true;
  loadInventory({ archiveStatus: button.dataset.inventoryArchiveStatus });
  $("inventoryPanel").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("keywords").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-inventory-keyword]");
  if (!button) return;
  if (button.classList.contains("active")) {
    resetInventoryView();
    return;
  }
  clearInventoryFilterState();
  button.classList.add("active");
  button.setAttribute("aria-pressed", "true");
  $("inventorySearch").value = "";
  $("inventoryPanel").open = true;
  loadInventory({ keyword: button.dataset.inventoryKeyword });
  $("inventoryPanel").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("inventoryPanel").addEventListener("toggle", () => {
  if ($("inventoryPanel").open && currentMediaId && !inventoryListState && inventoryTreeMediaId !== currentMediaId) loadInventoryTree();
});
function handleInventoryTreeClick(event) {
  const more = event.target.closest("button.tree-more");
  if (more) {
    if (more.dataset.containerPath) {
      loadContainerTree(more.dataset.containerPath, more.dataset.containerPrefix, more.parentElement, Number(more.dataset.containerOffset));
    } else {
      loadInventoryTree(more.dataset.treePrefix, more.parentElement, Number(more.dataset.treeOffset));
    }
    return;
  }
  const containerSummary = event.target.closest("summary[data-container-path]");
  if (containerSummary) {
    const container = containerSummary.parentElement;
    if (!container.open && container.dataset.loaded !== "true") {
      loadContainerTree(containerSummary.dataset.containerPath, containerSummary.dataset.containerPrefix, container.querySelector(".tree-children"));
    }
    return;
  }
  const summary = event.target.closest("summary[data-tree-prefix]");
  if (!summary) return;
  const folder = summary.parentElement;
  if (!folder.open && folder.dataset.loaded !== "true") {
    loadInventoryTree(summary.dataset.treePrefix, folder.querySelector(".tree-children"));
  }
}
$("inventoryTree").addEventListener("click", handleInventoryTreeClick);
$("inventoryFiles").addEventListener("click", handleInventoryTreeClick);
$("caseMedia").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-media-id]");
  if (row) openMedia(Number(row.dataset.mediaId));
});
$("decisionReason").addEventListener("change", updateDecisionAvailability);
$("updateCheck").addEventListener("click", () => requestUpdate("check"));
$("updateInstall").addEventListener("click", () => requestUpdate("install"));
$("offlineUpdateFile").addEventListener("change", () => {
  $("offlineUpdateMessage").textContent = $("offlineUpdateFile").files[0]
    ? `${$("offlineUpdateFile").files[0].name.toUpperCase()} · ${formatBytes($("offlineUpdateFile").files[0].size)}`
    : "";
  renderUpdateState(updateState);
});
$("offlineUpdateInstall").addEventListener("click", installOfflineUpdate);
$("decisionEvidence").addEventListener("input", updateDecisionAvailability);
$("decisionSpecialist").addEventListener("input", updateDecisionAvailability);
for (const button of document.querySelectorAll("[data-decision]")) {
  button.addEventListener("click", () => {
    currentDecision = button.dataset.decision;
    if (currentDecision !== "secure") $("decisionEvidence").value = "";
    if (currentDecision !== "specialist_consulted") $("decisionSpecialist").value = "";
    updateDecisionFields();
    for (const peer of document.querySelectorAll("[data-decision]")) peer.classList.toggle("active", peer === button);
    $("decisionState").textContent = decisionLabels[currentDecision];
    updateDecisionAvailability();
  });
}
for (const input of [$("caseNumber"), $("operator")]) {
  input.addEventListener("input", () => {
    if (input === $("caseNumber")) {
      caseHistorySignature = "";
      renderCaseHistory(knownCases);
    }
    updateCaseSessionUi();
  });
}
updateCaseSessionUi();
loadProfiles();
const restoreUpdateView = sessionStorage.getItem(UPDATE_DIALOG_RESTORE_KEY) === "1";
if (restoreUpdateView) openSettings("updates");
refresh().finally(() => { if (restoreUpdateView) forgetUpdateDialog(); });
setInterval(() => refresh(false), 2500);
