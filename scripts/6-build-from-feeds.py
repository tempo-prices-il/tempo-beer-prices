#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
from datetime import datetime, timezone
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
DUMPS=Path(sys.argv[1] if len(sys.argv)>1 else 'dumps')
products=json.loads((ROOT/'products.json').read_text())
barcodes={p['barcode']:p for p in products}
stores={
 ('RamiLevy','011'):('רמי לוי','עפולה','יהושוע חנקין 14, עפולה'),
 ('RamiLevy','722'):('סופר קופיקס','חטיבה תשע עפולה','חטיבה תשע 34, עפולה'),
 ('Shufersal','499'):('יש חסד','עפולה עילית','פנחס רוזן 24, עפולה'),
 ('Shufersal','397'):('שופרסל אקספרס','פארק עפולה','רובע יזרעאל, עפולה'),
 ('Shufersal','251'):('יוניברס','עפולה - כורש','כורש 5, עפולה'),
 ('Shufersal','218'):('יוניברס','עפולה - יצחק רבין','שד׳ יצחק רבין 5, עפולה'),
 ('Yohananof','037'):('יוחננוף','עפולה','קהילת ציון 30, עפולה'),
 ('Osherad','019'):('אושר עד','עפולה','חיים לסקוב, עפולה'),
}
source_links={
 'RamiLevy':'https://url.retail.publishedprices.co.il/login',
 'Shufersal':'https://prices.shufersal.co.il/',
 'Yohananof':'https://url.publishedprices.co.il/login',
 'Osherad':'https://url.publishedprices.co.il/login',
}
def latest(chain,kind,sid):
 xs=[p for p in (DUMPS/chain).glob(kind+'*.xml') if re.search(r'-'+re.escape(sid)+r'-',p.name)]
 return max(xs,key=lambda p:p.name) if xs else None
def tx(el,name):
 r=el.xpath('./*[local-name()="'+name+'"]');return (r[0].text or '').strip() if r else ''
def parse_price(p):
 out={}
 if not p:return out
 root=etree.parse(str(p)).getroot()
 for el in root.xpath('.//*[local-name()="Item"]'):
  code=tx(el,'ItemCode')
  if code in barcodes:
   try: price=float(tx(el,'ItemPrice'))
   except: continue
   if 0<price<1000:out[code]=price
 return out
def parse_promos(p,now):
 out={}
 if not p:return out
 root=etree.parse(str(p)).getroot()
 for prom in root.xpath('.//*[local-name()="Promotion"]'):
  start=tx(prom,'PromotionStartDateTime');end=tx(prom,'PromotionEndDateTime')
  try:
   s=datetime.fromisoformat(start);e=datetime.fromisoformat(end)
   if not(s<=now.replace(tzinfo=None)<=e):continue
  except:continue
  club=tx(prom,'ClubID')
  if club not in ('','0'):continue
  desc=tx(prom,'PromotionDescription')
  for it in prom.xpath('.//*[local-name()="PromotionItem"]'):
   code=tx(it,'ItemCode')
   if code not in barcodes or tx(it,'RewardType')=='2':continue
   try: qty=float(tx(it,'MinQty') or '1'); total=float(tx(it,'DiscountedPrice')); unit=total/max(qty,1)
   except:continue
   if unit<=0:continue
   rec={'promoPrice':round(unit,2),'promoTotal':round(total,2),'promoQty':qty,'promo':desc,'promoStart':start[:10],'promoEnd':end[:10]}
   if code not in out or unit<out[code]['promoPrice']:out[code]=rec
 return out
now=datetime.now(timezone.utc).astimezone()
area=[{**p,'source':'https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations','prices':[],'error':None} for p in products]
bycode={p['barcode']:p for p in area}
for (chain,sid),(chain_name,store,address) in stores.items():
 prices=parse_price(latest(chain,'PriceFull',sid)); promos=parse_promos(latest(chain,'PromoFull',sid),now)
 for code,regular in prices.items():
  r={'chain':chain_name,'store':store,'address':address,'price':f'{regular:.2f}','promoPrice':None,'promo':None,'promoStart':None,'promoEnd':None,'promoQty':None,'promoTotal':None,'source':source_links[chain]}
  if code in promos and promos[code]['promoPrice']<regular:
   m=promos[code];r.update({**m,'promoPrice':f"{m['promoPrice']:.2f}",'promoTotal':f"{m['promoTotal']:.2f}"})
  bycode[code]['prices'].append(r)
for p in area:
 p['prices'].sort(key=lambda r:(float(r['promoPrice'] or r['price']),r['chain'],r['store']))
data={'updatedAt':now.isoformat(),'refreshStatus':'success','defaultArea':'עפולה','source':'קובצי שקיפות המחירים של הרשתות (PriceFull + PromoFull)','areas':{'עפולה':area}}
out=ROOT/'docs/data.feed-preview.json';out.write_text(json.dumps(data,ensure_ascii=False,indent=2))
coverage=sum(bool(p['prices']) for p in area);rows=sum(len(p['prices']) for p in area);promos=sum(bool(r['promoPrice']) for p in area for r in p['prices'])
print(json.dumps({'output':str(out),'products_with_prices':coverage,'products_total':len(area),'rows':rows,'active_promos':promos},ensure_ascii=False))
if coverage<18 or rows<60: raise SystemExit('feed validation failed: insufficient coverage')
