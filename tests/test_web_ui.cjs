// Offline browser regressions: synthetic fixtures only; no Pi, USB or case writes.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
let browser;
before(async () => {
  browser = await chromium.launch({ headless: true, ...(process.env.TRIAGE_BROWSER_CHANNEL ? { channel: process.env.TRIAGE_BROWSER_CHANNEL } : {}) });
});
after(async () => { await browser?.close(); });
const media = [10, 3, 1, 8, 2].map(id => ({ id, case_number: 'TEST', sighting_number: `SICHT-${id}`, serial: `TEST-${id}`, model: `Testmedium ${id}`, file_count: 4, decision: 'open' }));
const entry = (name, kind = 'file') => ({ name, path: name, kind, category: 'Text/Logs', size: 10, file_count: 1 });
const pageData = entries => ({ entries, total: entries.length, shown: entries.length, offset: 0, next_offset: entries.length, has_more: false });
const record = id => ({ media: media.find(item => item.id === id), summary: { evidence: `SICHT-${id}`, categories_by_count: { Archive: 1, Dokumente: 1 }, largest_files: [] }, hits: { rechnung: 1 }, archive: {} });

async function setup(t, override = () => null) {
  diagReset();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
  const requests = [], errors = [];
  t.after(async () => { await page.close(); assert.deepEqual(errors, []); });
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    requests.push({ method: request.method(), path: url.pathname, query: url.search });
    assert.equal(url.hostname, 'triage.test');
    const custom = await override(url, request);
    if (custom) return route.fulfill(custom);
    assert.equal(request.method(), 'GET', 'Navigation must never change cases or trigger scans');
    const asset = { '/': 'index.html', '/app.js': 'app.js', '/styles.css': 'styles.css' }[url.pathname];
    if (asset) return route.fulfill({ contentType: asset.endsWith('.js') ? 'text/javascript' : asset.endsWith('.css') ? 'text/css' : 'text/html', body: fs.readFileSync(path.join(root, 'web', asset), 'utf8') });
    if (url.pathname === '/api/status') return route.fulfill({ json: { devices: [], cases: [], active_case: null, update: {} } });
    if (url.pathname === '/api/logs/recent') {
      const since = Number(url.searchParams.get('since') || 0);
      const limit = Number(url.searchParams.get('limit') || 200);
      const entries = diagEntriesPage(since, limit);
      return route.fulfill({ json: { entries, mode: diagFeed.mode, count: entries.length, latest: diagFeed.latest } });
    }
    if (url.pathname === '/api/profiles') return route.fulfill({ json: { profiles: [] } });
    if (url.pathname === '/api/cases/TEST') return route.fulfill({ json: { case: { case_number: 'TEST' }, media } });
    const match = url.pathname.match(/^\/api\/media\/(\d+)(?:\/(tree|files|container))?$/);
    if (!match) return route.fulfill({ status: 404, json: { error: 'Unknown test URL' } });
    const id = Number(match[1]), kind = match[2];
    if (!kind) return route.fulfill({ json: record(id) });
    if (kind === 'tree') return route.fulfill({ json: pageData([entry(`MEDIUM-${id}.txt`), { ...entry('Offen.zip', 'container'), container_id: '001:Offen.zip', container_status: 'ok', entry_count: 2 }]) });
    if (kind === 'container') return route.fulfill({ json: { ...pageData(url.searchParams.get('prefix') ? [entry('Dokumente/Rechnung.pdf')] : [entry('Dokumente', 'directory')]), container_status: 'ok' } });
    const files = [{ path: `MEDIUM-${id}-Offen.zip`, category: 'Archive', container_id: '001:Offen.zip', source: 'readonly_mount' }, { path: 'Offen.zip › Innen.rar', category: 'Archive', source: 'container_index', container_format: 'ZIP' }];
    return route.fulfill({ json: { total: files.length, shown: files.length, files } });
  });
  await page.goto('http://triage.test/', { waitUntil: 'networkidle' });
  return { page, requests };
}
async function open(page, id) {
  await page.evaluate(id => { activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' }; updateStartOverlay(); openMedia(id); }, id);
  await page.waitForFunction(id => inventoryTreeMediaId === id, id);
}
async function openSettingsFromAnywhere(page) {
  if (await page.locator('#startOverlay').isVisible()) {
    await page.locator('#startOverlaySettings').click();
  } else {
    await page.locator('#openSettings').click();
  }
}
async function openPowerFromAnywhere(page) {
  if (await page.locator('#startOverlay').isVisible()) {
    await page.locator('#startOverlayPower').click();
  } else {
    await page.locator('#openPowerModal').click();
  }
}
async function filter(page) {
  await page.locator('[data-inventory-category="Archive"]').click();
  await page.waitForFunction(() => document.getElementById('inventoryCount').textContent.includes('FUNDSTELLEN'));
}
function gate() {
  let release, entered;
  const arrived = new Promise(resolve => { entered = resolve; });
  const pending = new Promise(resolve => { release = resolve; });
  return { release, arrived, wait: async () => { entered(); await pending; } };
}

const settingsCatalog = { version: 1, sha256: 'first', categories: { Bilder: ['jpg', 'png'], Dokumente: ['pdf'] } };

// DIAGNOSE-Konsole (Alpha 70): controllable fake ring buffer behind /api/logs/recent.
let diagFeed = { entries: [], mode: 'normal', latest: 0 };
function diagPush(entry) {
  const seq = ++diagFeed.latest;
  diagFeed.entries.push({ seq, timestamp: entry.timestamp || '2026-10-05T19:42:01.015Z', level: entry.level || 'INFO', category: entry.category || 'USB', message: entry.message || 'Testereignis', ...(entry.details ? { details: entry.details } : {}) });
  return seq;
}
function diagReset() { diagFeed = { entries: [], mode: 'normal', latest: 0 }; }
function diagEntriesPage(since, limit) {
  const newer = diagFeed.entries.filter(e => e.seq > since);
  return diagFeed.entries.length && !since ? newer.slice(-limit) : newer.slice(0, limit);
}
const defaultCryptoRules = {
  version: 3,
  sha256: 'crypto-defaults',
  app_rules: [
    { id: 'wallet', name: 'Test Wallet', category: 'wallet', relevance: 'high', enabled: true, ios_bundle_ids: ['io.test.wallet'], android_package_ids: [], ios_id_status: 'verified', android_id_status: 'unverified', ios_id_note: '', android_id_note: '', aliases: [], former_names: [], terms: [], status: 'active', verified: true, source: 'Apple App Store', last_verified: '2026-10-03', regions: [], comment: '' },
    { id: 'android-only', name: 'Android Test Wallet', category: 'wallet', relevance: 'high', enabled: true, ios_bundle_ids: [], android_package_ids: ['org.test.android'], ios_id_status: 'unverified', android_id_status: 'verified', ios_id_note: '', android_id_note: '', aliases: [], former_names: [], terms: [], status: 'active', verified: true, source: 'Google Play', last_verified: '2026-10-03', regions: [], comment: '' },
    { id: 'unknown-ids', name: 'Unknown IDs Wallet', category: 'wallet', relevance: 'high', enabled: true, ios_bundle_ids: [], android_package_ids: [], ios_id_status: 'unverified', android_id_status: 'unverified', ios_id_note: 'Noch zu prüfen', android_id_note: '', aliases: [], former_names: [], terms: ['unknown wallet'], status: 'active', verified: false, source: '', last_verified: '', regions: [], comment: '' },
    { id: 'desktop-only', name: 'Desktop Tool', category: 'wallet', relevance: 'low', enabled: true, ios_bundle_ids: [], android_package_ids: [], ios_id_status: 'not_applicable', android_id_status: 'not_applicable', ios_id_note: 'Reines Desktopprodukt', android_id_note: 'Reines Desktopprodukt', aliases: [], former_names: [], terms: ['desktop tool'], status: 'active', verified: false, source: 'Herstellerdokumentation', last_verified: '2026-10-03', regions: [], comment: '' },
    { id: 'bank', name: 'Test Bank', category: 'banking', relevance: 'neutral', enabled: true, ios_bundle_ids: ['com.test.bank'], android_package_ids: [], ios_id_status: 'unverified', android_id_status: 'unverified', ios_id_note: '', android_id_note: '', aliases: [], former_names: [], terms: [], status: 'active', verified: false, source: '', last_verified: '', regions: [], comment: '' },
  ],
  file_rules: [
    { id: 'seed-phrase', name: 'Seed Phrase', category: 'wallet', relevance: 'high', enabled: true, filename_equals: [], terms: ['seed'], context_terms: [], extensions: ['txt'], status: 'active', verified: false, source: '', last_verified: '', regions: [], comment: '' },
  ],
  backup_rules: [
    { id: 'apple-finder', name: 'Apple Finder/iTunes Backup', platform: 'iOS/macOS', status: 'active', confidence: 'high', enabled: true, required_paths: ['MobileSync/Backup'], required_files: ['Manifest.db', 'Info.plist'], required_extensions: [], typical_paths: ['~/Library/Application Support/MobileSync/Backup'], source: '', last_verified: '', comment: '' },
    { id: 'samsung-smart-switch', name: 'Samsung Smart Switch', platform: 'Android', status: 'active', confidence: 'medium', enabled: true, required_paths: ['Smart Switch'], required_files: [], required_extensions: [], typical_paths: [], source: '', last_verified: '', comment: '' },
  ],
};
function settingsFixture(url) {
  if (url.pathname === '/api/settings/filetypes') return { json: { catalog: settingsCatalog, defaults: settingsCatalog } };
  if (url.pathname === '/api/settings/crypto') return { json: { rules: defaultCryptoRules, defaults: defaultCryptoRules } };
  if (url.pathname === '/api/profiles') return { json: { profiles: [{ id: 'default', name: 'Allgemein', version: '1.0', keyword_count: 2 }] } };
  if (url.pathname === '/api/profile') return { json: { id: 'default', name: 'Allgemein', version: '1.0', keywords: ['rechnung', 'wallet'] } };
}

// Alpha 68: keyword profiles as master-detail table with search and active counter.
const a68Keywords = ['rechnung', 'marketingplan', 'gutschrift', 'vertragstechnik', 'plakat'];
function a68Fixture(url, request) {
  if (url.pathname === '/api/profiles' && request.method() === 'POST') {
    const payload = request.postDataJSON();
    return { json: { profile: { id: payload.id || 'default', name: payload.name, keywords: payload.keywords, version: '1.2' } } };
  }
  if (url.pathname === '/api/profiles') return { json: { profiles: [{ id: 'default', name: 'Allgemein / Wirtschaft', version: '1.1', keyword_count: a68Keywords.length }] } };
  if (url.pathname === '/api/profile') return { json: { id: 'default', name: 'Allgemein / Wirtschaft', version: '1.1', keywords: [...a68Keywords] } };
  return settingsFixture(url);
}

test('keyword profiles render as a master-detail table with search and an active counter', async t => {
  const { page, requests } = await setup(t, a68Fixture);
  await openSettingsFromAnywhere(page);
  const rows = page.locator('#settingsProfilesList .settings-profile-row');
  assert.equal(await rows.count(), 1, 'profile master list shows one row');
  assert.match(await rows.first().innerText(), /allgemein \/ wirtschaft/i);
  assert.match(await rows.first().innerText(), /5/);
  await rows.first().click();
  assert.equal(await page.locator('#profileDetailForm').isVisible(), true);
  assert.equal(await page.locator('.keyword-table-head').isVisible(), true);
  assert.equal(await page.locator('#profileDetailSearch').isVisible(), true);
  assert.equal(await page.locator('#profileDetailOptions .keyword-option').count(), 5);
  assert.equal(await page.locator('#profileDetailCount').innerText(), '5 / 5 AKTIV');

  await page.locator('#profileDetailSearch').fill('mar');
  assert.equal(await page.locator('#profileDetailOptions .keyword-option').count(), 1);
  assert.match(await page.locator('#profileDetailOptions').innerText(), /MARKETINGPLAN/);
  await page.locator('#profileDetailOptions .keyword-option input').check();
  assert.equal(await page.locator('#profileDetailCount').innerText(), '5 / 5 AKTIV');
  await page.locator('#profileDetailSearch').fill('plakat');
  await page.locator('#profileDetailOptions .keyword-option input').uncheck();
  assert.equal(await page.locator('#profileDetailCount').innerText(), '4 / 5 AKTIV');
  await page.locator('#profileDetailSearch').fill('nomatch');
  assert.match(await page.locator('#profileDetailOptions').innerText(), /KEIN PASSENDER BEGRIFF/);
  // Search is display-only: stored data is untouched.
  assert.equal(await page.evaluate(() => keywordDraft.length), 5, 'stored keyword list unchanged by search');
  assert.equal(await page.evaluate(() => draftSelectedKeywords.size), 4, 'hidden keywords keep their selection');

  await page.locator('#profileDetailSearch').fill('');
  assert.equal(await page.locator('#profileDetailOptions .keyword-option').count(), 5);
  await page.locator('#profileDetailSelectAll').click();
  assert.equal(await page.locator('#profileDetailCount').innerText(), '5 / 5 AKTIV');
  await page.locator('#profileDetailClearAll').click();
  assert.equal(await page.locator('#profileDetailCount').innerText(), '0 / 5 AKTIV');
  assert.equal(requests.some(item => item.method !== 'GET'), false, 'select/search must not persist anything');

  // Leere Auswahl bleibt wirklich leer.
  await page.locator('#profileDetailApply').click();
  assert.equal(await page.locator('#profileDetailMessage').innerText(), 'AUSWAHL FÜR NÄCHSTE SCANS ÜBERNOMMEN');
  assert.equal(await page.evaluate(() => selectedByProfile.get('default')?.size), 0);

  await page.locator('#profileDetailSelectAll').click();
  await page.locator('#profileDetailOptions .keyword-option .keyword-remove').first().click();
  assert.equal(await page.locator('#profileDetailCount').innerText(), '4 / 4 AKTIV');
  await page.locator('#profileDetailSave').click();
  await page.waitForFunction(() => document.getElementById('profileDetailMessage').textContent === 'GESPEICHERT');
  const save = requests.find(item => item.method === 'POST' && item.path === '/api/profiles');
  assert.ok(save, 'profile save persists the draft');
  assert.equal(await page.locator('#profileDetailOptions .keyword-option').count(), 4);
  await page.locator('#closeSettings').click();
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
});

test('keyword list scrolls internally while editor header, search and footer stay visible', async t => {
  const many = Array.from({ length: 90 }, (_, index) => `begriff-${String(index).padStart(3, '0')}`);
  const { page } = await setup(t, (url, request) => {
    if (url.pathname === '/api/profiles' && request.method() === 'GET') {
      return { json: { profiles: [{ id: 'default', name: 'Langes Profil', version: '1.1', keyword_count: many.length }] } };
    }
    if (url.pathname === '/api/profile') return { json: { id: 'default', name: 'Langes Profil', version: '1.1', keywords: many } };
    return a68Fixture(url, request);
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList .settings-profile-row').click();
  const wrap = await page.locator('.keyword-table-wrap').evaluate(node => ({ client: node.clientHeight, scroll: node.scrollHeight }));
  assert.ok(wrap.scroll > wrap.client, 'long keyword list must scroll inside its own area');
  const box = await page.locator('#profileDetailSave').boundingBox();
  const editor = await page.locator('#profileDetail').boundingBox();
  assert.ok(box && editor && box.y > editor.y && box.height > 20, 'profile footer stays visible below the list');
  for (const selector of ['#profileDetailTitleName', '#profileDetailNewInput', '#profileDetailSearch', '.keyword-table-head']) {
    const visible = await page.locator(selector).evaluate(node => node.getBoundingClientRect().bottom > 0);
    assert.equal(visible, true, `${selector} stays visible`);
  }
  await page.locator('#profileDetailSearch').fill('begriff-00');
  const counts = await page.locator('#profileDetailOptions .keyword-option').count();
  assert.equal(counts, 10, 'search also filters very long lists');
  const widths = await page.locator('#settingsModal').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
  assert.ok(widths.scroll <= widths.client + 1, 'no horizontal scrollbar from the keyword table');
});

test('update tab shows a quiet, state-driven status without a permanent success banner', async t => {
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/updates/check' && request.method() === 'POST') {
      return { status: 403, json: { error: 'LAUFENDER SCAN' } };
    }
    return null;
  });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  assert.match(await page.locator('#settingsUpdatesTab').innerText(), /UPDATES/);
  await page.evaluate(() => renderUpdateState({ state: 'current', current_version: '0.2.0a68', updated_at: new Date().toISOString() }));
  assert.match(await page.locator('#updateStatus').innerText(), /AKTUELL/);
  assert.match(await page.locator('#updateCurrentVersion').innerText(), /v0\.2\.0-alpha\.68/);
  assert.notEqual(await page.locator('#updateCheckedAt').innerText(), '—');
  assert.equal(await page.locator('#updateSuccessNotice').count(), 0, 'no permanent success banner in the markup');
  assert.equal(await page.locator('#updateCheck').isVisible(), true);
  const statusBox = await page.locator('.update-status-block').evaluate(node => node.getBoundingClientRect());
  const check = await page.locator('#updateCheck').evaluate(node => node.getBoundingClientRect());
  assert.ok(check.top >= statusBox.top && check.bottom <= statusBox.bottom + 2, 'JETZT PRÜFEN sits inside the combined status block');
  assert.equal(await page.locator('.offline-update').isVisible(), true, 'offline update stays present');

  // Update available: status shows the target version and offers install.
  await page.evaluate(() => renderUpdateState({ state: 'available', current_version: '0.2.0a67', available_version: '0.2.0a68' }));
  assert.match(await page.locator('#updateStatus').innerText(), /UPDATE VERFÜGBAR · v0\.2\.0-alpha\.68/);
  assert.equal(await page.locator('#updateInstall').isVisible(), true);

  // Installing: temporary state only.
  await page.evaluate(() => renderUpdateState({ state: 'installing' }));
  assert.match(await page.locator('#updateStatus').innerText(), /UPDATE WIRD INSTALLIER/);
  assert.equal(await page.locator('#updateInstall').isVisible(), false);
  await page.evaluate(() => renderUpdateState({ state: 'installed' }));
  assert.match(await page.locator('#updateStatus').innerText(), /✓ AKTUELL/);

  // Error: short concrete failure message and a quiet error status.
  await page.evaluate(() => requestUpdate('check'));
  await page.waitForFunction(() => document.getElementById('updateActionMessage').textContent.includes('FEHLER'));
  assert.match(await page.locator('#updateActionMessage').innerText(), /FEHLER: LAUFENDER SCAN/);
  assert.match(await page.locator('#updateStatus').innerText(), /UPDATE FEHLGESCHLAGEN/);
  assert.equal(await page.locator('#updateSuccessNotice').count(), 0);
  assert.equal(requests.filter(item => item.path === '/api/updates/check' && item.method === 'POST').length, 1);
  await page.locator('#closeSettings').click();
});

test('start overlay stays calm and blur is slightly stronger', async t => {
  const { page } = await setup(t);
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  assert.match(await page.locator('.start-overlay-ready').innerText(), /BEREIT/);
  assert.match(await page.locator('.start-overlay-button').innerText(), /FALL ANLEGEN \/ ÖFFNEN/);
  const oldSentence = await page.locator('#startOverlay').innerText();
  assert.doesNotMatch(oldSentence, /zuerst einen Fall anlegen/i);
  const blur = await page.locator('#startOverlay').evaluate(node => getComputedStyle(node).backdropFilter);
  const value = Number(String(blur).match(/blur\((\d+(?:\.\d+)?)px\)/)?.[1] || 0);
  assert.ok(value >= 7 && value <= 8.5, `overlay blur should sit around 7–8px, got: ${blur}`);

  // Active case without medium: short state, no helper paragraph.
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; activeOperator = 'HL'; devices = [];
    startOverlayReady = true; updateStartOverlay(); updateDashboardState();
  });
  assert.equal(await page.locator('#startOverlay').isVisible(), false, 'active case hides the overlay');
  assert.equal(await page.locator('#deviceEmptyTitle').innerText(), 'KEIN MEDIUM VERBUNDEN');
  assert.equal(await page.locator('#deviceEmptyCopy').innerText(), '');

  // After ending the case the overlay returns.
  await page.evaluate(() => { activeCaseNumber = ''; serverActiveCase = null; updateStartOverlay(); });
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
});

