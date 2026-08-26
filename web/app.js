const $ = (id) => document.getElementById(id);
let devices = [];
const deviceStates = new Map();
const runningPaths = new Set();
let batchTotal = 0;
let batchDone = 0;
let autoStartTimer = null;
let currentCaseMedia = [];
let currentMediaId = null;
let currentDecision = null;
let inventoryTreeMediaId = null;
let caseHistorySignature = "";
let knownCases = [];
let activeCaseNumber = null;
let activeOperator = "";
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

function renderResults(summary, hits = {}) {
  $("resultEvidence").textContent = summary.evidence || "SICHTUNG";
  $("resultDuration").textContent = `${Number(summary.duration_seconds || 0).toLocaleString("de-AT")} s`;
  $("fileCount").textContent = Number(summary.file_count || 0).toLocaleString("de-AT");
  $("directoryCount").textContent = Number(summary.directory_count || 0).toLocaleString("de-AT");
  $("keywordMatches").textContent = Number(summary.keyword_matches || 0).toLocaleString("de-AT");
  $("totalBytes").textContent = formatBytes(summary.total_file_bytes);
  const categories = Object.entries(summary.categories_by_count || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...categories.map(([, count]) => count), 1);
  $("categories").innerHTML = categories.map(([name, count]) => `
    <div class="bar-row"><span>${escapeHtml(name.toUpperCase())}</span><div class="bar-track"><div class="bar-fill" style="width:${(count / max) * 100}%"></div></div><span class="bar-value">${Number(count)}</span></div>
  `).join("");
  $("keywords").innerHTML = Object.entries(hits).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]).map(([word, count]) => `
    <div class="keyword-row"><span>${escapeHtml(word.toUpperCase())}</span><b>${Number(count)}</b></div>
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
  $("archiveRegister").textContent = archive.media_register || "media-register.csv";
  $("archiveReport").textContent = archive.case_report || "case-report.txt";
  $("archiveAudit").textContent = archive.audit_log || "audit.log";
  $("archiveManifestCount").textContent = Number(archive.manifest_entries || 0).toLocaleString("de-AT");
}

const decisionLabels = {
  open: "ENTSCHEIDUNG OFFEN",
  secure: "ZUR SICHERUNG AUSGEWÄHLT",
  not_selected: "NICHT ZUR SICHERUNG AUSGEWÄHLT",
  review: "WEITERE PRÜFUNG",
};

function renderDecision(media) {
  if (!media) return;
  currentMediaId = media.id;
  currentDecision = media.decision === "open" ? null : media.decision;
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
    if (inventoryTreeMediaId !== record.media.id) {
      inventoryTreeMediaId = null;
      $("inventoryTree").innerHTML = "";
      $("inventorySearchResults").hidden = true;
      $("inventorySearch").value = "";
      $("inventoryCount").textContent = "—";
    }
    const connected = devices.some((device) => device.serial && device.serial === record.media.serial);
    $("detailConnectionState").textContent = connected ? "● DATENTRÄGER ONLINE" : "○ DATENTRÄGER OFFLINE";
    $("detailConnectionState").className = connected ? "connected" : "disconnected";
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

async function loadCase(caseNumber) {
  if (!caseNumber) {
    currentCaseMedia = [];
    renderMediaCards([]);
    $("casePanel").hidden = true;
    $("caseDelete").disabled = true;
    $("caseDownload").classList.add("disabled");
    $("caseDownload").setAttribute("aria-disabled", "true");
    $("caseDownload").href = "#";
    return;
  }
  try {
    const response = await fetch(`/api/cases/${encodeURIComponent(caseNumber)}`);
    const data = await response.json();
    if (response.status === 404) {
      currentCaseMedia = [];
      renderMediaCards([]);
      $("casePanel").hidden = true;
      $("caseDelete").disabled = true;
      $("caseDownload").classList.add("disabled");
      $("caseDownload").setAttribute("aria-disabled", "true");
      $("caseDownload").href = "#";
      return;
    }
    if (!response.ok) throw new Error(data.error || "Fallakte nicht verfügbar");
    currentCaseMedia = data.media || [];
    renderMediaCards(currentCaseMedia);
    renderDevices(devices);
    $("casePanel").hidden = false;
    $("caseDelete").disabled = false;
    $("casePanelNumber").textContent = data.case.case_number;
    $("caseDownload").classList.remove("disabled");
    $("caseDownload").setAttribute("aria-disabled", "false");
    $("caseDownload").href = `/api/cases/${encodeURIComponent(data.case.case_number)}/export.zip`;
    $("caseMedia").innerHTML = data.media.map((medium) => `
      <tr data-media-id="${Number(medium.id)}"><td>${escapeHtml(medium.sighting_number)}</td><td>${escapeHtml(medium.evidence_number || "—")}</td><td>${escapeHtml([medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path)}</td><td>${Number(medium.file_count).toLocaleString("de-AT")}</td><td>${Number(medium.keyword_matches).toLocaleString("de-AT")}</td><td>${statusTag(medium.decision)}</td></tr>
    `).join("");
  } catch (error) {
    $("decisionMessage").textContent = error.message;
  }
}

function renderMediaCards(media) {
  for (const device of devices) {
    const alreadyRecorded = device.serial && media.some((medium) => medium.serial === device.serial);
    if (alreadyRecorded && deviceStates.get(device.path) === "ready") deviceStates.set(device.path, "complete");
  }
  const renderCard = (medium, connected) => {
    const title = medium.evidence_number || "NUR GESICHTET";
    const model = [medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path;
    return `<div class="media-card-shell${connected ? " online" : " offline"}"><button class="media-card complete${connected ? " online" : " offline"}${Number(medium.id) === currentMediaId ? " active" : ""}" type="button" data-media-id="${Number(medium.id)}">
      <span class="media-card-top"><b>${escapeHtml(title)}</b>${statusTag(medium.decision)}</span>
      <strong>${escapeHtml(medium.sighting_number)}</strong>
      <small>${escapeHtml(model)}</small>
      <span class="media-card-metrics"><i>${Number(medium.file_count).toLocaleString("de-AT")} DATEIEN</i><i>${Number(medium.keyword_matches).toLocaleString("de-AT")} TREFFER</i></span>
      <span class="connection-badge ${connected ? "connected" : "disconnected"}">${connected ? "● ONLINE" : "○ OFFLINE"}</span>
      <em>DETAILS ÖFFNEN →</em>
    </button>${connected ? `<button class="media-eject" type="button" data-eject-device="${escapeHtml(medium.device_path)}">⏏ SICHER AUSWERFEN</button>` : ""}</div>`;
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
  if (!activeCaseNumber) {
    $("deviceCount").textContent = `${online} ONLINE · WARTET AUF FALL`;
    $("deviceEmptyTitle").textContent = "KEIN FALL AKTIV";
    $("deviceEmptyCopy").textContent = "Fallnummer und Kürzel eingeben, dann „Fall starten“. Erst danach ist Auto-Scan freigeschaltet.";
    $("deviceEmpty").hidden = false;
    return;
  }
  const offline = currentCaseMedia.filter((medium) => !devices.some((device) => device.serial && device.serial === medium.serial)).length;
  $("deviceCount").textContent = `${online} ONLINE · ${offline} OFFLINE`;
  $("deviceEmptyTitle").textContent = "NOCH KEIN MEDIUM IN DIESEM AUFTRAG";
  $("deviceEmptyCopy").textContent = "USB-Medium einstecken. Auto-Scan übernimmt die geschützte Grobsichtung.";
  $("deviceEmpty").hidden = online > 0;
}

function updateOrderSummary() {
  $("auftragSummary").textContent = activeCaseNumber ? `AKTIV: ${activeCaseNumber}` : "KEIN FALL AKTIV · SCAN GESPERRT";
  $("autoScanToggle").nextElementSibling.textContent = $("autoScanToggle").checked ? "AUTO-SCAN EIN" : "AUTO-SCAN AUS";
}

function updateCaseSessionUi(message = "") {
  const draftCase = $("caseNumber").value.trim().toUpperCase();
  const draftOperator = $("operator").value.trim().toUpperCase();
  const ready = Boolean(draftCase && draftOperator && !runningPaths.size);
  const sameSession = activeCaseNumber === draftCase && activeOperator === draftOperator;
  $("caseStart").disabled = !ready || sameSession;
  $("caseStart").textContent = activeCaseNumber && !sameSession ? "↻ ANDEREN FALL STARTEN" : "▶ FALL STARTEN";
  $("caseStop").disabled = !activeCaseNumber || runningPaths.size > 0;
  $("activeCaseDisplay").classList.toggle("locked", !activeCaseNumber);
  $("activeCaseNumber").textContent = activeCaseNumber || "KEIN FALL";
  $("activeCaseOperator").textContent = activeCaseNumber ? `BEARBEITER: ${activeOperator}` : "SCAN GESPERRT";
  if (message) {
    $("caseStartMessage").textContent = message;
  } else if (!draftCase || !draftOperator) {
    $("caseStartMessage").textContent = "FALLNUMMER UND KÜRZEL EINGEBEN";
  } else if (sameSession) {
    $("caseStartMessage").textContent = "DIESER FALL IST AKTIV";
  } else if (activeCaseNumber) {
    $("caseStartMessage").textContent = `${activeCaseNumber} BLEIBT AKTIV, BIS DER WECHSEL BESTÄTIGT WIRD`;
  } else {
    $("caseStartMessage").textContent = "BEREIT — FALL MUSS AUSDRÜCKLICH GESTARTET WERDEN";
  }
  $("caseStartMessage").className = `case-start-message${ready && !sameSession ? " warning" : activeCaseNumber ? " ready" : ""}`;
  updateOrderSummary();
  updateScanAvailability();
  updateDecisionAvailability();
}

const stateLabels = {
  ready: "BEREIT", scanning: "SCAN LÄUFT", complete: "FERTIG", error: "PRÜFEN", unavailable: "NICHT BEREIT",
};

function resetDeviceStatesForCase() {
  for (const device of devices) {
    const recorded = activeCaseNumber && device.serial && currentCaseMedia.some((medium) => medium.serial === device.serial);
    if (runningPaths.has(device.path)) deviceStates.set(device.path, "scanning");
    else if (recorded) deviceStates.set(device.path, "complete");
    else deviceStates.set(device.path, device.scan_supported ? "ready" : "unavailable");
  }
}

function renderDevices(items, activePaths = []) {
  devices = items || [];
  const active = new Set(activePaths);
  const presentPaths = new Set(devices.map((device) => device.path));
  for (const path of deviceStates.keys()) if (!presentPaths.has(path)) deviceStates.delete(path);
  for (const device of devices) {
    if (active.has(device.path)) deviceStates.set(device.path, "scanning");
    else if (!deviceStates.has(device.path)) deviceStates.set(device.path, device.scan_supported ? "ready" : "unavailable");
  }
  const visibleDevices = devices.filter((device) => !(
    device.serial && currentCaseMedia.some((medium) => medium.serial === device.serial)
  ));
  $("deviceList").innerHTML = activeCaseNumber ? visibleDevices.map((device) => {
    const state = deviceStates.get(device.path) || "ready";
    const model = [device.vendor, device.model].filter(Boolean).join(" ") || (device.media_type === "optical" ? "CD/DVD-Laufwerk" : "USB-Datenträger");
    const serial = device.serial || "NICHT GEMELDET";
    const type = device.media_type === "optical" ? "CD/DVD" : "USB";
    const disabled = !device.scan_supported || state === "scanning";
    return `<article class="device-card" data-state="${state}">
      <span class="device-card-top"><i class="device-led" title="${stateLabels[state]}"></i><b>NEUES MEDIUM</b><em>● ONLINE</em></span>
      <div class="device-copy"><strong>${escapeHtml(model)}</strong><span>${escapeHtml(device.path)} · ${formatBytes(device.size)} · ${type}</span><code title="${escapeHtml(serial)}">SERIAL ${escapeHtml(serial.length > 22 ? `${serial.slice(0, 22)}…` : serial)}</code></div>
      <div class="device-state"><b>${stateLabels[state]}</b><small>${escapeHtml(device.unavailable_reason || "")}</small></div>
      <div class="device-progress" aria-label="Scanfortschritt"><i></i></div>
      <button type="button" data-scan-device="${escapeHtml(device.path)}" ${disabled ? "disabled" : ""}>${state === "complete" ? "ERNEUT SCANNEN" : "SCANNEN"}</button>
    </article>`;
  }).join("") : "";
  if (!activeCaseNumber) {
    $("mediaCards").innerHTML = "";
    $("offlineMediaPanel").hidden = true;
  }
  renderMediaCards(currentCaseMedia);
  updateDashboardState();
  updateScanAvailability();
  scheduleAutoScan(400);
}

function updateScanAvailability() {
  for (const button of document.querySelectorAll("[data-scan-device]")) {
    const device = devices.find((item) => item.path === button.dataset.scanDevice);
    button.disabled = !device?.scan_supported || deviceStates.get(device.path) === "scanning" || !activeCaseNumber || !activeOperator;
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
  $("caseList").innerHTML = knownCases.map((item) => `<button type="button" class="case-list-item${item.case_number === activeCaseNumber ? " active" : item.case_number === selected ? " selected" : ""}" data-case-number="${escapeHtml(item.case_number)}">
    <strong>${escapeHtml(item.case_number)}</strong><span>${Number(item.media_count)} MEDIEN</span><span class="open-count">${Number(item.open_count)} OFFEN</span>
  </button>`).join("") || "<p>NOCH KEINE FÄLLE VORHANDEN</p>";
}

async function refresh(loadLatest = false, manual = false) {
  if (manual) {
    $("deviceRefresh").disabled = true;
    setSystemState("DATENTRÄGER WERDEN AKTUALISIERT", "busy");
  }
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("offline");
    const data = await response.json();
    renderDevices(data.devices || [], data.active_devices || []);
    renderCaseHistory(data.cases || []);
    if (loadLatest && data.latest) renderRecord(data.latest);
    if (manual) setSystemState(activeCaseNumber ? "DATENTRÄGER AKTUELL" : "KEIN FALL AKTIV");
  } catch (_) {
    setSystemState("VERBINDUNG PRÜFEN", "error");
  } finally {
    if (manual) $("deviceRefresh").disabled = false;
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
  if (!activeCaseNumber || !activeOperator) {
    setSystemState("ZUERST FALL STARTEN", "locked");
    $("auftragPanel").open = true;
    return;
  }
  if (standalone) { batchTotal = 1; batchDone = 0; }
  runningPaths.add(devicePath);
  deviceStates.set(devicePath, "scanning");
  renderDevices(devices);
  updateProgress();
  try {
    const response = await fetch("/api/scans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_number: activeCaseNumber, operator: activeOperator, device_path: devicePath }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan fehlgeschlagen");
    deviceStates.set(devicePath, "complete");
    await loadCase(data.media.case_number);
    $("auftragPanel").open = false;
    $("results").hidden = true;
  } catch (error) {
    $("progressLabel").textContent = `FEHLER: ${error.message}`;
    deviceStates.set(devicePath, "error");
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
  const paths = devices.filter((device) => device.scan_supported && deviceStates.get(device.path) === "ready").map((device) => device.path);
  if (!paths.length) return;
  batchTotal = paths.length;
  batchDone = 0;
  await Promise.allSettled(paths.map((path) => runScan(path, false)));
  await refresh(false);
}

function maybeAutoScan() {
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
  $("saveDecision").disabled = true;
  $("decisionMessage").textContent = "Wird protokolliert …";
  try {
    const response = await fetch(`/api/media/${currentMediaId}/decision`, {
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
    if (!response.ok) throw new Error(data.error || "Entscheidung konnte nicht gespeichert werden");
    renderRecord(data);
    $("decisionMessage").textContent = "ENTSCHEIDUNG MIT ZEITSTEMPEL PROTOKOLLIERT";
  } catch (error) {
    $("decisionMessage").textContent = `FEHLER: ${error.message}`;
  } finally {
    updateDecisionAvailability();
  }
}

function treeEntriesHtml(entries) {
  return entries.map((entry) => {
    if (entry.kind === "directory") {
      return `<details class="tree-folder" data-loaded="false">
        <summary data-tree-prefix="${escapeHtml(entry.path)}"><span class="tree-arrow">▶</span><b>${escapeHtml(entry.name)}</b><small>${Number(entry.file_count).toLocaleString("de-AT")} DATEIEN · ${formatBytes(entry.size)}</small></summary>
        <div class="tree-children"><p class="tree-loading">ORDNER ÖFFNEN …</p></div>
      </details>`;
    }
    return `<div class="tree-file"><span>·</span><b>${escapeHtml(entry.name)}</b><small>${escapeHtml(entry.category)} · ${formatBytes(entry.size)}</small></div>`;
  }).join("") || '<p class="tree-loading">ORDNER IST LEER</p>';
}

async function loadInventoryTree(prefix = "", target = $("inventoryTree"), offset = 0) {
  if (!currentMediaId) return;
  if (offset === 0) target.innerHTML = '<p class="tree-loading">VERZEICHNIS WIRD GELADEN …</p>';
  else target.querySelector(".tree-more")?.remove();
  try {
    const response = await fetch(`/api/media/${currentMediaId}/tree?prefix=${encodeURIComponent(prefix)}&limit=300&offset=${offset}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    const entries = treeEntriesHtml(data.entries || []);
    if (offset === 0) target.innerHTML = entries;
    else target.insertAdjacentHTML("beforeend", entries);
    if (data.has_more) target.insertAdjacentHTML("beforeend", `<button class="tree-more" type="button" data-tree-prefix="${escapeHtml(prefix)}" data-tree-offset="${Number(data.next_offset)}">WEITERE EINTRÄGE LADEN</button>`);
    inventoryTreeMediaId = currentMediaId;
    $("inventoryCount").textContent = `${data.total} EINTRÄGE AUF DIESER EBENE`;
    if (prefix === "" && offset === 0 && data.entries?.length === 1 && data.entries[0].kind === "directory") {
      const folder = target.querySelector(":scope > .tree-folder");
      if (folder) {
        folder.open = true;
        folder.dataset.loaded = "true";
        await loadInventoryTree(data.entries[0].path, folder.querySelector(".tree-children"));
      }
    }
  } catch (error) {
    target.innerHTML = `<p class="tree-loading error">FEHLER: ${escapeHtml(error.message)}</p>`;
  }
}

