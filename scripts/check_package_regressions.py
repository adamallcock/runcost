#!/usr/bin/env python3
"""Regression gates for precision, provenance, ownership and resolver semantics."""
from __future__ import annotations
import copy
import json
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Inexact, ROUND_UP, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/python'))
sys.path.insert(0, str(ROOT))
import runcost as r
import runcost.price_resolver as resolver
from scripts.check_fixtures import validate_schema


def card(name='input', component='input_uncached_tokens', url='https://example.com/a'):
    return {'schema_version':'0.1','id':name,'provider':'openai','model':'probe','components':[{'usage_component':component,'unit':'token','price':{'amount':'1','currency':'USD','per':'1'}}],'source':{'name':'same-source','url':url,'retrieved_at':'2026-10-04T00:00:00Z'}}

USAGE = {'schema_version':'0.1','provider':'openai','surface':'openai.responses','model':{'requested':'probe','returned':'probe','billed':'probe','alias_resolution':'none'},'components':[{'name':'input_uncached_tokens','quantity':'1','unit':'token'}]}
RESPONSE = {'object':'response','model':'probe','usage':{'input_tokens':1,'output_tokens':0}}
V2 = [{'id':'openai','models':[{'id':'probe','prices':{'input_mtok':'1','output_mtok':'2','cache_write_1h_mtok':'3','web_searches_kcount':'4','input_image_mtok':'5','output_image_mtok':'6','input_video_mtok':'7','output_video_mtok':'8','output_reasoning_mtok':'9','input_document_kpages':'10'}}]}]


def rejects(function):
    try:
        function()
    except (ValueError, TypeError, ArithmeticError):
        return
    raise AssertionError('invalid contract was accepted')