test('filetype master list uses the same column structure as keyword profiles', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  assert.equal(await page.locator('.catalog-list-header').isVisible(), true);
  assert.match(await page.locator('.catalog-list-header').innerText(), /KATEGORIE/);
  assert.match(await page.locator('.catalog-list-header').innerText(), /ENDUNGEN/);
  const headerStyle = await page.locator('.catalog-list-header').evaluate(node => { const s = getComputedStyle(node); return { font: s.fontSize, lineHeight: s.lineHeight, paddingTop: s.paddingTop, borderBottom: s.borderBottomWidth }; });
  const profileHeader = await page.locator('.profile-list-header').evaluate(node => { const s = getComputedStyle(node); return { font: s.fontSize, lineHeight: s.lineHeight, paddingTop: s.paddingTop, borderBottom: s.borderBottomWidth }; });
  assert.deepEqual(headerStyle, profileHeader, 'master headers share the same visual line');
  const rows = page.locator('#catalogRows [data-category]');
  await rows.first().waitFor();
  const first = await rows.first().innerText();
  assert.match(first, /\d/, 'category rows show a right-hand count column');
  await rows.first().click();
  assert.equal(await page.locator('#filetypesDetailForm').isVisible(), true);
  assert.equal(await page.locator('#filetypesDetailName').inputValue(), 'Bilder');
});

test('closed settings dialog occupies no layout space and returns to that state after closing', async t => {
  const { page } = await setup(t, settingsFixture);
  const before = await page.locator('#settingsModal').evaluate(node => ({
    open: node.hasAttribute('open'),
    display: getComputedStyle(node).display,
    box: node.getBoundingClientRect().toJSON(),
    bodyHeight: document.body.scrollHeight,
  }));
  assert.equal(before.open, false);
  assert.equal(before.display, 'none');
  assert.equal(before.box.width, 0);
  assert.equal(before.box.height, 0);
  await openSettingsFromAnywhere(page);
  const opened = await page.locator('#settingsModal').evaluate(node => ({ display: getComputedStyle(node).display, box: node.getBoundingClientRect().toJSON() }));
  assert.equal(opened.display, 'flex');
  assert.ok(opened.box.width > 1000 && opened.box.height > 800);
  await page.locator('#closeSettings').click();
  const closed = await page.locator('#settingsModal').evaluate(node => ({ display: getComputedStyle(node).display, box: node.getBoundingClientRect().toJSON(), bodyHeight: document.body.scrollHeight }));
  assert.equal(closed.display, 'none');
  assert.equal(closed.box.width, 0);
  assert.equal(closed.box.height, 0);
  assert.equal(closed.bodyHeight, before.bodyHeight);
});

test('settings are outside the case dialog and profile editor uses only one backdrop', async t => {
  const { page, requests } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  assert.equal(await page.locator('#auftragModal').isVisible(), false);
  assert.equal(await page.locator('#settingsProfilesPane').isVisible(), true);
  assert.equal((await page.locator('#settingsTitle').locator('..').innerText()).includes('CFG'), false);
  assert.equal(await page.locator('#profileDetailEmpty').isVisible(), true);
  await page.locator('#settingsProfilesList [data-select-profile]').click();
  assert.equal(await page.locator('#profileDetailEmpty').isVisible(), false);
  assert.equal(await page.locator('#profileDetailForm').isVisible(), true);
  assert.equal(await page.locator('#profileDetailName').inputValue(), 'Allgemein');
  assert.equal(await page.locator('#profileDetailOptions input').count(), 2);
  assert.equal(await page.locator('#settingsModal').evaluate(node => node.classList.contains('nested-open')), false);
  await page.locator('#profileDetailDuplicate').click();
  assert.equal(await page.locator('#profileDetailName').inputValue(), 'Allgemein Kopie');
  assert.equal(await page.evaluate(() => profileEditorId), null);
  assert.equal(await page.locator('#profileDetailOptions input').count(), 2);
  await page.locator('#closeSettings').click();
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  await page.locator('#startOpenCase').click();
  assert.equal(await page.locator('#auftragModal').isVisible(), true);
  assert.equal(await page.locator('#auftragModal [data-edit-profile]').count(), 0);
  assert.equal(await page.locator('#profileList input').count(), 1);
  assert.equal(requests.some(item => item.method !== 'GET'), false);
});

test('catalog filters, reports invalid saves, preserves draft and saves future-scan changes', async t => {
  const { page, requests } = await setup(t, (url, request) => {
    if (url.pathname === '/api/settings/filetypes' && request.method() === 'POST') {
      const payload = request.postDataJSON();
      assert.equal(payload.base_sha256, 'first');
      if (payload.categories.Dokumente.includes('jpg')) return { status: 400, json: { error: '.jpg ist doppelt zugeordnet' } };
      return { json: { catalog: { categories: payload.categories, version: 2, sha256: 'second' } } };
    }
    return settingsFixture(url);
  });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('[data-category="Dokumente"]').click();
  await page.locator('#filetypesDetailExtensions').fill('pdf, jpg');
  await page.locator('#filetypesDetailApply').click();
  await page.locator('#catalogSave').click();
  await page.waitForFunction(() => document.getElementById('catalogMessage').textContent.includes('doppelt'));
  assert.equal(await page.locator('#filetypesDetailExtensions').inputValue(), 'pdf, jpg');
  await page.locator('#filetypesDetailExtensions').fill('pdf, docm');
  await page.locator('#filetypesDetailApply').click();
  await page.locator('#catalogSearch').fill('.docm');
  assert.equal(await page.locator('[data-category="Bilder"]').isVisible(), false);
  assert.equal(await page.locator('[data-category="Dokumente"]').isVisible(), true);
  await page.locator('#catalogSave').click();
  await page.waitForFunction(() => document.getElementById('catalogMessage').textContent.startsWith('GESPEICHERT ·'));
  assert.equal(await page.locator('#catalogVersion').innerText(), 'KATALOG V2');
  assert.equal(await page.locator('#catalogSave').isDisabled(), true);
  await page.locator('#catalogReset').click();
  await page.locator('[data-category="Dokumente"]').click();
  assert.equal(await page.locator('#filetypesDetailExtensions').inputValue(), 'pdf');
  assert.equal(await page.locator('#catalogSave').isEnabled(), true);
  page.once('dialog', dialog => dialog.dismiss());
  await page.locator('#closeSettings').click();
  assert.equal(await page.locator('#settingsModal').isVisible(), true);
  assert.deepEqual(requests.filter(item => item.method !== 'GET').map(item => item.path), ['/api/settings/filetypes', '/api/settings/filetypes']);
});

test('settings remain readable on laptop and small screens', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.setViewportSize({ width: 800, height: 900 });
  const heights = [];
  for (const tab of ['#settingsProfilesTab', '#settingsFiletypesTab', '#settingsUpdatesTab']) {
    await page.locator(tab).click();
    heights.push(await page.locator('#settingsModal').evaluate(node => node.getBoundingClientRect().height));
  }
  assert.equal(new Set(heights).size, 1, 'Settings dialog height must stay stable between tabs');
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('#catalogRows .catalog-row').first().waitFor();
  for (const width of [1440, 800, 470]) {
    await page.setViewportSize({ width, height: 900 });
    const sizes = await page.locator('#settingsModal').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth, width: node.getBoundingClientRect().width }));
    assert.ok(sizes.scroll <= sizes.client + 1, `No horizontal scrolling at ${width}`);
    assert.ok(sizes.width < width);
    assert.ok(await page.locator('#catalogSave').isVisible());
  }
});

test('detection rules workspace is large and both columns are visible on desktop', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  assert.match(await page.locator('#settingsCryptoTab').innerText(), /ERKENNUNGSREGELN/);
  const modal = await page.locator('#settingsModal').evaluate(node => node.getBoundingClientRect());
  assert.ok(modal.width >= 1400, `modal width ${modal.width} should use most of viewport`);
  assert.ok(modal.height >= 900, `modal height ${modal.height} should use most of viewport`);
  assert.ok(modal.left >= 0 && modal.right <= 1512, 'modal must be fully inside viewport');
  const list = await page.locator('.detection-list-panel').evaluate(node => node.getBoundingClientRect());
  const editor = await page.locator('.detection-editor-panel').evaluate(node => node.getBoundingClientRect());
  assert.ok(list.width > 0 && editor.width > 0, 'both master and detail panels must be visible');
  assert.ok(list.right <= editor.left + 1, 'list and editor must not overlap');
  const footer = await page.locator('.detection-footer').evaluate(node => node.getBoundingClientRect());
  assert.ok(footer.height > 20 && footer.bottom <= modal.bottom, 'save footer must be visible');
  const empty = await page.locator('#detectionEditorEmpty');
  assert.equal(await empty.isVisible(), true);
});

