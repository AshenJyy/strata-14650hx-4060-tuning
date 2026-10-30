import ast
import ctypes
import html
import json
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

OUT = Path(r'${WORKSPACE}\outputs')
KEY = Path(r'${STRATA_ROOT}\local-api-key.txt').read_text().strip()
MODEL = 'qwen3.8-flash-next-gyro-s-abliterated'
BASE = 'http://127.0.0.1:8082'

def api(path, data=None, timeout=900):
    req = urllib.request.Request(BASE + path, data=None if data is None else json.dumps(data).encode(),
                                 headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=timeout)

class Memory(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in
        ['total_phys', 'avail_phys', 'total_page', 'avail_page', 'total_virtual', 'avail_virtual', 'extended']]

resource_samples = []
monitor_stop = threading.Event()
def monitor():
    while not monitor_stop.is_set():
        m = Memory(); m.length = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        row = {'time': time.time(), 'system_ram_used_gib': (m.total_phys-m.avail_phys)/2**30,
               'system_ram_free_gib': m.avail_phys/2**30}
        try:
            raw = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,temperature.gpu,power.draw',
                                           '--format=csv,noheader,nounits'], creationflags=subprocess.CREATE_NO_WINDOW,
                                           timeout=5, text=True).strip().splitlines()[0].split(',')
            row.update(dict(zip(['gpu_memory_mib','gpu_utilization_percent','gpu_temperature_c','gpu_power_w'], map(float, raw))))
        except Exception:
            pass
        resource_samples.append(row)
        monitor_stop.wait(1)

def stream_case(case):
    payload = {'model': MODEL, 'messages': case['messages'], 'stream': True,
               'stream_options': {'include_usage': True}, 'temperature': 0, 'max_tokens': case.get('max_tokens', 384),
               'chat_template_kwargs': {'enable_thinking': case.get('thinking', False)}}
    payload.update(case.get('extra', {}))
    started = time.perf_counter(); first = None; content = ''; reasoning = ''; calls = {}; usage = {}; finish = None
    with api('/v1/chat/completions', payload) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            chunk = line[6:].strip()
            if chunk == b'[DONE]': break
            item = json.loads(chunk)
            if item.get('error'): raise RuntimeError(str(item['error']))
            if item.get('usage'): usage = item['usage']
            for choice in item.get('choices', []):
                delta = choice.get('delta', {})
                piece = delta.get('content') or ''
                thought = delta.get('reasoning_content') or delta.get('reasoning') or ''
                if first is None and (piece or thought or delta.get('tool_calls')):
                    first = time.perf_counter()
                content += piece; reasoning += thought
                finish = choice.get('finish_reason') or finish
                for call in delta.get('tool_calls') or []:
                    entry = calls.setdefault(call.get('index',0), {'name':'','arguments':''})
                    f = call.get('function',{})
                    entry['name'] += f.get('name') or ''
                    entry['arguments'] += f.get('arguments') or ''
    elapsed = time.perf_counter()-started
    with api('/metrics', timeout=15) as r: metrics = json.load(r)
    history = metrics.get('requests') or []
    last = history[0] if history else {}
    result = {**case, 'content':content, 'reasoning':reasoning, 'tool_calls':list(calls.values()),
              'usage':usage, 'finish_reason':finish, 'wall_seconds':elapsed,
              'first_token_seconds':None if first is None else first-started, 'server_metrics':last,
              'completion_tokens_per_wall_second':usage.get('completion_tokens',0)/elapsed}
    if first is not None and elapsed > first-started and usage.get('completion_tokens',0)>1:
        result['stream_decode_tokens_per_second']=(usage['completion_tokens']-1)/(elapsed-(first-started))
    return result

def message(text): return [{'role':'user','content':text}]
def json_answer(text):
    s = text.strip()
    if s.startswith('```'): s = re.sub(r'^```(?:json)?\s*|\s*```$', '', s)
    return json.loads(s)