def basic_results():
    results = {}
    # Decimal boundaries and helper arithmetic must ignore all ambient settings.
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_UP
        context.traps[Inexact] = True
        results['budget'] = r.evaluate_budget('0.123456789123456789',budget='1')
        results['reconciliation'] = r.reconcile_cost('0.123456789123456789','1.23456789123456789')
        results['boundaries'] = [r.evaluate_budget(value,budget='1')['estimated_cost'] for value in ('0.12345678912345678','0.123456789123456789','0.1234567891234567895','0.0000000000000000001','-0.0000000000000000001')]
    assert results['budget']['remaining'] == '0.876543210876543211'
    assert results['reconciliation']['signed_residual'] == '1.111111102111111101'
    assert results['boundaries'] == ['0.12345678912345678','0.123456789123456789','0.12345678912345679','0','0']
    rejects(lambda: r.evaluate_budget('0',budget='-0.0000000000000000001'))
    rejects(lambda: r.evaluate_budget('0',budget='1',warning_threshold='1.0000000000000000001'))
    rejects(lambda: r.reconcile_cost('0','0',tolerance='-0.0000000000000000001'))
    owned = card()
    catalog = r.compile_price_catalog([owned])
    owned['components'][0]['price']['amount'] = '99'
    catalog.price_cards[0]['components'][0]['price']['amount'] = '98'
    catalog.identity_candidates(USAGE)[0]['components'][0]['price']['amount'] = '97'
    assert r.calculate_cost(usage_ledger=USAGE,price_cards=catalog)['total'] == '1'
    provenance_usage = copy.deepcopy(USAGE)
    provenance_usage['components'].append({'name':'output_text_tokens','quantity':'1','unit':'token'})
    ledger = r.calculate_cost(usage_ledger=provenance_usage,price_cards=[card(),card('output','output_text_tokens','https://example.com/b')],mode='strict')
    assert len(ledger['price_sources']) == 2
    results['provenance'] = ledger
    for adjustment in ({'type':'typo','value':'50'},{'type':'multiplier','value':'bad'},{'type':'percentage_discount','value':'NaN'}):
        for mode in ('compatibility','strict'):
            rejects(lambda: r.calculate_cost(usage_ledger=USAGE,price_cards=[card()],discount_policies=[{'id':'invalid','adjustment':adjustment}],mode=mode))
    results['v2'] = r.price_cards_from_genai_prices(V2)
    assert len(results['v2'][0]['components']) == 9
    assert results['v2'][0]['metadata']['genai_prices']['unsupported_prices'] == {'input_document_kpages':'10'}
    dirty = copy.deepcopy(ledger)
    dirty['metadata'] = {'raw_usage':{'prompt':'PRIVATE_SENTINEL'},'unknown_attributes':{'token':'PRIVATE_SENTINEL'}}
    dirty['attribution'] = {'tenant_id':'PRIVATE_SENTINEL','tags':{'email':'PRIVATE_SENTINEL'}}
    dirty['debug_trace'] = {'secret':'PRIVATE_SENTINEL'}
    dirty['components'][0]['metadata'] = {'prompt':'PRIVATE_SENTINEL'}
    dirty['price_sources'][0]['url'] = 'https://example.com/PRIVATE_SENTINEL'
    dirty['warnings'] = [{'code':'usage_missing','message':'PRIVATE_SENTINEL','metadata':{'field':'PRIVATE_SENTINEL'}}]
    before = copy.deepcopy(dirty)
    exported = r.export_cost_ledger(dirty)
    assert dirty == before and 'PRIVATE_SENTINEL' not in json.dumps(exported)
    validate_schema(exported,json.loads((ROOT/'schemas/cost-ledger.schema.json').read_text()))
    results['export'] = exported
    # Unsupported Chinese holiday rules cannot be inferred from weekday windows.
    snapshot = json.loads((ROOT/'fixtures/source-files/deepseek-official-pricing-snapshot.json').read_text())
    ds_usage = copy.deepcopy(USAGE)
    ds_usage.update(provider='deepseek',surface='deepseek.chat_completions',model={'requested':'deepseek-flash','returned':'deepseek-flash','billed':'deepseek-flash'},context={'priced_at':'2026-10-01T06:00:00Z'})
    ds_cards = r.price_cards_from_official_snapshot(snapshot)
    blocked = r.calculate_cost(usage_ledger=ds_usage,price_cards=ds_cards)
    assert blocked['total'] == '0' and any(w['code']=='billing_schedule_unsupported' for w in blocked['warnings'])
    ds_usage['context']['pricing_period']='offpeak'
    assert r.calculate_cost(usage_ledger=ds_usage,price_cards=ds_cards)['total'] != '0'
    return results


def schema_negatives():
    from scripts.check_product_expansion import run_python_case
    fixture=json.loads((ROOT/'fixtures/expansion/cases.json').read_text())
    case=next(case for case in fixture['cases'] if case['operation']=='from_batch_results')
    batch=run_python_case(case,fixture)
    schema=json.loads((ROOT/'schemas/batch-ledger.schema.json').read_text())
    validate_schema(batch,schema)
    successful=next(item for item in batch['items'] if item['status']=='succeeded')
    del successful['ledger']
    try:
        validate_schema(batch,schema)
    except AssertionError:
        pass
    else:
        raise AssertionError('succeeded batch item without ledger was accepted')
    conditional = {'type':'object','allOf':[{'if':{'properties':{'status':{'const':'succeeded'}}},'then':{'required':['ledger']},'else':{'required':['error']}}]}
    for value in ({'status':'succeeded'},{'status':'errored'}):
        try:
            validate_schema(value,conditional)
        except AssertionError:
            pass
        else:
            raise AssertionError('conditional schema was ignored')
    for value,schema in ((-0.5,{'type':'number','minimum':0}),([1,1],{'type':'array','uniqueItems':True}),({'extra':1},{'type':'object','additionalProperties':False}),('x',{'anyOf':[{'const':'a'},{'const':'b'}]})):
        try:
            validate_schema(value,schema)
        except AssertionError:
            pass
        else:
            raise AssertionError('JSON Schema keyword was ignored')