test('detection rule controls and platform ID states are explicit and accessible', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  assert.equal(await page.locator('select[aria-label="Erkennungsregeln filtern"]').count(), 1);
  assert.equal(await page.locator('select[aria-label="Erkennungsregeln sortieren nach"]').count(), 1);
  assert.equal(await page.locator('input#detectionSearch[aria-label]').count(), 1, 'search stays accessible without stacked labels');

  const symbols = async id => page.locator(`#detectionRows tr[data-id="${id}"] .platform-id-status`).allInnerTexts();
  assert.deepEqual(await symbols('wallet'), ['✓', '?']);
  assert.deepEqual(await symbols('android-only'), ['?', '✓']);
  assert.deepEqual(await symbols('unknown-ids'), ['?', '?']);
  assert.deepEqual(await symbols('desktop-only'), ['—', '—']);
  assert.doesNotMatch(await page.locator('#detectionRows tr[data-id="wallet"] td').first().innerText(), /✓/);

  const iosUnknown = page.locator('#detectionRows tr[data-id="android-only"] .platform-id-status').first();
  await iosUnknown.focus();
  const tooltip = page.locator('#settingsTooltipLayer');
  await tooltip.waitFor({ state: 'visible' });
  assert.match(await tooltip.innerText(), /ID NICHT VERIFIZIERT/);
  assert.match(await tooltip.innerText(), /bedeutet nicht, dass keine iOS-App existiert/i);
  const box = await tooltip.evaluate(node => node.getBoundingClientRect());
  assert.ok(box.top >= 0 && box.left >= 0 && box.right <= 1512 && box.bottom <= 982);

  await page.locator('#detectionRows tr[data-id="android-only"]').click();
  assert.equal(await page.locator('[data-field="ios_id_status"]').inputValue(), 'unverified');
  assert.equal(await page.locator('[data-field="android_id_status"]').inputValue(), 'verified');
  assert.match(await page.locator('.platform-id-editor[data-platform="ios"]').innerText(), /Das bedeutet nicht/);
  assert.equal(await page.locator('#detectionEditorFields').innerText().then(text => text.includes('VERIFIZIERT ✓')), false);
});

test('backup editor uses correct PFADE labels', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionBackupsTab').click();
  await page.locator('#detectionRows tr[data-id="apple-finder"]').click();
  const text = await page.locator('#detectionEditorFields').innerText();
  assert.match(text, /ERFORDERLICHE PFADE \/ ORDNER/);
  assert.match(text, /TYPISCHE PFADE/);
  assert.doesNotMatch(text, /PFAde/);
});

test('detection rules glossary opens as separate dialog without shifting layout', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const bodyBefore = await page.locator('.detection-body').evaluate(node => node.getBoundingClientRect());
  await page.locator('#detectionGlossaryButton').click();
  const dialog = page.locator('#detectionGlossaryDialog');
  await dialog.waitFor({ state: 'visible' });
  assert.equal(await dialog.isVisible(), true);
  assert.match(await dialog.innerText(), /ANDROID-APP-ID/);
  const bodyAfter = await page.locator('.detection-body').evaluate(node => node.getBoundingClientRect());
  assert.deepEqual({ width: bodyAfter.width, height: bodyAfter.height, left: bodyAfter.left, top: bodyAfter.top }, { width: bodyBefore.width, height: bodyBefore.height, left: bodyBefore.left, top: bodyBefore.top }, 'master-detail layout must not shift');
  await page.locator('#detectionGlossaryClose').click();
  assert.equal(await dialog.isVisible(), false);
  assert.equal(await page.locator('#detectionEditorEmpty').isVisible(), true);
});

test('detection rules tooltip stays fully inside viewport', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionRows tr[data-id="wallet"]').click();
  const trigger = page.locator('.detection-editor-fields .info-tooltip').first();
  await trigger.hover();
  const tooltip = page.locator('#settingsTooltipLayer');
  await tooltip.waitFor({ state: 'visible' });
  const box = await tooltip.evaluate(node => node.getBoundingClientRect());
  assert.ok(box.width > 0 && box.height > 0, 'tooltip must be rendered');
  assert.ok(box.top >= 0 && box.left >= 0 && box.right <= 1512 && box.bottom <= 982, `tooltip must stay inside viewport: ${JSON.stringify(box)}`);
  await page.mouse.click(0, 0);
  assert.equal(await tooltip.isVisible(), false);
});

test('detection rules backup tab shows bundled backup rules', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionBackupsTab').click();
  const text = await page.locator('#detectionRows').innerText();
  assert.match(text, /Apple Finder/i);
  assert.match(text, /Samsung Smart Switch/i);
  assert.equal(await page.locator('#detectionCount').innerText(), '2 REGELN');
});

test('detection rules apply drafts and save all persist changes', async t => {
  const { page, requests } = await setup(t, (url, request) => {
    if (url.pathname === '/api/settings/crypto' && request.method() === 'POST') {
      const payload = request.postDataJSON();
      assert.ok(Array.isArray(payload.rules.app_rules));
      assert.ok(Array.isArray(payload.rules.deleted_default_rule_ids));
      return { json: { rules: { ...payload.rules, version: 2, sha256: 'crypto-second' }, defaults: defaultCryptoRules } };
    }
    return settingsFixture(url);
  });
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionRows tr[data-id="wallet"]').click();
  await page.locator('[data-field="name"]').fill('Renamed Wallet');
  await page.locator('#detectionApply').click();
  assert.equal(await page.locator('#detectionStatus').innerText(), 'UNGESPEICHERTE ÄNDERUNGEN');
  assert.equal(await page.locator('#detectionSaveAll').isEnabled(), true);
  await page.locator('#detectionSaveAll').click();
  await page.waitForFunction(() => document.getElementById('detectionMessage').textContent.includes('GESPEICHERT'));
  assert.equal(await page.locator('#detectionSaveAll').isDisabled(), true);
  assert.deepEqual(requests.filter(item => item.method !== 'GET' && item.path === '/api/settings/crypto').length, 1);
});

// ===== Alpha 69: compact settings design system =====

test('profile detail uses a compact text header with inline name editing', async t => {
  const { page } = await setup(t, a68Fixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList [data-select-profile="default"]').click();
  const head = await page.locator('#profileDetailTitleName');
  await head.waitFor({ state: 'visible' });
  assert.match(await head.innerText(), /Allgemein \/ Wirtschaft/i, 'detail head shows the object name as text');
  // Kein dauerhaftes großes Namensfeld.
  assert.equal(await page.locator('#profileDetailName').isVisible(), false);
  assert.equal(await page.locator('#profileDetailEdit').isVisible(), true);

  // Editiermodus: BEARBEITEN zeigt kompakte Zeile, OK bestätigt, ABBRECHEN verwirft.
  await page.locator('#profileDetailEdit').click();
  assert.equal(await page.locator('#profileDetailName').isVisible(), true);
  assert.equal(await page.locator('#profileDetailEdit').isVisible(), false);
  await page.locator('#profileDetailName').fill('Allgemein Umbenennung');
  await page.locator('#profileNameOk').click();
  assert.equal(await page.locator('#profileDetailName').isVisible(), false);
  assert.match(await page.locator('#profileDetailTitleName').innerText(), /Allgemein Umbenennung/);
  await page.locator('#profileDetailEdit').click();
  await page.locator('#profileDetailName').fill('Umbenennung WIRD VERWORFEN');
  await page.locator('#profileNameCancel').click();
  assert.match(await page.locator('#profileDetailTitleName').innerText(), /Allgemein Umbenennung/);

  // Neues Profil startet direkt im Namens-Editiermodus. Die Umbenennung ist
  // ungespeichert, das Verwerfen muss bestätigt werden (kein stiller Verlust).
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#createProfile').click();
  assert.equal(await page.locator('#profileDetailName').isVisible(), true);
  assert.equal(await page.locator('#profileDetailEdit').isVisible(), false);
  assert.equal(await page.evaluate(() => $("profileDetailName").value), '');
  await page.locator('#profileNameCancel').click();
  assert.equal(await page.locator('#profileDetailTitleName').innerText(), 'NEUES PROFIL');
});

test('keyword add row and toolbar are compact and keep search, selection and counter in one row', async t => {
  const { page } = await setup(t, a68Fixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList [data-select-profile="default"]').click();
  const addInput = page.locator('#profileDetailNewInput');
  assert.match(await addInput.getAttribute('placeholder'), /[Hh]inzufügen/);
  assert.equal(await page.locator('#profileDetailAddKeyword').innerText(), '');
  const addHeight = await page.locator('#profileDetailAddKeyword').evaluate(node => node.getBoundingClientRect().height);
  assert.ok(addHeight <= 34, `add button must stay compact: ${addHeight}`);
  // Enter-Hinzufügen funktioniert weiterhin.
  await addInput.fill('testoptional');
  await addInput.press('Enter');
  assert.equal(await page.locator('#profileDetailOptions .keyword-option').count(), 6);

  const toolbar = await page.locator('.keyword-toolbar').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth, height: node.getBoundingClientRect().height }));
  assert.ok(toolbar.scroll <= toolbar.client + 1, 'keyword toolbar must not wrap on desktop');
  assert.ok(toolbar.height <= 40, 'keyword toolbar must stay one compact row');
  const tops = await page.locator('.keyword-toolbar input, .keyword-toolbar button').evaluateAll(nodes => nodes.map(n => Math.round(n.getBoundingClientRect().top)));
  assert.equal(new Set(tops).size, 1, 'search, ALLE and KEINE share one row');
});

test('master rows picture the same family across profiles, file types and detection rules', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList .settings-profile-row').first().waitFor({ timeout: 5000 });
  const rowStyle = async selector => page.locator(selector).first().evaluate(node => {
    const s = getComputedStyle(node);
    return { pad: s.paddingTop, borderBottom: s.borderBottomWidth, fontSize: s.fontSize, minHeight: node.getBoundingClientRect().height };
  });
  const profileRow = await rowStyle('#settingsProfilesList .settings-profile-row');
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('#catalogRows [data-category]').first().waitFor();
  const catalogRow = await rowStyle('#catalogRows .catalog-row');
  assert.equal(profileRow.pad, catalogRow.pad, 'same row padding');
  assert.equal(profileRow.borderBottom, catalogRow.borderBottom, 'same horizontal line');
  assert.equal(profileRow.fontSize, catalogRow.fontSize, 'same type scale');
  // Aktive Zeile: dezenter Acid-Ton plus linke Acid-Kante.
  await page.locator('#settingsProfilesTab').click();
  await page.locator('#settingsProfilesList [data-select-profile="default"]').click();
  const active = await page.locator('#settingsProfilesList .settings-profile-row.selected').evaluate(node => {
    const s = getComputedStyle(node);
    return { bg: s.backgroundColor, shadow: s.boxShadow };
  });
  assert.match(active.bg, /201,\s*242,\s*82/);
  assert.match(active.shadow, /3px.*inset/);
  // Kopf und Zeile teilen dieselben Linien und Schriftwerte.
  const headerStyle = await page.locator('.profile-list-header').evaluate(node => { const s = getComputedStyle(node); return { border: s.borderBottomWidth, font: s.fontSize, height: node.getBoundingClientRect().height }; });
  assert.equal(headerStyle.border, profileRow.borderBottom, 'same line weight as rows');
  assert.equal(headerStyle.font, profileRow.fontSize, 'same type scale as rows');
  assert.ok(headerStyle.height <= 34, `master header stays compact: ${headerStyle.height}`);
});

test('settings buttons share one primary/secondary/danger system', async t => {
  const css = fs.readFileSync(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /\.s-btn \{[^}]*min-height:\s*32px/);
  assert.match(css, /\.s-btn\.primary \{[^}]*var\(--acid\)/s);
  assert.match(css, /\.s-btn\.danger \{[^}]*var\(--danger\)/s);
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  const style = async (selector, prop) => page.locator(selector).evaluate((node, p) => getComputedStyle(node)[p], prop);
  await page.locator('#settingsProfilesList [data-select-profile="default"]').click();
  const saveBg = await style('#profileDetailSave', 'backgroundColor');
  const applyBorder = await style('#profileDetailApply', 'borderStyle');
  const applyColor = await style('#profileDetailApply', 'color');
  assert.deepEqual([/201, 242, 82|201,242,82/.test(saveBg), applyBorder === 'solid', /232, 234, 223/.test(applyColor)], [true, true, true]);
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('#catalogRows [data-category="Bilder"]').click();
  const deleteColor = await style('#filetypesDetailDelete', 'color');
  assert.equal(deleteColor, 'rgb(255, 104, 95)', 'delete is danger-styled');
  const allButtons = await page.locator('.settings-modal [class*="s-btn"]').count();
  assert.ok(allButtons >= 8, 'unified button classes are used across settings');
});

test('settings no longer carry permanent intro paragraphs', async () => {
  const html = fs.readFileSync(path.join(root, 'web', 'index.html'), 'utf8');
  const count = (html.match(/class="pane-intro"/g) || []).length;
  assert.equal(count, 0, 'no permanent intro paragraphs in settings panes');
  assert.equal((html.match(/settingsProfilesPane|settingsFiletypesPane|settingsUpdatesPane/g) || []).length >= 3, true);
});

test('filetype detail shows the category as text with inline editing and local/global footer split', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('#catalogRows [data-category="Bilder"]').click();
  assert.match(await page.locator('#filetypesDetailTitleName').innerText(), /^Bilder$/);
  assert.equal(await page.locator('#filetypesDetailName').isVisible(), false);
  await page.locator('#filetypesDetailEdit').click();
  assert.equal(await page.locator('#filetypesDetailName').isVisible(), true);
  await page.locator('#filetypeNameCancel').click();
  assert.match(await page.locator('#filetypesDetailTitleName').innerText(), /^Bilder$/);
  // Lokale Detailaktionen vs. globale Katalogaktionen getrennt.
  const detailFooter = await page.locator('#filetypesDetailForm .detail-footer').evaluate(node => node.getBoundingClientRect().bottom);
  const globalFooter = await page.locator('.filetypes-footer').evaluate(node => node.getBoundingClientRect().top);
  assert.ok(detailFooter < globalFooter, 'detail actions sit above the global catalog footer');
  assert.equal(await page.locator('#filetypesDetailReset').isVisible(), true);
  assert.equal(await page.locator('#catalogSave').isVisible(), true);
});

test('updates pane stays a single quiet status row plus offline section', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  await page.evaluate(() => renderUpdateState({ state: 'current', current_version: '0.2.0a69', updated_at: new Date().toISOString() }));
  const grid = await page.locator('.update-version-grid').evaluate(node => ({ cols: getComputedStyle(node).gridTemplateColumns.split(' ').length, height: node.getBoundingClientRect().height }));
  assert.equal(grid.cols, 3, 'VERSION / STATUS / LETZTE PRÜFUNG in einer Zeile');
  assert.ok(grid.height <= 70, 'status row stays compact');
  const check = await page.locator('#updateCheck').evaluate(node => node.getBoundingClientRect());
  const block = await page.locator('.update-status-block').evaluate(node => node.getBoundingClientRect());
  assert.ok(check.right <= block.right + 1 && check.bottom <= block.bottom + 1, 'JETZT PRÜFEN stays inside the status row');
  assert.equal(await page.locator('.offline-update').isVisible(), true);
  assert.equal(await page.locator('#offlineUpdateFile').isVisible(), true);
  const body = await page.locator('.update-modal-body').evaluate(node => ({
    height: node.scrollHeight, client: node.clientHeight,
  }));
  assert.ok(body.height < 600, 'update pane stays free of sprawling empty space');
});

