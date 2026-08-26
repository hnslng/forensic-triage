const demoSummary = {
  evidence: "BM-FAST-001", duration_seconds: 0.732, file_count: 960, directory_count: 18,
  total_file_bytes: 553421052, keyword_matches: 60,
  categories_by_count: { Bilder: 600, Audio: 180, Dokumente: 100, Tabellen: 35, Archive: 18, Video: 10, Datenbanken: 5, "E-Mail": 5, Unbekannt: 7 },
  largest_files: [
    { path: "TRIAGE_TESTDATA/Video/video_0001.mp4", size: 209715200 },
    { path: "TRIAGE_TESTDATA/Video/video_0002.mp4", size: 157286400 },
    { path: "TRIAGE_TESTDATA/Video/video_0003.mp4", size: 104857600 },
    { path: "TRIAGE_TESTDATA/Video/video_0004.mp4", size: 52428800 },
    { path: "TRIAGE_TESTDATA/Video/video_0005.mp4", size: 26214400 },
  ],
};
const demoHits = { rechnung: 20, buchhaltung: 10, fibu: 5, datev: 3, kassabuch: 4, kunden: 15, steuerberater: 3 };
const $ = (id) => document.getElementById(id);
let devices = [];
const deviceStates = new Map();
const runningPaths = new Set();
let batchTotal = 0;
let batchDone = 0;
let activeInput = null;
let currentMediaId = null;
let currentDecision = null;
const formatBytes = (bytes) => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes || 0), unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toLocaleString("de-AT", { maximumFractionDigits: 1 })} ${units[unit]}`;
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
}[char]));

function renderResults(summary, hits = demoHits) {
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
  $("decisionEvidenceWrap").hidden = currentDecision !== "secure";
  $("decisionReason").value = media.reason_code || "";
  $("decisionNote").value = media.reason_note || "";
  for (const button of document.querySelectorAll("[data-decision]")) {
    button.classList.toggle("active", button.dataset.decision === currentDecision);
  }
  updateDecisionAvailability();
}

function renderRecord(record) {
  renderResults(record.summary, record.hits);
  if (record.media) {
    renderArchive(record.archive);
    renderDecision(record.media);
    loadCase(record.media.case_number);
    $("inventoryPanel").hidden = false;
  }
}

function statusTag(decision) {
  return `<span class="status-tag status-${decision}">${decisionLabels[decision] || decisionLabels.open}</span>`;
}

async function loadCase(caseNumber) {
  if (!caseNumber) return;
  try {
    const response = await fetch(`/api/cases/${encodeURIComponent(caseNumber)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Fallakte nicht verfügbar");
    $("casePanel").hidden = false;
    $("casePanelNumber").textContent = data.case.case_number;
    $("caseMedia").innerHTML = data.media.map((medium) => `
      <tr data-media-id="${Number(medium.id)}"><td>${escapeHtml(medium.sighting_number)}</td><td>${escapeHtml(medium.evidence_number || "—")}</td><td>${escapeHtml([medium.vendor, medium.model].filter(Boolean).join(" ") || medium.device_path)}</td><td>${Number(medium.file_count).toLocaleString("de-AT")}</td><td>${Number(medium.keyword_matches).toLocaleString("de-AT")}</td><td>${statusTag(medium.decision)}</td></tr>
    `).join("");
  } catch (error) {
    $("decisionMessage").textContent = error.message;
  }
}

const stateLabels = {
  ready: "BEREIT", scanning: "SCAN LÄUFT", complete: "FERTIG", error: "PRÜFEN", unavailable: "NICHT BEREIT",
};

function renderDevices(items, activePaths = []) {
  devices = items || [];
  const active = new Set(activePaths);
  const presentPaths = new Set(devices.map((device) => device.path));
  for (const path of deviceStates.keys()) if (!presentPaths.has(path)) deviceStates.delete(path);
  for (const device of devices) {
    if (active.has(device.path)) deviceStates.set(device.path, "scanning");
    else if (!deviceStates.has(device.path)) deviceStates.set(device.path, device.scan_supported ? "ready" : "unavailable");
  }
  $("deviceEmpty").hidden = devices.length > 0;
  $("deviceCount").textContent = `${devices.length} ${devices.length === 1 ? "MEDIUM" : "MEDIEN"}`;
  $("deviceList").innerHTML = devices.map((device) => {
    const state = deviceStates.get(device.path) || "ready";
    const model = [device.vendor, device.model].filter(Boolean).join(" ") || (device.media_type === "optical" ? "CD/DVD-Laufwerk" : "USB-Datenträger");
    const serial = device.serial || "NICHT GEMELDET";
    const type = device.media_type === "optical" ? "CD/DVD" : "USB";
    const disabled = !device.scan_supported || state === "scanning";
    return `<article class="device-card" data-state="${state}">
      <i class="device-led" title="${stateLabels[state]}"></i>
      <div class="device-copy"><strong>${escapeHtml(model)}</strong><span>${escapeHtml(device.path)} · ${formatBytes(device.size)} · ${type}</span><code title="${escapeHtml(serial)}">SERIAL ${escapeHtml(serial.length > 22 ? `${serial.slice(0, 22)}…` : serial)}</code></div>
      <div class="device-state"><b>${stateLabels[state]}</b><small>${escapeHtml(device.unavailable_reason || "RO-PRÜFUNG BEIM START")}</small></div>
      <button type="button" data-scan-device="${escapeHtml(device.path)}" ${disabled ? "disabled" : ""}>${state === "complete" ? "ERNEUT SCANNEN" : "SCANNEN"}</button>
    </article>`;
  }).join("");
  updateScanAvailability();
}

