"""Measure one already-running Strata configuration. Does not execute generated code."""
import argparse,datetime,json,os,time,urllib.request
from pathlib import Path

CASES=[
 ('warmup','用中文详细说明城市公共图书馆如何服务不同年龄的读者，至少写二十项具体措施并解释原因。'),
 ('prose','用中文详细说明如何维护一台家用自行车，给出至少二十条具体步骤，每条都解释原因。持续写作，不要过早总结。'),
 ('code','编写一个完整的Python模块，实现带TTL、最大容量和LRU淘汰的线程安全缓存。包含详细中文注释、类型标注、使用示例和至少六个单元测试。只输出代码，完整写出所有部分。'),
 ('json','只输出JSON数组，包含100个按id升序排列的对象。每个对象具有id、name、description、duration_minutes四个字段。id从1到100，内容是家庭整理工作的具体任务，description用完整中文句子详细解释。不要代码块，不要省略号，写出全部对象。')]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tokens',type=int,default=256)
    a=p.parse_args()
    if not 32<=a.tokens<=1024:p.error('tokens must be between 32 and 1024')
    if a.output.exists():p.error('Output already exists; use a new file.')
    base=os.environ.get('STRATA_BASE_URL','http://127.0.0.1:8082').rstrip('/')
    key=os.environ.get('STRATA_API_KEY','')
    def api(path,body=None):
        data=None if body is None else json.dumps(body,ensure_ascii=False).encode('utf-8')
        headers={'Content-Type':'application/json'}
        if key:headers['Authorization']='Bearer '+key
        return urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=900)
    with api('/metrics') as response:initial=json.load(response)
    engine=initial['engine']
    if engine.get('context')!=8192 or engine.get('kv')!='fp16':p.error('This protocol requires context=8192 and kv=fp16.')
    report={'label':a.label,'started':datetime.datetime.now().astimezone().isoformat(),'engine':engine,
            'method':{'warmup_tokens':a.tokens,'measured_tokens':a.tokens,'temperature':0,'seed':42,'thinking':False},
            'runs':[],'completed':False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    # Reserve the result path before making model requests.
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    try:
        for cid,prompt in CASES:
            with api('/metrics') as response:before=json.load(response)
            previous=(before.get('requests') or [{}])[0].get('id')
            messages=[{'role':'user','content':prompt}]
            payload={'model':engine['model'],'messages':messages,'max_tokens':a.tokens,'temperature':0,'seed':42,
                     'stream':True,'stream_options':{'include_usage':True},'chat_template_kwargs':{'enable_thinking':False}}
            start=time.perf_counter();first=None;text='';reasoning='';usage={}
            with api('/v1/chat/completions',payload) as response:
                for line in response:
                    if not line.startswith(b'data: '):continue
                    chunk=line[6:].strip()
                    if chunk==b'[DONE]':break
                    item=json.loads(chunk)
                    if item.get('error'):raise RuntimeError('Server returned a streaming error.')
                    if item.get('usage'):usage=item['usage']
                    for choice in item.get('choices',[]):
                        delta=choice.get('delta',{});piece=delta.get('content') or ''
                        thought=delta.get('reasoning_content') or delta.get('reasoning') or ''
                        if first is None and (piece or thought or delta.get('tool_calls')):first=time.perf_counter()
                        text+=piece;reasoning+=thought
            wall=time.perf_counter()-start
            with api('/metrics') as response:metrics=json.load(response)
            last=metrics['requests'][0]
            assert last['id']!=previous and last['output_tokens']==usage['completion_tokens'],'Concurrent or mismatched request metrics'
            assert not reasoning and usage['completion_tokens']==a.tokens and last['decode_tok_s']>0
            result={'id':cid,'messages':messages,'content':text,'usage':usage,'server_metrics':last,
                    'wall_seconds':wall,'first_token_seconds':None if first is None else first-start}
            if cid=='warmup':report['warmup']=result
            else:report['runs'].append(result)
            a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(cid+': '+str(last['decode_tok_s'])+' decode tok/s',flush=True)
        report['completed']=True
    except Exception as e:
        report['error_type']=type(e).__name__
        raise
    finally:
        report['finished']=datetime.datetime.now().astimezone().isoformat()
        a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
