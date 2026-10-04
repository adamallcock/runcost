#!/usr/bin/env python3
"""Measure actual cold, warm and HTTP-304 resolver paths against controlled data."""
from __future__ import annotations
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root',default=str(ROOT/'packages/python'))
    parser.add_argument('--output')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    sys.path.insert(0,args.package_root)
    import runcost as r
    import runcost.price_resolver as resolver
    models=[{'id':f'probe-{index}','prices':{'input_mtok':1,'output_mtok':2}} for index in range(1000)]
    payload=json.dumps([{'id':'openai','models':models}])
    fetches=compiles=0
    original=resolver.compile_price_catalog
    def compile_counted(cards):
        nonlocal compiles
        compiles+=1
        return original(cards)
    resolver.compile_price_catalog=compile_counted
    def fetch(url,headers,timeout):
        nonlocal fetches
        fetches+=1
        if headers.get('If-None-Match'):
            return {'status':304,'headers':{'etag':'"benchmark"'},'body':'','url':url}
        return {'status':200,'headers':{'etag':'"benchmark"'},'body':payload,'url':url}
    response={'object':'response','model':'probe-0','usage':{'input_tokens':100,'output_tokens':10}}
    try:
        with tempfile.TemporaryDirectory(prefix='runcost-resolver-performance-') as directory:
            options={'provider':'openai','sources':['genai-prices'],'cache_dir':directory,'fetcher':fetch,'now':'2026-10-04T00:00:00Z'}
            started=time.perf_counter();first=r.from_response_auto(response,**options);cold_ms=(time.perf_counter()-started)*1000
            initial_compiles=compiles
            started=time.perf_counter()
            for _ in range(100):
                quote=r.from_response_auto(response,**options)
                assert quote['total']==first['total']=='0.00012'
            warm_ms=(time.perf_counter()-started)*1000
            warm_compiles=compiles-initial_compiles
            before_304=compiles
            started=time.perf_counter();validated=r.from_response_auto(response,refresh=True,**options);validated_ms=(time.perf_counter()-started)*1000
            assert validated['total']==first['total']
            revalidation_compiles=compiles-before_304
            result={'cards':1000,'warm_quotes':100,'cold_ms':round(cold_ms,3),'warm_100_ms':round(warm_ms,3),'http_304_ms':round(validated_ms,3),'cold_compiles':initial_compiles,'warm_compiles':warm_compiles,'http_304_compiles':revalidation_compiles,'fetches':fetches}
            if args.check:
                assert fetches==2 and initial_compiles==1 and warm_compiles==0 and revalidation_compiles==0,result
    finally:
        resolver.compile_price_catalog=original
    encoded=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.output:Path(args.output).write_text(encoded)
    print(encoded,end='')
    return 0

if __name__=='__main__':raise SystemExit(main())
