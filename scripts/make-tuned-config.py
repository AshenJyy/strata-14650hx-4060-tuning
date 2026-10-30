"""Derive a new config from a working r2 install; never modify or launch the original."""
import argparse,json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.base.resolve()==a.out.resolve():p.error('Choose a different output file; the base is preserved.')
cfg=json.loads(a.base.read_text(encoding='utf-8-sig'))
args=cfg.get('user_args',[])
if not isinstance(args,list):p.error('Expected user_args as a JSON array.')
options={'--pool-cores':'2,4,6,8,10,12,14,16-23','--pool-workers':'15',
         '--pool-affinity':'all','--host-core':'first','--pool-tasks':'0'}
new=[];i=0
while i<len(args):
    flag=args[i]
    if flag in options:
        if i+1>=len(args):p.error('Missing argument for '+flag)
        i+=2
    elif any(flag.startswith(k+'=') for k in options):i+=1
    else:new.append(flag);i+=1
for flag,value in options.items():new.extend((flag,value))
cfg['user_args']=new
cfg['pool_cores']=options['--pool-cores']
cfg.setdefault('env',{}).update(STRATA_POOL_UMWAIT='10000',STRATA_POOL_UMWAIT_ESC='20000')
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('x',encoding='utf-8') as f:json.dump(cfg,f,ensure_ascii=False,indent=2)
print('Wrote a new configuration. No service was restarted. Verify the CPU numbering before use.')
