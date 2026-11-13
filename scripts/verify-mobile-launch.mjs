import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const origin = 'https://whobuiltmyhome.com';
const copyVersion = '20261113-ui';
const retiredDetailCopy = /Company match group|reviewed company labels|No additional data notes listed|independently verified construction|investigate the association/;
const browser = await chromium.launch();

try {
  for (const width of [375, 390, 430]) {
    const context = await browser.newContext({
      viewport: { width, height: 844 }, isMobile: true, hasTouch: true,
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${origin}/?v=${copyVersion}`, { waitUntil: 'networkidle' });
    // A push may start this check while Pages is still publishing. Allow one
    // fresh navigation after that deployment window, rather than testing old JS.
    if (!(await page.locator('script[type=module]').getAttribute('src')).includes(copyVersion)) {
      await page.waitForTimeout(60000);
      await page.goto(`${origin}/?v=${copyVersion}-${Date.now()}`, { waitUntil: 'networkidle', timeout: 30000 });
    }
    assert.ok((await page.locator('script[type=module]').getAttribute('src')).includes(copyVersion), 'new copy release is live');
    await page.waitForFunction(() => document.querySelector('#coverage-count').textContent === '16,025');
    const checkWidth = async label => assert.ok(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
      `${label}: horizontal overflow at ${width}px`,
    );
    const checkDialog = async () => {
      await page.locator('.detail-source-links a').waitFor();
      assert.ok(await page.locator('#property-dialog').isVisible());
      const text = await page.locator('#detail-body').innerText();
      assert.ok(text.includes('King County property record'));
      assert.ok(text.includes('Builder not confirmed'));
      assert.doesNotMatch(await page.locator('#detail-body').textContent(), retiredDetailCopy);
      assert.equal(await page.locator('.detail-evidence').evaluate(el => el.open), false);
      await page.locator('.detail-evidence summary').click();
      assert.ok(await page.locator('.recording-list li').first().isVisible());
      const recordURL = new URL(await page.locator('.detail-source-links a').getAttribute('href'));
      assert.equal(recordURL.hostname, 'blue.kingcounty.com');
      assert.equal(recordURL.searchParams.get('ParcelNbr'), new URL(page.url()).searchParams.get('pin'));
      const correctionURL = new URL(await page.locator('.detail-actions a[href^="mailto:"]').getAttribute('href'));
      assert.equal(correctionURL.pathname, 'hello@whobuiltmyhome.com');
      await checkWidth('home details');
      await page.locator('.detail-evidence summary').click();
    };

    await checkWidth('home');
    await page.locator('#collection').selectOption('buchan');
    await page.waitForFunction(() => document.querySelector('#result-summary').textContent.includes('2,975'));
    await page.locator('#toggle-map').click();
    await page.waitForFunction(() => /2,975/.test(document.querySelector('#map-status').textContent), null, { timeout: 60000 });
    await page.locator('#fit-map').click();
    await checkWidth('map');
    await page.locator('#search').fill('113 259TH AVE NE');
    await page.locator('#search-button').click();
    await page.waitForFunction(() => document.querySelectorAll('#property-list button').length === 1);
    await page.locator('#property-list button').click();
    await checkDialog();
    await page.locator('#copy-property-link').click();
    await page.waitForFunction(() => document.querySelector('#copy-status').textContent.includes('copied'));
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    const copiedURL = new URL(copied);
    assert.equal(copiedURL.origin, origin);
    assert.deepEqual([...copiedURL.searchParams.keys()], ['pin']);
    assert.ok(copiedURL.searchParams.get('pin'));
    await page.locator('#close-detail').click();
    await page.locator('#clear-filters').click();
    await page.waitForFunction(() => document.querySelector('#result-summary').textContent.includes('16,025'));
    await page.locator('#show-list').click();

    for (const value of ['year-asc', 'year-desc', 'city', 'address']) {
      await page.locator('#sort').selectOption(value);
      assert.equal(await page.locator('#property-list button').count(), 20);
    }
    const presets = page.locator('[data-year-from]');
    for (let index = 0; index < await presets.count(); index++) {
      const preset = presets.nth(index);
      const from = await preset.getAttribute('data-year-from');
      const to = await preset.getAttribute('data-year-to') || '';
      await preset.click();
      assert.equal(await page.locator('#year-from').inputValue(), from);
      assert.equal(await page.locator('#year-to').inputValue(), to);
    }
    await page.locator('#year-from').fill('2020');
    await page.locator('#year-from').press('Tab');
    await page.locator('#year-to').fill('2000');
    await page.locator('#year-to').press('Tab');
    assert.ok(await page.locator('#filter-error').isVisible());
    await page.locator('#clear-filters').click();
    await page.locator('#search').fill('no-such-address-ever');
    assert.ok(await page.locator('#empty-state').isVisible());
    await page.locator('#reset-empty').click();

    const contact = await page.locator('#contact a').getAttribute('href');
    assert.ok(contact.startsWith('mailto:hello@whobuiltmyhome.com?'));
    for (const selector of ['.source-note', '#project', '#privacy']) {
      await page.locator(`${selector} summary`).click();
      assert.equal(await page.locator(selector).evaluate(el => el.open), true);
      await checkWidth(selector);
      await page.locator(`${selector} summary`).click();
    }
    await page.goto(copied, { waitUntil: 'networkidle' });
    await checkDialog();
    await page.locator('#close-detail').click();

    if (width === 390) {
      const builders = await page.locator('#collection option').evaluateAll(options => options.filter(option => option.value && !option.disabled).map(option => ({ id: option.value, name: option.textContent })));
      assert.equal(builders.length, 9);
      for (const builder of builders) {
        await page.locator('#collection').selectOption(builder.id);
        await page.locator('#property-list button').first().click();
        await checkDialog();
        assert.ok((await page.locator('.detail-facts').innerText()).includes(builder.name));
        await page.locator('#close-detail').click();
      }
      const routes = [
        '/builders/buchan/', '/builders/burnstead/', '/builders/quadrant/',
        '/guides/find-home-builder-king-county/',
      ];
      for (const route of routes) {
        await page.goto(`${origin}${route}?v=${copyVersion}`, { waitUntil: 'networkidle' });
        assert.equal(await page.locator('h1').count(), 1);
        assert.doesNotMatch(await page.locator('main').innerText(), /Explore .*connections|Company match group|Go a little deeper/);
        await checkWidth(route);
        const recordDetails = page.locator('details.research-section');
        if (await recordDetails.count()) {
          await recordDetails.locator('summary').click();
          assert.equal(await recordDetails.evaluate(el => el.open), true);
          await checkWidth(route + ' records');
        }
        const searchLink = page.locator('.research-action .button');
        assert.equal(await searchLink.count(), 1, `${route} has a search button`);
        await searchLink.click();
        await page.waitForFunction(() => document.querySelector('#coverage-count')?.textContent === '16,025');
        assert.equal(new URL(page.url()).pathname, '/');
      }
      await page.goto(`${origin}/?pin=0000000000`, { waitUntil: 'networkidle' });
      await page.locator('#property-dialog').waitFor();
      assert.equal(await page.locator('#copy-property-link').isDisabled(), true);
      await page.locator('#close-detail').click();
      console.log('UI_AUDIT_PASS ' + JSON.stringify({ builders: 9, linkedPages: routes.length, invalidShare: true }));
    }

    assert.deepEqual(errors, []);
    console.log('MOBILE_PASS ' + JSON.stringify({ width, search: true, buchan: 2975, map: true, details: true, clipboard: true, sharedLink: true, contactLink: true, sort: true, yearFilters: true, emptyState: true, disclosures: true, noHorizontalOverflow: true }));
    await context.close();
  }
} finally {
  await browser.close();
}