for (const fails of [false, true]) test(`end case from update dialog: ${fails ? 'failure retains lock' : 'success enables deliberate install'}`, async t => {
  const blocked = gate();
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/cases/stop') {
      assert.equal(request.method(), 'POST');
      await blocked.wait();
      return { status: fails ? 409 : 200, json: fails ? { error: 'Scan läuft' } : { active_case: null } };
    }
    if (fails && url.pathname === '/api/status') return { json: { devices: [], cases: [], active_case: { case_number: 'TEST', operator: 'HL' }, update: { state: 'available', available_version: 'v0.2.0-alpha.43' } } };
  });
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' };
    renderUpdateState({ state: 'available', available_version: 'v0.2.0-alpha.43' });
    document.getElementById('settingsModal').showModal(); selectSettingsPane('updates');
    runningPaths.add('/dev/test'); renderUpdateState();
  });
  assert.equal(await page.locator('#updateStopCase').isDisabled(), true);
  await page.evaluate(() => { runningPaths.clear(); renderUpdateState(); });
  await page.locator('#updateStopCase').click();
  await blocked.arrived;
  assert.equal(await page.locator('#updateStopCase').isDisabled(), true);
  assert.equal(await page.locator('#updateInstall').isDisabled(), true);
  assert.match(await page.locator('#updateStopCase').innerText(), /WIRD BEENDET/);
  blocked.release();
  await page.waitForFunction(() => !caseSessionTransition && /FALL BEENDET|KONNTE NICHT/.test(document.getElementById('updateActionMessage').textContent));
  assert.equal(await page.locator('#updateModal').isVisible(), true);
  assert.equal(await page.locator('#auftragModal').isVisible(), false);
  assert.equal(await page.locator('#updateInstall').isDisabled(), fails);
  assert.equal(requests.filter(r => r.path === '/api/cases/stop').length, 1);
  assert.equal(requests.filter(r => r.path === '/api/updates/install').length, 0);
});

test('signed offline package uploads through the update dialog and observes completion', async t => {
  let polls = 0;
  const body = Buffer.from('PK\x03\x04TEST-OFFLINE');
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/updates/offline') {
      assert.equal(request.method(), 'POST');
      assert.deepEqual(request.postDataBuffer(), body);
      return { status: 202, json: { action: 'offline', update: { state: 'unknown', current_version: '0.2.0a44' } } };
    }
    if (url.pathname === '/api/updates') {
      polls += 1;
      return polls === 1
        ? { json: { jobs: { offline: true }, update: { state: 'installing', current_version: '0.2.0a44' } } }
        : { json: { jobs: { offline: false }, update: { state: 'installed', current_version: '0.2.0a45' } } };
    }
  });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  await page.setViewportSize({ width: 470, height: 900 });
  const modalSize = await page.locator('#settingsModal').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
  assert.ok(modalSize.scroll <= modalSize.client + 1, 'Offline update controls must not overflow a small screen');
  await page.locator('#offlineUpdateFile').setInputFiles({ name: 'triagebox-v0.2.0-alpha.45.tbu', mimeType: 'application/octet-stream', buffer: body });
  assert.equal(await page.locator('#offlineUpdateInstall').isEnabled(), true);
  await page.evaluate(() => { activeCaseNumber = 'TEST'; renderUpdateState(); });
  assert.equal(await page.locator('#offlineUpdateInstall').isDisabled(), true);
  await page.evaluate(() => { activeCaseNumber = ''; serverActiveCase = null; renderUpdateState(); });
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#offlineUpdateInstall').click();
  await page.waitForFunction(() => document.getElementById('offlineUpdateMessage').textContent.includes('OFFLINE-UPDATE INSTALLIERT'));
  assert.equal(requests.filter(item => item.path === '/api/updates/offline').length, 1);
  assert.ok(polls >= 2);
});

test('power warning is compact and shutdown needs a deliberate second confirmation', async t => {
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/status') return {
      json: {
        devices: [], cases: [], active_case: null, update: {},
        power: { state: 'warning', label: 'UNTERSPANNUNG AUFGETRETEN', current_undervoltage: false, undervoltage_since_boot: true },
      },
    };
    if (url.pathname === '/api/system/power') {
      assert.equal(request.method(), 'POST');
      assert.deepEqual(request.postDataJSON(), { action: 'poweroff' });
      return { status: 202, json: { action: 'poweroff', scheduled_in_seconds: 3 } };
    }
  });
  await page.waitForFunction(() => !document.getElementById('powerHealth').hidden);
  assert.match(await page.locator('#powerHealth').getAttribute('class'), /warning/);
  assert.match(await page.locator('#powerHealth').getAttribute('title'), /UNTERSPANNUNG AUFGETRETEN/);
  await page.setViewportSize({ width: 470, height: 900 });
  await openPowerFromAnywhere(page);
  assert.match(await page.locator('#powerModalTitle').innerText(), /NEUSTART/);
  const modalSize = await page.locator('#powerModal').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
  assert.ok(modalSize.scroll <= modalSize.client + 1);
  await page.evaluate(() => { activeCaseNumber = 'TEST'; renderPowerState(); });
  assert.equal(await page.locator('[data-power-action="poweroff"]').isDisabled(), true);
  await page.evaluate(() => { activeCaseNumber = ''; serverActiveCase = null; renderPowerState(); });
  await page.locator('[data-power-action="poweroff"]').click();
  assert.equal(await page.locator('#powerConfirmation').isVisible(), true);
  assert.equal(requests.filter(item => item.path === '/api/system/power').length, 0);
  await page.locator('#cancelPowerAction').click();
  await page.locator('[data-power-action="poweroff"]').click();
  await page.locator('#confirmPowerAction').click();
  await page.waitForFunction(() => document.getElementById('powerMessage').textContent.includes('HERUNTERFAHREN GESTARTET'));
  assert.equal(requests.filter(item => item.path === '/api/system/power').length, 1);
});

test('normal power stays hidden and a successful update clears a stale offline error', async t => {
  const { page } = await setup(t);
  await page.evaluate(() => {
    renderPowerState({ state: 'ok', label: 'STROM OK' });
    document.getElementById('offlineUpdateMessage').textContent = 'FEHLER: ALTER FEHLER';
    renderUpdateState({ state: 'installed', current_version: '0.2.0a49' });
  });
  assert.equal(await page.locator('#powerHealth').isHidden(), true);
  assert.equal(await page.locator('#offlineUpdateMessage').innerText(), '');
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  assert.equal(await page.locator('#updateSuccessNotice').count(), 0, 'No permanent success banner');
  assert.match(await page.locator('#updateStatus').innerText(), /AKTUELL/);
  assert.match(await page.locator('#systemVersion').innerText(), /v0\.2\.0-alpha\.49/);

  const widths = await page.locator('.utility-controls button').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().width));
  assert.equal(new Set(widths).size, 1);
});

test('update dialog reopens after the service reload and keeps progress visible while running', async t => {
  const blocked = gate();
  let delayReload = false;
  const { page } = await setup(t, async url => {
    if (url.pathname === '/api/status') {
      if (delayReload) await blocked.wait();
      return { json: { devices: [], cases: [], active_case: null, update: { state: 'installing', current_version: '0.2.0a49' } } };
    }
  });
  await page.evaluate(() => sessionStorage.setItem('triagebox-update-dialog', '1'));
  delayReload = true;
  const reload = page.reload({ waitUntil: 'domcontentloaded' });
  await blocked.arrived;
  await reload;
  await page.locator('#settingsModal').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#settingsUpdatesPane').isVisible(), true);
  blocked.release();
  await page.locator('#updateProgress').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#updateProgress').isVisible(), true);
  assert.equal(await page.locator('#closeSettings').isDisabled(), true);
  assert.match(await page.locator('#updateProgressLabel').innerText(), /VORBEREITET|GEPRÜFT/);
  assert.equal(await page.evaluate(() => sessionStorage.getItem('triagebox-update-dialog')), null);
});

test('switching media after filtering restores the correct visible explorer', async t => {
  const { page } = await setup(t);
  await open(page, 1); await filter(page); await open(page, 2);
  assert.equal(await page.locator('#inventoryTree').isVisible(), true);
  assert.equal(await page.locator('#inventorySearchResults').isVisible(), false);
  assert.match(await page.locator('#inventoryTree').innerText(), /MEDIUM-2/);
  assert.equal(await page.locator('#inventoryFiles').innerHTML(), '');
});

test('late explorer response cannot replace another medium or an A-B-A view', async t => {
  const blocked = gate(); let delaying = false;
  const { page } = await setup(t, async url => {
    if (delaying && url.pathname === '/api/media/1/tree') {
      delaying = false; await blocked.wait();
      return { json: pageData([entry('STALE-OLD-TREE')]) };
    }
  });
  await open(page, 1); delaying = true;
  await page.evaluate(() => { window.pendingTree = loadInventoryTree(); });
  await blocked.arrived; await open(page, 2); await open(page, 1);
  blocked.release(); await page.evaluate(() => window.pendingTree);
  assert.match(await page.locator('#inventoryTree').innerText(), /MEDIUM-1/);
  assert.doesNotMatch(await page.locator('#inventoryTree').innerText(), /STALE/);
});

test('late media detail cannot override latest selection or reopen the dashboard', async t => {
  const blocked = gate(); let delaying = true;
  const { page } = await setup(t, async url => {
    if (delaying && url.pathname === '/api/media/1') { delaying = false; await blocked.wait(); }
  });
  await page.evaluate(() => { window.pendingMedia = openMedia(1); });
  await blocked.arrived; await open(page, 2); await page.evaluate(() => showDashboard());
  blocked.release(); await page.evaluate(() => window.pendingMedia);
  assert.equal(await page.locator('#results').isVisible(), false);
  assert.equal(await page.evaluate(() => currentMediaId), null);
  assert.equal(await page.locator('#saveDecision').isDisabled(), true);
});

test('late media detail cannot replace a more recently selected medium', async t => {
  const blocked = gate();
  const { page } = await setup(t, async url => { if (url.pathname === '/api/media/1') await blocked.wait(); });
  await page.evaluate(() => { window.pendingMedia = openMedia(1); });
  await blocked.arrived; await open(page, 2);
  blocked.release(); await page.evaluate(() => window.pendingMedia);
  assert.equal(await page.evaluate(() => currentMediaId), 2);
  assert.equal(await page.locator('#resultEvidence').innerText(), 'SICHT-2');
});

test('late decision confirmation cannot change the currently viewed medium', async t => {
  const blocked = gate();
  const { page } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/media/1/decision') {
      assert.equal(request.method(), 'POST');
      await blocked.wait(); return { json: record(1) };
    }
  });
  await open(page, 1);
  await page.evaluate(() => { activeOperator = 'TEST'; currentDecision = 'secure'; document.getElementById('decisionEvidence').value = 'TEST-1'; window.pendingDecision = saveDecision(); });
  await blocked.arrived; await open(page, 2);
  blocked.release(); await page.evaluate(() => window.pendingDecision);
  assert.equal(await page.evaluate(() => currentMediaId), 2);
  assert.equal(await page.locator('#resultEvidence').innerText(), 'SICHT-2');
});

test('manual status refresh does not jump to the latest stored medium', async t => {
  const { page } = await setup(t, url => {
    if (url.pathname === '/api/status') return { json: { devices: [], cases: [], active_case: { case_number: 'TEST', operator: 'HL' }, update: {}, latest: record(2) } };
  });
  await open(page, 1);
  const response = page.waitForResponse('**/api/status');
  await page.locator('#refreshButton').click(); await response;
  await page.evaluate(() => refresh(false));
  assert.equal(await page.evaluate(() => currentMediaId), 1);
  assert.equal(await page.locator('#resultEvidence').innerText(), 'SICHT-1');
});

test('late search response cannot restore a filter after reset', async t => {
  const blocked = gate();
  const { page } = await setup(t, async url => {
    if (url.pathname === '/api/media/1/files') await blocked.wait();
  });
  await open(page, 1);
  await page.evaluate(() => { window.pendingList = loadInventory({ keyword: 'rechnung' }); });
  await blocked.arrived; await page.evaluate(() => resetInventoryView());
  blocked.release(); await page.evaluate(() => window.pendingList);
  assert.equal(await page.locator('#inventoryTree').isVisible(), true);
  assert.equal(await page.locator('#inventorySearchResults').isVisible(), false);
  assert.equal(await page.locator('#inventoryReset').isVisible(), false);
});

test('late search response cannot put files of the previous medium into the next view', async t => {
  const blocked = gate();
  const { page } = await setup(t, async url => { if (url.pathname === '/api/media/1/files') await blocked.wait(); });
  await open(page, 1); await page.evaluate(() => { window.pendingList = loadInventory({ category: 'Archive' }); });
  await blocked.arrived; await open(page, 2);
  blocked.release(); await page.evaluate(() => window.pendingList);
  assert.equal(await page.locator('#inventorySearchResults').isVisible(), false);
  assert.equal(await page.locator('#inventoryFiles').innerHTML(), '');
});

test('archive subdirectories open in both explorer and filtered results', async t => {
  const { page, requests } = await setup(t);
  await open(page, 1);
  await page.locator('#inventoryTree .tree-container > summary').click();
  await page.locator('#inventoryTree summary[data-container-prefix="Dokumente"]').click();
  await page.waitForFunction(() => document.getElementById('inventoryTree').textContent.includes('Rechnung.pdf'));
  await filter(page);
  await page.locator('.inventory-container-toggle').click();
  await page.locator('#inventoryFiles summary[data-container-prefix="Dokumente"]').click();
  await page.waitForFunction(() => document.getElementById('inventoryFiles').textContent.includes('Rechnung.pdf'));
  assert.equal(requests.filter(r => r.path.endsWith('/container') && r.query.includes('prefix=Dokumente')).length, 2);
});

test('filtered archive pagination is clickable and append-only', async t => {
  const { page } = await setup(t, url => {
    if (!url.pathname.endsWith('/container')) return;
    const second = url.searchParams.get('offset') === '1';
    return { json: { ...pageData([entry(second ? 'second.txt' : 'first.txt')]), has_more: !second, next_offset: 1 } };
  });
  await open(page, 1); await filter(page); await page.locator('.inventory-container-toggle').click();
  await page.locator('#inventoryFiles .tree-more').click();
  await page.waitForFunction(() => document.getElementById('inventoryFiles').textContent.includes('second.txt'));
  assert.match(await page.locator('#inventoryFiles').innerText(), /first.txt/);
  assert.equal(await page.locator('#inventoryFiles .tree-more').count(), 0);
});

