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
  assert.deepEqual(await labels(), ['SICHT-1', 'SICHT-2', 'SICHT-3', 'SICHT-8', 'SICHT-10']);
  assert.deepEqual(await page.locator('#caseMedia tr td:first-child').allTextContents(), await labels());
  await page.evaluate(() => { devices = [{ serial: 'TEST-10' }, { serial: 'TEST-2' }]; renderMediaCards(currentCaseMedia); });
  assert.deepEqual(await page.locator('#mediaCards .media-card > strong').allTextContents(), ['SICHT-2', 'SICHT-10']);
  assert.deepEqual(await labels(), ['SICHT-1', 'SICHT-3', 'SICHT-8']);
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
  assert.equal(await page.locator('#archiveUnknownCount').getAttribute('class'), '');
  await open(page, 2);
  assert.equal(await page.locator('#archiveStatus').isVisible(), false);
});
