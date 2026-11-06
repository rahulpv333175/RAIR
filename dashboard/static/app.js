'use strict';
const $ = id => document.getElementById(id);
const state = {data:null, ready:false, busy:false, custom:false, docs:[], run:null, rendered:new Set(), failures:0, cursor:0, legacyProgress:false};
const node = (tag, cls, text) => { const n = document.createElement(tag); if(cls) n.className=cls; if(text!==undefined) n.textContent=text; return n; };
const icon = name => { const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'); const use=document.createElementNS(svg.namespaceURI,'use'); use.setAttribute('href','#i-'+name); svg.append(use); svg.setAttribute('aria-hidden','true'); return svg; };
const pct = n => Number.isFinite(n) ? (n*100).toFixed(1)+'%' : '—';
function error(message) { $('error-banner').textContent=message; $('error-banner').hidden=!message; }
async function api(path, options) {
  const response = await fetch(path, options);
  let data;
  try { data=await response.json(); } catch { throw new Error('The dashboard returned an unreadable response. Check that its server is running.'); }
  if(!response.ok) { const e=new Error(data.error || 'Request failed.'); e.data=data;e.status=response.status; throw e; }
  return data;
}
function setBusy(busy) {
  state.busy=busy;
  $('question-fields').disabled=busy;
  $('run').disabled=busy || !state.ready;
  $('run').querySelector('span').textContent=busy ? 'Comparing…' : 'Run comparison';
}
function markCustom() {
  state.custom=true; $('example').value='custom'; $('case-note').textContent='Custom question · supplied documents';
  if(state.run) { state.run=null;localStorage.removeItem('rair-kair-run');resetResults(); }
}
function renderDocuments() {
  const container=$('documents'); container.replaceChildren();
  state.docs.forEach((doc,index)=>{
    const card=node('div','doc-card'); card.dataset.documentId=doc.document_id || '';
    const top=node('div','doc-top'); const field=node('div','title-field');
    const titleLabel=node('label',null,'Document '+(index+1)+' title'); titleLabel.htmlFor='doc-title-'+index;
    const title=node('input'); title.id=titleLabel.htmlFor; title.value=doc.title; title.maxLength=300;
    title.addEventListener('input',()=>{doc.title=title.value;markCustom();});
    field.append(titleLabel,title); top.append(field);
    const remove=node('button','remove-doc','Remove'); remove.type='button'; remove.setAttribute('aria-label','Remove document '+(index+1));
    remove.addEventListener('click',()=>{state.docs.splice(index,1);markCustom();renderDocuments();}); top.append(remove);
    const label=node('label',null,'Source sentences · one per line'); label.htmlFor='doc-text-'+index;
    const text=node('textarea'); text.id=label.htmlFor; text.rows=3; text.value=doc.sentences.join('\n');
    text.addEventListener('input',()=>{doc.sentences=text.value.split(/\r?\n/).filter(s=>s.trim());markCustom();});
    card.append(top,label,text);container.append(card);
  });
  $('source-count').textContent=state.docs.length+' source document'+(state.docs.length===1?'':'s');
  $('add-document').disabled=state.docs.length>=20;
}
function showTask(task) {
  $('question').value=task.question;
  state.docs=task.documents.map(d=>({...d,sentences:[...d.sentences]}));renderDocuments();
}
function resetResults() {
  state.rendered.clear();state.cursor=0;$('download').hidden=true;$('elapsed').textContent='';$('gold-note').hidden=true;
  $('run-status').textContent='Ready for a new comparison';$('run-detail').textContent='Both systems will use this question and the same supplied sources.';
  $('run-indicator').className='idle-indicator';
  for(const system of ['RAIR','KAIR']) {
    const key=system.toLowerCase(); const status=$(key+'-status');status.textContent='Ready';status.dataset.status='idle';
    $(key+'-answer').replaceChildren(node('p','empty-title','Run both systems to see their answers.'),node('p','muted','An answer can include citations, an abstention, or an explicit error.'));
    $(key+'-usage').hidden=true;$(key+'-trace').replaceChildren(node('p','muted','No live trace yet.'));
    $(key+'-trace-count').textContent=system==='RAIR'?'Gaps, queries and verified facts':'Agents, queries and selection';
    $(key+'-trace').parentElement.open=false;
    $(key+'-live-steps').replaceChildren();$(key+'-live-updates').hidden=true;
  }
  $('verified-count').textContent='Verified facts';renderAgents();
}
function selectExample(id) {
  if(id==='custom') { state.custom=true;showTask({question:'',documents:[{title:'My source',sentences:['']}]}); }
  else { const example=state.data.examples.find(e=>e.id===id); if(!example)return;state.custom=false;showTask(example.task); }
  $('case-note').textContent=id==='custom'?'Custom question · supplied documents':id.startsWith('demo-')?'Illustrative two-hop example':'Previously used development question';
  resetResults();error('');
}
function renderAgents(result) {
  const list=$('agent-list'); list.replaceChildren();
  const agents=result ? result.agents : Array.from({length:state.data?.num_agents || 2},(_,i)=>({agent_id:'A'+(i+1),initialized:false}));
  for(const agent of agents) {
    const card=node('div','agent-card'+(result?.selected_agent_id===agent.agent_id?' selected':''));
    const copy=node('div');copy.append(node('strong',null,'Agent '+agent.agent_id.replace(/^A/,'')));
    let detail='Private memory';
    if(result) detail=agent.initialized ? (agent.known.length+' facts · '+agent.required.length+' open'+(agent.status==='error'?' · error':'')) : 'Not run';
    copy.append(node('span',null,detail));card.append(icon('doc'),copy);list.append(card);
  }
  $('selector-label').textContent=result?.selected_agent_id ? 'Selected '+result.selected_agent_id : 'Select proposal';
}
function viewSource(documentId) {
  $('sources-editor').open=true;
  for(const card of $('documents').children) {
    const match=card.dataset.documentId===documentId;
    card.classList.toggle('highlight',match);
    if(match)card.scrollIntoView({behavior:'smooth',block:'center'});
  }
}
function traceList(container,title,items) {
  if(!items.length)return;
  container.append(node('h3',null,title)); const list=node('ul');
  for(const item of items)list.append(node('li',null,item));container.append(list);
}
function renderTrace(system,result) {
  const container=$(system.toLowerCase()+'-trace');container.replaceChildren();
  renderDetailedTrace(container,system,result);
  const details=node('details');details.append(node('summary',null,'Full engine result · prompts, responses and budgets'));
  details.addEventListener('toggle',()=>{
    if(details.open && !details.querySelector('pre')) {const raw=node('pre',null,JSON.stringify(result,null,2));raw.tabIndex=0;details.append(raw);}
  });container.append(details);
}
function renderLiveEvent(event) {
  const key=event.system.toLowerCase(),data=event.details;
  $(key+'-live-updates').hidden=false;
  const names={decompose:'Gaps generated',retrieve:'Retrieval completed',filter:'Evidence selected',extract:'Candidates extracted',verify:'Verification completed',update:'Candidates proposed',check:'Admission check completed',selection:'Proposal selected'};
  const title=event.elapsed_seconds.toFixed(1)+'s · '+(data.agent_id?data.agent_id+' · ':'')+
    (data.round?'round '+data.round+' · ':'')+(data.iteration?'competition '+data.iteration+' · ':'')+
    (names[event.stage] || event.stage)+(data.query?' · '+data.query:'');
  const box=rdetails($(key+'-live-steps'),title);
  if(data.gap_id)box.append(node('p',null,'Selected gap: '+data.gap_id));
  if(data.gaps)rtable(box,['Gap','Information needed','Depends on','Status'],data.gaps.map(g=>[g.gap_id,g.description,g.depends_on.join(', ') || 'Independent',g.resolved?'Resolved by verifier':'Unresolved']),'Current gap state');
  if(data.documents)rtable(box,['Title','BM25 score'],data.documents.map(d=>[d.title,Number(d.score).toFixed(4)]),'Retrieved documents');
  if(data.evidence)rsources(box,'Selected original source sentences',data.evidence);
  if(data.candidates)rfacts(box,'Candidates (not yet committed facts)',data.candidates);
  if(data.decisions)rtable(box,['Candidate','Support','Relevant','Value type','Placeholder','Resolves gap','Admitted','Reason'],data.decisions.map(d=>[d.candidate_id,d.supported_by_evidence,d.relevant_to_gap,d.answer_type_ok,d.contains_unresolved_placeholder,d.resolves_gap,d.accepted,d.reason]),'Verifier decisions');
  if(data.promoted)rfacts(box,'New facts admitted to shared memory',data.promoted);
  if(data.fact_check) {
    rtable(box,['Candidate','Binary check'],data.candidates.map(c=>[c.candidate_id,data.fact_check.accepted_candidate_ids.includes(c.candidate_id)?'Accepted':'Rejected']),'Candidate checks');
    rlist(box,'Remaining requirements proposed by checker',data.fact_check.required);
    box.append(node('p','muted small','Private state is committed only after context filtering succeeds.'));
  }
  if(data.known)rfacts(box,'Committed private knowledge',data.known);
  if(data.required)rlist(box,event.stage==='update'?'Proposed unresolved requirements':'Committed unresolved requirements',data.required);
  if(data.context)rsources(box,event.stage==='selection'?'Selected context for the next competition':'Committed refined context',data.context);
  if(Object.hasOwn(data,'selected_agent_id'))box.append(node('p',null,'Selected: '+(data.selected_agent_id || 'none')+' · '+data.reason));
  if(data.proposal_requirements)rtable(box,['Eligible proposal','Unresolved requirements'],Object.entries(data.proposal_requirements),'Proposal comparison');
}
function renderResult(system,result,runId) {
  const identity=runId+system;if(state.rendered.has(identity))return;state.rendered.add(identity);
  const key=system.toLowerCase(); const card=$(key+'-answer');card.replaceChildren();
  const heading=node('div','answer-heading');heading.append(node('span',null,'Answer:'));
  heading.append(node('strong',null,result.status==='answered'?result.prediction.answer:result.status==='abstained'?'Abstained':'Engine error'));card.append(heading);
  if(result.status==='abstained')card.append(node('p','answer-description','The engine did not find sufficient verified facts to support a complete answer.'));
  if(result.error)card.append(node('p','answer-description',result.error.stage+': '+result.error.message));
  if(result.status==='answered' && !result.sources.length)card.append(node('p','answer-description','No source sentences were returned. Inspect the full trace.'));
  result.sources.forEach((source,index)=>{
    const item=node('div','citation');const title=node('button','citation-title','['+(index+1)+'] '+source.title);title.type='button';
    title.addEventListener('click',()=>viewSource(source.document_id));
    item.append(title,node('span','citation-meta',' · sentence '+(source.sentence_index+1)),node('p',null,source.text));card.append(item);
  });
  const usage=$(key+'-usage');usage.replaceChildren();usage.hidden=false;
  const u=result.usage;
  for(const [label,value] of [['Model calls',u.llm_calls],['Retrievals',u.retrieval_calls],['Prompt tokens',u.prompt_tokens],['Output tokens',u.completion_tokens],['Time',u.elapsed_seconds.toFixed(2)+'s']]) {
    const part=node('span');part.append(node('strong',null,String(value)),document.createTextNode(' '+label.toLowerCase()));usage.append(part);
  }
  if(!u.token_counts_complete)usage.append(node('span',null,'Token counts incomplete'));
  $(key+'-trace-count').textContent=u.llm_calls+' calls · '+result.stop_reason;
  renderTrace(system,result);
  if(system==='RAIR')$('verified-count').textContent=result.state.verified_facts.length+' verified fact'+(result.state.verified_facts.length===1?'':'s');
  else renderAgents(result);
}

function renderBenchmark(data) {
  const container=$('benchmark-content');container.replaceChildren();
  if(!data.available) { $('benchmark-description').textContent=data.message;return; }
  const total=Object.values(data.systems).reduce((sum,s)=>sum+s.num_runs,0);
  $('benchmark-description').textContent=data.questions+' fresh questions · '+data.seeds+' seeds · '+total+' total runs';
  const wrap=node('div','table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Benchmark results. Scroll horizontally on narrow screens.');
  const table=node('table');table.setAttribute('aria-label','Recorded Step 5 benchmark');
  const head=node('thead');const header=node('tr');for(const title of ['System','Exact match','Answer F1','Abstentions','Errors']){const cell=node('th',null,title);cell.scope='col';header.append(cell);}head.append(header);table.append(head);
  const body=node('tbody');
  for(const [name,label] of [['RAIR','Updated RAIR'],['RAIR_REFERENCE','Step 4 RAIR core control'],['KAIR','KAIR']]) {
    const value=data.systems[name];const row=node('tr',name==='RAIR'?'featured':'');
    for(const text of [label,pct(value.metrics.exact_match),pct(value.metrics.answer_f1),String(value.abstained),String(value.error)])row.append(node('td',null,text));body.append(row);
  }
  table.append(body);wrap.append(table,node('p','table-note',data.systems.RAIR.num_runs+' runs per system · same model, source pools, final policy and budgets'));
  const aside=node('div');const insight=node('div','insight');const endpoint=data.core.exact_match;
  const points=value=>(value>=0?'+':'')+(value*100).toFixed(1);
  insight.append(node('span','label','RAIR core improvement'),node('strong',null,points(endpoint.estimate)+' percentage points'),node('p',null,'95% interval: '+points(endpoint.ci95[0])+' to '+points(endpoint.ci95[1])+' points'));
  const interval=data.comparison.exact_match.ci95;
  const conclusion=interval[0]<=0 && interval[1]>=0?'RAIR vs KAIR: superiority is not established.':interval[0]>0?'KAIR scored higher under this recorded protocol.':'RAIR scored higher under this recorded protocol.';
  aside.append(insight,node('div','comparison-note',conclusion));container.append(wrap,aside);
}
async function checkConnection() {
  $('health').disabled=true;$('health-label').textContent='Checking Ollama…';
  try {
    const health=await api('/api/health');state.ready=health.ready;
    $('health').dataset.ready=String(health.ready);$('health-label').textContent=health.ready?'Ollama connected':'Ollama unavailable';
    $('health').title=health.ready?'Check the local Ollama connection':health.message;
    if(!state.run)error(health.ready?'':'Start Ollama and make sure '+health.model+' is installed, then click “Ollama unavailable” to check again. '+health.message);
  } catch(e) {state.ready=false;$('health').dataset.ready='false';$('health-label').textContent='Server unavailable';error(e.message);}
  finally {$('health').disabled=false;$('run').disabled=state.busy || !state.ready;}
}
function renderJob(job) {
  if(job.task && state.taskRun!==job.id) {
    showTask(job.task);$('seed').value=job.seed;
    state.custom=!job.example_id;$('example').value=job.example_id || 'custom';state.taskRun=job.id;
    $('case-note').textContent=job.example_id?.startsWith('demo-')?'Illustrative two-hop example':state.custom?'Custom question · supplied documents':'Previously used development question';
  }
  $('run-status').textContent=job.stage;
  $('run-indicator').className='idle-indicator '+job.status;
  $('elapsed').textContent=job.elapsed_seconds.toFixed(1)+'s elapsed';
  $('download').hidden=false;$('download').href='/api/runs/'+job.id+'/download';
  const p=job.progress;
  $('run-detail').textContent=job.status==='running' && p.system ? p.system+' · '+(p.phase || 'running')+' · '+p.llm_calls+'/'+job.controls.max_llm_calls+' model calls started · '+p.retrieval_calls+'/'+job.controls.max_retrieval_calls+' retrievals' : job.status==='completed'?'Live demonstration complete. The Benchmark view contains the historical research comparison.':job.status==='failed'?'Completed engine traces are preserved. This run is not a valid completed comparison.':'The model is being checked and warmed before either engine starts.';
  for(const system of ['RAIR','KAIR']) {
    const result=job.results?.[system];const pill=$(system.toLowerCase()+'-status');
    const status=result?.status || job.result_statuses?.[system] || (job.status==='failed'?'failed':p.system===system?'running':'waiting');
    pill.dataset.status=status;pill.textContent=status.charAt(0).toUpperCase()+status.slice(1);
    if(result)renderResult(system,result,job.id);
    else if(job.status==='failed' && !job.result_statuses?.[system])$(system.toLowerCase()+'-answer').replaceChildren(node('p','empty-title','No result'),node('p','muted','This engine did not return a result before the comparison stopped.'));
  }
  if(job.evaluation) {
    const text=['Gold answer (revealed after both runs): '+job.gold_answer];
    for(const system of ['RAIR','KAIR'])text.push(system+': exact match '+pct(job.evaluation[system].exact_match)+', F1 '+pct(job.evaluation[system].answer_f1));
    $('gold-note').textContent=text.join(' · ');$('gold-note').hidden=false;
  }
  if(job.error)error(job.error);
}
async function poll(runId) {
  if(state.run!==runId)return;
  try {
    if(state.taskRun!==runId) {
      const initial=await api('/api/runs/'+runId);
      if(state.run!==runId)return;
      renderJob(initial);
    }
    let job;
    if(state.legacyProgress)job=await api('/api/runs/'+runId);
    else {
      try {job=await api('/api/runs/'+runId+'/progress?after='+state.cursor);}
      catch(e) {
        if(state.run!==runId)return;
        if(e.status!==404 || e.data?.error!=='Unknown endpoint.')throw e;
        // An already-running Python process can serve newer assets with older routes.
        state.legacyProgress=true;job=await api('/api/runs/'+runId);
      }
    }
    if(state.run!==runId)return;
    error('');
    renderJob(job);
    if(state.legacyProgress)$('run-detail').textContent+=' · Compatibility mode: restart the dashboard server to enable live steps.';
    for(const event of job.events || []) {
      if(event.sequence<=state.cursor)continue;
      renderLiveEvent(event);state.cursor=event.sequence;
    }
    if(Number.isInteger(job.cursor))state.cursor=job.cursor;
    for(const system of Object.keys(job.result_statuses || {})) {
      if(state.rendered.has(runId+system))continue;
      const result=await api('/api/runs/'+runId+'/results/'+system);
      if(state.run!==runId)return;
      renderResult(system,result,runId);
    }
    state.failures=0;
    if(job.status==='running')setTimeout(()=>poll(runId),state.legacyProgress?1200:500);
    else setBusy(false);
  } catch(e) {
    if(state.run!==runId)return;
    state.failures++;
    error('Connection interrupted: '+e.message+' Completed results are saved in the results folder.');
    if(state.failures<5)setTimeout(()=>poll(runId),2500);
    else {state.ready=false;setBusy(false);$('run-status').textContent='Connection lost · check the server';}
  }
}
$('comparison-form').addEventListener('submit',async event=>{
  event.preventDefault();if(state.busy)return;error('');
  const seed=Number($('seed').value);
  if(!$('question').value.trim()){error('Enter a question before running.');$('question').focus();return;}
  if(!Number.isInteger(seed) || seed<0 || seed>2147483645){error('Enter a valid whole-number seed.');return;}
  const payload=state.custom ? {question:$('question').value,documents:state.docs.map(d=>({title:d.title,sentences:d.sentences})),seed} : {example_id:$('example').value,seed};
  setBusy(true);
  try {
    const started=await api('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    resetResults();state.run=started.id;state.taskRun=null;state.failures=0;localStorage.setItem('rair-kair-run',started.id);poll(started.id);
  } catch(e) {
    if(e.data?.active_run) {resetResults();state.run=e.data.active_run;state.taskRun=null;poll(state.run);error(e.message);}
    else {setBusy(false);error(e.message);}
  }
});
$('question').addEventListener('input',markCustom);
$('seed').addEventListener('input',()=>{if(state.run){state.run=null;localStorage.removeItem('rair-kair-run');resetResults();}});
$('example').addEventListener('change',()=>{state.run=null;localStorage.removeItem('rair-kair-run');selectExample($('example').value);});
$('add-document').addEventListener('click',()=>{state.docs.push({title:'New source',sentences:['']});markCustom();renderDocuments();});
$('health').addEventListener('click',checkConnection);
async function initialize() {
  try {
    const data=await api('/api/bootstrap');state.data=data;
    state.legacyProgress=!data.api_features?.includes('live_progress_v1');
    $('model-label').textContent=data.model+' · runs on this computer';
    $('budget-label').textContent='Each engine: '+data.controls.max_retrieval_calls+' retrievals · '+data.controls.max_llm_calls+' model calls · temperature '+data.controls.temperature;
    $('seed').value=data.seed;
    $('example').replaceChildren();
    const demos=node('optgroup');demos.label='Illustrative examples';const previous=node('optgroup');previous.label='Previously evaluated development questions';
    for(const example of data.examples) {const option=node('option',null,example.label);option.value=example.id;(example.id.startsWith('demo-')?demos:previous).append(option);}
    const custom=node('option',null,'Write your own question and sources');custom.value='custom';
    $('example').append(demos,previous,custom);selectExample('demo-complete');renderBenchmark(data.benchmark);
    await checkConnection();
    const saved=data.active_run || localStorage.getItem('rair-kair-run');
    if(saved) {
      try {const job=await api('/api/runs/'+saved);state.run=saved;state.taskRun=null;setBusy(job.status==='running');renderJob(job);poll(saved);}
      catch {localStorage.removeItem('rair-kair-run');}
    }
  } catch(e) {error('Dashboard initialization failed: '+e.message);$('run-status').textContent='Unable to load dashboard';}
}
initialize();
initializeResearch();
