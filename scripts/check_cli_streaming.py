#!/usr/bin/env python3
"""Prove early JSONL output, canonical parity, cache reuse and atomic failures."""
from __future__ import annotations
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/python'))
from runcost import from_response, canonical_json_bytes


def main():
    response={'object':'response','model':'probe','usage':{'input_tokens':1,'output_tokens':0}}
    card={'schema_version':'0.1','id':'probe','provider':'openai','model':'probe','components':[{'usage_component':'input_uncached_tokens','unit':'token','price':{'amount':'1','currency':'USD','per':'1'}}],'source':{'name':'user'}}
    value={'response':response,'options':{'provider':'openai','surface':'openai.responses'},'price_cards':[card]}
    expected=from_response(response,provider='openai',surface='openai.responses',price_cards=[card])
    line=json.dumps(value)+'\n'
    first=b'['+canonical_json_bytes(expected).rstrip(b'\n')
    env={**os.environ,'PYTHONPATH':str(ROOT/'packages/python')}
    commands=[[sys.executable,'-m','runcost.cli'],['node',str(ROOT/'packages/javascript/core/cli.js')]]
    calls=0
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal calls
            calls+=1
            body=b'[{"id":"openai","models":[{"id":"probe","prices":{"input_mtok":1,"output_mtok":2}}]}]'
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*_): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        with tempfile.TemporaryDirectory(prefix='runcost-streaming-') as temporary:
            root=Path(temporary)
            for index,command in enumerate(commands):
                process=subprocess.Popen([*command,'quote','-','--jsonl','--no-resolve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
                try:
                    process.stdin.write(line.encode());process.stdin.flush()
                    ready=queue.Queue()
                    threading.Thread(target=lambda:ready.put(process.stdout.read(len(first))),daemon=True).start()
                    received=ready.get(timeout=10)
                    assert received==first,(index,received,first,process.poll())
                    process.stdin.close()
                    assert process.stdout.read()==b']\n'
                    assert process.wait(timeout=10)==0,process.stderr.read()
                finally:
                    if process.poll() is None:process.kill();process.wait()
                source=root/f'input-{index}.jsonl';source.write_text(line*2)
                actual=subprocess.check_output([*command,'quote',str(source),'--jsonl','--no-resolve','--output-jsonl'],env=env)
                assert actual==canonical_json_bytes(expected)*2
                output=root/f'output-{index}.json';output.write_text('existing-output')
                source.write_text(line+'invalid-json\n')
                failed=subprocess.run([*command,'quote',str(source),'--jsonl','--no-resolve','--output',str(output)],env=env,capture_output=True,timeout=15)
                assert failed.returncode!=0 and output.read_text()=='existing-output'
                assert not list(root.glob('.runcost-*'))
                remote={'response':response,'options':{'provider':'openai','surface':'openai.responses','source_urls':{'genai-prices':f'http://127.0.0.1:{server.server_port}/prices/new_data/v2/data_slim.json'}}}
                source.write_text((json.dumps(remote)+'\n')*60)
                before=calls
                actual=subprocess.check_output([*command,'quote',str(source),'--jsonl','--price-source','genai-prices','--cache-dir',str(root/f'cache-{index}'),'--now','2026-10-04T00:00:00Z'],env=env,timeout=20)
                try:
                    rows=json.loads(actual)
                except json.JSONDecodeError as exc:
                    raise AssertionError((index,actual[max(0,exc.pos-100):exc.pos+100])) from exc
                assert len(rows)==60 and calls-before==1,(calls-before,'JSONL repeated source fetches')
    finally:
        server.shutdown();server.server_close();worker.join()
    print('Streaming CLI checks passed: output before EOF, JSONL parity, atomic failure, 60 quotes / one fetch per language')
    return 0

if __name__=='__main__':raise SystemExit(main())
