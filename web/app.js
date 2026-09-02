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
let updateState = { state: "unknown", message: "UPDATE NOCH NICHT GEPRÜFT" };
let updateActionInProgress = null;
let serverActiveCase = null;
let caseSessionTransition = false;
const wait = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
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
  const summaryLabels = { current: "", installed: "", available: "UPDATE", checking: "PRÜFT", installing: "LÄUFT", error: "UPDATE-FEHLER" };
  $("updateStatus").textContent = statusLabels[state] || updateState.message || "NOCH NICHT GEPRÜFT";
  $("updateCurrentVersion").textContent = formatReleaseVersion(updateState.current_version);
  $("systemVersion").textContent = formatReleaseVersion(updateState.current_version);
  $("updateCheckedAt").textContent = updateState.updated_at
    ? new Date(updateState.updated_at).toLocaleString("de-AT")
    : "—";
  $("updateSummary").textContent = summaryLabels[state] ?? "STATUS";
  $("openUpdateModal").classList.toggle("update-available", state === "available");
  $("updateInstall").hidden = state !== "available";
  $("updateInstall").textContent = available ? `${available.toUpperCase()} INSTALLIEREN` : "UPDATE INSTALLIEREN";
  const activeCase = activeCaseNumber || serverActiveCase?.case_number;
  const actionRunning = Boolean(updateActionInProgress) || state === "checking" || state === "installing";
  $("updateModal").classList.toggle("update-busy", actionRunning);
  $("updateInstall").disabled = Boolean(activeCase) || runningPaths.size > 0 || actionRunning;
  $("updateCheck").disabled = actionRunning;
  if (!updateActionInProgress) {
    if (state === "available" && activeCase) {
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
  if (updateActionInProgress) return;
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
    renderUpdateState(previousUpdateState);
    $("updateActionMessage").textContent = `FEHLER: ${error.message}`;
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
    <button class="profile-edit" type="button" data-edit-profile="${escapeHtml(profile.id)}">BEARBEITEN</button>
  </label>`).join("");
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
    const isArchive = name === "Archive" && Number(archiveEncryption.total || 0);
    const archiveStats = isArchive ? `<span class="archive-stats"><span><b>${Number(archiveEncryption.encrypted || 0)}</b> VERSCHLÜSSELT</span><span class="${Number(archiveEncryption.unknown || 0) ? "warning" : ""}"><b>${Number(archiveEncryption.unknown || 0)}</b> UNGEPRÜFT</span></span>` : "";
    return `<button class="bar-row result-filter${isArchive ? " has-archive-stats" : ""}" type="button" data-inventory-category="${escapeHtml(name)}" aria-pressed="false" title="${escapeHtml(name)} im Dateiverzeichnis anzeigen"><span class="bar-value">${Number(count)}</span><span class="bar-name">${escapeHtml(name.toUpperCase())}</span><span class="bar-track"><span class="bar-fill" style="width:${(count / max) * 100}%"></span></span>${archiveStats}</button>`;
  }).join("");
  $("keywords").innerHTML = Object.entries(hits).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]).map(([word, count]) => `
    <button class="keyword-row result-filter" type="button" data-inventory-keyword="${escapeHtml(word)}" aria-pressed="false" title="Trefferpfade für ${escapeHtml(word)} anzeigen"><span>${escapeHtml(word.toUpperCase())}</span><b>${Number(count)}</b></button>
  `).join("");
  $("largestFiles").innerHTML = (summary.largest_files || []).map((file, index) => `
    <tr><td>${String(index + 1).padStart(2, "0")}</td><td>${escapeHtml(file.path)}</td><td>${formatBytes(file.size)}</td></tr>
  `).join("");
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
  $("mediaCards").innerHTML = onlineMedia.map((medium) => renderCard(medium, true)).join("");
  $("offlineMediaCards").innerHTML = offlineMedia.map((medium) => renderCard(medium, false)).join("");
  $("offlineMediaPanel").hidden = offlineMedia.length === 0;
  $("offlineMediaCount").textContent = `${offlineMedia.length} ${offlineMedia.length === 1 ? "MEDIUM" : "MEDIEN"}`;
  updateDashboardState();
}

function updateDashboardState() {
  const online = devices.length;
  if (deviceDiscoveryError) {
    $("deviceCount").textContent = "ERKENNUNG GESTÖRT · LETZTER STAND";
    $("deviceEmptyTitle").textContent = "DATENTRÄGERERKENNUNG PRÜFEN";
    $("deviceEmptyCopy").textContent = "Ein Geräteabruf ist noch offen oder fehlgeschlagen. Der Verbindungsstatus ist derzeit unbekannt; neue Scans warten auf eine erfolgreiche Erkennung.";
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
  const offline = currentCaseMedia.filter((medium) => !devices.some((device) => device.serial && device.serial === medium.serial)).length;
  $("deviceCount").textContent = `${online} ONLINE · ${offline} OFFLINE`;
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
    renderRecord(data);
    $("decisionMessage").textContent = "ENTSCHEIDUNG MIT ZEITSTEMPEL PROTOKOLLIERT";
  } catch (error) {
    if (revision !== mediaViewRevision || mediaId !== currentMediaId) return;
    $("decisionMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    updateDecisionAvailability();
  }
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
        encrypted_headers: "NAMEN VERSCHLÜSSELT",
        incomplete: "UNVOLLSTÄNDIG",
        tool_unavailable: "WERKZEUG FEHLT",
      };
      const state = stateLabels[entry.container_status]
        || (entry.truncated ? `${Number(entry.entry_count).toLocaleString("de-AT")} EINTRÄGE · LIMIT`
          : `${Number(entry.entry_count).toLocaleString("de-AT")} EINTRÄGE`);
      const encryptionState = entry.encrypted && entry.container_status !== "encrypted_headers" ? " · VERSCHLÜSSELT" : "";
      return `<details class="tree-folder tree-container" data-loaded="false">
        <summary data-container-path="${escapeHtml(entry.container_id || entry.path)}" data-container-prefix=""><span class="tree-arrow">▶</span><b>${escapeHtml(entry.name)}</b><small>${escapeHtml(state + encryptionState)}</small></summary>
        <div class="tree-children"><p class="tree-loading">${escapeHtml(format)}-VERZEICHNIS ÖFFNEN …</p></div>
      </details>`;
    }
    return `<div class="tree-file"><span>·</span><b>${escapeHtml(entry.name)}</b><small>${escapeHtml(entry.category)} · ${entry.size_known === false ? "GRÖSSE NICHT INDEXIERT" : formatBytes(entry.size)}</small></div>`;
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
    const row = `<tr${inside ? ' class="inventory-inner-file"' : ""}><td title="${path}">${pathCell}${note}</td><td><span class="inventory-location">${escapeHtml(location)}</span>${matchNote}</td><td>${escapeHtml(file.category)}</td><td>${escapeHtml(file.extension || "—")}</td><td>${file.size_known === false ? "—" : formatBytes(file.size)}</td></tr>`;
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

async function loadInventory({ category = "", keyword = "", search = null, offset = 0 } = {}) {
  if (!currentMediaId) return;
  const searchText = search === null ? $("inventorySearch").value.trim() : search;
  if (!searchText && !category && !keyword) {
    $("inventorySearch").focus();
    return;
  }
  if (searchText && !category && !keyword) clearInventoryFilterState();
  if (offset === 0) {
    inventoryViewRevision += 1;
    inventoryListState = { category, keyword, search: searchText, nextOffset: 0 };
    $("inventoryFiles").innerHTML = '<tr><td colspan="5">FUNDSTELLEN WERDEN GELADEN …</td></tr>';
  }
  const target = $("inventoryFiles");
  const request = beginInventoryRequest(target);
  $("inventoryTree").hidden = true;
  $("inventorySearchResults").hidden = false;
  $("inventoryFilterLabel").textContent = (category ? `DATEITYP: ${category}` : keyword ? `STICHWORT: ${keyword}` : `SUCHE: ${searchText}`).toUpperCase();
  $("inventoryFilterBar").hidden = false;
  $("inventoryReset").hidden = false;
  $("inventoryMore").hidden = true;
  $("inventoryCount").textContent = "LÄDT …";
  try {
    const parameters = new URLSearchParams({ limit: "250", offset: String(offset) });
    if (searchText) parameters.set("q", searchText);
    if (category) parameters.set("category", category);
    if (keyword) parameters.set("keyword", keyword);
    const response = await fetch(`/api/media/${request.mediaId}/files?${parameters}`);
    const data = await response.json();
    if (!inventoryRequestIsCurrent(target, request)) return;
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    const visible = Number(data.offset || 0) + Number(data.shown || 0);
    $("inventoryCount").textContent = `${visible} / ${data.total} FUNDSTELLEN`;
    const rows = inventoryRowsHtml(data.files);
    if (offset === 0) $("inventoryFiles").innerHTML = rows;
    else $("inventoryFiles").insertAdjacentHTML("beforeend", rows);
    inventoryListState = { category, keyword, search: searchText, nextOffset: Number(data.next_offset || visible) };
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

async function stopCaseSession() {
  if (runningPaths.size) return;
  invalidateMediaView();
  caseSessionTransition = true;
  clearTimeout(autoStartTimer);
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
  openAuftrag();
  try {
    const response = await fetch("/api/cases/stop", { method: "POST" });
    if (!response.ok) throw new Error("Fall konnte am Gerät nicht beendet werden");
    serverActiveCase = null;
    renderUpdateState(updateState);
  } catch (error) {
    $("caseStartMessage").textContent = `FEHLER: ${error.message}`;
    caseSessionTransition = false;
    await refresh(false);
    return;
  } finally {
    caseSessionTransition = false;
  }
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
}

function openProfileEditor(profileId = null) {
  const createNew = profileId === null;
  const detail = createNew ? null : profileDetails.get(profileId);
  profileEditorId = profileId;
  keywordDraft = createNew ? [] : [...(detail?.keywords || [])];
  draftSelectedKeywords = createNew ? new Set() : new Set(selectedByProfile.get(profileId) || detail?.keywords || []);
  $("keywordProfileName").value = createNew ? "" : detail?.name || "";
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
    activeProfileIds.add(data.profile.id);
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
$("homeLogo").addEventListener("click", showDashboard);
$("openAuftragModal").addEventListener("click", openAuftrag);
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
$("openUpdateModal").addEventListener("click", () => $("updateModal").showModal());
$("closeUpdateModal").addEventListener("click", () => $("updateModal").close());
$("updateModal").addEventListener("click", (event) => {
  if (event.target === $("updateModal")) $("updateModal").close();
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
refresh();
setInterval(() => refresh(false), 2500);
