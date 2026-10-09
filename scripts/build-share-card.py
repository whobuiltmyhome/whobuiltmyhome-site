"""Build the exact, text-led sharing card using the site's established palette."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'social-preview.png'
OUT.parent.mkdir(exist_ok=True)
S = 2
im = Image.new('RGB', (1200*S, 630*S), '#f7f6f0')
d = ImageDraw.Draw(im)
FONT = Path('/usr/share/fonts/truetype/dejavu')
def f(size, serif=False, bold=False):
    name = 'DejaVuSerif' if serif else 'DejaVuSans'
    if bold: name += '-Bold'
    return ImageFont.truetype(str(FONT / (name + '.ttf')), size*S)
def text(x,y,s,size=22,fill='#21352e',serif=False,bold=False):
    d.text((x*S,y*S),s,font=f(size,serif,bold),fill=fill)
def line(points,fill='#214f40',width=3):
    d.line([(x*S,y*S) for x,y in points],fill=fill,width=width*S)
def box(coords,fill,outline=None,radius=14):
    d.rounded_rectangle(tuple(int(v*S) for v in coords),radius=radius*S,fill=fill,outline=outline,width=2*S)

line([(64,78),(83,60),(102,78)])
line([(70,75),(70,97),(96,97),(96,75)])
text(120,65,'Who Built My Home?',25,bold=True)
line([(64,128),(1136,128)],fill='#d9dfd4',width=1)
text(64,165,'KING COUNTY, WASHINGTON',15,fill='#53635c',bold=True)
text(60,211,"Your home's story",54,serif=True)
text(60,284,'starts with evidence.',49,fill='#214f40',serif=True)
text(64,381,'Search an address.',23)
text(64,418,'Explore builder connections.',23)
text(64,486,'Free to explore. No account needed.',18,fill='#53635c')

box((796,181,1136,496),'#fffefa','#d9dfd4',18)
text(825,211,'FOLLOW THE RECORDS',13,fill='#53635c',bold=True)
for y,label,sub in [(262,'Find a home','Address and county parcel'),(334,'Explore connections','Reviewed company matches'),(406,'See the evidence','Official county sources')]:
    d.ellipse((825*S,(y+4)*S,843*S,(y+22)*S),fill='#e9eee5')
    line([(830,y+13),(834,y+17),(841,y+8)],width=2)
    text(857,y,label,18,bold=True)
    text(857,y+29,sub,13,fill='#53635c')
line([(64,548),(1136,548)],fill='#d9dfd4',width=1)
text(64,571,'whobuiltmyhome.com',19,fill='#214f40',bold=True)
text(568,575,'County associations; original builder may be unconfirmed.',13,fill='#53635c')
im.resize((1200,630),Image.Resampling.LANCZOS).quantize(colors=128).save(OUT,optimize=True)
print(OUT)