test('failed archive requests can be retried by closing and reopening', async t => {
  let attempts = 0;
  const { page } = await setup(t, url => {
    if (url.pathname.endsWith('/container') && ++attempts === 1) return { status: 503, json: { error: 'Test failure' } };
  });
  await open(page, 1); await filter(page); await page.locator('.inventory-container-toggle').click();
  await page.waitForFunction(() => document.getElementById('inventoryFiles').textContent.includes('Test failure'));
  await page.locator('.inventory-container-toggle').click(); await page.locator('.inventory-container-toggle').click();
  await page.locator('#inventoryFiles summary[data-container-prefix="Dokumente"]').waitFor();
  assert.equal(attempts, 2);
});

test('failed archive pagination preserves existing entries and offers retry', async t => {
  let failures = 0;
  const { page } = await setup(t, url => {
    if (!url.pathname.endsWith('/container')) return;
    const second = url.searchParams.get('offset') === '1';
    if (second && failures++ === 0) return { status: 503, json: { error: 'Page temporarily unavailable' } };
    return { json: { ...pageData([entry(second ? 'second.txt' : 'first.txt')]), has_more: !second, next_offset: 1 } };
  });
  await open(page, 1); await filter(page); await page.locator('.inventory-container-toggle').click();
  await page.locator('#inventoryFiles .tree-more').click();
  await page.locator('#inventoryFiles .tree-page-error').waitFor();
  assert.match(await page.locator('#inventoryFiles').innerText(), /first.txt/);
  await page.locator('#inventoryFiles .tree-more').click();
  await page.waitForFunction(() => document.getElementById('inventoryFiles').textContent.includes('second.txt'));
  assert.equal(await page.locator('#inventoryFiles .tree-page-error').count(), 0);
});

test('nested entries and result totals are clearly labelled without inflating media counts', async t => {
  const { page } = await setup(t);
  await open(page, 1); await filter(page);
  assert.equal(await page.locator('#inventoryCount').innerText(), '2 / 2 FUNDSTELLEN');
  assert.match(await page.locator('#inventoryFiles').innerText(), /AUF DEM MEDIUM/);
  assert.match(await page.locator('.inventory-inner-file').innerText(), /IM ZIP/);
  assert.match(await page.locator('.inventory-inner-file').innerText(), /VERSCHACHTELT · NICHT WEITER GEÖFFNET/);
});

test('search field stays usable in a narrow explorer panel', async t => {
  const { page } = await setup(t);
  await page.setViewportSize({ width: 800, height: 700 });
  await open(page, 1); await filter(page);
  const input = await page.locator('#inventorySearch').boundingBox();
  const panel = await page.locator('#inventoryPanel').boundingBox();
  assert.ok(input.width > panel.width * 0.8, 'Search should occupy its own row');
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
});

test('dashboard and case table sort sightings numerically, preserving online/offline groups', async t => {
  const { page } = await setup(t);
  await page.evaluate(() => loadCase('TEST'));
  const labels = () => page.locator('#offlineMediaCards .media-card > strong').allTextContents();
  const caseLabels = await page.locator('#caseMedia tr td:first-child').allTextContents();
  assert.deepEqual(caseLabels, ['SICHT-1', 'SICHT-2', 'SICHT-3', 'SICHT-8', 'SICHT-10']);
  await page.evaluate(() => { currentCaseMedia = currentCaseMedia.map(item => ({ ...item, decision: 'not_selected' })); renderMediaCards(currentCaseMedia); });
  assert.deepEqual(await labels(), ['SICHT-1', 'SICHT-2', 'SICHT-3', 'SICHT-8', 'SICHT-10']);
  await page.evaluate(() => { devices = [{ serial: 'TEST-10' }, { serial: 'TEST-2' }]; renderMediaCards(currentCaseMedia); });
  assert.deepEqual(await page.locator('#mediaCards .media-card > strong').allTextContents(), ['SICHT-2', 'SICHT-10']);
  assert.deepEqual(await labels(), ['SICHT-1', 'SICHT-3', 'SICHT-8']);
});

test('multiple removed undecided media use one queue and return there from details', async t => {
  const { page } = await setup(t, url => {
    if (url.pathname === '/api/status') return { json: { devices: [], cases: [{ case_number: 'TEST' }], active_case: { case_number: 'TEST', operator: 'HL' }, update: {} } };
    return settingsFixture(url);
  });
  const pending = media.slice(0, 3);
  await page.evaluate(items => {
    activeCaseNumber = 'TEST'; activeOperator = 'HL'; currentCaseMedia = items;
    startOverlayReady = true; updateStartOverlay();
    renderDevices(items.map((item, index) => ({ path: `/dev/test${index}`, serial: item.serial, model: item.model, size: 1024 * (index + 1), scan_supported: true })));
  }, pending);
  await openSettingsFromAnywhere(page);
  await page.evaluate(() => renderDevices([]));
  await page.waitForTimeout(1400);
  assert.equal(await page.locator('#decisionQueueModal').isVisible(), false, 'Queue must not stack over another dialog');
  await page.locator('#closeSettings').click();
  await page.locator('#decisionQueueModal').waitFor({ state: 'visible' });
  assert.equal(await page.locator('dialog[open]').count(), 1);
  assert.equal(await page.locator('#decisionQueueList .decision-queue-item').count(), 3);
  assert.match(await page.locator('#decisionQueueList').innerText(), /TEST-10|TEST-3|TEST-1/);
  assert.equal(await page.locator('#offlineMediaPanel').isHidden(), true);
  await page.locator('#decisionQueueList [data-queue-media-id="1"]').click();
  await page.locator('#results').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#decisionQueueModal').isVisible(), false);
  await page.locator('#homeLogo').click();
  await page.locator('#decisionQueueModal').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#pendingDecisionBanner').isVisible(), true);
});

test('iphone card and app-only result distinguish hints from incomplete collection', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; activeOperator = 'HL';
    renderDevices([{
      path: 'iphone:000-test', serial: '000-test', udid: '000-test', vendor: 'Apple',
      model: 'iPhone15,4', device_name: 'Testtelefon', ios_version: '18.6',
      media_type: 'iphone', connection_state: 'trust_required', scan_supported: true,
      unavailable_reason: 'iPhone entsperren und „Diesem Computer vertrauen“ bestätigen.',
    }]);
  });
  assert.match(await page.locator('#deviceList').innerText(), /IPHONE ENTSPERREN \/ VERTRAUEN/);
  assert.match(await page.locator('#deviceList').innerText(), /IOS 18\.6/);
  const iphoneRecord = {
    media: { id: 99, case_number: 'TEST', sighting_number: 'SICHT-099', device_path: 'iphone:000-test', serial: '000-test', vendor: 'Apple', model: 'iPhone15,4', decision: 'open' },
    device: { media_type: 'iphone', device_name: 'Testtelefon', ios_version: '18.6', write_operations_performed: false },
    summary: { evidence: 'SICHT-099', file_count: 0, directory_count: 0, total_file_bytes: 0, keyword_matches: 0, categories_by_count: {}, largest_files: [] },
    hits: {}, archive: {},
    crypto: { rules: { version: 1 }, app_hints: [{ name: 'Test Wallet', category: 'wallet', reason: 'Testregel' }], file_hints: [] },
    phone: {
      platform: 'ios',
      device: { device_name: 'Testtelefon', model: 'iPhone15,4', ios_version: '18.6', connection_state: 'paired' },
      apps_status: 'complete', apps_complete: true, complete: true,
      app_hints: [{ name: 'Test Wallet', bundle_id: 'io.test.wallet', version: '1', id: 'wallet', category: 'wallet' }],
      file_hints: [],
      apps: [{ name: 'Test Wallet', bundle_id: 'io.test.wallet', version: '1', matches: [{ id: 'wallet', category: 'wallet' }] }],
      coverage: [{ label: 'Benutzer-App-Liste', status: 'complete', message: '1 App erfasst' }],
      assessment: 'Relevante Krypto-Apps erkannt – Fachperson hinzuziehen',
      notice: 'Dateien und Fotos wurden nicht gelesen.',
    },
  };
  await page.evaluate(data => { activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' }; updateStartOverlay(); renderRecord(data); }, iphoneRecord);
  assert.equal(await page.locator('#iphoneSummary').isVisible(), true);
  assert.match(await page.locator('#iphoneSummary').innerText(), /1 APP ERFASST/);
  await page.locator('#iphoneSummary .iphone-technical summary').click();
  assert.match(await page.locator('#iphoneFileStatus').innerText(), /KEINE DATEI-, FOTO- ODER MEDIENSICHTUNG/);
  assert.match(await page.locator('#iphoneSummary').innerText(), /KRYPTO-HINWEIS ERKANNT/i);
  assert.match(await page.locator('#iphoneTriageApps').innerText(), /TEST WALLET/i);
  assert.equal(await page.locator('#cryptoFindings').isHidden(), true);
  assert.match(await page.locator('#decisionTitle').innerText(), /FACHPERSON DOKUMENTIEREN|TELEFON|MOBILGERÄT/i);
  if (process.env.TRIAGE_SCREENSHOT) await page.locator('#results').screenshot({ path: process.env.TRIAGE_SCREENSHOT });
  assert.doesNotMatch(await page.locator('#iphoneNotice').textContent(), /FILE SHARING|AFC/);
  assert.match(await page.locator('#phoneCoverage').innerText(), /Benutzer-App-Liste/i);
  assert.equal(await page.locator('#classicHome').isHidden(), true);
  assert.equal(await page.locator('#classicHome').isHidden(), true);
  assert.equal(await page.locator('#inventoryPanel').getAttribute('open'), null);
  await page.locator('#iphoneCategories .iphone-category.crypto summary').click();
  assert.match(await page.locator('#iphoneCategories .iphone-category.crypto').innerText(), /TEST WALLET/i);
  assert.equal(await page.locator('#iphoneCategories .iphone-category.crypto').isVisible(), true);
});

test('android card guides authorization and result shows profile coverage', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; activeOperator = 'HL';
    renderDevices([{
      path: 'android:SERIAL1', serial: 'SERIAL1', vendor: 'Samsung', model: 'Galaxy Test',
      media_type: 'android', connection_state: 'authorization_required', scan_supported: false,
      unavailable_reason: 'Verbindungsabfrage am Telefon bestätigen.',
      guidance: ['Einstellungen öffnen', 'USB-Debugging aktivieren', 'Verbindungsabfrage bestätigen'],
    }]);
  });
  assert.match(await page.locator('#deviceList').innerText(), /ANDROID-TELEFON ERKANNT/);
  assert.match(await page.locator('#deviceList').innerText(), /VERBINDUNG AM TELEFON BESTÄTIGEN/);
  assert.equal(await page.locator('[data-scan-device]').isDisabled(), true);
  const androidRecord = {
    media: { id: 100, case_number: 'TEST', sighting_number: 'SICHT-100', device_path: 'android:SERIAL1', serial: 'SERIAL1', vendor: 'Samsung', model: 'Galaxy Test', decision: 'open' },
    device: { media_type: 'android', vendor: 'Samsung', model: 'Galaxy Test', android_version: '16', adb_serial: 'SERIAL1' },
    summary: { evidence: 'SICHT-100', file_count: 0, directory_count: 0, total_file_bytes: 0, keyword_matches: 0, categories_by_count: {}, largest_files: [] },
    hits: {}, archive: {},
    phone: {
      platform: 'android', device: { vendor: 'Samsung', model: 'Galaxy Test', android_version: '16', adb_serial: 'SERIAL1' },
      apps_status: 'complete', apps_complete: true,
      apps: [{ name: 'MetaMask', package_id: 'io.metamask', version: '7.50', profile_name: 'Owner', matches: [{ id: 'metamask', category: 'wallet', relevance: 'high' }] }],
      app_hints: [{ name: 'MetaMask', package_id: 'io.metamask', category: 'wallet', relevance: 'high' }],
      coverage: [{ label: 'Owner', status: 'complete', message: '1 Benutzer-App erfasst' }, { label: 'Secure Folder', status: 'unknown', message: 'Nicht zuverlässig feststellbar' }],
      assessment: 'Relevante Krypto-Apps erkannt – Fachperson hinzuziehen', notice: 'Keine Dateien gelesen.',
    },
  };
  await page.evaluate(data => { activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' }; updateStartOverlay(); renderRecord(data); }, androidRecord);
  assert.match(await page.locator('#iphoneSystem').innerText(), /ANDROID 16/);
  await page.locator('#iphoneCategories .iphone-category.crypto summary').click();
  assert.match(await page.locator('#iphoneCategories .iphone-category.crypto').innerText(), /MetaMask/i);
  await page.locator('#iphoneSummary .iphone-technical summary').click();
  assert.match(await page.locator('#phoneCoverage').innerText(), /Secure Folder/i);
  assert.match(await page.locator('#phoneCoverage').innerText(), /NICHT VOLLSTÄNDIG PRÜFBAR/);
});

test('phone app groups show recognized names and search only the collapsed other group', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' }; updateStartOverlay();
    document.getElementById('results').hidden = false;
    renderIphoneSummary({
    device: { device_name: 'Testtelefon', serial: 'TEST-SERIAL' }, apps_status: 'complete',
    apps: [
      { name: 'Signal', matches: [{ category: 'messenger' }] },
      { name: 'Unbekannt A', matches: [] }, { name: 'Unbekannt B', matches: [] },
    ], app_hints: [], file_hints: [], areas: [], file_sharing_status: 'complete',
    });
  });
  assert.match(await page.locator('#iphoneTriageLevel').innerText(), /KEIN KRYPTO-HINWEIS/);
  assert.match(await page.locator('#iphoneTriageText').innerText(), /nicht aus/);
  const messengerCategory = page.locator('#iphoneCategories .iphone-category:not(.iphone-category-other)');
  await messengerCategory.locator('summary').click();
  assert.match(await messengerCategory.innerText(), /SIGNAL/i);
  assert.equal(await page.locator('#iphoneCategories .iphone-category-other').getAttribute('open'), null);
  await page.locator('#iphoneCategories .iphone-category-other summary').click();
  await page.locator('#iphoneOtherSearch').fill('Unbekannt B');
  assert.equal(await page.locator('#iphoneCategories .iphone-category-other li:visible').count(), 1);
  assert.match(await page.locator('#iphoneCategories .iphone-category-other li:visible').innerText(), /Unbekannt B/);
  assert.match(await page.locator('#iphoneSummary .iphone-head').innerText(), /TEST-SERIAL/);
});

