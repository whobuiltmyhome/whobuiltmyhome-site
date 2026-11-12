import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const origin='https://whobuiltmyhome.com';
const id='G-YG0TM1H4F3';
const config=await readFile('analytics-config.js','utf8');
assert.ok(config.includes(id));
const browser=await chromium.launch({headless:true});
const summaries=[];
try {
 for (const scenario of [
  {name:'invalid',path:'/',query:'?q=123+Synthetic+Street&pin=0000000000&utm_source=probe%40example.com'},
  {name:'valid',path:'/',query:'?utm_source=agent_outreach&utm_medium=email&utm_campaign=launch_2026_10'},
  {name:'guide',path:'/guides/find-home-builder-king-county/',query:''}
 ]) {
  const context=await browser.newContext();
  const page=await context.newPage();
  const events=[]; const violations=[]; const receipts=[];
  await page.route('**/analytics-config.js',r=>r.fulfill({contentType:'application/javascript',body:config.replace('enhancedMeasurementReviewed: false','enhancedMeasurementReviewed: true')}));
  await page.route(/https:\/\/[^/]*google-analytics\.com\/.*collect/,async route=>{
   const req=route.request();
   const u=new URL(req.url());
   for(const line of (req.postData()||'').split('\n')) {
    const p=new URLSearchParams(u.search);
    for(const [k,v] of new URLSearchParams(line)) p.set(k,v);
    const record=Object.fromEntries(p);
    const text=JSON.stringify(record);
    if(/Synthetic|0000000000|probe@|example\.com|view_search_results/i.test(text) ||
       p.get('tid')!==id || (p.has('dl') && p.get('dl')!==origin+scenario.path) ||
       (p.has('dr') && /[?#]/.test(p.get('dr')))) {
      violations.push('Unexpected destination, URL, event or synthetic private value');
      await route.abort(); return;
    }
    if(p.get('en')) events.push(record);
   }
   await route.continue();
  });
  page.on('response',r=>{if(/google-analytics\.com\/.*collect/.test(r.url())) receipts.push(r.status());});
  await page.goto(origin+scenario.path+scenario.query,{waitUntil:'networkidle',timeout:60000});
  if(scenario.path==='/') {
   await page.locator('#search').fill('Synthetic');
   await page.locator('#search-button').click();
  }
  await page.evaluate(async()=>{
    const a=await import('/analytics.js');
    // Exercise only exported, allowlisted events with synthetic input.
    a.trackPropertyOpen();
    a.trackSourceClick({source:'county_record',url:'https://example.com/private'});
    a.trackShare({pin:'0000000000',address:'123 Synthetic Street'});
    history.replaceState(null,'','?q=123+Synthetic+Street&pin=0000000000');
  });
  await page.waitForTimeout(8000);
  assert.deepEqual(violations,[],scenario.name);
  assert.ok(receipts.some(s=>s>=200&&s<300),'No successful Google collection response: '+scenario.name);
  assert.equal(events.filter(e=>e.en==='page_view').length,1,'Duplicate/missing pageview: '+scenario.name);
  for(const name of ['property_open','source_click','share']) assert.ok(events.some(e=>e.en===name),'Missing '+name);
  if(scenario.path==='/') assert.ok(events.some(e=>e.en==='search_performed'),'Missing search');
  const pv=events.find(e=>e.en==='page_view');
  if(scenario.name==='valid') {
   assert.equal(pv.cs,'agent_outreach'); assert.equal(pv.cm,'email'); assert.equal(pv.cn,'launch_2026_10');
  }
  if(scenario.name==='invalid') assert.equal(pv.cs,'unattributed');
  summaries.push({scenario:scenario.name,events:events.map(e=>e.en),http:receipts,canonicalPage:pv.dl,campaign:{source:pv.cs,medium:pv.cm,name:pv.cn}});
  await context.close();
 }
 console.log('ANALYTICS_VERIFICATION_PASS '+JSON.stringify(summaries));
} finally { await browser.close(); }
