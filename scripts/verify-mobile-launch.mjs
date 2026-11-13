import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch();
try {
 for (const width of [375, 390, 430]) {
  const context = await browser.newContext({viewport:{width,height:844},isMobile:true,hasTouch:true,permissions:['clipboard-read','clipboard-write']});
  const page = await context.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://whobuiltmyhome.com/',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#coverage-count').textContent==='16,025');
  const checkWidth=async label=>assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),label+' horizontal overflow at '+width);
  await checkWidth('home');
  await page.locator('#collection').selectOption('buchan');
  await page.waitForFunction(()=>document.querySelector('#result-summary').textContent.includes('2,975'));
  await page.locator('#toggle-map').click();
  await page.waitForFunction(()=>/2,975/.test(document.querySelector('#map-status').textContent),null,{timeout:60000});
  await checkWidth('map');
  await page.locator('#search').fill('113 259TH AVE NE');
  await page.locator('#search-button').click();
  await page.waitForFunction(()=>document.querySelectorAll('#property-list button').length===1);
  await page.locator('#property-list button').click();
  await page.locator('.detail-source-links a').first().waitFor();
  assert.ok(await page.locator('#property-dialog').isVisible());
  await page.locator('#copy-property-link').click();
  await page.waitForFunction(()=>document.querySelector('#copy-status').textContent.includes('copied'));
  const copied=await page.evaluate(()=>navigator.clipboard.readText());
  const u=new URL(copied);
  assert.equal(u.origin,'https://whobuiltmyhome.com');
  assert.deepEqual([...u.searchParams.keys()],['pin']);
  assert.ok(u.searchParams.get('pin'));
  await checkWidth('details');
  await page.locator('#close-detail').click();
  await page.locator('#clear-filters').click();
  await page.waitForFunction(()=>document.querySelector('#result-summary').textContent.includes('16,025'));
  const contact=await page.locator('#contact a').getAttribute('href');
  assert.ok(contact.startsWith('mailto:hello@whobuiltmyhome.com?'));
  await page.goto(copied,{waitUntil:'networkidle'});
  await page.locator('.detail-source-links a').first().waitFor();
  assert.ok(await page.locator('#property-dialog').isVisible());
  assert.deepEqual(errors,[]);
  console.log('MOBILE_PASS '+JSON.stringify({width,search:true,buchan:2975,map:true,details:true,clipboard:true,sharedLink:true,contactLink:true,noHorizontalOverflow:true}));
  await context.close();
 }
} finally { await browser.close(); }