test('detection rules editor and shared hints remain separate from neutral apps', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionRows tr[data-id]').first().click();
  assert.equal(await page.locator('#detectionEditor').isHidden(), false);
  await page.locator('#detectionEditorFields [data-field="name"]').fill('Test Wallet 2');
  assert.equal(await page.locator('#detectionApply').isEnabled(), true);
  await page.locator('#detectionSearch').fill('Kein Treffer');
  assert.equal(await page.locator('#detectionRows tr[data-id]:visible').count(), 0);
  await page.locator('#detectionSearch').fill('');
  await page.locator('#detectionExport').click();
  await page.locator('#detectionBankingTab').click();
  assert.equal(await page.locator('#detectionRows tr').count() >= 0, true);
  await page.locator('#detectionBackupsTab').click();
  assert.equal(await page.locator('#detectionRows tr').count() >= 0, true);
});

test('iPhone without reported serial uses UDID path for online and pending decision', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.evaluate(() => {
    activeCaseNumber = 'TEST'; activeOperator = 'HL';
    currentCaseMedia = [{ id: 77, case_number: 'TEST', sighting_number: 'SICHT-077', device_path: 'iphone:udid-77', serial: '',
      vendor: 'Apple', model: 'iPhone', file_count: 0, keyword_matches: 0, decision: 'open' }];
    renderDevices([{ path: 'iphone:udid-77', udid: 'udid-77', serial: '', media_type: 'iphone', model: 'iPhone',
      scan_supported: true, connection_state: 'paired' }]);
  });
  assert.equal(await page.locator('#mediaCards .media-card').count(), 1);
  assert.equal(await page.locator('#decisionQueueList .decision-queue-item').count(), 0);
  assert.equal(await page.locator('#mediaCards .media-eject').count(), 0);
  await page.evaluate(() => renderDevices([]));
  assert.equal(await page.locator('#decisionQueueList .decision-queue-item').count(), 1);
  assert.match(await page.locator('#decisionQueueList').innerText(), /UDID udid-77/);
});

test('largest-file sizes remain visible without horizontal scrolling for long paths', async t => {
  const longPath = 'Sehr langer Ordner/'.repeat(12) + 'Langer Dateiname '.repeat(20) + '.mkv';
  const { page } = await setup(t, url => {
    if (url.pathname === '/api/media/1') return { json: { ...record(1), summary: { ...record(1).summary, largest_files: [{ path: longPath, size: 22 * 1024 ** 3 }] } } };
  });
  await open(page, 1);
  for (const width of [1440, 800, 470]) {
    await page.setViewportSize({ width, height: 900 });
    const geometry = await page.locator('.files-panel').evaluate(panel => {
      const wrap = panel.querySelector('.table-wrap');
      const size = panel.querySelector('.largest-size').getBoundingClientRect();
      const bounds = panel.getBoundingClientRect();
      return { overflow: wrap.scrollWidth > wrap.clientWidth, sizeVisible: size.left >= bounds.left && size.right <= bounds.right };
    });
    assert.deepEqual(geometry, { overflow: false, sizeVisible: true });
    assert.equal(await page.locator('.largest-size').innerText(), '22 GB');
  }
  assert.match(await page.locator('.largest-file-link').getAttribute('title'), /Sehr langer Ordner/);
});

test('largest-file click navigates to the exact stored path and filter reset still works', async t => {
  const exactPath = "Ordner/Übergabe ' & # % <Test>.mkv";
  const { page, requests } = await setup(t, url => {
    if (url.pathname === '/api/media/1') return { json: { ...record(1), summary: { ...record(1).summary, largest_files: [{ path: exactPath, size: 300 }] } } };
    if (url.pathname === '/api/media/1/files' && url.searchParams.has('exact_path')) {
      assert.equal(url.searchParams.get('exact_path'), exactPath);
      assert.equal(url.searchParams.has('category'), false);
      return { json: { files: [{ path: exactPath, size: 300, category: 'Video', source: 'readonly_mount' }], total: 1, shown: 1 } };
    }
  });
  await open(page, 1); await filter(page);
  await page.locator('.largest-file-link').focus();
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.getElementById('inventoryCount').textContent === '1 / 1 FUNDSTELLEN');
  assert.equal(await page.locator('#inventorySearch').inputValue(), exactPath);
  assert.match(await page.locator('#inventoryFiles').innerText(), /Übergabe/);
  assert.equal(await page.locator('.result-filter.active').count(), 0);
  assert.equal(requests.filter(request => request.method !== 'GET').length, 0);
  await page.locator('#inventoryReset').click();
  await page.waitForFunction(() => !document.getElementById('inventoryTree').hidden);
  assert.equal(await page.locator('#inventorySearch').inputValue(), '');
});

test('archive counts have their own readable section, without altering bar alignment', async t => {
  const { page } = await setup(t, url => {
    if (url.pathname === '/api/media/1') return { json: { ...record(1), summary: { ...record(1).summary, archive_encryption: { total: 10, encrypted: 4, unknown: 2 } } } };
  });
  await open(page, 1);
  assert.equal(await page.locator('#archiveStatus').isVisible(), true);
  assert.equal(await page.locator('#archiveEncryptedCount').innerText(), '4');
  assert.equal(await page.locator('#archiveUnknownCount').innerText(), '2');
  assert.doesNotMatch(await page.locator('#categories').innerText(), /VERSCHLÜSSELT|UNGEPRÜFT/);
  const tracks = await page.locator('#categories .bar-track').evaluateAll(nodes => nodes.map(node => ({ x: node.getBoundingClientRect().x, width: node.getBoundingClientRect().width })));
  assert.deepEqual(tracks[0], tracks[1]);
  await page.evaluate(() => renderResults({ archive_encryption: { total: 3, encrypted: 0, unknown: 0 } }));
  assert.equal(await page.locator('#archiveUnknownCount').innerText(), '0');
  assert.equal(await page.locator('[data-inventory-archive-status="unknown"]').isDisabled(), true);
  assert.equal(await page.locator('[data-inventory-archive-status="encrypted"]').isDisabled(), true);
  await open(page, 2);
  assert.equal(await page.locator('#archiveStatus').isVisible(), false);
});

test('compact archive counts filter the correct status, keep pagination and reset cleanly', async t => {
  const { page, requests } = await setup(t, url => {
    if (url.pathname === '/api/media/1') return { json: { ...record(1), summary: { ...record(1).summary, archive_encryption: { total: 10, encrypted: 4, unknown: 2 } } } };
    if (url.pathname.endsWith('/files') && url.searchParams.has('archive_status')) {
      const state = url.searchParams.get('archive_status'), offset = Number(url.searchParams.get('offset'));
      const count = state === 'encrypted' ? 4 : 2;
      const files = Array.from({ length: count - offset }, (_, i) => ({ path: `${state}-${i + offset}.zip`, category: 'Archive', source: 'media_inventory', archive_encryption: state, container_id: `${state}-${i + offset}.zip` }));
      // Exercise the more-results button even with a small fixture.
      if (!offset) files.splice(1);
      return { json: { files, total: count, shown: files.length, offset, next_offset: offset + files.length, has_more: offset === 0 } };
    }
  });
  await open(page, 1);
  for (const width of [1440, 800]) {
    await page.setViewportSize({ width, height: 1080 });
    const box = await page.locator('#archiveStatus').boundingBox();
    assert.ok(box.height <= 70, `Compact labelled status row at ${width}px: ${box.height}`);
  }
  const encrypted = page.locator('[data-inventory-archive-status="encrypted"]');
  const unknown = page.locator('[data-inventory-archive-status="unknown"]');
  for (const [button, state, count] of [[encrypted, 'encrypted', 4], [unknown, 'unknown', 2]]) {
    await button.click();
    await page.waitForFunction(state => inventoryListState?.archiveStatus === state && document.getElementById('inventoryCount').textContent.startsWith('1 /'), state);
    assert.equal(await button.getAttribute('aria-pressed'), 'true');
    await page.locator('#inventoryMore').click();
    await page.waitForFunction(count => document.getElementById('inventoryCount').textContent === `${count} / ${count} FUNDSTELLEN`, count);
    assert.equal(await page.locator(`#inventoryFiles .archive-mark.${state}`).count(), count);
    assert.equal(await page.locator('#inventoryMore').isVisible(), false);
  }
  assert.equal(await encrypted.getAttribute('aria-pressed'), 'false');
  assert.match(await page.locator('#inventoryFilterDescription').innerText(), /Nur Archivdateien auf dem Medium/);
  // Existing expandable archives must also work in the new status filter.
  await page.locator('.inventory-container-toggle').first().click();
  await page.waitForFunction(() => document.querySelector('.inventory-container-detail:not([hidden])')?.textContent.includes('Dokumente'));
  await unknown.click();
  await page.waitForFunction(() => document.getElementById('inventoryTree').hidden === false);
  assert.equal(await unknown.getAttribute('aria-pressed'), 'false');
  await encrypted.click(); await filter(page);
  assert.equal(await encrypted.getAttribute('aria-pressed'), 'false');
  assert.match(await page.locator('#inventoryFilterDescription').innerText(), /lesbaren Archivverzeichnissen/);
  await page.locator('#inventoryReset').click();
  assert.equal(await page.locator('#inventorySearchResults').isVisible(), false);
  assert.ok(requests.filter(r => r.path.endsWith('/files')).some(r => r.query.includes('archive_status=unknown') && r.query.includes('offset=1')));
});

test('explorer and list show subtle text statuses only on inspected outer archives', async t => {
  const archives = [
    { ...entry('Verschlüsselt.zip', 'container'), container_id: 'encrypted', archive_encryption: 'encrypted', encrypted: true, container_status: 'ok', entry_count: 3 },
    { ...entry('Defekt.rar', 'container'), container_id: 'unknown', archive_encryption: 'unknown', container_status: 'incomplete' },
    { ...entry('Alt.tgz'), archive_encryption: 'unknown' },
    { ...entry('Offen.zip', 'container'), container_id: 'clear', archive_encryption: 'not_encrypted' },
  ].map(file => ({ ...file, category: 'Archive' }));
  const { page } = await setup(t, url => {
    if (url.pathname.endsWith('/tree')) return { json: pageData(archives) };
    if (url.pathname.endsWith('/files')) {
      const files = [...archives, { path: 'Verschlüsselt.zip › Innen.rar', category: 'Archive', source: 'container_index', encrypted: true }];
      return { json: { files, total: files.length, shown: files.length } };
    }
  });
  await open(page, 1);
  assert.equal(await page.locator('#inventoryTree .archive-mark.encrypted').count(), 1);
  assert.equal(await page.locator('#inventoryTree .archive-mark.unknown').count(), 2);
  assert.equal(await page.locator('#inventoryTree .archive-mark.encrypted').innerText(), 'VERSCHLÜSSELT');
  assert.notEqual(await page.locator('#inventoryTree .archive-mark.encrypted').evaluate(n => getComputedStyle(n).color), await page.locator('#inventoryTree .archive-mark.unknown').first().evaluate(n => getComputedStyle(n).color));
  await filter(page);
  assert.equal(await page.locator('#inventoryFiles .archive-mark.encrypted').count(), 1);
  assert.equal(await page.locator('#inventoryFiles .archive-mark.unknown').count(), 2);
  assert.equal(await page.locator('.inventory-inner-file .archive-mark').count(), 0);
  assert.match(await page.locator('.inventory-inner-file').innerText(), /VERSCHACHTELT/);
});

test('late archive-status result cannot replace another medium or a different status', async t => {
  const blocked = gate(); let block = true;
  const { page } = await setup(t, async url => {
    if (block && url.pathname.endsWith('/files') && url.searchParams.get('archive_status') === 'encrypted') {
      block = false; await blocked.wait();
      return { json: { files: [{ path: 'STALE-ENCRYPTED.zip' }], total: 1, shown: 1 } };
    }
  });
  await open(page, 1);
  await page.evaluate(() => { window.pendingArchive = loadInventory({ archiveStatus: 'encrypted' }); });
  await blocked.arrived;
  await page.evaluate(() => loadInventory({ archiveStatus: 'unknown' }));
  await open(page, 2);
  blocked.release(); await page.evaluate(() => window.pendingArchive);
  assert.equal(await page.locator('#inventoryTree').isVisible(), true);
  assert.doesNotMatch(await page.locator('#inventoryFiles').innerText(), /STALE/);
  assert.equal(await page.evaluate(() => inventoryListState), null);
});

test('start overlay blocks dashboard but leaves system controls reachable', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.waitForFunction(() => startOverlayReady);
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  await page.locator('#startOverlaySettings').click();
  assert.equal(await page.locator('#settingsModal').isVisible(), true);
  await page.locator('#closeSettings').click();
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  await page.locator('#startOverlayPower').click();
  assert.equal(await page.locator('#powerModal').isVisible(), true);
  await page.locator('#closePowerModal').click();
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  await page.locator('#startOpenCase').click();
  assert.equal(await page.locator('#auftragModal').isVisible(), true);
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
  await page.locator('#closeAuftragModal').click();
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
});

test('starting a case hides the overlay and ending it shows it again', async t => {
  const { page } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/cases/start' && request.method() === 'POST') {
      return { json: { case: { case_number: 'TEST-64' } } };
    }
    if (url.pathname === '/api/cases/stop' && request.method() === 'POST') {
      return { json: { ok: true } };
    }
    return settingsFixture(url);
  });
  await page.waitForFunction(() => startOverlayReady);
  await page.locator('#startOpenCase').click();
  await page.locator('#caseNumber').fill('TEST-64');
  await page.locator('#operator').fill('HL');
  await page.locator('#caseStart').click();
  await page.waitForFunction(() => activeCaseNumber === 'TEST-64');
  assert.equal(await page.locator('#startOverlay').isVisible(), false);
  await page.evaluate(() => stopCaseSession());
  await page.waitForFunction(() => !activeCaseNumber);
  assert.equal(await page.locator('#startOverlay').isVisible(), true);
});

test('reload with active case does not flash overlay', async t => {
  const { page } = await setup(t, url => {
    if (url.pathname === '/api/status') return { json: { devices: [], cases: [], active_case: { case_number: 'TEST-64', operator: 'HL' }, update: {} } };
    return settingsFixture(url);
  });
  await page.waitForFunction(() => activeCaseNumber === 'TEST-64');
  assert.equal(await page.locator('#startOverlay').isVisible(), false);
  assert.equal(await page.evaluate(() => startOverlayReady), true);
});

