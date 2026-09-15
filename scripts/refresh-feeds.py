#!/usr/bin/env python3
import os,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
work=Path(tempfile.mkdtemp(prefix='tempo-feeds-')); repo=work/'scrapers'; dumps=work/'dumps'
subprocess.run(['git','clone','--depth','1','https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers.git',str(repo)],check=True)
subprocess.run([sys.executable,'-m','pip','install','-q','-r',str(repo/'requirements.txt')],check=True)
code='''from il_supermarket_scarper import ScarpingTask\nfrom il_supermarket_scarper.utils.files.file_types import FileTypesFilters\nfrom il_supermarket_scarper.utils import _now\nchains=["RAMI_LEVY","SHUFERSAL","YOHANANOF","OSHER_AD"]\nrx=r"(?i)(Stores|PriceFull|PromoFull).*-(011|037|019|499|397|251|218)-.*"\ns=ScarpingTask(output_configuration={"output_mode":"disk"},status_configuration={"database_type":"json","base_path":"status"},multiprocessing=4,enabled_scrapers=chains,files_types=[FileTypesFilters.STORE_FILE.name,FileTypesFilters.PRICE_FULL_FILE.name,FileTypesFilters.PROMO_FULL_FILE.name],file_name_regex=rx,timeout_in_seconds=1500)\ns.start(limit=None,when_date=_now());s.join()\n'''
env={**os.environ,'PYTHONPATH':str(repo)}
subprocess.run([sys.executable,'-c',code],cwd=work,env=env,check=True,timeout=1600)
subprocess.run([sys.executable,str(root/'scripts/build-from-feeds.py'),str(dumps)],cwd=root,check=True)
preview=root/'docs/data.feed-preview.json'; target=root/'docs/data.json'
# Atomic publish only after parser validation completed successfully.
os.replace(preview,target)
print('Validated PriceFull and PromoFull refresh published atomically.')
