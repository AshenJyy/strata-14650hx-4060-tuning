import ctypes, hashlib, json, os, re, sys, urllib.request
from pathlib import Path

root=Path(r'${STRATA_ROOT}'); work=root/'custom/r3'
os.environ.update({'STRATA_DATA_DIR':str(root),'STRATA_COMPONENTS_DIR':str(root/'components'),
                  'STRATA_HOME':str(root/'state'),'TEMP':str(root/'temp'),'TMP':str(root/'temp')})
sys.path.insert(0,str(root/'terminal/current'))
from strata_control import profiles, runtime
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetCurrentProcess.restype=ctypes.c_void_p
k.SetProcessAffinityMask.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
if not k.SetProcessAffinityMask(k.GetCurrentProcess(),16777215): raise ctypes.WinError(ctypes.get_last_error())
name='launch-gyro-s-abliterated-8k'; mode=sys.argv[1]
assert re.fullmatch(r'[a-zA-Z0-9_-]+',mode)
target=work/'configs'/(mode+'.json')
cfg=json.loads(target.read_text(encoding='utf-8-sig'))
assert cfg['host']=='127.0.0.1' and cfg['port']==8082
assert cfg['model_name']=='qwen3.8-flash-next-gyro-s-abliterated'
assert cfg['env']['STRATA_ROUTE_TAIL_SKIP']=='0' and cfg['env']['STRATA_ROUTE_PRIOR']=='0'
release=Path(cfg['exe']).parent
assert release.parent==root/'custom/releases'
manifest=json.loads((release/'BUILD.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    with (release/item['path']).open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==item['sha256'],item['path']

def stop():
    if runtime.status(name).get('state') not in ('stopped','stale'):
        r=runtime.stop(name,timeout=60)
        if not r.get('ok'): raise RuntimeError('Cannot stop engine: '+str(r.get('error')))

def select(path):
    proposal,revision=profiles.propose_source(name,str(path))
    profiles.save(name,proposal,expected_revision=revision,expected_source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

stop();select(target)
try:
    result=runtime.start(name,wait=60)
    if not result.get('ok'): raise RuntimeError('Start failed: '+str(result.get('error')))
    key=(root/'local-api-key.txt').read_text().strip()
    req=urllib.request.Request('http://127.0.0.1:8082/v1/load',data=b'{}',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as response: json.load(response)
    print(json.dumps({'mode':mode,'exe':cfg['exe'],'loaded':True}),flush=True)
except Exception:
    stop(); select(root/'install/strata-gyro-s-abliterated-14650hx-4060-r2.json')
    runtime.start(name,wait=60)
    raise