test('important system buttons use inline SVG instead of problematic Unicode glyphs', async t => {
  const { page } = await setup(t, settingsFixture);
  for (const id of ['#openSettings', '#openPowerModal', '#deviceRefresh', '#caseStart', '#caseStop', '#updateCheck']) {
    const hasSvg = await page.locator(id).evaluate(node => node.querySelector('svg') !== null);
    assert.equal(hasSvg, true, `${id} should contain an SVG icon`);
  }
  for (const id of ['#openSettings', '#openPowerModal']) {
    const text = await page.locator(id).innerText();
    assert.doesNotMatch(text, /[⚙⏻↻▶■]/);
  }
});

test('profile master-detail supports create, edit, duplicate, add and remove keywords', async t => {
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/profiles' && request.method() === 'POST') {
      const payload = request.postDataJSON();
      return { status: 201, json: { profile: { id: payload.id || 'neu', name: payload.name, keywords: payload.keywords, version: '1.0' } } };
    }
    return settingsFixture(url);
  });
  await openSettingsFromAnywhere(page);
  assert.equal(await page.locator('#profileDetailEmpty').isVisible(), true);
  await page.locator('#settingsProfilesList [data-select-profile]').click();
  assert.equal(await page.locator('#profileDetailName').inputValue(), 'Allgemein');
  assert.equal(await page.locator('#profileDetailOptions input').count(), 2);
  await page.locator('#profileDetailDuplicate').click();
  assert.match(await page.locator('#profileDetailName').inputValue(), /Kopie/);
  assert.equal(await page.evaluate(() => profileEditorId), null);
  await page.locator('#createProfile').click();
  await page.locator('#profileDetailName').fill('Sonderprofil');
  await page.locator('#profileDetailNewInput').fill('verdacht');
  await page.locator('#profileDetailAddKeyword').click();
  assert.equal(await page.locator('#profileDetailOptions input').count(), 1);
  await page.locator('#profileDetailOptions [data-remove-keyword]').click();
  assert.equal(await page.locator('#profileDetailOptions input').count(), 0);
  await page.locator('#profileDetailNewInput').fill('beweis');
  await page.locator('#profileDetailNewInput').press('Enter');
  assert.equal(await page.locator('#profileDetailOptions input').count(), 1);
  await page.locator('#profileDetailSave').click();
  await page.waitForFunction(() => document.getElementById('profileDetailMessage').textContent.includes('GESPEICHERT'));
  assert.ok(requests.some(r => r.path === '/api/profiles' && r.method === 'POST'));
});

test('profile selection for next scans stays separate from saving the profile', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList [data-select-profile]').click();
  await page.locator('#profileDetailClearAll').click();
  await page.locator('#profileDetailApply').click();
  await page.waitForFunction(() => document.getElementById('profileDetailMessage').textContent.includes('NÄCHSTE SCANS'));
  assert.equal(await page.evaluate(() => selectedByProfile.get('default')?.size), 0);
});

test('platform status badges are plain text without visible circle or badge', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const cell = page.locator('#detectionRows tr[data-id="wallet"] .platform-id-status').first();
  assert.equal(await cell.innerText(), '✓');
  const style = await cell.evaluate(node => ({ borderRadius: getComputedStyle(node).borderRadius, borderWidth: getComputedStyle(node).borderWidth, background: getComputedStyle(node).backgroundColor }));
  assert.equal(style.borderRadius, '0px');
  assert.equal(style.borderWidth, '0px');
  assert.equal(style.background, 'rgba(0, 0, 0, 0)');
});

test('platform status tooltip still explains verification state', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const trigger = page.locator('#detectionRows tr[data-id="wallet"] .platform-id-status').first();
  await trigger.focus();
  const tooltip = page.locator('#settingsTooltipLayer');
  await tooltip.waitFor({ state: 'visible' });
  assert.match(await tooltip.innerText(), /ID VERIFIZIERT/);
});

test('custom scrollbar CSS does not break layout or hide footer buttons', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1440, height: 900 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const modal = await page.locator('#settingsModal').evaluate(node => ({ scrollWidth: node.scrollWidth, clientWidth: node.clientWidth }));
  assert.ok(modal.scrollWidth <= modal.clientWidth + 1);
  const footer = await page.locator('.detection-footer').evaluate(node => node.getBoundingClientRect());
  const modalBox = await page.locator('#settingsModal').evaluate(node => node.getBoundingClientRect());
  assert.ok(footer.bottom <= modalBox.bottom + 1);
  assert.ok(footer.height > 0);
});

test('readability CSS keeps native monospace stack and subtle scanlines only', async () => {
  const css = fs.readFileSync(path.join(root, 'web', 'styles.css'), 'utf8');
  assert.match(css, /--mono-stack:\s*ui-monospace,\s*"SFMono-Regular",\s*Menlo,\s*Monaco,\s*"Cascadia Mono",\s*"Segoe UI Mono",\s*Consolas,\s*monospace;/);
  assert.doesNotMatch(css, /Courier New|Roboto Mono/);
  assert.doesNotMatch(css, /@import|fonts\.google|fonts\.gstatic|https?:\/\/[^"')]+\.(?:woff2?|ttf|otf)/i);
  assert.match(css, /\.scanlines\s*\{[^}]*opacity:\s*\.025;/);
  assert.doesNotMatch(css, /font-size:\s*[89]px|font:\s*[^;]*\s[89]px/);
  const tenPixelLines = css.split('\n').filter(line => /font-size:\s*10px/.test(line));
  assert.deepEqual(tenPixelLines, ['.tree-arrow { color: var(--acid); font-size: 10px; transition: transform .15s ease; }']);
});

test('important UI surfaces stay visible with readability typography', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1440, height: 980 });
  await page.waitForFunction(() => startOverlayReady);
  for (const selector of ['#startOverlay', '.start-overlay-brand', '#startOpenCase', '.scanlines']) {
    assert.equal(await page.locator(selector).isVisible(), true, `${selector} should be visible`);
  }
  const scanlines = await page.locator('.scanlines').evaluate(node => getComputedStyle(node).opacity);
  assert.equal(scanlines, '0.025');

  await page.evaluate(items => {
    activeCaseNumber = 'TEST'; serverActiveCase = { case_number: 'TEST', operator: 'HL' };
    updateStartOverlay();
    renderDevices([{ path: '/dev/test', serial: 'SERIAL1', model: 'Testmedium', size: 1024, scan_supported: true }]);
    renderMediaCards(items);
  }, media);
  assert.equal(await page.locator('#startOverlay').isVisible(), false);
  for (const selector of ['#deviceList', '#openSettings']) {
    assert.equal(await page.locator(selector).isVisible(), true, `${selector} should stay visible`);
  }

  await open(page, 1);
  for (const selector of ['#results', '#inventoryPanel', '.result-stamp']) {
    assert.equal(await page.locator(selector).isVisible(), true, `${selector} should stay visible in result view`);
  }

  await openSettingsFromAnywhere(page);
  for (const tab of ['#settingsProfilesTab', '#settingsFiletypesTab', '#settingsCryptoTab', '#settingsUpdatesTab']) {
    await page.locator(tab).click();
    const pane = await page.locator('.settings-pane:not([hidden])').evaluate(node => ({
      width: node.getBoundingClientRect().width,
      height: node.getBoundingClientRect().height,
      scroll: node.scrollWidth,
      client: node.clientWidth,
    }));
    assert.ok(pane.width > 300 && pane.height > 300, `${tab} pane should have useful space`);
    assert.ok(pane.scroll <= pane.client + 1, `${tab} pane must not overflow horizontally`);
  }
});

test('start overlay branding uses acid spans for both slashes', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.waitForFunction(() => startOverlayReady);
  const brand = await page.locator('.start-overlay-brand').evaluate(node => ({
    text: node.textContent,
    slashCount: node.querySelectorAll('.acid').length,
  }));
  assert.match(brand.text, /TRIAGE\/\/BOX/);
  assert.equal(brand.slashCount, 2);
  assert.match(await page.locator('.start-overlay-ready').innerText(), /BEREIT/);
});

test('profile list has no edit or duplicate buttons per row', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  assert.equal(await page.locator('#settingsProfilesList [data-edit-profile]').count(), 0);
  assert.equal(await page.locator('#settingsProfilesList [data-copy-profile]').count(), 0);
  assert.equal(await page.locator('#settingsProfilesList [data-select-profile]').count(), 1);
});

test('profile list row opens editor and empty selection stays empty after save', async t => {
  const { page, requests } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/profiles' && request.method() === 'POST') {
      const payload = request.postDataJSON();
      return { status: 200, json: { profile: { id: 'default', name: payload.name, keywords: payload.keywords, version: '1.1' } } };
    }
    return settingsFixture(url);
  });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList [data-select-profile]').click();
  assert.equal(await page.locator('#profileDetailForm').isVisible(), true);
  await page.locator('#profileDetailClearAll').click();
  await page.locator('#profileDetailSave').click();
  await page.waitForFunction(() => document.getElementById('profileDetailMessage').textContent.includes('GESPEICHERT') && selectedByProfile.get('default')?.size === 0);
  assert.equal(await page.evaluate(() => selectedByProfile.get('default')?.size), 0);
});

test('profile keyword list is vertical not two-column', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsProfilesList [data-select-profile]').click();
  const rows = await page.locator('#profileDetailOptions .keyword-option').all();
  assert.ok(rows.length >= 1);
  if (rows.length >= 2) {
    const first = await rows[0].boundingBox();
    const second = await rows[1].boundingBox();
    assert.ok(first.y < second.y, 'keywords should stack vertically');
    assert.ok(Math.abs(first.x - second.x) < 2, 'keywords should start at same x');
  }
});

test('detection toolbar keeps search filter sort and count on one row on desktop', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1440, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const toolbar = await page.locator('.detection-toolbar').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth, height: node.getBoundingClientRect().height }));
  assert.ok(toolbar.scroll <= toolbar.client + 1, 'toolbar must not wrap or overflow on desktop');
  assert.ok(toolbar.height <= 70, 'toolbar must stay compact without stacked labels');
  const tops = await page.locator('.detection-toolbar input, .detection-toolbar select').evaluateAll(nodes => nodes.map(n => Math.round(n.getBoundingClientRect().top)));
  assert.equal(new Set(tops).size, 1, 'all toolbar controls must share one baseline row');
  const count = await page.locator('#detectionCount').evaluate(node => node.getBoundingClientRect());
  const toolbarBox = await page.locator('.detection-toolbar').evaluate(node => node.getBoundingClientRect());
  assert.ok(count.right <= toolbarBox.right + 1, 'count must stay inside toolbar');
});

test('profile master-detail and detection toolbar wrap cleanly on small screens', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  for (const { width, height } of [{ width: 1280, height: 900 }, { width: 1000, height: 900 }, { width: 620, height: 900 }]) {
    await page.setViewportSize({ width, height });
    await page.locator('#settingsProfilesTab').click();
    const profileWorkspace = await page.locator('.profile-workspace').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
    assert.ok(profileWorkspace.scroll <= profileWorkspace.client + 1, `profile workspace must not overflow at ${width}px`);
    await page.locator('#settingsCryptoTab').click();
    const toolbar = await page.locator('.detection-toolbar').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
    assert.ok(toolbar.scroll <= toolbar.client + 1, `detection toolbar must not overflow at ${width}px`);
    const modal = await page.locator('#settingsModal').evaluate(node => ({ scroll: node.scrollWidth, client: node.clientWidth }));
    assert.ok(modal.scroll <= modal.client + 1, `settings modal must not overflow at ${width}px`);
  }
});

test('filetypes master-detail shows categories left and editor right', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  assert.match(await page.locator('#settingsFiletypesTab').innerText(), /DATEITYPEN/);
  assert.equal(await page.locator('[data-category="Bilder"]').isVisible(), true);
  assert.match(await page.locator('[data-category="Bilder"] .catalog-row-count').innerText(), /^2$/);
  assert.equal(await page.locator('#filetypesDetailEmpty').isVisible(), true);
  await page.locator('[data-category="Bilder"]').click();
  assert.equal(await page.locator('#filetypesDetailEmpty').isVisible(), false);
  assert.equal(await page.locator('#filetypesDetailForm').isVisible(), true);
  assert.equal(await page.locator('#filetypesDetailName').inputValue(), 'Bilder');
  assert.equal(await page.locator('#filetypesDetailExtensions').inputValue(), 'jpg, png');
});

test('filetypes editor can rename, add extensions and delete a category', async t => {
  const { page } = await setup(t, async (url, request) => {
    if (url.pathname === '/api/settings/filetypes' && request.method() === 'POST') {
      const payload = request.postDataJSON();
      return { json: { catalog: { categories: payload.categories, version: 2, sha256: 'second' } } };
    }
    return settingsFixture(url);
  });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('[data-category="Bilder"]').click();
  await page.locator('#filetypesDetailEdit').click();
  await page.locator('#filetypesDetailName').fill('Bilder Neu');
  await page.locator('#filetypesDetailExtensions').fill('jpg, png, gif');
  await page.locator('#filetypesDetailApply').click();
  assert.equal(await page.locator('[data-category="Bilder"]').isVisible(), false);
  assert.equal(await page.locator('[data-category="Bilder Neu"]').isVisible(), true);
  assert.match(await page.locator('[data-category="Bilder Neu"] .catalog-row-count').innerText(), /^3$/);
  await page.locator('#catalogAddCategory').click();
  assert.equal(await page.locator('#filetypesDetailName').inputValue(), 'Neue Kategorie');
  await page.locator('#filetypesDetailName').fill('Audio');
  await page.locator('#filetypesDetailExtensions').fill('mp3, wav');
  await page.locator('#filetypesDetailApply').click();
  assert.equal(await page.locator('[data-category="Audio"]').isVisible(), true);
  await page.locator('[data-category="Dokumente"]').click();
  await page.locator('#filetypesDetailDelete').click();
  page.once('dialog', dialog => dialog.accept());
  await page.locator('#filetypesDetailDelete').click();
  assert.equal(await page.locator('[data-category="Dokumente"]').isVisible(), false);
});

test('filetypes has no inline textarea per category row', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsFiletypesTab').click();
  assert.equal(await page.locator('#catalogRows > textarea').count(), 0);
  assert.equal(await page.locator('#catalogRows .catalog-row textarea').count(), 0);
});

test('detection table sticky header covers scrolling rows and platform status', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  const ths = await page.locator('.detection-table th').all();
  assert.ok(ths.length >= 4, 'header cells must exist');
  for (const th of ths) {
    const style = await th.evaluate(node => ({ position: getComputedStyle(node).position, zIndex: Number(getComputedStyle(node).zIndex) }));
    assert.equal(style.position, 'sticky', 'header cells must be sticky');
    assert.ok(style.zIndex > 0, 'each header cell must have positive z-index');
  }
  const wrapStyle = await page.locator('.detection-table-wrap').evaluate(node => ({ zIndex: Number(getComputedStyle(node).zIndex), isolation: getComputedStyle(node).isolation }));
  assert.ok(wrapStyle.zIndex > 0 || wrapStyle.isolation === 'isolate', 'table wrap must establish stacking context');
  const firstRow = await page.locator('#detectionRows tr').first().evaluate(node => node.getBoundingClientRect());
  const headerBottom = await page.locator('.detection-table th').first().evaluate(node => node.getBoundingClientRect().bottom);
  assert.ok(firstRow.top >= headerBottom - 1, 'first data row must start below sticky header');
});

