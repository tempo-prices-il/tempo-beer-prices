#!/usr/bin/env python3
import os,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
work=Path(tempfile.mkdtemp(prefix='tempo-feeds-')); repo=work/'scrapers'; dumps=work/'dumps'
subprocess.run(['git','clone','--depth','1','https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers.git',str(repo)],check=True)
subprocess.run([sys.executable,'-m','pip','install','-q','-r',str(repo/'requirements.txt')],check=True)
# Full set of branches used by the validated 15-city publication. The builder
# validates every required city and minimum row counts before atomic publish.
ids='001|005|011|014|015|019|020|022|023|028|029|030|032|036|037|038|039|044|057|058|064|066|071|095|096|097|111|121|140|142|147|159|189|195|211|218|226|251|281|297|302|306|312|314|319|326|327|333|336|339|342|359|361|365|368|384|397|418|429|435|439|441|453|468|499|716|717|727|734'
code=f'''from il_supermarket_scarper import ScarpingTask\nfrom il_supermarket_scarper.utils.files.file_types import FileTypesFilters\nfrom il_supermarket_scarper.utils import _now\nchains=["RAMI_LEVY","SHUFERSAL","YOHANANOF","OSHER_AD"]\nrx=r"(?i)(Stores.*|(?:PriceFull|PromoFull).*-({ids})-[0-9]{{8}}-.*)"\ns=ScarpingTask(output_configuration={{"output_mode":"disk"}},status_configuration={{"database_type":"json","base_path":"status"}},multiprocessing=4,enabled_scrapers=chains,files_types=[FileTypesFilters.STORE_FILE.name,FileTypesFilters.PRICE_FULL_FILE.name,FileTypesFilters.PROMO_FULL_FILE.name],file_name_regex=rx,timeout_in_seconds=1500)\ns.start(limit=None,when_date=_now());s.join()\n'''
env={**os.environ,'PYTHONPATH':str(repo)}
subprocess.run([sys.executable,'-c',code],cwd=work,env=env,check=True,timeout=1600)
# Kiryat Yam currently depends on Osher Ad branch 029. Its FTP listing can
# lag the other feeds, so retry with backoff before validation. Never publish
# without it: the builder's required-city check keeps the old dataset intact.
critical='''from il_supermarket_scarper import ScarpingTask\nfrom il_supermarket_scarper.utils.files.file_types import FileTypesFilters\nfrom il_supermarket_scarper.utils import _now\ns=ScarpingTask(output_configuration={"output_mode":"disk"},status_configuration={"database_type":"json","base_path":"critical-status"},multiprocessing=1,enabled_scrapers=["OSHER_AD"],files_types=[FileTypesFilters.STORE_FILE.name,FileTypesFilters.PRICE_FULL_FILE.name,FileTypesFilters.PROMO_FULL_FILE.name],file_name_regex=r"(?i)(Stores.*|(?:PriceFull|PromoFull).*-029-[0-9]{8}-.*)",timeout_in_seconds=240)\ns.start(limit=None,when_date=None);s.join()\n'''
for attempt in range(3):
 subprocess.run([sys.executable,'-c',critical],cwd=work,env=env,check=True,timeout=300)
 if any((dumps/'Osherad').glob('PriceFull*-029-*.xml')): break
 if attempt<2:
  import time; time.sleep(180)
subprocess.run([sys.executable,str(root/'scripts/build-from-feeds.py'),str(dumps)],cwd=root,check=True)
preview=root/'docs/data.feed-preview.json'; target=root/'docs/data.json'
os.replace(preview,target)
print('Validated full 15-city PriceFull and PromoFull refresh published atomically.')