async function loadInventory() {
  if (!currentMediaId) return;
  const search = $("inventorySearch").value.trim();
  if (!search) {
    $("inventorySearchResults").hidden = true;
    $("inventoryTree").hidden = false;
    await loadInventoryTree();
    return;
  }
  $("inventoryCount").textContent = "LÄDT …";
  try {
    const query = encodeURIComponent(search);
    const response = await fetch(`/api/media/${currentMediaId}/files?q=${query}&limit=250`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    $("inventoryCount").textContent = `${data.shown} / ${data.total} ANGEZEIGT`;
    $("inventoryTree").hidden = true;
    $("inventorySearchResults").hidden = false;
    $("inventoryFiles").innerHTML = data.files.map((file) => `
      <tr><td>${escapeHtml(file.path)}</td><td>${escapeHtml(file.category)}</td><td>${escapeHtml(file.extension || "—")}</td><td>${formatBytes(file.size)}</td></tr>
    `).join("");
  } catch (error) {
    $("inventoryCount").textContent = `FEHLER: ${error.message}`;
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
  try {
    const response = await fetch("/api/cases/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_number: caseNumber, operator }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Fall konnte nicht gestartet werden");
    activeCaseNumber = data.case.case_number;
    activeOperator = operator;
    $("caseNumber").value = activeCaseNumber;
    currentMediaId = null;
    currentCaseMedia = [];
    caseHistorySignature = "";
    await loadCase(activeCaseNumber);
    resetDeviceStatesForCase();
    renderDevices(devices);
    updateCaseSessionUi(`FALL ${activeCaseNumber} AKTIV · SCANS FREIGEGEBEN`);
    setSystemState("SYSTEM BEREIT", "ready");
    $("auftragPanel").open = false;
    await refresh(false);
    scheduleAutoScan(150);
  } catch (error) {
    $("caseStartMessage").textContent = `FEHLER: ${error.message}`;
    $("caseStartMessage").className = "case-start-message warning";
    updateCaseSessionUi($("caseStartMessage").textContent);
  }
}

function stopCaseSession() {
  if (runningPaths.size) return;
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
  $("caseDownload").classList.add("disabled");
  $("caseDownload").setAttribute("aria-disabled", "true");
  $("caseDownload").href = "#";
  $("caseDelete").disabled = true;
  caseHistorySignature = "";
  resetDeviceStatesForCase();
  renderDevices(devices);
  renderCaseHistory(knownCases);
  updateCaseSessionUi("FALL BEENDET · SCANS GESPERRT");
  setSystemState("KEIN FALL AKTIV", "locked");
  $("auftragPanel").open = true;
}

async function deleteCurrentCase() {
  const caseNumber = activeCaseNumber;
  if (!caseNumber || $("caseDelete").disabled) return;
  const password = $("deletePassword").value;
  $("deleteMessage").textContent = "FALL WIRD ENTFERNT …";
  try {
    const response = await fetch(`/api/cases/${encodeURIComponent(caseNumber)}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Fall konnte nicht gelöscht werden");
    $("deleteModal").close();
    $("deletePassword").value = "";
    stopCaseSession();
    setSystemState("FALL ENTFERNT · KEIN FALL AKTIV", "locked");
    await refresh(false);
  } catch (error) {
    $("deleteMessage").textContent = `FEHLER: ${error.message}`;
  }
}

async function ejectDevice(devicePath) {
  setSystemState("DATENTRÄGER WIRD AUSGEWORFEN …", "busy");
  try {
    const response = await fetch("/api/devices/eject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_path: devicePath }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Auswerfen fehlgeschlagen");
    setSystemState("DATENTRÄGER KANN ABGEZOGEN WERDEN", "ready");
    await refresh(false);
  } catch (error) {
    setSystemState(`FEHLER: ${error.message}`, "error");
  }
}

async function openMedia(mediaId) {
  try {
    const response = await fetch(`/api/media/${mediaId}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Medienakte nicht verfügbar");
    renderRecord(data);
    renderMediaCards(currentCaseMedia);
    $("dashboardView").hidden = true;
    $("results").hidden = false;
    $("results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    $("decisionMessage").textContent = `FEHLER: ${error.message}`;
  }
}

function showDashboard() {
  if ($("evidenceModal").open) $("evidenceModal").close();
  if ($("deleteModal").open) $("deleteModal").close();
  $("results").hidden = true;
  $("dashboardView").hidden = false;
  currentMediaId = null;
  renderMediaCards(currentCaseMedia);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

setInterval(() => { $("clock").textContent = `UTC ${new Date().toISOString().slice(11, 19)}`; }, 1000);
$("autoScanToggle").addEventListener("change", () => {
  updateOrderSummary();
  if (!activeCaseNumber) setSystemState("KEIN FALL AKTIV", "locked");
  scheduleAutoScan(100);
});
$("deviceRefresh").addEventListener("click", () => refresh(false, true));
$("deviceList").addEventListener("click", (event) => {
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
$("openEvidenceModal").addEventListener("click", () => $("evidenceModal").showModal());
$("closeEvidenceModal").addEventListener("click", () => $("evidenceModal").close());
$("evidenceModal").addEventListener("click", (event) => {
  if (event.target === $("evidenceModal")) $("evidenceModal").close();
});
$("caseList").addEventListener("click", (event) => {
  const item = event.target.closest("button[data-case-number]");
  if (!item) return;
  $("caseNumber").value = item.dataset.caseNumber;
  caseHistorySignature = "";
  renderCaseHistory(knownCases);
  updateCaseSessionUi();
  $("casePicker").open = false;
});
$("caseStart").addEventListener("click", startCaseSession);
$("caseStop").addEventListener("click", stopCaseSession);
$("caseDelete").addEventListener("click", () => {
  $("deleteCaseNumber").textContent = activeCaseNumber || "—";
  $("deletePassword").value = "";
  $("deleteMessage").textContent = "";
  $("deleteModal").showModal();
  $("deletePassword").focus();
});
$("cancelDelete").addEventListener("click", () => $("deleteModal").close());
$("deleteForm").addEventListener("submit", (event) => { event.preventDefault(); deleteCurrentCase(); });
$("refreshButton").addEventListener("click", refresh);
$("saveDecision").addEventListener("click", saveDecision);
$("inventoryLoad").addEventListener("click", loadInventory);
$("inventorySearch").addEventListener("keydown", (event) => { if (event.key === "Enter") loadInventory(); });
$("inventoryPanel").addEventListener("toggle", () => {
  if ($("inventoryPanel").open && currentMediaId && inventoryTreeMediaId !== currentMediaId) loadInventoryTree();
});
$("inventoryTree").addEventListener("click", (event) => {
  const more = event.target.closest("button.tree-more");
  if (more) {
    loadInventoryTree(more.dataset.treePrefix, more.parentElement, Number(more.dataset.treeOffset));
    return;
  }
  const summary = event.target.closest("summary[data-tree-prefix]");
  if (!summary) return;
  const folder = summary.parentElement;
  if (!folder.open && folder.dataset.loaded !== "true") {
    folder.dataset.loaded = "true";
    setTimeout(() => loadInventoryTree(summary.dataset.treePrefix, folder.querySelector(".tree-children")), 0);
  }
});
$("caseMedia").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-media-id]");
  if (row) openMedia(Number(row.dataset.mediaId));
});
$("decisionReason").addEventListener("change", updateDecisionAvailability);
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
refresh();
setInterval(() => refresh(false), 2500);