function updateScanAvailability() {
  const hasCase = $("caseNumber").value.trim().length > 0;
  const hasOperator = $("operator").value.trim().length > 0;
  const available = devices.some((device) => device.scan_supported && deviceStates.get(device.path) !== "scanning");
  $("scanAllButton").disabled = !available || !hasCase || !hasOperator;
  for (const button of document.querySelectorAll("[data-scan-device]")) {
    const device = devices.find((item) => item.path === button.dataset.scanDevice);
    button.disabled = !device?.scan_supported || deviceStates.get(device.path) === "scanning" || !hasCase || !hasOperator;
  }
}

function updateDecisionAvailability() {
  const reasonRequired = currentDecision === "not_selected";
  const hasReason = $("decisionReason").value.length > 0;
  const hasEvidence = $("decisionEvidence").value.trim().length > 0;
  $("saveDecision").disabled = !currentMediaId || !currentDecision || (reasonRequired && !hasReason) || (currentDecision === "secure" && !hasEvidence) || !$("operator").value.trim();
}

function openKeyboard(input) {
  activeInput = input || activeInput || $("caseNumber");
  $("keyboardTarget").textContent = activeInput === $("caseNumber") ? "FALLNUMMER" : activeInput === $("decisionEvidence") ? "BEWEISMITTEL" : "BEARBEITER";
  $("screenKeyboard").hidden = false;
}

function buildKeyboard() {
  const rows = [
    "1234567890".split(""),
    "QWERTZUIOP".split(""),
    "ASDFGHJKL".split(""),
    "YXCVBNM-_.".split(""),
    ["BACKSPACE", "CLEAR", "NEXT"],
  ];
  const labels = { BACKSPACE: "⌫ LÖSCHEN", CLEAR: "LEEREN", NEXT: "WEITER ↵" };
  $("keyboardKeys").innerHTML = rows.map((row) => `<div class="keyboard-row" style="--key-count:${row.length}">${row.map((key) => `<button type="button" class="${labels[key] ? "wide" : ""}" data-key="${key}">${labels[key] || key}</button>`).join("")}</div>`).join("");
  $("keyboardKeys").addEventListener("click", (event) => {
    const key = event.target.closest("button")?.dataset.key;
    if (!key || !activeInput) return;
    if (key === "BACKSPACE") activeInput.value = activeInput.value.slice(0, -1);
    else if (key === "CLEAR") activeInput.value = "";
    else if (key === "NEXT") {
      if (activeInput === $("caseNumber")) openKeyboard($("operator"));
      else if (activeInput === $("operator") && !$("decisionEvidenceWrap").hidden) openKeyboard($("decisionEvidence"));
      else { $("screenKeyboard").hidden = true; $("scanAllButton").focus(); }
      updateScanAvailability();
      return;
    } else activeInput.value += key === "SPACE" ? " " : key;
    activeInput.value = activeInput.value.toUpperCase().slice(0, 36);
    updateScanAvailability();
  });
}

async function refresh(loadLatest = true) {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("offline");
    const data = await response.json();
    renderDevices(data.devices || [], data.active_devices || []);
    if (loadLatest && data.latest) renderRecord(data.latest);
  } catch (_) {
    $("systemState").textContent = "VERBINDUNG PRÜFEN";
  }
}

function updateProgress() {
  $("progressPanel").hidden = batchTotal === 0;
  const percent = batchTotal ? Math.round((batchDone / batchTotal) * 100) : 0;
  $("progressValue").textContent = `${percent}%`;
  $("progressBar").style.width = `${Math.max(runningPaths.size ? 8 : 0, percent)}%`;
  if (runningPaths.size) $("progressLabel").textContent = `${runningPaths.size} Grobsichtung${runningPaths.size === 1 ? "" : "en"} parallel …`;
  else if (batchDone === batchTotal) $("progressLabel").textContent = "Sichtungslauf abgeschlossen";
  $("progressLog").textContent = runningPaths.size ? `$ RO-Prüfung + Inventarisierung: ${[...runningPaths].join(" · ")}` : "$ Protokolle und Prüfsummen aktualisiert";
}

