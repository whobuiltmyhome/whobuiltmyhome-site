"""Create an offline review artifact using the actual frontend and release.

Only fetch transport is substituted with the exact released JSON, so the browser
can exercise the app without a server. This artifact is not a deployed release.
"""
import argparse
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'data/manifest.json').read_text())
assets = {'data/manifest.json': manifest}
for key in ('indexUrl', 'detailsUrl'):
    assets[manifest[key]] = json.loads((root / manifest[key]).read_text())
payload = json.dumps(assets, separators=(',', ':'), ensure_ascii=False).replace('<', '\\u003c')

analytics = (root / 'analytics.js').read_text()
analytics = re.sub(r"^import .*?;\s*", '', analytics, count=1, flags=re.S)
exports = re.findall(r'^export (?:function|const) (\w+)', analytics, re.M)
analytics = re.sub(r'^export ', '', analytics, flags=re.M)
config = (root / 'analytics-config.js').read_text().replace('export const ', 'const ')
module = '(function(){\n' + config + '\n' + analytics + '\nreturn {' + ','.join(exports) + '};\n})()'
app = (root / 'app.js').read_text()
pattern = r"import\s*\{([^}]+)\}\s*from\s*['\"]\./analytics\.js['\"];?"
match = re.search(pattern, app)
if not match:
    raise SystemExit('Expected explicit analytics import; preview bundler needs review.')
app = re.sub(pattern, lambda m: 'const {' + m.group(1) + '} = ' + module + ';', app, count=1)
fetch_adapter = '''
const reviewAssets = JSON.parse(document.getElementById('review-assets').textContent);
const fetch = async (input) => {
  const path = new URL(String(input), document.baseURI).pathname;
  const key = 'data/' + path.split('/data/').pop();
  if (!(key in reviewAssets)) throw new Error('Preview asset not found: ' + key);
  return {ok:true, json:async()=>structuredClone(reviewAssets[key])};
};
'''
html = (root / 'index.html').read_text()
html = html.replace('<link rel="stylesheet" href="./styles.css" />', '<style>' + (root/'styles.css').read_text() + '</style>')
html = html.replace('<script type="module" src="./app.js"></script>', '<script id="review-assets" type="application/json">' + payload + '</script>\n<script type="module">' + fetch_adapter + app.replace('</script', '<\\/script') + '</script>')
html = html.replace('<body>', '<body><div style="padding:8px 16px;background:#e9efe9;color:#234637;text-align:center;font:13px system-ui">Working preview · Not published · Analytics disabled</div>')
html = html.replace('href="./"', 'href="#explorer"')
html = html.replace('Copy record link</button>', 'Copy local preview link</button>')
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(html)
print(args.output.resolve())