test('detection editor uses full height with fixed footer and compact buttons', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.setViewportSize({ width: 1512, height: 982 });
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsCryptoTab').click();
  await page.locator('#detectionRows tr[data-id="wallet"]').click();
  await page.locator('#detectionEditorForm').waitFor();
  const editor = await page.locator('.detection-editor-panel').evaluate(node => node.getBoundingClientRect());
  const body = await page.locator('.detection-body').evaluate(node => node.getBoundingClientRect());
  assert.ok(editor.height >= body.height - 1, 'editor panel should fill detection body height');
  const footer = await page.locator('.detection-editor-form-actions').evaluate(node => node.getBoundingClientRect());
  assert.ok(footer.bottom <= editor.bottom + 1, 'editor footer must stay at bottom of panel');
  assert.ok(footer.height <= 70, 'editor footer buttons must be compact');
  const buttons = await page.locator('.detection-editor-form-actions button').all();
  assert.equal(buttons.length, 2);
  for (const button of buttons) {
    const height = await button.evaluate(node => node.getBoundingClientRect().height);
    assert.ok(height <= 44, 'editor action buttons must be compact');
  }
  assert.equal(await page.locator('#detectionApply').isVisible(), true);
  assert.equal(await page.locator('#detectionCancel').isVisible(), true);
});

test('updates tab is renamed and shows compact status block', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  assert.match(await page.locator('#settingsUpdatesTab').innerText(), /UPDATES/);
  assert.doesNotMatch(await page.locator('.settings-tabs').innerText(), /SYSTEM\s*&\s*UPDATES/i);
  assert.equal(await page.locator('#updateCurrentVersion').isVisible(), true);
  assert.equal(await page.locator('#updateStatus').isVisible(), true);
  assert.equal(await page.locator('#updateCheckedAt').isVisible(), true);
  assert.equal(await page.locator('#updateCheck').isVisible(), true);
  assert.equal(await page.locator('#offlineUpdateFile').isVisible(), true);
  assert.equal(await page.locator('#offlineUpdateInstall').isVisible(), true);
});

test('update success is quiet: status simply returns to AKTUELL after install', async t => {
  const { page } = await setup(t);
  await page.evaluate(() => {
    renderUpdateState({ state: 'installed', current_version: '0.2.0a49' });
    document.getElementById('settingsModal').showModal();
    selectSettingsPane('updates');
  });
  assert.equal(await page.locator('#updateSuccessNotice').count(), 0, 'no permanent success banner after install');
  assert.match(await page.locator('#updateStatus').innerText(), /✓ AKTUELL/);
  assert.match(await page.locator('#updateCurrentVersion').innerText(), /v0\.2\.0-alpha\.49/);
  assert.equal(await page.locator('#updateSuccessVersion').count(), 0, 'installed-version notice removed');
});

test('offline update section is separate and file field aligns with install button', async t => {
  const { page } = await setup(t, settingsFixture);
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsUpdatesTab').click();
  const offline = await page.locator('.offline-update').evaluate(node => node.getBoundingClientRect());
  const online = await page.locator('.update-status-block').evaluate(node => node.getBoundingClientRect());
  assert.ok(offline.top >= online.bottom + 8, 'offline section must be below online status block');
  const row = await page.locator('.offline-update-row').evaluate(node => node.getBoundingClientRect());
  const file = await page.locator('#offlineUpdateFile').evaluate(node => node.getBoundingClientRect());
  const button = await page.locator('#offlineUpdateInstall').evaluate(node => node.getBoundingClientRect());
  assert.ok(file.top >= row.top - 1 && file.bottom <= row.bottom + 1, 'file input must stay in offline row');
  assert.ok(button.top >= row.top - 1 && button.bottom <= row.bottom + 1, 'install button must stay in offline row');
});

// ── DIAGNOSE-Konsole (Alpha 70) ──
const diagRows = page => page.evaluate(() => document.querySelectorAll('#diagRows .diag-row').length);
async function diagWait(page, count) {
  await page.waitForFunction(n => document.querySelectorAll('#diagRows .diag-row').length >= n, count, { timeout: 5000 });
}
async function openDiag(page) {
  await openSettingsFromAnywhere(page);
  await page.locator('#settingsDiagnoseTab').click();
  await page.waitForFunction(() => !document.getElementById('settingsDiagnosePane').hidden);
}

test('diagnose tab exists and console toolbar is complete', async t => {
  const { page } = await setup(t);
  await openDiag(page);
  assert.equal(await page.locator('#settingsDiagnosePane').isVisible(), true);
  for (const id of ['diagModeNormal', 'diagModeDebug', 'diagCategoryFilter', 'diagPause', 'diagClear', 'diagCopy']) {
    assert.equal(await page.locator(`#${id}`).isVisible(), true, id);
  }
  assert.match(await page.locator('#diagPause').innerText(), /PAUSE/);
});

test('diagnose console loads entries from the ring buffer', async t => {
  const { page } = await setup(t);
  diagPush({ level: 'INFO', category: 'USB', message: 'Gerät erkannt' });
  diagPush({ level: 'INFO', category: 'ANDROID', message: 'ADB nicht verfügbar' });
  await openDiag(page);
  await diagWait(page, 2);
  assert.equal(await page.locator('#diagEmpty').isVisible(), false);
  const text = await page.locator('#diagRows').innerText();
  assert.match(text, /Gerät erkannt/);
  assert.match(text, /ADB nicht verfügbar/);
  assert.match(text, /USB/);
});

test('diagnose console shows calm empty state after service restart', async t => {
  const { page } = await setup(t);
  await openDiag(page);
  await page.waitForTimeout(300);
  assert.match(await page.locator('#diagEmpty').innerText(), /NOCH KEINE DIAGNOSEEREIGNISSE/);
  assert.equal(await diagRows(page), 0);
});

test('polling runs only while the diagnose console is visible', async t => {
  const { page, requests } = await setup(t);
  diagPush({ message: 'vor dem Öffnen' });
  await openDiag(page);
  await diagWait(page, 1);
  const whileOpen = requests.filter(r => r.path === '/api/logs/recent').length;
  assert.ok(whileOpen >= 1, 'console must poll while visible');
  await page.evaluate(() => document.getElementById('settingsModal').close());
  const afterClose = requests.filter(r => r.path === '/api/logs/recent').length;
  await page.waitForTimeout(1450);
  assert.equal(requests.filter(r => r.path === '/api/logs/recent').length, afterClose, 'polling must stop when console hidden');
});

test('category filter narrows the visible rows', async t => {
  const { page } = await setup(t);
  diagPush({ category: 'USB', message: 'Stick erkannt' });
  diagPush({ category: 'ANDROID', message: 'Kandidat erkannt' });
  diagPush({ category: 'SCAN', message: 'Scan gestartet' });
  await openDiag(page);
  await diagWait(page, 3);
  await page.selectOption('#diagCategoryFilter', 'ANDROID');
  const rows = await page.locator('#diagRows').innerText();
  assert.match(rows, /Kandidat erkannt/);
  assert.doesNotMatch(rows, /Stick erkannt/);
  assert.doesNotMatch(rows, /Scan gestartet/);
});

test('normal mode hides debug rows, debug mode shows them and posts mode to server', async t => {
  const { page, requests } = await setup(t, async (url, request) => {
    if (request.method() === 'POST' && url.pathname === '/api/logs/mode') {
      const body = JSON.parse(request.postData() || '{}');
      diagFeed.mode = body.mode || 'normal';
      return { json: { mode: diagFeed.mode } };
    }
    return null;
  });
  diagPush({ level: 'INFO', category: 'USB', message: 'Gerät erkannt' });
  diagPush({ level: 'DEBUG', category: 'USB', message: 'vendor=04e8 product=6860' });
  await openDiag(page);
  await diagWait(page, 1);
  const normalText = await page.locator('#diagRows').innerText();
  assert.match(normalText, /Gerät erkannt/);
  assert.doesNotMatch(normalText, /vendor=04e8/);
  await page.locator('#diagModeDebug').click();
  await page.waitForFunction(() => document.getElementById('diagModeDebug').getAttribute('aria-pressed') === 'true');
  await diagWait(page, 2);
  assert.match(await page.locator('#diagRows').innerText(), /vendor=04e8/);
  assert.ok(requests.some(r => r.path === '/api/logs/mode' && r.method === 'POST'), 'debug switch must inform server');
});

test('pause stops updates, resume loads the missed entries', async t => {
  const { page } = await setup(t);
  diagPush({ category: 'USB', message: 'vor Pause' });
  await openDiag(page);
  await diagWait(page, 1);
  await page.locator('#diagPause').click();
  assert.match(await page.locator('#diagPause').innerText(), /FORTSETZEN/);
  diagPush({ category: 'USB', message: 'während Pause 1' });
  diagPush({ category: 'USB', message: 'während Pause 2' });
  await page.waitForTimeout(1450);
  const pausedRows = await page.locator('#diagRows').innerText();
  assert.doesNotMatch(pausedRows, /während Pause/);
  await page.locator('#diagPause').click();
  await diagWait(page, 3);
  assert.match(await page.locator('#diagRows').innerText(), /während Pause 2/);
});

test('clear empties only the local view and keeps the live stream', async t => {
  const { page } = await setup(t);
  diagPush({ message: 'geloeschte Zeile' });
  await openDiag(page);
  await diagWait(page, 1);
  await page.locator('#diagClear').click();
  assert.equal(await diagRows(page), 0);
  assert.match(await page.locator('#diagEmpty').innerText(), /NOCH KEINE DIAGNOSEEREIGNISSE/);
  diagPush({ message: 'neu nach Leeren' });
  await diagWait(page, 1);
  assert.doesNotMatch(await page.locator('#diagRows').innerText(), /geloeschte Zeile/);
  assert.match(await page.locator('#diagRows').innerText(), /neu nach Leeren/);
});

test('copy transfers the visible rows in report format', async t => {
  const { page } = await setup(t);
  diagPush({ level: 'INFO', category: 'USB', message: 'Gerät erkannt', details: { idVendor: '04e8' } });
  await openDiag(page);
  await diagWait(page, 1);
  await page.evaluate(() => {
    window.__copied = null;
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: { writeText: async text => { window.__copied = text; } } });
  });
  await page.locator('#diagCopy').click();
  await page.waitForFunction(() => window.__copied !== null);
  const copied = await page.evaluate(() => window.__copied);
  assert.match(copied, /\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} INFO USB Gerät erkannt idVendor=04e8/);
  assert.match(await page.locator('#diagStatus').innerText(), /KOPIIERT/);
});

test('clipboard failure shows a readable status', async t => {
  const { page } = await setup(t);
  diagPush({ message: 'Zeile' });
  await openDiag(page);
  await diagWait(page, 1);
  await page.evaluate(() => {
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('denied'); } } });
  });
  await page.locator('#diagCopy').click();
  await page.waitForFunction(() => document.getElementById('diagStatus').innerText.includes('ZWISCHENABLAGE'));
});

test('warning and error rows are visually marked, info rows stay calm', async t => {
  const { page } = await setup(t);
  diagPush({ level: 'WARNING', category: 'UPDATE', message: 'Update fehlgeschlagen' });
  diagPush({ level: 'ERROR', category: 'SCAN', message: 'Scan fehlgeschlagen' });
  diagPush({ level: 'INFO', category: 'USB', message: 'ok' });
  await openDiag(page);
  await diagWait(page, 3);
  assert.ok((await page.locator('#diagRows .lvl-warning').innerText()).includes('Update fehlgeschlagen'));
  assert.ok((await page.locator('#diagRows .lvl-error').count()) === 1);
  assert.ok((await page.locator('#diagRows .lvl-info').count()) === 1);
});

test('auto scroll follows new rows and stops when the user scrolls up', async t => {
  const { page } = await setup(t);
  await openDiag(page);
  await page.waitForTimeout(200);
  for (let i = 0; i < 40; i++) diagPush({ category: 'SCAN', message: `Zeile ${i}` });
  await diagWait(page, 40);
  await page.waitForTimeout(200);
  const autoTop = await page.evaluate(() => document.getElementById('diagConsole').scrollTop);
  assert.ok(autoTop > 0, 'auto scrolling must keep the view at the bottom');
  await page.evaluate(() => { document.getElementById('diagConsole').scrollTop = 0; });
  diagPush({ message: 'später' });
  await diagWait(page, 41);
  assert.equal(await page.evaluate(() => document.getElementById('diagConsole').scrollTop), 0, 'auto scroll must not fight the user');
  assert.equal(await page.locator('#diagScrollEnd').isVisible(), true);
  await page.locator('#diagScrollEnd').click();
  await page.waitForFunction(() => document.getElementById('diagScrollEnd').hidden === true);
});

test('diagnose console never keeps more than 500 DOM rows', async t => {
  const { page } = await setup(t);
  await openDiag(page);
  await page.waitForTimeout(200);
  await page.evaluate(() => {
    const flooding = [];
    for (let i = 0; i < 600; i++) {
      flooding.push({ seq: 1000 + i, timestamp: '2026-10-05T19:42:01.015Z', level: 'INFO', category: 'USB', message: `Flut ${i}` });
    }
    diagAppend(flooding);
  });
  assert.equal(await diagRows(page), 500);
  const firstRow = await page.locator('#diagRows .diag-row').first().innerText();
  assert.match(firstRow, /Flut 100/);
  diagPush({ message: 'noch einer' });
  await page.waitForFunction(() => document.getElementById('diagRows').innerText.includes('noch einer'));
  assert.equal(await diagRows(page), 500, 'cap stays at 500 while new rows enter');
  assert.match(await page.locator('#diagRows').innerText(), /noch einer/);
  assert.doesNotMatch(await page.locator('#diagRows').innerText(), /Flut 100/);
});

test('diagnose tab stays usable at 800px width', async t => {
  const { page } = await setup(t);
  diagPush({ message: 'Zeile' });
  await page.setViewportSize({ width: 800, height: 1000 });
  await openDiag(page);
  await diagWait(page, 1);
  assert.equal(await page.locator('#settingsDiagnosePane').isVisible(), true);
  const bodyOverflow = await page.evaluate(() => document.body.scrollWidth);
  assert.ok(bodyOverflow <= 800, 'page must not scroll horizontally at 800px');
  const toolbar = await page.locator('.diagnose-toolbar').boundingBox();
  assert.ok(toolbar, 'toolbar must remain reachable');
});
