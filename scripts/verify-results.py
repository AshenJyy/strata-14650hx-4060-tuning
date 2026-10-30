"""Offline consistency checks for the published measurements; no model requests."""
import hashlib,json,math,statistics
from pathlib import Path

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'data/export-manifest.json').read_text(encoding='utf-8'))
for f in manifest['files']:
    p=root/f['path']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==f['export_sha256'],f['path']
    if f['exact_copy']:assert f['source_sha256']==f['export_sha256']

def check(j):
    assert j['completed'] and j['restored']
    for name,summary in j['summary'].items():
        rr=[r for s in j['sessions'] if s['mode']==name for r in s['runs']]
        assert rr and all(r['usage']['completion_tokens']==j['method']['measured_tokens'] for r in rr)
        measured={
            'median_tps':statistics.median(r['server_metrics']['decode_tok_s'] for r in rr),
            'median_ttft':statistics.median(r['first_token_seconds'] for r in rr),
            'wall_tps':sum(r['usage']['completion_tokens'] for r in rr)/sum(r['wall_seconds'] for r in rr)}
        for field,value in measured.items():assert math.isclose(value,summary[field],rel_tol=1e-10),(name,field)
        for case,value in summary['by_workload'].items():
            actual=statistics.median(r['server_metrics']['decode_tok_s'] for r in rr if r['id']==case)
            assert math.isclose(value,actual,rel_tol=1e-10),(name,case)
    return j

data={name:check(json.loads((root/'data'/name).read_text(encoding='utf-8')))
      for name in ('final-results.json','main-formal.json','pgo-confirmation.json')}
check(json.loads((root/'data/r2/experiments/20261030-125657/results.json').read_text(encoding='utf-8')))
assert len(data['final-results.json']['sessions'])==sum(len(data[k]['sessions']) for k in ('main-formal.json','pgo-confirmation.json'))
build=json.loads((root/'data/builds/r2.json').read_text(encoding='utf-8'))
assert hashlib.sha256((root/'patches/r2.patch').read_bytes()).hexdigest()==build['patch_sha256']
for name in ('parity.json','parity-r3pgo.json'):
    parity=json.loads((root/'data/r3'/name).read_text(encoding='utf-8'))
    assert all(v['bitwise_equal'] and v['returncode']==0 for v in parity['variants'].values())
failed=[p for stage in ('r2','r3') for p in (root/'data'/stage/'experiments').glob('*/results.json')
        if not json.loads(p.read_text(encoding='utf-8'))['completed']]
assert failed,'The unsuccessful screening run must remain in the export.'
summary=data['final-results.json']['summary']
print(json.dumps({'verified_imported_artifacts':len(manifest['files']),
    'preserved_failed_runs':len(failed),'baseline_tps':summary['r2']['median_tps'],
    'selected_tps':summary['r2-tuned16']['median_tps'],
    'gain_percent':100*(summary['r2-tuned16']['median_tps']/summary['r2']['median_tps']-1)},indent=2))