async function runScan(devicePath, standalone = true) {
  const caseNumber = $("caseNumber").value.trim().toUpperCase();
  const operator = $("operator").value.trim().toUpperCase();
  if (!caseNumber) { $("caseNumber").focus(); return; }
  if (!operator) { $("operator").focus(); return; }
  const normalizedCase = caseNumber.replace(/[^A-Z0-9._-]/g, "-").slice(0, 80);
  if (standalone) { batchTotal = 1; batchDone = 0; }
  runningPaths.add(devicePath);
  deviceStates.set(devicePath, "scanning");
  renderDevices(devices);
  $("screenKeyboard").hidden = true;
  updateProgress();
  try {
    const response = await fetch("/api/scans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_number: normalizedCase, operator, device_path: devicePath }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan fehlgeschlagen");
    deviceStates.set(devicePath, "complete");
    renderRecord(data);
  } catch (error) {
    $("progressLabel").textContent = `FEHLER: ${error.message}`;
    deviceStates.set(devicePath, "error");
    $("systemState").textContent = "PRÜFUNG NÖTIG";
  } finally {
    runningPaths.delete(devicePath);
    batchDone += 1;
    renderDevices(devices);
    updateProgress();
    updateScanAvailability();
  }
}

async function runAllScans() {
  const paths = devices.filter((device) => device.scan_supported && deviceStates.get(device.path) !== "scanning").map((device) => device.path);
  if (!paths.length) return;
  batchTotal = paths.length;
  batchDone = 0;
  await Promise.allSettled(paths.map((path) => runScan(path, false)));
  await refresh(false);
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
        reason_code: $("decisionReason").value || null,
        reason_note: $("decisionNote").value,
        operator: $("operator").value.trim().toUpperCase(),
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

async function loadInventory() {
  if (!currentMediaId) return;
  $("inventoryCount").textContent = "LÄDT …";
  try {
    const query = encodeURIComponent($("inventorySearch").value.trim());
    const response = await fetch(`/api/media/${currentMediaId}/files?q=${query}&limit=250`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Verzeichnis nicht verfügbar");
    $("inventoryCount").textContent = `${data.shown} / ${data.total} ANGEZEIGT`;
    $("inventoryFiles").innerHTML = data.files.map((file) => `
      <tr><td>${escapeHtml(file.path)}</td><td>${escapeHtml(file.category)}</td><td>${escapeHtml(file.extension || "—")}</td><td>${formatBytes(file.size)}</td></tr>
    `).join("");
  } catch (error) {
    $("inventoryCount").textContent = `FEHLER: ${error.message}`;
  }
}

async function openMedia(mediaId) {
  try {
    const response = await fetch(`/api/media/${mediaId}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Medienakte nicht verfügbar");
    renderRecord(data);
    $("results").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    $("decisionMessage").textContent = `FEHLER: ${error.message}`;
  }
}

setInterval(() => { $("clock").textContent = `UTC ${new Date().toISOString().slice(11, 19)}`; }, 1000);
$("scanAllButton").addEventListener("click", runAllScans);
$("deviceList").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-scan-device]");
  if (button) runScan(button.dataset.scanDevice);
});
$("refreshButton").addEventListener("click", refresh);
$("saveDecision").addEventListener("click", saveDecision);
$("inventoryLoad").addEventListener("click", loadInventory);
$("inventorySearch").addEventListener("keydown", (event) => { if (event.key === "Enter") loadInventory(); });
$("caseMedia").addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-media-id]");
  if (row) openMedia(Number(row.dataset.mediaId));
});
$("decisionReason").addEventListener("change", updateDecisionAvailability);
$("decisionEvidence").addEventListener("input", updateDecisionAvailability);
for (const button of document.querySelectorAll("[data-decision]")) {
  button.addEventListener("click", () => {
    currentDecision = button.dataset.decision;
    $("decisionEvidenceWrap").hidden = currentDecision !== "secure";
    if (currentDecision !== "secure") $("decisionEvidence").value = "";
    for (const peer of document.querySelectorAll("[data-decision]")) peer.classList.toggle("active", peer === button);
    $("decisionState").textContent = decisionLabels[currentDecision];
    updateDecisionAvailability();
  });
}
$("keyboardButton").addEventListener("click", () => openKeyboard(activeInput));
$("keyboardClose").addEventListener("click", () => { $("screenKeyboard").hidden = true; });
for (const input of document.querySelectorAll(".case-input")) {
  input.addEventListener("focus", () => {
    activeInput = input;
    $("keyboardTarget").textContent = input === $("caseNumber") ? "FALLNUMMER" : input === $("decisionEvidence") ? "BEWEISMITTEL" : "BEARBEITER";
    if (window.matchMedia("(pointer: coarse)").matches) openKeyboard(input);
  });
  input.addEventListener("input", updateScanAvailability);
  input.addEventListener("input", updateDecisionAvailability);
}
buildKeyboard();
renderResults(demoSummary, demoHits);
refresh();
setInterval(() => refresh(false), 2500);
