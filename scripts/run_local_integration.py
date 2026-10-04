#!/usr/bin/env python3
"""Exercise installed RunCost with caller-owned evidence; response content stays local."""
from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from runcost import from_response_auto, export_cost_ledger, reconcile_cost


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--response',required=True,help='local provider response JSON')
    parser.add_argument('--provider',required=True)
    parser.add_argument('--surface',required=True)
    parser.add_argument('--reported-total',required=True,help='independently observed USD total for this exact scope')
    parser.add_argument('--tolerance',default='0')
    parser.add_argument('--cache-dir',required=True)
    parser.add_argument('--offline',action='store_true',help='use an already-populated price cache')
    parser.add_argument('--output',required=True,help='sanitized local report path')
    args=parser.parse_args()
    response=json.loads(Path(args.response).read_text(encoding='utf-8'))
    options={'provider':args.provider,'surface':args.surface,'cache_dir':args.cache_dir}
    started=time.perf_counter()
    first=from_response_auto(response,offline=args.offline,**options)
    first_ms=(time.perf_counter()-started)*1000
    started=time.perf_counter()
    offline=from_response_auto(response,offline=True,**options)
    offline_ms=(time.perf_counter()-started)*1000
    parity=first['total']==offline['total'] and first['components']==offline['components']
    comparison=reconcile_cost(first,args.reported_total,tolerance=args.tolerance)
    result={'schema_version':'0.1','evidence_kind':'caller_supplied_scope','first_quote_ms':round(first_ms,3),'offline_quote_ms':round(offline_ms,3),'offline_parity':parity,'ledger':export_cost_ledger(first),'reconciliation':comparison,'warning_codes':sorted({item['code'] for item in first.get('warnings',[])})}
    Path(args.output).write_text(json.dumps(result,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'offline_parity':parity,'reconciliation_status':comparison['status'],'warning_count':len(result['warning_codes'])},sort_keys=True))
    return 0 if parity and comparison['status'] in ('matched','within_tolerance') and not result['warning_codes'] else 1

if __name__=='__main__':
    raise SystemExit(main())
