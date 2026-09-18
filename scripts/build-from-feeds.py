import json,re,sys
from pathlib import Path
from datetime import datetime
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]; D=Path(sys.argv[1] if len(sys.argv)>1 else 'dumps')
products=json.load(open(ROOT/'products.json')); bc={x['barcode']:x for x in products}
chainlabels={'RamiLevy':'רמי לוי','Yohananof':'יוחננוף','Osherad':'אושר עד','Shufersal':'שופרסל','YaynotBitanAndCarrefour':'קרפור מרקט','ShukAhir':'שוק העיר','Keshet':'קשת טעמים'}
links={'RamiLevy':'https://url.retail.publishedprices.co.il/login','Yohananof':'https://url.publishedprices.co.il/login','Osherad':'https://url.publishedprices.co.il/login','Shufersal':'https://prices.shufersal.co.il/','YaynotBitanAndCarrefour':'https://prices.carrefour.co.il/','ShukAhir':'http://shuk-hayir.binaprojects.com/Main.aspx','Keshet':'https://url.publishedprices.co.il/login'}
citycodes={'4000':'חיפה','2500':'נשר','7600':'עכו','9100':'נהריה','1139':'כרמיאל','8000':'צפת','6700':'טבריה','7700':'עפולה','9200':'בית שאן','1061':'נצרת','8800':'שפרעם','874':'מגדל העמק','240':'יקנעם','6500':'חדרה','9300':'זכרון יעקב','7800':'פרדס חנה-כרכור','1020':'אור עקיבא','9500':'קרית ביאליק','9600':'קרית ים','6800':'קרית אתא','8200':'קרית מוצקין','2800':'קרית שמונה'}
def tx(e,n):
 r=e.xpath('./*[local-name()="'+n+'"]');return (r[0].text or '').strip() if r else ''
def getstorecity(d):
 code=d.get('City',''); name=d.get('StoreName','')
 aliases=[('חיפה','חיפה'),('נשר','נשר'),('טירת כרמל','טירת כרמל'),('עכו','עכו'),('נהריה','נהריה'),('כרמיאל','כרמיאל'),('צפת','צפת'),('טבריה','טבריה'),('עפולה','עפולה'),('בית שאן','בית שאן'),('נצרת','נצרת'),('שפרעם','שפרעם'),('מגדל העמק','מגדל העמק'),('יקנעם','יקנעם'),('חדרה','חדרה'),('זכרון','זכרון יעקב'),('פרדס חנה','פרדס חנה-כרכור'),('אור עקיבא','אור עקיבא'),('קרית שמונה','קרית שמונה'),('קריית שמונה','קרית שמונה')]
 match=next((c for k,c in aliases if k in name),None)
 return match or citycodes.get(code)
def latest(chain,kind,sid):
 xs=[]
 for p in (D/chain).glob(kind+'*.xml'):
  if re.search(r'-'+re.escape(sid)+r'-[0-9]{8}-',p.name):xs.append(p)
 return max(xs,key=lambda p:p.name) if xs else None
def prices(p):
 out={}
 if not p:return out
 for e in etree.parse(str(p)).xpath('.//*[local-name()="Item"]'):
  c=tx(e,'ItemCode')
  if c in bc:
   try:v=float(tx(e,'ItemPrice'))
   except:continue
   if 0<v<1000:out[c]=v
 return out
def promos(p):
 out={};now=datetime.now().replace(tzinfo=None)
 if not p:return out
 for e in etree.parse(str(p)).xpath('.//*[local-name()="Promotion"]'):
  try:s=datetime.fromisoformat(tx(e,'PromotionStartDateTime') or tx(e,'PromotionStartDate'));z=datetime.fromisoformat(tx(e,'PromotionEndDateTime') or tx(e,'PromotionEndDate'))
  except:continue
  if not s<=now<=z or (tx(e,'ClubID') or tx(e,'ClubId')) not in ('','0'):continue
  desc=tx(e,'PromotionDescription')
  for it in (e.xpath('.//*[local-name()="PromotionItem"]') or e.xpath('./*[local-name()="PromotionItems"]/*[local-name()="Item"]')):
   c=tx(it,'ItemCode')
   if c not in bc or (tx(it,'RewardType') or tx(e,'RewardType'))=='2':continue
   try:q=float(tx(it,'MinQty') or tx(e,'MinQty') or 1);total=float(tx(it,'DiscountedPrice') or tx(e,'DiscountedPrice'));unit=total/max(q,1)
   except:continue
   if unit>0 and (c not in out or unit<out[c]['unit']):out[c]={'unit':unit,'qty':q,'total':total,'desc':desc,'start':s.date().isoformat(),'end':z.date().isoformat()}
 return out
