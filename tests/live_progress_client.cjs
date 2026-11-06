// Browser-independent polling regression checks; Node built-ins only.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function fixture() {
  const source=fs.readFileSync(path.join(__dirname,'../dashboard/static/app.js'),'utf8');
  const context=vm.createContext({document:{getElementById:()=>({})},setTimeout:()=>{}});
  vm.runInContext(source.slice(0,source.indexOf("$('comparison-form').addEventListener")),context);
  vm.runInContext(`
    var calls=[],shown=[],finished=[],busy=[],messages=[];
    renderJob=job=>{if(job.task)state.taskRun=job.id;for(const system of Object.keys(job.results || {})){if(!state.rendered.has(job.id+system))renderResult(system,job.results[system],job.id);}};
    renderLiveEvent=event=>shown.push(event.sequence);
    renderResult=(system,result,id)=>{finished.push(system);state.rendered.add(id+system);};
    setBusy=value=>busy.push(value);error=message=>messages.push(message);
    state.run='run';state.taskRun='run';
  `,context);
  return context;
}

async function main() {
  let context=fixture();
  vm.runInContext(`api=async path=>{
    calls.push(path);
    if(path.endsWith('/results/RAIR') || path.endsWith('/results/KAIR'))return {};
    return state.cursor===0
      ? {id:'run',status:'running',cursor:1,events:[{sequence:1}],result_statuses:{RAIR:'answered'}}
      : {id:'run',status:'completed',cursor:2,events:[{sequence:1},{sequence:2}],result_statuses:{RAIR:'answered',KAIR:'answered'}};
  };`,context);
  await vm.runInContext("poll('run')",context);
  await vm.runInContext("poll('run')",context);
  assert.deepEqual(JSON.parse(vm.runInContext('JSON.stringify(calls)',context)),[
    '/api/runs/run/progress?after=0','/api/runs/run/results/RAIR',
    '/api/runs/run/progress?after=1','/api/runs/run/results/KAIR']);
  assert.equal(vm.runInContext('JSON.stringify(shown)',context),'[1,2]');
  assert.equal(vm.runInContext('JSON.stringify(finished)',context),'["RAIR","KAIR"]');
  assert.equal(vm.runInContext('JSON.stringify(busy)',context),'[false]');

  context=fixture();
  vm.runInContext(`state.taskRun=null;api=async path=>{
    calls.push(path);
    return path==='/api/runs/run'?{id:'run',task:{}}:
      {id:'run',status:'completed',cursor:0,events:[],result_statuses:{}};
  };`,context);
  await vm.runInContext("poll('run')",context);
  assert.equal(vm.runInContext('JSON.stringify(calls)',context),'["/api/runs/run","/api/runs/run/progress?after=0"]');

  context=fixture();
  vm.runInContext(`api=async path=>{state.run='new-run';return {id:'run',events:[{sequence:1}]};};`,context);
  await vm.runInContext("poll('run')",context);
  assert.equal(vm.runInContext('shown.length',context),0);
  assert.equal(vm.runInContext('state.cursor',context),0);

  context=fixture();
  vm.runInContext(`var polls=0;api=async path=>{
    calls.push(path);
    if(path.includes('/progress')){const e=new Error('Unknown endpoint.');e.status=404;e.data={error:e.message};throw e;}
    return {id:'run',status:++polls===1?'running':'completed',results:polls===1?{RAIR:{}}:{RAIR:{},KAIR:{}}};
  };`,context);
  await vm.runInContext("poll('run')",context);
  await vm.runInContext("poll('run')",context);
  assert.equal(vm.runInContext('state.legacyProgress',context),true);
  assert.equal(vm.runInContext('JSON.stringify(calls)',context),'["/api/runs/run/progress?after=0","/api/runs/run","/api/runs/run"]');
  assert.equal(vm.runInContext('JSON.stringify(finished)',context),'["RAIR","KAIR"]');
  assert.equal(vm.runInContext('state.failures',context),0);
  assert.equal(vm.runInContext('JSON.stringify(messages)',context),'["",""]');

  context=fixture();
  vm.runInContext(`api=async()=>{const e=new Error('Run not retained.');e.status=404;e.data={error:e.message};throw e;};`,context);
  await vm.runInContext("poll('run')",context);
  assert.equal(vm.runInContext('state.legacyProgress',context),false);
  assert.equal(vm.runInContext('state.failures',context),1);
  console.log('PASS: delta polling, replay, result retrieval, stale responses, older-server compatibility and genuine error handling.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
