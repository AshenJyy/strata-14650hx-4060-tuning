import datetime, json, statistics, subprocess, sys, threading, time, traceback
from pathlib import Path

work=Path(r'${STRATA_ROOT}\custom\r2')
sys.path.insert(0,r'${WORKSPACE}\work')
import strata_abliterated_bench as bench
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
out=work/'experiments'/stamp;out.mkdir(parents=True)
(work/'last-experiment.txt').write_text(str(out),encoding='utf-8')
cases=[
 ('prose','用中文详细说明如何维护一台家用自行车，给出至少二十条具体步骤，每条都解释原因。持续写作，不要过早总结。'),
 ('code','编写一个完整的Python模块，实现带TTL、最大容量和LRU淘汰的线程安全缓存。包含详细中文注释、类型标注、使用示例和至少六个单元测试。只输出代码，完整写出所有部分。'),
 ('json','只输出JSON数组，包含100个按id升序排列的对象。每个对象具有id、name、description、duration_minutes四个字段。id从1到100，内容是家庭整理工作的具体任务，description用完整中文句子详细解释。不要代码块，不要省略号，写出全部对象。')]
order=sys.argv[1:];assert order
report={'started':datetime.datetime.now().astimezone().isoformat(),'order':order,'sessions':[],'completed':False,
        'method':{'warmup_tokens':256,'measured_tokens':256,'temperature':0,'seed':42,'thinking':False,'context':8192,'kv':'fp16','cpu':'8P8E24T','pruning':False}}
def save():
    report['resource_samples']=bench.resource_samples
    p=out/'results.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
def switch(mode,label):
    print('SWITCH '+mode+' '+label,flush=True)
    p=subprocess.run([sys.executable,str(work/'switch.py'),mode],capture_output=True,text=True,encoding='utf-8',timeout=1100,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(label+'-switch.log')).write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    if p.returncode: raise RuntimeError('Switch failed: '+label)
    with bench.api('/metrics',timeout=20) as r: info=json.load(r)['engine']
    assert info['pool_workers']==23 and info['context']==8192 and info['kv']=='fp16'
    return info
def run(cid,prompt):
    began=time.time()
    r=bench.stream_case({'id':cid,'messages':bench.message(prompt),'max_tokens':256,'extra':{'seed':42}})
    r.update(started_unix=began,ended_unix=time.time())
    assert not r.get('reasoning') and r['usage']['completion_tokens']==256 and r['server_metrics']['decode_tok_s']>0
    return r
monitor=threading.Thread(target=bench.monitor,daemon=True);monitor.start()
try:
    for i,mode in enumerate(order,1):
        e=switch(mode,f'{i}-{mode}')
        s={'index':i,'mode':mode,'engine_start':e,'runs':[]};report['sessions'].append(s);save()
        print('WARMUP '+mode,flush=True)
        s['warmup']=run('warmup','用中文详细说明城市公共图书馆如何服务不同年龄的读者，至少写二十项具体措施并解释原因。');save()
        for cid,prompt in cases:
            print('RUN '+mode+' '+cid,flush=True)
            r=run(cid,prompt);s['runs'].append(r);save()
            print(json.dumps({'mode':mode,'case':cid,'tps':r['server_metrics']['decode_tok_s'],'ttft':round(r['first_token_seconds'],3)},ensure_ascii=False),flush=True)
        with bench.api('/metrics',timeout=20) as r: s['engine_end']=json.load(r)['engine']
        cfg=json.loads((work/'configs'/(mode+'.json')).read_text(encoding='utf-8'))
        log=Path(cfg['log'])
        if log.exists(): (out/(f'{i}-{mode}.engine.log')).write_bytes(log.read_bytes())
        save()
    report['summary']={}
    for mode in dict.fromkeys(order):
        runs=[x for s in report['sessions'] if s['mode']==mode for x in s['runs']]
        report['summary'][mode]={'median_tps':statistics.median(x['server_metrics']['decode_tok_s'] for x in runs),
            'by_workload':{cid:statistics.median(x['server_metrics']['decode_tok_s'] for x in runs if x['id']==cid) for cid,_ in cases},
            'median_ttft':statistics.median(x['first_token_seconds'] for x in runs),
            'wall_tps':sum(x['usage']['completion_tokens'] for x in runs)/sum(x['wall_seconds'] for x in runs)}
    report['completed']=True
    print('SUMMARY '+json.dumps(report['summary']),flush=True)
except Exception as e:
    report['error']=str(e);report['traceback']=traceback.format_exc();print(report['traceback'],flush=True)
finally:
    try: report['restored_engine']=switch('r1','restore-r1');report['restored']=True
    except Exception as e: report['restore_error']=str(e);report['restored']=False
    bench.monitor_stop.set();monitor.join(timeout=8)
    report['finished']=datetime.datetime.now().astimezone().isoformat();save()
    print('RESULT '+str(out/'results.json'),flush=True)
if not report['completed'] or not report['restored']: raise SystemExit(1)
