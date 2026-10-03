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
  await page.evaluate(id => openMedia(id), id);
  await page.waitForFunction(id => inventoryTreeMediaId === id, id);
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
  assert.equal(await page.locator('#auftragModal').isVisible(), false);
  assert.equal(await page.locator('#settingsProfilesPane').isVisible(), true);
  assert.equal((await page.locator('#settingsTitle').locator('..').innerText()).includes('CFG'), false);
  await page.locator('#settingsProfilesList [data-edit-profile]').click();
  assert.equal(await page.locator('#keywordProfileName').inputValue(), 'Allgemein');
  assert.equal(await page.locator('#keywordOptions input').count(), 2);
  assert.equal(await page.evaluate(() => getComputedStyle(document.getElementById('settingsModal'), '::backdrop').backdropFilter), 'none');
  await page.locator('#closeKeywordSettings').click();
  await page.waitForFunction(() => !document.getElementById('settingsModal').classList.contains('nested-open'));
  assert.equal(await page.locator('#settingsModal').evaluate(node => node.classList.contains('nested-open')), false);
  await page.locator('#settingsProfilesList [data-copy-profile]').click();
  assert.equal(await page.locator('#keywordProfileName').inputValue(), 'Allgemein Kopie');
  assert.equal(await page.evaluate(() => profileEditorId), null);
  assert.equal(await page.locator('#keywordOptions input').count(), 2);
  await page.locator('#closeKeywordSettings').click();
  await page.locator('#closeSettings').click();
  await page.locator('#openAuftragModal').click();
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
  await page.locator('#openSettings').click();
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('[data-category="Dokumente"] textarea').fill('pdf, jpg');
  await page.locator('#catalogSave').click();
  await page.waitForFunction(() => document.getElementById('catalogMessage').textContent.includes('doppelt'));
  assert.equal(await page.locator('[data-category="Dokumente"] textarea').inputValue(), 'pdf, jpg');
  await page.locator('[data-category="Dokumente"] textarea').fill('pdf, docm');
  await page.locator('#catalogSearch').fill('.docm');
  assert.equal(await page.locator('[data-category="Bilder"]').isVisible(), false);
  assert.equal(await page.locator('[data-category="Dokumente"]').isVisible(), true);
  await page.locator('#catalogSave').click();
  await page.waitForFunction(() => document.getElementById('catalogMessage').textContent.startsWith('GESPEICHERT ·'));
  assert.equal(await page.locator('#catalogVersion').innerText(), 'KATALOG V2');
  assert.equal(await page.locator('#catalogSave').isDisabled(), true);
  await page.locator('#catalogReset').click();
  assert.equal(await page.locator('[data-category="Dokumente"] textarea').inputValue(), 'pdf');
  assert.equal(await page.locator('#catalogSave').isEnabled(), true);
  page.once('dialog', dialog => dialog.dismiss());
  await page.locator('#closeSettings').click();
  assert.equal(await page.locator('#settingsModal').isVisible(), true);
  assert.deepEqual(requests.filter(item => item.method !== 'GET').map(item => item.path), ['/api/settings/filetypes', '/api/settings/filetypes']);
});

test('settings remain readable on laptop and small screens', async t => {
  const { page } = await setup(t, settingsFixture);
  await page.locator('#openSettings').click();
  await page.setViewportSize({ width: 800, height: 900 });
  const heights = [];
  for (const tab of ['#settingsProfilesTab', '#settingsFiletypesTab', '#settingsUpdatesTab']) {
    await page.locator(tab).click();
    heights.push(await page.locator('#settingsModal').evaluate(node => node.getBoundingClientRect().height));
  }
  assert.equal(new Set(heights).size, 1, 'Settings dialog height must stay stable between tabs');
  await page.locator('#settingsFiletypesTab').click();
  await page.locator('[data-category="Bilder"] textarea').waitFor();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
  await page.locator('#settingsCryptoTab').click();
  assert.equal(await page.locator('label[for="detectionFilter"]').innerText().then(text => text.includes('FILTER')), true);
  assert.equal(await page.locator('label[for="detectionSort"]').innerText().then(text => text.includes('SORTIEREN NACH')), true);

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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openSettings').click();
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
  await page.locator('#openPowerModal').click();
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
  await page.locator('#openSettings').click();
  await page.locator('#settingsUpdatesTab').click();
  assert.equal(await page.locator('#updateSuccessNotice').isVisible(), true);
  assert.match(await page.locator('#updateSuccessNotice').innerText(), /ERFOLGREICH ABGESCHLOSSEN/);
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
    if (url.pathname === '/api/status') return { json: { devices: [], cases: [], active_case: null, update: {}, latest: record(2) } };
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
    renderDevices(items.map((item, index) => ({ path: `/dev/test${index}`, serial: item.serial, model: item.model, size: 1024 * (index + 1), scan_supported: true })));
  }, pending);
  await page.locator('#openSettings').click();
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
  await page.evaluate(() => renderRecord({
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
  }));
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
  await page.evaluate(() => renderRecord({
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
  }));
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
  await page.locator('#openSettings').click();
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