records = '\n'.join(f'Record {i:03}: station S{i%17:02}, temperature {17+i%11} C, pressure {1000+i%31} hPa, inspection normal.' for i in range(1,121))
records = records.replace('Record 061:', 'Record 061: special access code NEBULA-7419-ORCHID;')
tasks = [
 {'id':'math','title':'金额计算','messages':message('购买3件单价129元的商品和2件单价87元的商品，商品合计按原价的85%计费，再加12元运费。只输出JSON对象，键为total，值为最终金额数字，不要解释。'),'expected':{'total':488.85}},
 {'id':'logic','title':'约束推理','messages':message('四人A、B、C、D各占一个时段10、11、12、13点。C在13点；B紧挨着在D之前；A不能在10点，并且A在C之前。按10点到13点的顺序，仅输出四个人名组成的JSON数组。'),'expected':['B','D','A','C']},
 {'id':'extract','title':'中文信息提取','messages':message('从下列记录提取信息，只输出JSON，不要推测未提供的信息。字段仅限name、phone、city、quantity。记录：王敏计划在成都收货，订购蓝色笔记本7本。没有留下电话号码。缺失字段填null。'),'expected':{'name':'王敏','phone':None,'city':'成都','quantity':7}},
 {'id':'revision','title':'中文多次修订理解','messages':message('根据最终有效通知答题，只输出JSON，键为date、time、room。初稿：11月6日14:00在A201开会。修订一：日期推迟两天，时间不变，换到B305。修订二：时间提前30分钟，地点恢复为初稿的地点，日期保持修订一。最终的日期用MM-DD格式。'),'expected':{'date':'11-08','time':'13:30','room':'A201'}},
 {'id':'instruction','title':'严格格式与排序','messages':message('把这些数去重、从小到大排序，再只保留偶数：8、3、2、8、-4、3、0、11、2。只输出JSON数组，不要代码块或其他文字。'),'expected':[-4,0,2,8]},
 {'id':'unknown','title':'信息不足时不编造','messages':message('仅依据材料回答，不能补充外部知识。材料：一家未命名公司2025年营业收入为1200万元，同比增长20%。材料没有披露净利润。问题：该公司2025年净利润是多少万元？只输出JSON，键为net_profit，材料无法确定时值为null。'),'expected':{'net_profit':None}},
 {'id':'long_retrieval','title':'长文本检索','messages':message('Read the records below. Return only the special access code from Record 061, without explanation.\n'+records),'expected_text':'NEBULA-7419-ORCHID','max_tokens':64},
 {'id':'merge','title':'Python区间合并','messages':message('只输出Python代码，实现merge_intervals(intervals)。输入为若干[start,end]整数闭区间，顺序任意；合并重叠或端点相接的区间，按起点升序返回list[list[int]]；空输入返回[]；不要修改输入。不能导入库，不要输入输出，不要解释。'),'max_tokens':512,'code_function':'merge_intervals'},
 {'id':'unique','title':'Python滑动窗口','messages':message('只输出Python代码，实现longest_unique(s)，返回字符串最长无重复字符子串的长度。要求O(n)时间，支持Unicode，空字符串返回0。不能导入库，不要输入输出，不要解释。'),'max_tokens':512,'code_function':'longest_unique'},
 {'id':'tool','title':'工具调用参数','messages':message('请调用库存查询工具，查成都仓库CD-02中SKU为CN-405的商品库存。不要猜测库存，也不要写普通回答。'),
  'extra':{'tools':[{'type':'function','function':{'name':'lookup_inventory','description':'查询指定仓库中指定SKU的库存',
          'parameters':{'type':'object','properties':{'warehouse':{'type':'string'},'sku':{'type':'string'}},'required':['warehouse','sku'],'additionalProperties':False}}}],
          'tool_choice':{'type':'function','function':{'name':'lookup_inventory'}}},'expected_tool':{'name':'lookup_inventory','arguments':{'warehouse':'CD-02','sku':'CN-405'}},'max_tokens':128},
 {'id':'reasoning_mod','title':'思考模式：余数约束','messages':message('求所有满足以下条件的正整数n：n小于1000，n除以5余4，除以7余6，除以9余8。最终只用JSON给出count（解的数量）和sum（所有解的和），不要在最终答案中解释。'),'expected':{'count':3,'sum':1887},'thinking':True,'max_tokens':768,'extra':{'reasoning_budget_tokens':512}},
 {'id':'reasoning_prob','title':'思考模式：组合概率','messages':message('袋中有5个红球、3个蓝球、2个绿球。不放回随机取出2个球，求颜色不同的概率。最终只输出最简分数形式，例如1/2。'),'expected_text':'31/45','thinking':True,'max_tokens':768,'extra':{'reasoning_budget_tokens':512}},
]