areas={}
for chain,label in chainlabels.items():
 sf=next(iter((D/chain).glob('Stores*.xml')),None)
 if not sf:continue
 for st in etree.parse(str(sf)).xpath('.//*[local-name()="Store"]'):
  d={x.tag.split('}')[-1]:(x.text or '').strip() for x in st};sid=d.get('StoreID','');city=getstorecity(d)
  if not city or (chain=='RamiLevy' and sid=='722') or d.get('Address','').lower()=='unknown':continue
  pf=latest(chain,'PriceFull',sid)
  if not pf:continue
  pp=prices(pf);pm=promos(latest(chain,'PromoFull',sid))
  if not pp:continue
  area=areas.setdefault(city,[{**x,'source':'https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations','prices':[],'error':None} for x in products]);by={x['barcode']:x for x in area}
  sub=d.get('StoreName') or city;addr=(d.get('Address') or '')+', '+city
  for c,v in pp.items():
   row={'chain':label,'store':sub,'address':addr,'price':f'{v:.2f}','promoPrice':None,'promo':None,'promoStart':None,'promoEnd':None,'promoQty':None,'promoTotal':None,'source':links[chain]}
   m=pm.get(c)
   if m and m['unit']<v:row.update({'promoPrice':f"{m['unit']:.2f}",'promo':m['desc'],'promoStart':m['start'],'promoEnd':m['end'],'promoQty':m['qty'],'promoTotal':f"{m['total']:.2f}"})
   by[c]['prices'].append(row)
for a in areas.values():
 for p in a:p['prices'].sort(key=lambda r:(float(r['promoPrice'] or r['price']),r['chain'],r['store']))
# only publish cities with at least 10 priced products; Afula keeps 21
areas={c:a for c,a in areas.items() if sum(bool(x['prices']) for x in a)>=10}
order=['חדרה','פרדס חנה-כרכור','זכרון יעקב','אור עקיבא','חיפה','נשר','קרית אתא','קרית ביאליק','קרית מוצקין','קרית ים','עכו','נהריה','כרמיאל','צפת','טבריה','עפולה','בית שאן','נצרת','שפרעם','מגדל העמק','יקנעם','קרית שמונה']
required={'חדרה','פרדס חנה-כרכור','זכרון יעקב','אור עקיבא','חיפה','נשר','קרית ביאליק','קרית ים','עכו','נהריה','כרמיאל','טבריה','עפולה','מגדל העמק','קרית שמונה'}
# Keep newly discovered cities offline until their branches are CHP-exact verified.
areas={c:areas[c] for c in order if c in required and c in areas}
if set(areas)!=required: raise SystemExit('feed validation failed: missing or extra required cities: '+str(required.symmetric_difference(areas)))
minimum={'חדרה':50,'פרדס חנה-כרכור':12,'זכרון יעקב':12,'אור עקיבא':10,'חיפה':35,'נשר':25,'קרית ביאליק':18,'קרית ים':10,'עכו':25,'נהריה':25,'כרמיאל':12,'טבריה':45,'עפולה':80,'מגדל העמק':22,'קרית שמונה':24}
for c,n in minimum.items():
 if sum(len(x['prices']) for x in areas[c])<n: raise SystemExit(f'feed validation failed: insufficient rows for {c}')
# Merge manually verified rows and promo corrections after every official rebuild.
# These rows were branch/product cross-checked against clean CHP evidence. Exact
# existing branch matches are updated; verified fallback chains are appended.
overrides=json.load(open(ROOT/'scripts/verified-overrides.json'))
for o in overrides:
 city=o['city']; c=o['barcode']; row=o['row']
 if city not in areas: raise SystemExit(f'override city missing: {city}')
 product=next((x for x in areas[city] if x['barcode']==c),None)
 if not product: raise SystemExit(f'override product missing: {city} {c}')
 exact=[x for x in product['prices'] if x['chain']==row['chain'] and x['store']==row['store']]
 if exact:
  if len(exact)!=1: raise SystemExit(f'ambiguous override branch: {city} {c} {row["chain"]} {row["store"]}')
  exact[0].update(row)
 elif row['chain'] in ('קשת טעמים','ויקטורי','מחסני השוק בשבילך','סופר ספיר','קרפור מרקט','שוק העיר'):
  product['prices'].append(row)
 else:
  raise SystemExit(f'override branch disappeared: {city} {c} {row["chain"]} {row["store"]}')
 product['prices'].sort(key=lambda r:(float(r['promoPrice'] or r['price']),r['chain'],r['store']))

data={'updatedAt':datetime.now().astimezone().isoformat(),'refreshStatus':'success','defaultArea':'עפולה','source':'קובצי שקיפות המחירים של הרשתות (PriceFull + PromoFull)','areas':areas}
json.dump(data,open(ROOT/'docs/data.feed-preview.json','w'),ensure_ascii=False,indent=2)
for c,a in areas.items():print(c,sum(bool(x['prices']) for x in a),sum(len(x['prices']) for x in a),sum(bool(r['promoPrice']) for x in a for r in x['prices']))
