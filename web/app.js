const $ = (id) => document.getElementById(id);
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
let catalogState = null;
let catalogDefaults = null;
let catalogBusy = false;
let catalogDirty = false;
let settingsRevision = 0;
let updateState = { state: "unknown", message: "UPDATE NOCH NICHT GEPRÜFT" };
let updateActionInProgress = null;
const UPDATE_DIALOG_RESTORE_KEY = "triagebox-update-dialog";
let powerState = { state: "unknown", label: "STROMSTATUS UNBEKANNT" };
let pendingPowerAction = null;
let powerActionInProgress = false;
let serverActiveCase = null;
let caseSessionTransition = false;
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

const nestedAuftragDialogs = ["keywordModal", "caseArchiveModal", "deleteModal"];

function syncAuftragBackdrop() {
  const nestedOpen = nestedAuftragDialogs.some((id) => $(id).open);
  $("auftragModal").classList.toggle("nested-open", $("auftragModal").open && nestedOpen);
  $("caseArchiveModal").classList.toggle("nested-open", $("caseArchiveModal").open && $("deleteModal").open);
  $("settingsModal").classList.toggle("nested-open", $("settingsModal").open && $("keywordModal").open);
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

function renderKeywordOptions() {
  $("keywordOptions").innerHTML = keywordDraft.map((keyword) => `<label class="keyword-option">
    <input type="checkbox" value="${escapeHtml(keyword)}" ${draftSelectedKeywords.has(keyword) ? "checked" : ""} />
    <span>${escapeHtml(keyword.toUpperCase())}</span>
    <button class="keyword-remove" type="button" data-remove-keyword="${escapeHtml(keyword)}" aria-label="${escapeHtml(keyword)} entfernen">×</button>
  </label>`).join("");
}

function renderProfileList() {
  $("profileList").innerHTML = availableProfiles.map((profile) => `<label class="profile-list-item">
    <input type="checkbox" value="${escapeHtml(profile.id)}" ${activeProfileIds.has(profile.id) ? "checked" : ""} />
    <span class="profile-list-copy"><strong>${escapeHtml(profile.name.toUpperCase())}</strong><small>V${escapeHtml(profile.version)} · ${Number(profile.keyword_count)} STICHWÖRTER</small></span>
  </label>`).join("");
  $("settingsProfilesList").innerHTML = availableProfiles.map((profile) => `<article class="settings-profile">
    <div><strong>${escapeHtml(profile.name)}</strong><small>${Number(profile.keyword_count)} Stichwörter · Version ${escapeHtml(profile.version)}</small></div>
    <button type="button" data-edit-profile="${escapeHtml(profile.id)}">BEARBEITEN</button>
    <button type="button" data-copy-profile="${escapeHtml(profile.id)}">DUPLIZIEREN</button>
  </article>`).join("") || '<p>Noch keine Profile vorhanden.</p>';
}

function selectSettingsPane(pane = "profiles") {
  for (const name of ["Profiles", "Filetypes", "Updates"]) {
    const active = name.toLowerCase() === pane.toLowerCase();
    $(`settings${name}Pane`).hidden = !active;
    $(`settings${name}Tab`).setAttribute("aria-pressed", String(active));
  }
}

async function openSettings(initialPane = "profiles") {
  if ($("auftragModal").open) $("auftragModal").close();
  if (!$("settingsModal").open) $("settingsModal").showModal();
  selectSettingsPane(initialPane);
  const revision = ++settingsRevision;
  catalogState = null; catalogDirty = false;
  $("catalogRows").innerHTML = "";
  $("catalogSave").disabled = true;
  $("catalogReset").disabled = true;
  $("catalogAddCategory").disabled = true;
  $("catalogMessage").textContent = "DATEITYPEN WERDEN GELADEN …";
  loadProfiles();
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

function closeSettings() {
  if (catalogBusy || isUpdateBusy()) return;
  if (catalogDirty && !window.confirm("Ungespeicherte Änderungen am Dateityp-Katalog verwerfen?")) return;
  ++settingsRevision;
  $("settingsModal").close();
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
    return `<tr><td class="largest-size">${formatBytes(file.size)}</td><td><button class="largest-file-link" type="button" data-inventory-file="${escapeHtml(path)}" title="Im Dateiverzeichnis anzeigen: ${escapeHtml(path)}" aria-label="Im Dateiverzeichnis anzeigen: ${escapeHtml(path)}"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(folder)}</small><span aria-hidden="true">↗</span></button></td></tr>`;
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
  const liveDevice = devices.find((device) => device.serial && device.serial === media.serial) || {};
  const device = { ...liveDevice, ...storedDevice };
  const model = [media.vendor || device.vendor, media.model || device.model].filter(Boolean).join(" ") || "UNBEKANNT";
  const isOptical = device.type === "rom" || device.media_type === "optical" || String(media.device_path || "").startsWith("/dev/sr");
  const readOnly = device.read_only_verified === true
    ? "BEIM SCAN VERIFIZIERT"
    : (device.read_only || device.ro ? "AKTIV" : "NICHT DOKUMENTIERT");
  $("evidenceDeviceModel").textContent = model;
  $("evidenceDeviceSerial").textContent = media.serial || device.serial || "NICHT GEMELDET";
  $("evidenceDeviceCapacity").textContent = Number(media.size || device.size || 0) > 0
    ? formatBytes(media.size || device.size)
    : "NICHT GEMELDET";
  $("evidenceDeviceType").textContent = isOptical ? "CD/DVD (USB)" : "USB-DATENTRÄGER";
  $("evidenceDevicePath").textContent = media.device_path || device.path || "—";
  $("evidenceDeviceReadOnly").textContent = readOnly;
}

const decisionLabels = {
  open: "ENTSCHEIDUNG OFFEN",
  secure: "ZUR SICHERUNG AUSGEWÄHLT",
  not_selected: "NICHT ZUR SICHERUNG AUSGEWÄHLT",
  review: "ENTSCHEIDUNG OFFEN · ALTER STATUS",
};

function renderDecision(media) {
  if (!media) return;
  currentMediaId = media.id;
  currentDecision = ["secure", "not_selected"].includes(media.decision) ? media.decision : null;
  $("decisionState").textContent = decisionLabels[media.decision] || decisionLabels.open;
  $("decisionEvidence").value = media.evidence_number || "";
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
  $("decisionEvidenceWrap").hidden = !secure;
  $("decisionReasonWrap").hidden = secure;
  $("decisionNoteWrap").hidden = secure;
  $("decisionHelp").hidden = secure;
}

function renderRecord(record) {
  renderResults(record.summary, record.hits);
  if (record.media) {
    clearInventoryView();
    const connected = devices.some((device) => device.serial && device.serial === record.media.serial);
    $("detailConnectionState").textContent = deviceDiscoveryError ? "STATUS UNBEKANNT" : connected ? "● ONLINE" : "○ OFFLINE";
    $("detailConnectionState").className = connected && !deviceDiscoveryError ? "connected" : "disconnected";
    renderDeviceEvidence(record.media, record.device);
    renderArchive(record.archive);
    renderDecision(record.media);
    loadCase(record.media.case_number);
    $("inventoryPanel").hidden = false;
    if ($("inventoryPanel").open) loadInventoryTree();
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
  return !["secure", "not_selected"].includes(medium?.decision);
}

function pendingOfflineMedia() {
  const onlineSerials = new Set(devices.map((device) => device.serial).filter(Boolean));
  return sortedSightings(currentCaseMedia.filter((medium) => decisionIsOpen(medium) && (!medium.serial || !onlineSerials.has(medium.serial))));
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
    const serial = medium.serial || "NICHT GEMELDET";
    const capacity = Number(medium.size || 0) > 0 ? formatBytes(medium.size) : "GRÖSSE NICHT GEMELDET";
    return `<button type="button" class="decision-queue-item" data-queue-media-id="${Number(medium.id)}">
      <span class="decision-queue-position">${index + 1} / ${count}</span>
      <strong>${escapeHtml(medium.sighting_number || `SICHT-${medium.id}`)}</strong>
      <span class="decision-queue-model">${escapeHtml(model)}</span>
      <code title="${escapeHtml(serial)}">SERIAL ${escapeHtml(serial)}</code>
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
  const nextSerials = new Set((items || []).map((device) => device.serial).filter(Boolean));
  if (devicePresenceInitialized) {
    const removed = [...confirmedOnlineSerials].filter((serial) => !nextSerials.has(serial));
    const requiresDecision = removed.some((serial) => currentCaseMedia.some((medium) => medium.serial === serial && decisionIsOpen(medium)));
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
    const alreadyRecorded = device.serial && media.some((medium) => medium.serial === device.serial);
    if (alreadyRecorded && deviceStates.get(device.path) === "ready") deviceStates.set(device.path, "complete");
  }
  const renderCard = (medium, connected) => {
    const evidenceLabel = medium.evidence_number
      ? `<b>${escapeHtml(medium.evidence_number)}</b>`
      : "";
    const model = [medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path;
    const ejectLabel = String(medium.device_path || "").startsWith("/dev/sr")
      ? "⏏ CD/DVD AUSWERFEN"
      : "⏏ SICHER AUSWERFEN";
    return `<div class="media-card-shell${connected ? " online" : " offline"}"><button class="media-card complete${connected ? " online" : " offline"}${Number(medium.id) === currentMediaId ? " active" : ""}" type="button" data-media-id="${Number(medium.id)}">
      <span class="media-card-top">${evidenceLabel}${statusTag(medium.decision)}</span>
      <strong>${escapeHtml(medium.sighting_number)}</strong>
      <small>${escapeHtml(model)}</small>
      <span class="media-card-metrics"><i>${Number(medium.file_count).toLocaleString("de-AT")} DATEIEN</i><i>${Number(medium.keyword_matches).toLocaleString("de-AT")} TREFFER</i></span>
      <span class="connection-badge ${connected && !deviceDiscoveryError ? "connected" : "disconnected"}">${deviceDiscoveryError ? "STATUS UNBEKANNT" : connected ? "● ONLINE" : "○ OFFLINE"}</span>
      <em>DETAILS ÖFFNEN →</em>
    </button>${connected ? `<button class="media-eject" type="button" data-eject-device="${escapeHtml(medium.device_path)}" ${deviceDiscoveryError ? "disabled" : ""}>${ejectLabel}</button>` : ""}</div>`;
  };
  const onlineMedia = media.filter((medium) => devices.some((device) => device.serial && device.serial === medium.serial));
  const offlineMedia = media.filter((medium) => !devices.some((device) => device.serial && device.serial === medium.serial));
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
  const offline = currentCaseMedia.filter((medium) => !devices.some((device) => device.serial && device.serial === medium.serial) && !decisionIsOpen(medium)).length;
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
  $("caseStart").textContent = activeCaseNumber && !sameSession ? "↻ ANDEREN FALL STARTEN" : "▶ FALL STARTEN";
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
    const recorded = activeCaseNumber && device.serial && currentCaseMedia.some((medium) => medium.serial === device.serial);
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
    device.serial && currentCaseMedia.some((medium) => medium.serial === device.serial)
  ));
  const dashboardDevices = activeCaseNumber
    ? visibleDevices
    : visibleDevices.filter((device) => device.media_type === "optical");
  $("deviceList").innerHTML = dashboardDevices.map((device) => {
    const state = deviceStates.get(device.path) || "ready";
    const model = [device.vendor, device.model].filter(Boolean).join(" ") || (device.media_type === "optical" ? "CD/DVD-Laufwerk" : "USB-Datenträger");
    const serial = device.serial || "NICHT GEMELDET";
    const type = device.media_type === "optical" ? "CD/DVD" : "USB";
    const disabled = deviceDiscoveryError || !device.scan_supported || state === "scanning" || state === "timeout";
    const stateReason = state === "timeout"
      ? "ABZIEHEN UND NEU VERBINDEN"
      : (deviceErrors.get(device.path) || device.unavailable_reason || "");
    const optical = device.media_type === "optical";
    const ejectDisabled = deviceDiscoveryError || ["scanning", "timeout"].includes(state) || device.mounted;
    return `<article class="device-card" data-state="${state}">
      <span class="device-card-top"><i class="device-led" title="${stateLabels[state]}"></i><b>${optical ? "CD/DVD-LAUFWERK" : "NEUES MEDIUM"}</b><em>${deviceDiscoveryError ? "STATUS UNBEKANNT" : "● ONLINE"}</em></span>
      <div class="device-copy"><strong>${escapeHtml(model)}</strong><span>${escapeHtml(device.path)} · ${formatBytes(device.size)} · ${type}</span><code title="${escapeHtml(serial)}">SERIAL ${escapeHtml(serial.length > 22 ? `${serial.slice(0, 22)}…` : serial)}</code></div>
      <div class="device-state"><b>${stateLabels[state]}</b><small title="${escapeHtml(stateReason)}">${escapeHtml(stateReason)}</small></div>
      <div class="device-progress" aria-label="Scanfortschritt"><i></i></div>
      <div class="device-card-actions${optical ? " optical" : ""}">
        <button type="button" data-scan-device="${escapeHtml(device.path)}" ${disabled ? "disabled" : ""}>${state === "complete" ? "ERNEUT SCANNEN" : "SCANNEN"}</button>
        ${optical ? `<button class="device-eject" type="button" data-eject-device="${escapeHtml(device.path)}" ${ejectDisabled ? "disabled" : ""}>⏏ CD/DVD AUSWERFEN</button>` : ""}
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
    const connected = devices.some((device) => device.serial && device.serial === detailMedium.serial);
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
  $("saveDecision").disabled = !currentMediaId || !currentDecision || (reasonRequired && !hasReason) || (currentDecision === "secure" && !hasEvidence) || !activeOperator;
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
    if (!activeCaseNumber) return;
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
    return;
  }
  if (activeCaseNumber === serverCaseNumber && activeOperator === serverOperator) return;
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
  $("progressLog").textContent = runningPaths.size ? `$ RO-Prüfung + Inventarisierung: ${[...runningPaths].join(" · ")}` : "$ Protokolle und Prüfsummen aktualisiert";
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
  if (!keepUpdateOpen) openAuftrag();
  try {
    const response = await fetch("/api/cases/stop", { method: "POST" });
    if (!response.ok) throw new Error("Fall konnte am Gerät nicht beendet werden");
    serverActiveCase = null;
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
  if ($("keywordModal").open) $("keywordModal").close();
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
  keywordDraft = [...(detail?.keywords || [])];
  draftSelectedKeywords = new Set(duplicate ? keywordDraft : selectedByProfile.get(profileId) || keywordDraft);
  $("keywordProfileName").value = duplicate ? `${(detail?.name || "Profil").slice(0, 34)} Kopie` : detail?.name || "";
  $("keywordModalTitle").textContent = createNew ? "NEUES PROFIL" : "PROFIL BEARBEITEN";
  $("keywordNewInput").value = "";
  $("keywordMessage").textContent = "";
  $("saveKeywordSettings").hidden = createNew;
  renderKeywordOptions();
  openNestedAuftragDialog("keywordModal");
  if (createNew) $("keywordProfileName").focus();
}

function addKeywordFromInput() {
  const input = $("keywordNewInput");
  const keyword = input.value.trim();
  if (!keyword) return;
  if (keywordDraft.some((item) => item.toLocaleLowerCase("de") === keyword.toLocaleLowerCase("de"))) {
    $("keywordMessage").textContent = "DIESES STICHWORT IST BEREITS VORHANDEN";
    return;
  }
  keywordDraft.push(keyword);
  draftSelectedKeywords.add(keyword);
  input.value = "";
  $("keywordMessage").textContent = "";
  renderKeywordOptions();
  input.focus();
}

function selectedDraftFromControls() {
  return new Set([...$("keywordOptions").querySelectorAll("input:checked")].map((input) => input.value));
}

async function saveProfileEditor() {
  const name = $("keywordProfileName").value.trim();
  draftSelectedKeywords = selectedDraftFromControls();
  $("saveProfileSettings").disabled = true;
  $("keywordMessage").textContent = "PROFIL WIRD GESPEICHERT …";
  try {
    const response = await fetch("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: profileEditorId, name, keywords: keywordDraft }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Profil konnte nicht gespeichert werden");
    const savedSelection = new Set([...draftSelectedKeywords].filter((word) => data.profile.keywords.includes(word)));
    selectedByProfile.set(data.profile.id, savedSelection.size ? savedSelection : new Set(data.profile.keywords));
    await loadProfiles(activeProfileIds);
    updateKeywordSummary();
    $("keywordModal").close();
    setSystemState(`PROFIL ${data.profile.name.toUpperCase()} GESPEICHERT`, "ready");
  } catch (error) {
    $("keywordMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    $("saveProfileSettings").disabled = false;
  }
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
$("openSettings").addEventListener("click", () => openSettings());
$("closeSettings").addEventListener("click", closeSettings);
$("settingsModal").addEventListener("cancel", (event) => { event.preventDefault(); closeSettings(); });
$("settingsModal").addEventListener("click", (event) => { if (event.target === $("settingsModal")) closeSettings(); });
$("settingsProfilesTab").addEventListener("click", () => selectSettingsPane("profiles"));
$("settingsFiletypesTab").addEventListener("click", () => selectSettingsPane("filetypes"));
$("settingsUpdatesTab").addEventListener("click", () => selectSettingsPane("updates"));
$("settingsProfilesList").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit-profile]");
  const copy = event.target.closest("[data-copy-profile]");
  if (edit) openProfileEditor(edit.dataset.editProfile);
  if (copy) openProfileEditor(copy.dataset.copyProfile, true);
});
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
$("createProfile").addEventListener("click", () => openProfileEditor(null));
$("closeKeywordSettings").addEventListener("click", () => $("keywordModal").close());
$("keywordModal").addEventListener("click", (event) => {
  if (event.target === $("keywordModal")) $("keywordModal").close();
});
$("selectAllKeywords").addEventListener("click", () => {
  for (const checkbox of $("keywordOptions").querySelectorAll("input")) checkbox.checked = true;
});
$("clearAllKeywords").addEventListener("click", () => {
  for (const checkbox of $("keywordOptions").querySelectorAll("input")) checkbox.checked = false;
});
$("saveKeywordSettings").addEventListener("click", () => {
  if (profileEditorId) selectedByProfile.set(profileEditorId, selectedDraftFromControls());
  updateKeywordSummary();
  $("keywordModal").close();
});
$("addKeyword").addEventListener("click", addKeywordFromInput);
$("keywordNewInput").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); addKeywordFromInput(); } });
$("keywordOptions").addEventListener("click", (event) => {
  const remove = event.target.closest("button[data-remove-keyword]");
  if (!remove) return;
  event.preventDefault();
  event.stopPropagation();
  const keyword = remove.dataset.removeKeyword;
  draftSelectedKeywords = selectedDraftFromControls();
  draftSelectedKeywords.delete(keyword);
  keywordDraft = keywordDraft.filter((item) => item !== keyword);
  renderKeywordOptions();
});
$("saveProfileSettings").addEventListener("click", saveProfileEditor);
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
for (const button of document.querySelectorAll("[data-decision]")) {
  button.addEventListener("click", () => {
    currentDecision = button.dataset.decision;
    if (currentDecision !== "secure") $("decisionEvidence").value = "";
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
