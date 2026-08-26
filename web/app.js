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
let devicePresent = false;
let activeInput = null;
const formatBytes = (bytes) => {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes || 0), unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toLocaleString("de-AT", { maximumFractionDigits: 1 })} ${units[unit]}`;
};

function renderResults(summary, hits = demoHits) {
  $("resultEvidence").textContent = (summary.evidence || "OHNE NUMMER").replace("__", " / ");
  $("resultDuration").textContent = `${Number(summary.duration_seconds || 0).toLocaleString("de-AT")} s`;
  $("fileCount").textContent = Number(summary.file_count || 0).toLocaleString("de-AT");
  $("directoryCount").textContent = Number(summary.directory_count || 0).toLocaleString("de-AT");
  $("keywordMatches").textContent = Number(summary.keyword_matches || 0).toLocaleString("de-AT");
  $("totalBytes").textContent = formatBytes(summary.total_file_bytes);
  const categories = Object.entries(summary.categories_by_count || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...categories.map(([, count]) => count), 1);
  $("categories").innerHTML = categories.map(([name, count]) => `
    <div class="bar-row"><span>${name.toUpperCase()}</span><div class="bar-track"><div class="bar-fill" style="width:${(count / max) * 100}%"></div></div><span class="bar-value">${count}</span></div>
  `).join("");
  $("keywords").innerHTML = Object.entries(hits).filter(([, count]) => count > 0).sort((a, b) => b[1] - a[1]).map(([word, count]) => `
    <div class="keyword-row"><span>${word.toUpperCase()}</span><b>${count}</b></div>
  `).join("");
  $("largestFiles").innerHTML = (summary.largest_files || []).map((file, index) => `
    <tr><td>${String(index + 1).padStart(2, "0")}</td><td>${file.path}</td><td>${formatBytes(file.size)}</td></tr>
  `).join("");
  $("results").hidden = false;
}

function renderDevice(device) {
  const present = Boolean(device && device.path);
  devicePresent = present;
  $("deviceInfo").hidden = !present;
  $("deviceEmpty").hidden = present;
  updateScanAvailability();
  if (!present) return;
  $("deviceModel").textContent = [device.vendor, device.model].filter(Boolean).join(" ") || "USB-Datenträger";
  $("deviceMeta").textContent = `${device.path} · ${formatBytes(device.size)} · USB`;
  const serial = device.serial || "NICHT GEMELDET";
  $("deviceSerial").textContent = `SERIAL ${serial.length > 26 ? `${serial.slice(0, 26)}…` : serial}`;
  $("deviceSerial").title = serial;
}

function updateScanAvailability() {
  const hasCase = $("caseNumber").value.trim().length > 0;
  const hasEvidence = $("evidenceNumber").value.trim().length > 0;
  $("scanButton").disabled = !devicePresent || !hasCase || !hasEvidence;
}

function openKeyboard(input) {
  activeInput = input || activeInput || $("caseNumber");
  $("keyboardTarget").textContent = activeInput === $("caseNumber") ? "FALLNUMMER" : "BEWEISMITTEL";
  $("screenKeyboard").hidden = false;
}

function buildKeyboard() {
  const keys = "1234567890QWERTZUIOPASDFGHJKLYXCVBNM-_/ .".split("");
  $("keyboardKeys").innerHTML = keys.map((key) => `<button type="button" data-key="${key === " " ? "SPACE" : key}">${key === " " ? "LEER" : key}</button>`).join("") +
    '<button type="button" class="wide" data-key="BACKSPACE">⌫ LÖSCHEN</button><button type="button" class="wide" data-key="CLEAR">LEEREN</button><button type="button" class="wide" data-key="NEXT">WEITER ↵</button>';
  $("keyboardKeys").addEventListener("click", (event) => {
    const key = event.target.closest("button")?.dataset.key;
    if (!key || !activeInput) return;
    if (key === "BACKSPACE") activeInput.value = activeInput.value.slice(0, -1);
    else if (key === "CLEAR") activeInput.value = "";
    else if (key === "NEXT") {
      if (activeInput === $("caseNumber")) openKeyboard($("evidenceNumber"));
      else { $("screenKeyboard").hidden = true; $("scanButton").focus(); }
      updateScanAvailability();
      return;
    } else activeInput.value += key === "SPACE" ? " " : key;
    activeInput.value = activeInput.value.toUpperCase().slice(0, 36);
    updateScanAvailability();
  });
}

async function refresh() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("offline");
    const data = await response.json();
    renderDevice(data.devices?.[0]);
    if (data.latest) renderResults(data.latest.summary, data.latest.hits);
  } catch (_) {
    renderResults(demoSummary, demoHits);
  }
}

async function runScan() {
  const caseNumber = $("caseNumber").value.trim().toUpperCase();
  const evidenceNumber = $("evidenceNumber").value.trim().toUpperCase();
  if (!caseNumber) { $("caseNumber").focus(); return; }
  if (!evidenceNumber) { $("evidenceNumber").focus(); return; }
  const evidence = `${caseNumber}__${evidenceNumber}`.replace(/[^A-Z0-9._-]/g, "-").slice(0, 80);
  $("scanButton").disabled = true;
  $("progressPanel").hidden = false;
  $("screenKeyboard").hidden = true;
  $("results").hidden = true;
  let progress = 8;
  $("progressValue").textContent = "08%";
  $("progressBar").style.width = "8%";
  $("progressLabel").textContent = "Schreibschutz wird geprüft …";
  const timer = setInterval(() => {
    progress = Math.min(progress + Math.ceil(Math.random() * 9), 88);
    $("progressValue").textContent = `${progress}%`;
    $("progressBar").style.width = `${progress}%`;
    if (progress > 35) $("progressLabel").textContent = "Dateisystem wird inventarisiert …";
    if (progress > 70) $("progressLabel").textContent = "Auswertung wird erstellt …";
  }, 260);
  try {
    const response = await fetch("/api/scans", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ evidence }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Scan fehlgeschlagen");
    clearInterval(timer);
    $("progressValue").textContent = "100%";
    $("progressBar").style.width = "100%";
    $("progressLabel").textContent = "Scan abgeschlossen";
    renderResults(data.summary, data.hits);
  } catch (error) {
    clearInterval(timer);
    $("progressLabel").textContent = `FEHLER: ${error.message}`;
    $("progressValue").textContent = "!";
    $("systemState").textContent = "PRÜFUNG NÖTIG";
  } finally {
    updateScanAvailability();
  }
}

setInterval(() => { $("clock").textContent = `UTC ${new Date().toISOString().slice(11, 19)}`; }, 1000);
$("scanButton").addEventListener("click", runScan);
$("refreshButton").addEventListener("click", refresh);
$("keyboardButton").addEventListener("click", () => openKeyboard(activeInput));
$("keyboardClose").addEventListener("click", () => { $("screenKeyboard").hidden = true; });
for (const input of document.querySelectorAll(".case-input")) {
  input.addEventListener("focus", () => {
    activeInput = input;
    $("keyboardTarget").textContent = input === $("caseNumber") ? "FALLNUMMER" : "BEWEISMITTEL";
    if (window.matchMedia("(pointer: coarse)").matches) openKeyboard(input);
  });
  input.addEventListener("input", updateScanAvailability);
}
buildKeyboard();
renderResults(demoSummary, demoHits);
refresh();