def resolver_checks(directory):
    fetch_count = 0
    lock = threading.Lock()
    def fetch(url,headers,timeout):
        nonlocal fetch_count
        with lock:
            fetch_count += 1
        time.sleep(0.03)
        return {'status':200,'body':json.dumps(V2),'url':url}
    options = {'provider':'openai','sources':['genai-prices'],'cache_dir':directory,'fetcher':fetch,'now':'2026-10-04T00:00:00Z'}
    with ThreadPoolExecutor(max_workers=8) as pool:
        outputs = list(pool.map(lambda _:r.from_response_auto(RESPONSE,**options),range(8)))
    assert fetch_count == 1,(fetch_count,'cold fetches must coalesce')
    assert all(v['total']=='0.000001' for v in outputs)
    public = r.resolve_price_catalog(**options)
    public['price_cards'][0]['components'][0]['price']['amount']='999'
    assert r.from_response_auto(RESPONSE,**options)['total']=='0.000001'
    first = resolver._resolve_price_catalog(**options)['price_cards']
    for _ in range(40):
        assert resolver._resolve_price_catalog(**options)['price_cards'] is first
    def fail(*_):
        raise OSError('controlled refresh failure')
    strict = {**options,'fetcher':fail,'refresh':True,'mode':'strict'}
    rejects(lambda:r.from_response_auto(RESPONSE,**strict))
    rejects(lambda:r.estimate_cost_auto(provider='openai',surface='openai.responses',model='probe',components={'input_uncached_tokens':'1'},**{k:v for k,v in strict.items() if k!='provider'}))
    span={'attributes':{'gen_ai.system':'openai','gen_ai.response.model':'probe','gen_ai.usage.input_tokens':1,'gen_ai.usage.output_tokens':0}}
    rejects(lambda:r.from_otel_genai_span_auto(span,**strict))
    items=[{'custom_id':'a','response':{'status_code':200,'body':{'model':'probe','usage':{'prompt_tokens':1,'completion_tokens':0}}}},{'custom_id':'b','response':{'status_code':200,'body':{'model':'second','usage':{'prompt_tokens':1,'completion_tokens':0}}}}]
    def batch_fetch(url,headers,timeout):
        data=V2 if 'genai' in url else {'openai':{'models':{'probe':{'cost':{'input':1,'output':2}},'second':{'cost':{'input':1,'output':2}}}}}
        return {'status':200,'body':json.dumps(data),'url':url}
    batch=r.from_batch_results_auto(items,provider='openai',endpoint='/v1/chat/completions',sources=['genai-prices','models.dev'],cache_dir=directory/'batch',fetcher=batch_fetch)
    assert batch['metadata']['price_resolution']['selected_source']=='models.dev',batch
    assert [item['id'] for item in batch['items']]==['a','b']
    assert all(item['ledger']['total']!='0' for item in batch['items'])
    rejects(lambda:r.from_batch_results_auto(items,provider='openai',endpoint='/v1/chat/completions',**{k:v for k,v in strict.items() if k!='provider'}))
    return {'cold_fetches':fetch_count,'warm_identity_reuses':40,'batch_source':batch['metadata']['price_resolution']['selected_source']}


def main():
    expected=basic_results()
    schema_negatives()
    with tempfile.TemporaryDirectory(prefix='runcost-regressions-') as temporary:
        directory=Path(temporary)
        stats=resolver_checks(directory/'python-cache')
        shared=directory/'input.json'
        shared.write_text(json.dumps({'usage':USAGE,'card':card(),'v2':V2,'dirty':{**expected['provenance'],'metadata':{'secret':'PRIVATE_SENTINEL'},'attribution':{'tenant_id':'PRIVATE_SENTINEL'},'warnings':[{'code':'usage_missing','message':'PRIVATE_SENTINEL','metadata':{'field':'PRIVATE_SENTINEL'}}]}}))
        output=subprocess.check_output(['node',str(ROOT/'scripts/check_package_regressions.mjs'),str(shared),str(directory/'js-cache')],text=True,cwd=ROOT)
        actual=json.loads(output)
        # Export fixture differs in the omitted private fields only.
        assert actual['basic']==expected,(actual['basic'],expected)
        print('Package regressions passed:',json.dumps({'python':stats,'javascript':actual['resolver']},sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