def check_code(result):
    code = result['content'].strip()
    match = re.search(r'```(?:python)?\s*\n(.*?)```', code, re.S)
    if match: code=match.group(1)
    tree = ast.parse(code)
    # Generated code is checked structurally, then run with a small builtin set in a disposable process.
    banned = (ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.ClassDef,ast.With,ast.AsyncWith)
    allowed_attrs={'sort','append','extend','get','add','remove','discard','copy','items','keys','values','pop'}
    for node in ast.walk(tree):
        if isinstance(node,banned): raise ValueError('unsupported code construct')
        if isinstance(node,ast.Name) and (node.id.startswith('__') or node.id in {'eval','exec','open','compile','input','getattr','setattr','globals','locals','vars','breakpoint','help'}): raise ValueError('forbidden name')
        if isinstance(node,ast.Attribute) and node.attr not in allowed_attrs: raise ValueError('unsupported attribute: '+node.attr)
    cases = ([[[],[]],[[[1,3],[2,6],[8,10],[15,18]],[[1,6],[8,10],[15,18]]],[[[1,4],[4,5]],[[1,5]]],[[[5,7],[1,2],[2,4]],[[1,4],[5,7]]],[[[-5,-1],[-3,2],[7,7]], [[-5,2],[7,7]]],[[[1,10],[2,3],[1,10]],[[1,10]]]]
             if result['id']=='merge' else [['',0],['abcabcbb',3],['bbbbb',1],['pwwkew',3],['abba',2],['a😀b😀c',3],['汉字汉',2],['abcdef',6]])
    worker = """import builtins,copy,json,sys
d=json.load(sys.stdin)
names=['len','range','enumerate','sorted','min','max','set','dict','list','tuple','int','str','bool','zip','abs','sum','reversed']
scope={'__builtins__':{k:getattr(builtins,k) for k in names}}
exec(compile(d['code'],'<model-code>','exec'),scope)
checks=[]
for value,expected in d['cases']:
 before=copy.deepcopy(value)
 try:
  actual=scope[d['function']](value)
  checks.append({'ok':actual==expected and value==before,'expected':expected,'actual':actual,'input_preserved':value==before})
 except Exception as e: checks.append({'ok':False,'error':type(e).__name__})
print(json.dumps(checks,ensure_ascii=False))
"""
    proc=subprocess.run([sys.executable,'-I','-c',worker],input=json.dumps({'code':code,'function':result['code_function'],'cases':cases}),
                        capture_output=True,text=True,encoding='utf-8',timeout=8,creationflags=subprocess.CREATE_NO_WINDOW)
    if proc.returncode: raise ValueError(proc.stderr[-600:])
    checks=json.loads(proc.stdout)
    result['code_checks']=checks
    return all(c['ok'] for c in checks)

def grade(result):
    try:
        if 'expected' in result: return json_answer(result['content'])==result['expected']
        if 'expected_text' in result: return result['content'].strip()==result['expected_text']
        if 'code_function' in result: return check_code(result)
        if 'expected_tool' in result:
            calls=result['tool_calls']; expected=result['expected_tool']
            return len(calls)==1 and calls[0]['name']==expected['name'] and json.loads(calls[0]['arguments'])==expected['arguments']
    except Exception as e:
        result['grading_note']=str(e)
        return False
    return None

def save(report):
    report['resource_samples']=resource_samples
    (OUT/'Gyro-S-abliterated-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    OUT.mkdir(exist_ok=True)
    report={'started':datetime.now().isoformat(),'model':MODEL,'configuration':{'cpu':'i7-14650HX, 8 P cores / 16 logical CPUs','gpu':'RTX 4060 Laptop 8GB','ram':'32GB','context':8192,'parallel':1,'mtp':True,'route_tail_skip':0,'route_prior':0,'thinking':False,'temperature':0},'tests':[]}
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    try:
        # First request is recorded separately because it includes cold runtime caches.
        cases=[{'id':'cold','title':'首次请求','messages':message('只回答两个字：就绪'),'max_tokens':16}]
        for i, topic in enumerate(['维护一台家用自行车','整理一个家庭书架','准备一次轻松的公园野餐'],1):
            cases.append({'id':f'speed{i}','title':f'持续生成速度{i}','messages':message(f'用中文详细说明如何{topic}，给出至少二十条具体步骤，每条都解释原因。持续写作，不要过早总结。'),'max_tokens':256})
        cases+=tasks
        for case in cases:
            print('RUN '+case['id']+' '+case['title'],flush=True)
            try:
                result=stream_case(case)
                result['passed']=grade(result)
            except Exception as e:
                result={**case,'error':str(e),'passed':False}
            report['tests'].append(result);save(report)
            print(json.dumps({'id':case['id'],'passed':result.get('passed'),'seconds':round(result.get('wall_seconds',0),2),'tokens':result.get('usage',{}).get('completion_tokens'),'finish':result.get('finish_reason')},ensure_ascii=False),flush=True)
    finally:
        monitor_stop.set();thread.join(timeout=6)
        report['finished']=datetime.now().isoformat();save(report)
    print('BENCHMARK COMPLETE',flush=True)

if __name__=='__main__': main()
