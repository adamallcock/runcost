import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import * as r from '../packages/javascript/core/index.js';
const input=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const dir=process.argv[3];
const {usage,card,v2,dirty}=input;
const basic={
  budget:r.evaluateBudget('0.123456789123456789',{budget:'1'}),
  reconciliation:r.reconcileCost('0.123456789123456789','1.23456789123456789'),
  boundaries:['0.12345678912345678','0.123456789123456789','0.1234567891234567895','0.0000000000000000001','-0.0000000000000000001'].map(v=>r.evaluateBudget(v,{budget:'1'}).estimated_cost)
};
assert.throws(()=>r.evaluateBudget('0',{budget:'-0.0000000000000000001'}));
assert.throws(()=>r.evaluateBudget('0',{budget:'1',warningThreshold:'1.0000000000000000001'}));
assert.throws(()=>r.reconcileCost('0','0',{tolerance:'-0.0000000000000000001'}));
const catalog=r.compilePriceCatalog([card]);
card.components[0].price.amount='99';
assert.throws(()=>{catalog.priceCards[0].components[0].price.amount='98';},TypeError);
assert.equal(catalog.byModel.set,undefined);
assert.equal(r.calculateCost({usageLedger:usage,priceCards:catalog}).total,'1');
const pristine={...card,components:[{...card.components[0],price:{...card.components[0].price,amount:'1'}}]};
const second={...pristine,id:'output',components:[{...pristine.components[0],usage_component:'output_text_tokens'}],source:{...pristine.source,url:'https://example.com/b'}};
basic.provenance=r.calculateCost({usageLedger:{...usage,components:[...usage.components,{name:'output_text_tokens',quantity:'1',unit:'token'}]},priceCards:[pristine,second],mode:'strict'});
assert.equal(basic.provenance.price_sources.length,2);
for(const adjustment of [{type:'typo',value:'50'},{type:'multiplier',value:'bad'},{type:'percentage_discount',value:'NaN'}]) for(const mode of ['compatibility','strict']) assert.throws(()=>r.calculateCost({usageLedger:usage,priceCards:[pristine],discountPolicies:[{id:'invalid',adjustment}],mode}));
basic.v2=r.priceCardsFromGenAIPrices(v2);
const before=JSON.stringify(dirty);
basic.export=r.exportCostLedger(dirty);
assert.equal(JSON.stringify(dirty),before);
assert(!JSON.stringify(basic.export).includes('PRIVATE_SENTINEL'));
let fetches=0;
const fetcher=async url=>{fetches++;await new Promise(resolve=>setTimeout(resolve,30));return {status:200,body:JSON.stringify(v2),url};};
const options={provider:'openai',sources:['genai-prices'],cacheDir:dir,fetcher,now:'2026-10-04T00:00:00Z'};
const response={object:'response',model:'probe',usage:{input_tokens:1,output_tokens:0}};
const outputs=await Promise.all(Array.from({length:8},()=>r.fromResponseAuto(response,options)));
assert.equal(fetches,1);
assert(outputs.every(v=>v.total==='0.000001'));
const publicCatalog=await r.resolvePriceCatalog(options);publicCatalog.price_cards[0].components[0].price.amount='999';
assert.equal((await r.fromResponseAuto(response,options)).total,'0.000001');
const strict={...options,fetcher:async()=>{throw new Error('controlled refresh failure');},refresh:true,mode:'strict'};
await assert.rejects(r.fromResponseAuto(response,strict));
await assert.rejects(r.estimateCostAuto({...strict,surface:'openai.responses',model:'probe',components:{input_uncached_tokens:'1'}}));
await assert.rejects(r.fromOTelGenAISpanAuto({attributes:{'gen_ai.system':'openai','gen_ai.response.model':'probe','gen_ai.usage.input_tokens':1,'gen_ai.usage.output_tokens':0}},strict));
const items=['probe','second'].map((model,i)=>({custom_id:i?'b':'a',response:{status_code:200,body:{model,usage:{prompt_tokens:1,completion_tokens:0}}}}));
const batch=await r.fromBatchResultsAuto(items,{provider:'openai',endpoint:'/v1/chat/completions',sources:['genai-prices','models.dev'],cacheDir:path.join(dir,'batch'),fetcher:async url=>({status:200,url,body:JSON.stringify(url.includes('genai')?v2:{openai:{models:{probe:{cost:{input:1,output:2}},second:{cost:{input:1,output:2}}}}})})});
assert.equal(batch.metadata.price_resolution.selected_source,'models.dev');
assert.deepEqual(batch.items.map(item=>item.id),['a','b']);
assert(batch.items.every(item=>item.ledger.total!=='0'));
await assert.rejects(r.fromBatchResultsAuto(items,{...strict,endpoint:'/v1/chat/completions'}));
// A streaming body is stopped at the configured cap before reading another chunk.
let reads=0,canceled=false;
await r.resolvePriceCatalog({sources:['genai-prices'],cacheDir:'memory://bounded-reader',maxBytes:8,fetcher:async url=>({status:200,url,headers:{},body:{getReader:()=>({read:async()=>{reads++;return {done:false,value:new Uint8Array(9)};},cancel:async()=>{canceled=true;}})}})});
assert.equal(reads,1);assert(canceled);
console.log(JSON.stringify({basic,resolver:{cold_fetches:fetches,batch_source:batch.metadata.price_resolution.selected_source,stream_reads:reads}}));
