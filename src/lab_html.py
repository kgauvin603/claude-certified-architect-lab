LAB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Claude Certified Architect Lab</title>
<style>
:root {
  --bg: #0f1117; --surface: #1a1f2e; --surface2: #252b3b;
  --accent: #4f8ef7; --success: #22c55e; --warn: #f59e0b; --err: #ef4444;
  --text: #e2e8f0; --dim: #94a3b8; --border: #2d3748;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; min-height: 100vh; }
header { padding: 1.25rem 2rem; border-bottom: 1px solid var(--border); display: flex; align-items: baseline; gap: 1.5rem; }
h1 { font-size: 1.3rem; color: var(--accent); font-weight: 700; }
header span { font-size: 0.8rem; color: var(--dim); }
#statusBar { padding: 0.4rem 2rem; background: var(--surface); border-bottom: 1px solid var(--border); font-size: 0.75rem; display: flex; align-items: center; gap: 0.5rem; color: var(--dim); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); flex-shrink: 0; }
.dot.warn { background: var(--warn); animation: pulse 1.2s infinite; }
.layout { display: grid; grid-template-columns: 380px 1fr; gap: 1rem; padding: 1rem 2rem; }
.bottom { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 0 2rem 2rem; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }
.card h2 { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 1rem; font-weight: 600; }
label { display: block; font-size: 0.75rem; color: var(--dim); margin-bottom: 0.25rem; margin-top: 0.75rem; }
label:first-of-type { margin-top: 0; }
input, textarea { width: 100%; padding: 0.45rem 0.7rem; background: var(--bg); border: 1px solid var(--border); border-radius: 5px; color: var(--text); font-size: 0.875rem; }
textarea { resize: vertical; min-height: 70px; }
input:focus, textarea:focus { outline: none; border-color: var(--accent); }
.scenarios { margin-top: 1rem; }
.scenarios p { font-size: 0.72rem; color: var(--dim); margin-bottom: 0.5rem; }
.sbtn { display: inline-block; margin: 0.2rem 0.2rem 0.2rem 0; padding: 0.25rem 0.55rem; background: transparent; border: 1px solid var(--border); border-radius: 4px; color: var(--dim); font-size: 0.72rem; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
.sbtn:hover { border-color: var(--accent); color: var(--accent); }
.submit { width: 100%; margin-top: 1rem; padding: 0.65rem; background: var(--accent); border: none; border-radius: 5px; color: #fff; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: filter 0.15s; }
.submit:hover:not(:disabled) { filter: brightness(1.12); }
.submit:disabled { opacity: 0.45; cursor: not-allowed; }

/* Timeline */
.tl { list-style: none; padding: 0; }
.tl-item { display: flex; gap: 0.75rem; padding: 0.55rem 0; position: relative; }
.tl-item + .tl-item::before { content: ''; position: absolute; left: 7px; top: -8px; height: 16px; width: 1px; background: var(--border); }
.tl-dot { width: 15px; height: 15px; border-radius: 50%; background: var(--border); flex-shrink: 0; margin-top: 2px; transition: background 0.25s; }
.tl-item.active .tl-dot { background: var(--accent); animation: pulse 1.2s infinite; }
.tl-item.done .tl-dot { background: var(--success); }
.tl-item.fail .tl-dot { background: var(--err); }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.3} }
.tl-label { font-size: 0.82rem; font-weight: 500; line-height: 1.3; }
.tl-detail { font-size: 0.72rem; color: var(--dim); margin-top: 0.15rem; }
.events-box { margin-top: 0.75rem; max-height: 180px; overflow-y: auto; border-top: 1px solid var(--border); padding-top: 0.5rem; }
.ev { font-size: 0.7rem; font-family: monospace; color: var(--dim); padding: 0.15rem 0; }
.ev-new { color: var(--text); }

/* Response / Explanation */
.placeholder { color: var(--dim); font-size: 0.82rem; padding: 1.5rem; text-align: center; }
.badges { margin-bottom: 0.9rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.badge { padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.7rem; font-weight: 700; }
.b-complete { background: #14532d; color: #86efac; }
.b-clarify { background: #713f12; color: #fde68a; }
.b-escalate { background: #7f1d1d; color: #fca5a5; }
.b-neutral { background: var(--surface2); color: var(--dim); }
.rid { font-size: 0.68rem; color: var(--dim); font-family: monospace; }
.fact-list { list-style: none; font-size: 0.78rem; margin: 0.5rem 0 0.8rem; }
.fact-list li { padding: 0.2rem 0; border-top: 1px solid var(--border); }
.fact-list li:first-child { border-top: none; }
.fact-src { font-size: 0.68rem; color: var(--dim); }
details summary { font-size: 0.75rem; color: var(--dim); cursor: pointer; margin-top: 0.5rem; }
pre { font-size: 0.7rem; white-space: pre-wrap; word-break: break-word; max-height: 250px; overflow-y: auto; margin-top: 0.5rem; background: var(--bg); padding: 0.75rem; border-radius: 4px; }
.concept { margin-bottom: 0.75rem; }
.cn { font-size: 0.75rem; font-weight: 600; color: var(--accent); margin-bottom: 0.2rem; }
.cn-sub { color: var(--dim) !important; }
.ct { font-size: 0.75rem; color: var(--dim); line-height: 1.55; }
hr { border: none; border-top: 1px solid var(--border); margin: 0.75rem 0; }
.section-head { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.07em; color: var(--dim); margin-bottom: 0.5rem; }
</style>
</head>
<body>
<header>
  <h1>Claude Certified Architect Lab</h1>
  <span>Interactive multi-agent orchestration demo &mdash; exam prep</span>
</header>
<div id="statusBar">
  <div class="dot warn" id="sDot"></div>
  <span id="sTxt">Connecting to live event stream&hellip;</span>
</div>

<div class="layout">
  <!-- LEFT: Request form -->
  <div class="card">
    <h2>Request</h2>
    <form id="chatForm">
      <label>User ID</label>
      <input id="userId" value="user-001">
      <label>Session ID</label>
      <input id="sessionId" value="session-001">
      <label>Request Text</label>
      <textarea id="reqText" placeholder="Describe your support request&hellip;"></textarea>
      <div class="scenarios">
        <p>Quick scenarios:</p>
        <button type="button" class="sbtn" data-txt="I need to refund my most recent order">Refund recent order</button>
        <button type="button" class="sbtn" data-txt="Look up account for John">Look up John&rsquo;s account</button>
        <button type="button" class="sbtn" data-txt="Get details for order ORD-00000001">Get order ORD-00000001</button>
        <button type="button" class="sbtn" data-txt="Extract invoice data: Invoice #INV-2024-001, Vendor: ACME Corp, Amount Due: $1500.00, Date: 2024-01-15, Currency: USD">Extract invoice data</button>
      </div>
      <button type="submit" class="submit" id="submitBtn">Submit Request</button>
    </form>
  </div>

  <!-- RIGHT: Live trace -->
  <div class="card">
    <h2>Live Orchestration Trace</h2>
    <ul class="tl">
      <li class="tl-item" id="s1"><div class="tl-dot"></div><div><div class="tl-label">1. Orchestrator receives request</div><div class="tl-detail" id="d1">Waiting&hellip;</div></div></li>
      <li class="tl-item" id="s2"><div class="tl-dot"></div><div><div class="tl-label">2. Researcher gathers facts</div><div class="tl-detail" id="d2">Waiting&hellip;</div></div></li>
      <li class="tl-item" id="s3"><div class="tl-dot"></div><div><div class="tl-label">3. MCP tools execute</div><div class="tl-detail" id="d3">Waiting&hellip;</div></div></li>
      <li class="tl-item" id="s4"><div class="tl-dot"></div><div><div class="tl-label">4. Validator checks consistency</div><div class="tl-detail" id="d4">Waiting&hellip;</div></div></li>
      <li class="tl-item" id="s5"><div class="tl-dot"></div><div><div class="tl-label">5. Decision is made</div><div class="tl-detail" id="d5">Waiting&hellip;</div></div></li>
      <li class="tl-item" id="s6"><div class="tl-dot"></div><div><div class="tl-label">6. Response is returned</div><div class="tl-detail" id="d6">Waiting&hellip;</div></div></li>
    </ul>
    <div class="events-box" id="evBox"><div class="ev" style="text-align:center">Events will appear here&hellip;</div></div>
  </div>
</div>

<div class="bottom">
  <div class="card">
    <h2>Response</h2>
    <div id="respPanel"><div class="placeholder">Submit a request to see the response</div></div>
  </div>
  <div class="card">
    <h2>Exam Explanation</h2>
    <div id="expPanel"><div class="placeholder">Submit a request to see exam concept explanations</div></div>
  </div>
</div>

<script>
(function() {
var eventBuffer = {};
var currentRid = null;
var toolsSeen = [];
var es = null;

function connectSSE() {
  es = new EventSource('/events');
  es.onopen = function() {
    document.getElementById('sDot').classList.remove('warn');
    document.getElementById('sTxt').textContent = 'Live event stream connected';
  };
  es.onmessage = function(e) {
    try {
      var d = JSON.parse(e.data);
      var rid = d.request_id, ev = d.event;
      if (!eventBuffer[rid]) eventBuffer[rid] = [];
      eventBuffer[rid].push(ev);
      pushEvent(ev, rid);
      updateTimeline(ev);
    } catch(_) {}
  };
  es.onerror = function() {
    document.getElementById('sDot').classList.add('warn');
    document.getElementById('sTxt').textContent = 'Reconnecting…';
    es.close();
    setTimeout(connectSSE, 3000);
  };
}
connectSSE();

document.querySelectorAll('.sbtn').forEach(function(b) {
  b.addEventListener('click', function() {
    document.getElementById('reqText').value = b.dataset.txt;
  });
});

function resetUI() {
  ['s1','s2','s3','s4','s5','s6'].forEach(function(id, i) {
    document.getElementById(id).className = 'tl-item';
    document.getElementById('d' + (i+1)).textContent = 'Waiting…';
  });
  document.getElementById('evBox').innerHTML = '';
  toolsSeen = [];
  currentRid = null;
}

function setStep(id, state, detail) {
  var el = document.getElementById(id);
  el.className = 'tl-item ' + state;
  if (detail) document.getElementById(id.replace('s','d')).textContent = detail;
}

function updateTimeline(ev) {
  var e = ev.toLowerCase();
  if (e.indexOf('orchestrator: started') !== -1) { setStep('s1','active','Planning…'); }
  if (e.indexOf('orchestrator: plan') !== -1) { setStep('s1','active', ev.replace('Orchestrator: plan → ','')); }
  if (e.indexOf('researcher: started') !== -1) { setStep('s1','done','Plan dispatched'); setStep('s2','active','Running…'); }
  if (e.indexOf('tool:') !== -1) {
    var tool = ev.replace('Tool: ','').split('→')[0].trim();
    if (toolsSeen.indexOf(tool) === -1) toolsSeen.push(tool);
    setStep('s3','active', toolsSeen.join(', '));
  }
  if (e.indexOf('researcher: ok') !== -1) { setStep('s2','done',ev); setStep('s3','done','Complete'); }
  if (e.indexOf('researcher: failed') !== -1) { setStep('s2','fail',ev); setStep('s3','fail','Failed'); }
  if (e.indexOf('validator: started') !== -1) { setStep('s4','active','Checking…'); }
  if (e.indexOf('validator: valid') !== -1 && e.indexOf('invalid') === -1) { setStep('s4','done','Consistent'); }
  if (e.indexOf('validator: invalid') !== -1) { setStep('s4','fail',ev); }
  if (e.indexOf('decision:') !== -1) { setStep('s5','done',ev); }
  if (e.indexOf('response sent') !== -1) { setStep('s6','done','Complete'); }
}

function pushEvent(ev, rid) {
  var box = document.getElementById('evBox');
  var item = document.createElement('div');
  item.className = 'ev ev-new';
  item.textContent = '[' + (rid||'') + '] ' + ev;
  box.appendChild(item);
  box.scrollTop = box.scrollHeight;
  setTimeout(function(){ item.className = 'ev'; }, 1500);
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderResponse(r) {
  var out = document.getElementById('respPanel');
  var o = r.decision && r.decision.outcome;
  var c = r.decision && r.decision.confidence;
  var bmap = {complete:'b-complete',clarify:'b-clarify',escalate:'b-escalate'};
  var html = '<div class="badges">';
  if (o) html += '<span class="badge ' + (bmap[o]||'b-neutral') + '">' + esc(o.toUpperCase()) + '</span>';
  if (c) html += '<span class="badge b-neutral">' + esc(c.toUpperCase()) + '</span>';
  if (r.request_id) html += '<span class="rid">id: ' + esc(r.request_id) + '</span>';
  html += '</div>';
  if (r.decision && r.decision.clarifying_question) {
    html += '<p style="font-size:0.82rem;margin-bottom:0.5rem"><strong>Clarification needed:</strong> ' + esc(r.decision.clarifying_question) + '</p>';
  }
  if (r.decision && r.decision.escalation_detail) {
    html += '<p style="font-size:0.82rem;margin-bottom:0.5rem"><strong>Escalation:</strong> ' + esc(r.decision.escalation_detail) + '</p>';
  }
  var facts = (r.research && r.research.facts) || [];
  if (facts.length) {
    html += '<p style="font-size:0.72rem;color:var(--dim);margin-bottom:0.25rem">Facts gathered:</p><ul class="fact-list">';
    facts.forEach(function(f){ html += '<li>' + esc(f.key) + ': <strong>' + esc(f.value) + '</strong> <span class="fact-src">(' + esc(f.source) + ')</span></li>'; });
    html += '</ul>';
  }
  html += '<details><summary>Full JSON response</summary><pre>' + esc(JSON.stringify(r, null, 2)) + '</pre></details>';
  out.innerHTML = html;
}

function renderExplanation(exp) {
  var out = document.getElementById('expPanel');
  if (!exp) { out.innerHTML = '<div class="placeholder">No explanation available</div>'; return; }
  var o = exp.outcome;
  var bmap = {complete:'b-complete',clarify:'b-clarify',escalate:'b-escalate'};
  var html = '';
  if (o) html += '<div class="badges"><span class="badge ' + (bmap[o]||'b-neutral') + '">' + esc(o.toUpperCase()) + '</span></div>';

  function row(label, text) {
    if (!text) return '';
    return '<div class="concept"><div class="cn">' + esc(label) + '</div><div class="ct">' + esc(text) + '</div></div>';
  }

  html += row('Orchestrator', exp.orchestrator_role);
  if (exp.subagents_used && exp.subagents_used.length) {
    html += row('Subagents', exp.subagents_used.join(', '));
  }
  html += row('Tool Selection', exp.tool_selection_rationale);
  html += row('Exact vs Fuzzy', exp.exact_vs_fuzzy);
  html += row('Outcome', exp.outcome_explanation);

  if (exp.exam_concepts) {
    html += '<hr><div class="section-head">Exam Concept Mapping</div>';
    var labels = {
      tool_selection: 'Tool Selection',
      mcp_design: 'MCP Design',
      subagent_context_isolation: 'Context Isolation',
      structured_outputs: 'Structured Outputs',
      validation: 'Validation',
      confidence_and_escalation: 'Confidence & Escalation',
      observability: 'Observability'
    };
    Object.keys(exp.exam_concepts).forEach(function(k) {
      html += '<div class="concept"><div class="cn cn-sub">' + esc(labels[k]||k) + '</div><div class="ct">' + esc(exp.exam_concepts[k]) + '</div></div>';
    });
  }
  out.innerHTML = html;
}

document.getElementById('chatForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  var btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Processing…';
  resetUI();
  setStep('s1','active','Request received');
  document.getElementById('respPanel').innerHTML = '<div class="placeholder">Processing…</div>';
  document.getElementById('expPanel').innerHTML = '<div class="placeholder">Processing…</div>';

  var payload = {
    session_id: document.getElementById('sessionId').value || 'session-001',
    user_id: document.getElementById('userId').value || 'user-001',
    request_text: document.getElementById('reqText').value
  };

  try {
    var resp = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    var result = await resp.json();
    currentRid = result.request_id;
    setStep('s6', resp.ok ? 'done' : 'fail', resp.ok ? 'Response received' : 'Error');
    renderResponse(result);
    renderExplanation(result.exam_explanation);
  } catch(err) {
    document.getElementById('respPanel').innerHTML = '<div style="color:var(--err);font-size:0.85rem">Error: ' + esc(err.message) + '</div>';
    setStep('s6','fail','Error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit Request';
  }
});
})();
</script>
</body>
</html>"""
