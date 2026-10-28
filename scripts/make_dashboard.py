# Dashboard HTML Builder
from pathlib import Path

css_styles = """
:root {
  --bg-canvas: #f8f5f0;
  --bg-subtle: #f2ede4;
  --bg-surface: #ffffff;
  --border-default: rgba(74, 48, 38, 0.14);
  --border-dim: rgba(74, 48, 38, 0.08);
  --mocha-dark: #2d1c16;
  --mocha-primary: #4a3026;
  --mocha-hover: #5d3d31;
  --camel-primary: #bda081;
  --camel-light: #f3ece2;
  --sage-primary: #4a7558;
  --sage-light: #ebf3ee;
  --rose-primary: #c45761;
  --rose-light: #fbedee;
  --amber-primary: #b87a2a;
  --amber-light: #faf2e6;
  --text-primary: #2d1c16;
  --text-secondary: #665248;
  --text-tertiary: #99857b;
  --font-sans: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg-canvas); color: var(--text-primary); font-family: var(--font-sans); font-size: 14px; min-height: 100vh; }
.navbar { height: 68px; border-bottom: 1px solid var(--border-default); background: rgba(255,255,255,0.92); backdrop-filter: blur(16px); display: flex; align-items: center; justify-content: space-between; padding: 0 32px; position: sticky; top: 0; z-index: 100; }
.brand-wrap { display: flex; align-items: center; gap: 14px; }
.brand-logo { width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, var(--mocha-primary), var(--camel-primary)); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 20px; }
.brand-text h1 { font-size: 1.15rem; font-weight: 800; color: var(--mocha-dark); display: flex; align-items: center; gap: 8px; }
.brand-badge { font-size: 0.7rem; font-weight: 700; font-family: var(--font-mono); padding: 2px 8px; border-radius: 999px; background: var(--camel-light); color: var(--mocha-primary); }
.nav-actions { display: flex; align-items: center; gap: 12px; }
.auth-input-wrap { display: flex; align-items: center; background: var(--bg-subtle); border: 1px solid var(--border-default); border-radius: 12px; padding: 5px 12px; gap: 8px; }
.auth-input-wrap input { border: none; background: transparent; outline: none; font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-primary); width: 180px; }
.container { max-width: 1440px; margin: 0 auto; padding: 28px 32px 60px; display: flex; flex-direction: column; gap: 24px; }
.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.metric-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 18px; padding: 22px 24px; box-shadow: 0 2px 8px rgba(50,30,22,0.04); display: flex; flex-direction: column; gap: 8px; position: relative; overflow: hidden; }
.metric-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px; }
.card-sage::before { background: var(--sage-primary); }
.card-mocha::before { background: var(--mocha-primary); }
.card-sky::before { background: #48789e; }
.card-amber::before { background: var(--amber-primary); }
.metric-label { font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); }
.metric-value { font-size: 2.1rem; font-weight: 800; font-family: var(--font-mono); color: var(--mocha-dark); }
.panels-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.panel { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 18px; padding: 24px; box-shadow: 0 2px 8px rgba(50,30,22,0.04); display: flex; flex-direction: column; gap: 16px; }
.panel-header { display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-dim); padding-bottom: 12px; }
.panel-title { font-size: 1.05rem; font-weight: 700; color: var(--mocha-dark); display: flex; align-items: center; gap: 8px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }
.form-control { background: var(--bg-subtle); border: 1px solid var(--border-default); border-radius: 12px; padding: 10px 14px; font-size: 0.88rem; color: var(--text-primary); outline: none; }
.form-control:focus { background: #fff; border-color: var(--mocha-primary); }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 18px; border-radius: 12px; font-size: 0.88rem; font-weight: 600; cursor: pointer; border: 1px solid transparent; font-family: inherit; }
.btn-primary { background: var(--mocha-primary); color: #fff; }
.btn-primary:hover { background: var(--mocha-hover); }
.btn-secondary { background: var(--bg-subtle); border-color: var(--border-default); color: var(--mocha-dark); }
.btn-accent { background: var(--camel-primary); color: #fff; }
.btn-danger { background: var(--rose-light); border-color: rgba(196,87,97,0.2); color: var(--rose-primary); }
.btn-sm { padding: 6px 12px; font-size: 0.78rem; border-radius: 8px; }
.terminal-box { background: #201714; color: #e6dfd9; border-radius: 12px; padding: 14px; font-family: var(--font-mono); font-size: 0.78rem; line-height: 1.6; height: 180px; overflow-y: auto; }
.log-line { display: flex; gap: 8px; margin-bottom: 4px; }
.log-time { color: var(--camel-primary); flex-shrink: 0; }
.log-msg.error { color: #f87171; }
.log-msg.success { color: #4ade80; }
.log-msg.warning { color: #fbbf24; }
.table-panel { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 18px; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.table-wrap { overflow-x: auto; border: 1px solid var(--border-default); border-radius: 12px; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }
th { background: var(--bg-subtle); padding: 12px 16px; font-weight: 700; color: var(--text-secondary); border-bottom: 1px solid var(--border-default); }
td { padding: 12px 16px; border-bottom: 1px solid var(--border-dim); }
tr:hover td { background: var(--bg-subtle); }
.status-tag { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 700; font-family: var(--font-mono); }
.tag-active { background: var(--sage-light); color: var(--sage-primary); }
.tag-cooldown { background: var(--amber-light); color: var(--amber-primary); }
.tag-exhausted { background: var(--rose-light); color: var(--rose-primary); }
.modal-backdrop { position: fixed; inset: 0; background: rgba(30,20,15,0.45); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 999; opacity: 0; pointer-events: none; transition: opacity 0.2s; }
.modal-backdrop.open { opacity: 1; pointer-events: auto; }
.modal-card { background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 18px; padding: 28px; width: 100%; max-width: 480px; box-shadow: 0 16px 40px rgba(50,30,22,0.1); display: flex; flex-direction: column; gap: 16px; }
#toast-wrap { position: fixed; bottom: 24px; right: 28px; display: flex; flex-direction: column; gap: 10px; z-index: 9999; }
.toast { background: var(--mocha-dark); color: #fff; padding: 12px 18px; border-radius: 12px; font-size: 0.85rem; box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
"""

html_body = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privatemode AI ? ???? 2API ????</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>""" + css_styles + """</style>
</head>
<body>
  <header class="navbar">
    <div class="brand-wrap">
      <div class="brand-logo">???</div>
      <div class="brand-text">
        <h1>Privatemode AI <span class="brand-badge">2API GATEWAY</span></h1>
        <div style="font-size:0.75rem; color:var(--text-tertiary);">????? ? Clerk & SaaS ?? API Key ??????</div>
      </div>
    </div>
    <div class="nav-actions">
      <div class="auth-input-wrap">
        <span style="font-size:0.8rem; font-weight:600; color:var(--text-secondary);">?? ????:</span>
        <input type="password" id="gw-auth-key" placeholder="?? Bearer Key" oninput="saveAuthKey()" />
      </div>
      <button class="btn btn-secondary btn-sm" onclick="fetchPoolStats(true)">?? ????</button>
      <a href="/docs" target="_blank" class="btn btn-secondary btn-sm">?? OpenAPI</a>
    </div>
  </header>

  <main class="container">
    <section class="metrics-grid">
      <div class="metric-card card-sage">
        <span class="metric-label">?? ????? (Active)</span>
        <span class="metric-value" id="m-active">-</span>
        <span style="font-size:0.75rem; color:var(--text-tertiary);">????????</span>
      </div>
      <div class="metric-card card-mocha">
        <span class="metric-label">?? ?????? (Total)</span>
        <span class="metric-value" id="m-total">-</span>
        <span style="font-size:0.75rem; color:var(--text-tertiary);">accounts.json ???</span>
      </div>
      <div class="metric-card card-sky">
        <span class="metric-label">? ?????? (Requests)</span>
        <span class="metric-value" id="m-requests">-</span>
        <span style="font-size:0.75rem; color:var(--text-tertiary);">?????????</span>
      </div>
      <div class="metric-card card-amber">
        <span class="metric-label">? ?? / ??? (Cooldown)</span>
        <span class="metric-value" id="m-cooldown">-</span>
        <span style="font-size:0.75rem; color:var(--text-tertiary);">?????????</span>
      </div>
    </section>

    <section class="panels-grid">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">?? ????????????</div>
          <span style="font-size:0.75rem; color:var(--text-tertiary); font-family:var(--font-mono);">Turnstile + IMAP OTP</span>
        </div>
        <div style="display:flex; gap:12px; align-items:flex-end;">
          <div class="form-group" style="flex:1;">
            <label class="form-label">?????? (Accounts)</label>
            <input type="number" id="reg-count" class="form-control" value="1" min="1" max="20" />
          </div>
          <button class="btn btn-primary" id="btn-start-reg" onclick="startRegistration()">? ??????</button>
        </div>
        <div style="border-top:1px dashed var(--border-default); padding-top:14px; display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn btn-accent btn-sm" id="btn-recover-all" onclick="startRecoveryAll()">?? ???????? (????)</button>
          <button class="btn btn-secondary btn-sm" onclick="openSingleRecoverModal()">?? ????????</button>
        </div>
        <div class="form-group">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <label class="form-label">?? / ????????</label>
            <span id="job-status-badge" style="font-size:0.75rem; font-family:var(--font-mono); color:var(--text-tertiary);">????</span>
          </div>
          <div class="terminal-box" id="term-logs">
            <div class="log-line"><span class="log-time">[Ready]</span><span class="log-msg">???????????...</span></div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">?? 2API ?????? (Playground)</div>
          <span style="font-size:0.75rem; color:var(--text-tertiary); font-family:var(--font-mono);">/v1/chat/completions</span>
        </div>
        <div class="form-group">
          <label class="form-label">?? (Model) - ?? Privatemode ??????</label>
          <select id="play-model" class="form-control">
            <option value="glm-5.3">GLM-5.3 (????)</option>
            <option value="glm-latest" selected>glm-latest (??????)</option>
            <option value="glm-5.3-flash">GLM-5.3-Flash</option>
            <option value="glm-flash-latest">glm-flash-latest</option>
            <option value="gpt-oss-120b">gpt-oss-120b (128k)</option>
            <option value="deepseek-ocr-2">DeepSeek-OCR-2 (preview)</option>
            <option value="qwen3-embedding-4b">Qwen3-Embedding 4B</option>
            <option value="voxtral-mini-3b">Voxtral Mini 3B</option>
            <option value="whisper-large-v3">Whisper large-v3</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">????? (Prompt)</label>
          <input type="text" id="play-prompt" class="form-control" value="??????????????" />
        </div>
        <button class="btn btn-primary" id="btn-send-play" onclick="sendChatTest()">?? ????????</button>
        <div class="form-group">
          <label class="form-label">??????</label>
          <div class="terminal-box" id="play-response" style="height:120px; color:#4ade80;">
            <span style="color:#99857b;">????????? AI ????...</span>
          </div>
        </div>
      </div>
    </section>

    <section class="table-panel">
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
        <div style="display:flex; align-items:center; gap:12px;">
          <h2 style="font-size:1.1rem; font-weight:700; color:var(--mocha-dark);">?? ???????</h2>
          <span class="brand-badge" id="table-count-tag">0 ??</span>
        </div>
        <div style="display:flex; gap:10px;">
          <button class="btn btn-secondary btn-sm" onclick="openImportModal()">?? ????</button>
          <button class="btn btn-danger btn-sm" onclick="purgeDeadAccounts()">??? ??????</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>???? (Email)</th>
              <th>API Key (License Key)</th>
              <th>???? (Status)</th>
              <th>???? (Requests)</th>
              <th>???? (Failures)</th>
              <th>?? (Action)</th>
            </tr>
          </thead>
          <tbody id="accounts-tbody">
            <tr><td colspan="6" style="text-align:center; color:var(--text-tertiary); padding:32px;">?????????...</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <div class="modal-backdrop" id="import-modal">
    <div class="modal-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="font-size:1.1rem; font-weight:700; color:var(--mocha-dark);">?? ???? Privatemode ??</h3>
        <button class="btn btn-secondary btn-sm" onclick="closeImportModal()">?</button>
      </div>
      <div class="form-group">
        <label class="form-label">???? (Email)</label>
        <input type="email" id="manual-email" class="form-control" placeholder="user@outlook.com" />
      </div>
      <div class="form-group">
        <label class="form-label">?? (Password)</label>
        <input type="password" id="manual-pwd" class="form-control" placeholder="******" />
      </div>
      <div class="form-group">
        <label class="form-label">License API Key</label>
        <input type="text" id="manual-key" class="form-control" placeholder="e9bca6ac-b1a9-..." />
      </div>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
        <button class="btn btn-secondary" onclick="closeImportModal()">??</button>
        <button class="btn btn-primary" onclick="submitManualAccount()">????</button>
      </div>
    </div>
  </div>

  <div class="modal-backdrop" id="recover-modal">
    <div class="modal-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3 style="font-size:1.1rem; font-weight:700; color:var(--mocha-dark);">?? ????????</h3>
        <button class="btn btn-secondary btn-sm" onclick="closeSingleRecoverModal()">?</button>
      </div>
      <div class="form-group">
        <label class="form-label">Outlook ????</label>
        <input type="email" id="recover-target-email" class="form-control" placeholder="??: idetakai52@outlook.com" />
      </div>
      <p style="font-size:0.78rem; color:var(--text-tertiary);">????? Outlook IMAP ???? Clerk ?????????? API Key ?????</p>
      <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
        <button class="btn btn-secondary" onclick="closeSingleRecoverModal()">??</button>
        <button class="btn btn-accent" onclick="submitSingleRecover()">??????</button>
      </div>
    </div>
  </div>

  <div id="toast-wrap"></div>

  <script>
    var activeJobId = null;

    function getAuthHeaders() {
      var key = localStorage.getItem('pm_gateway_key') || '';
      var headers = { 'Content-Type': 'application/json' };
      if (key.trim()) {
        headers['Authorization'] = 'Bearer ' + key.trim();
      }
      return headers;
    }

    function saveAuthKey() {
      var key = document.getElementById('gw-auth-key').value;
      localStorage.setItem('pm_gateway_key', key);
    }

    function loadSavedAuthKey() {
      var saved = localStorage.getItem('pm_gateway_key') || '';
      var input = document.getElementById('gw-auth-key');
      if (input) input.value = saved;
    }

    function showToast(msg, type) {
      var wrap = document.getElementById('toast-wrap');
      var toast = document.createElement('div');
      toast.className = 'toast';
      var icon = (type === 'success') ? '? ' : ((type === 'error') ? '? ' : '?? ');
      toast.textContent = icon + msg;
      wrap.appendChild(toast);
      setTimeout(function() { toast.remove(); }, 4000);
    }

    async function fetchPoolStats(showNotify) {
      try {
        var res = await fetch('/v1/admin/pool', { headers: getAuthHeaders() });
        if (!res.ok) {
          if (res.status === 401) {
            showToast('401 ????????????????????', 'error');
          }
          throw new Error('HTTP ' + res.status);
        }
        var data = await res.json();
        document.getElementById('m-active').textContent = data.active_accounts;
        document.getElementById('m-total').textContent = data.total_accounts;
        document.getElementById('m-requests').textContent = data.total_requests_served;
        document.getElementById('m-cooldown').textContent = (data.rate_limited_accounts || 0) + (data.exhausted_accounts || 0);
        document.getElementById('table-count-tag').textContent = data.total_accounts + ' ??';
        if (showNotify) showToast('????????', 'info');
        fetchAccountsList();
      } catch (err) {
        console.error('fetchPoolStats error:', err);
      }
    }

    async function fetchAccountsList() {
      try {
        var res = await fetch('/v1/admin/accounts', { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var data = await res.json();
        var tbody = document.getElementById('accounts-tbody');
        tbody.innerHTML = '';
        if (!data.accounts || data.accounts.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary); padding:32px;">???????????????????????</td></tr>';
          return;
        }

        data.accounts.forEach(function(acc) {
          var tr = document.createElement('tr');
          var tagClass = 'tag-active';
          var tagText = '????';
          if (acc.status === 'exhausted' || acc.status === 'disabled') {
            tagClass = 'tag-exhausted';
            tagText = '????';
          } else if (acc.status === 'rate_limited') {
            tagClass = 'tag-cooldown';
            tagText = '????';
          }

          var safeEmail = String(acc.email).replace(/'/g, "\\'");
          var tdHtml = '';
          tdHtml += '<td style="font-weight:600; font-family:var(--font-mono);">' + acc.email + '</td>';
          tdHtml += '<td><span style="font-family:var(--font-mono); color:var(--text-secondary);">' + acc.api_key_masked + '</span></td>';
          tdHtml += '<td><span class="status-tag ' + tagClass + '">' + tagText + '</span></td>';
          tdHtml += '<td style="font-family:var(--font-mono);">' + (acc.total_requests || 0) + '</td>';
          tdHtml += '<td style="font-family:var(--font-mono);">' + (acc.consecutive_failures || 0) + '</td>';
          tdHtml += '<td><div style="display:flex; gap:6px;">';
          tdHtml += '<button class="btn btn-secondary btn-sm" onclick="resetAccount(\'' + safeEmail + '\')">??</button>';
          tdHtml += '<button class="btn btn-danger btn-sm" onclick="deleteAccount(\'' + safeEmail + '\')">??</button>';
          tdHtml += '</div></td>';

          tr.innerHTML = tdHtml;
          tbody.appendChild(tr);
        });
      } catch (err) {
        console.error('fetchAccountsList error:', err);
      }
    }

    async function startRegistration() {
      var count = parseInt(document.getElementById('reg-count').value, 10) || 1;
      var btn = document.getElementById('btn-start-reg');
      btn.disabled = true;
      document.getElementById('job-status-badge').textContent = '????????...';

      try {
        var res = await fetch('/v1/register', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ count: count, background: true })
        });
        var data = await res.json();
        if (data.job_id) {
          activeJobId = data.job_id;
          showToast('??? ' + count + ' ????????', 'success');
          pollJobStatus();
        } else {
          showToast('??????: ' + (data.message || '????'), 'error');
          btn.disabled = false;
        }
      } catch (err) {
        showToast('????: ' + err.message, 'error');
        btn.disabled = false;
      }
    }

    async function startRecoveryAll() {
      var btn = document.getElementById('btn-recover-all');
      btn.disabled = true;
      document.getElementById('job-status-badge').textContent = '?????????...';

      try {
        var res = await fetch('/v1/register/recover', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ background: true })
        });
        var data = await res.json();
        if (data.job_id) {
          activeJobId = data.job_id;
          showToast('????? ' + data.requested + ' ??????', 'success');
          pollJobStatus();
        } else {
          showToast(data.message || '??????????', 'info');
          btn.disabled = false;
        }
      } catch (err) {
        showToast('??????: ' + err.message, 'error');
        btn.disabled = false;
      }
    }

    async function pollJobStatus() {
      if (!activeJobId) return;
      try {
        var res = await fetch('/v1/register/status/' + activeJobId, { headers: getAuthHeaders() });
        if (!res.ok) return;
        var job = await res.json();
        var badge = document.getElementById('job-status-badge');
        badge.textContent = '???: ' + job.succeeded + ' ??, ' + job.failed + ' ??';

        var term = document.getElementById('term-logs');
        if (job.logs && job.logs.length > 0) {
          term.innerHTML = '';
          job.logs.forEach(function(log) {
            var div = document.createElement('div');
            div.className = 'log-line';
            var msgClass = '';
            if (log.level === 'error') msgClass = 'error';
            else if (log.level === 'success' || log.message.indexOf('??') !== -1) msgClass = 'success';
            else if (log.level === 'warning') msgClass = 'warning';

            div.innerHTML = '<span class="log-time">[' + log.time + ']</span><span class="log-msg ' + msgClass + '">' + log.message + '</span>';
            term.appendChild(div);
          });
          term.scrollTop = term.scrollHeight;
        }

        if (job.status === 'completed' || job.status === 'failed' || job.status === 'partial') {
          badge.textContent = '????: ' + job.succeeded + ' ??, ' + job.failed + ' ??';
          document.getElementById('btn-start-reg').disabled = false;
          document.getElementById('btn-recover-all').disabled = false;
          activeJobId = null;
          fetchPoolStats(false);
          return;
        }

        setTimeout(pollJobStatus, 2000);
      } catch (err) {
        console.error('pollJobStatus error:', err);
        setTimeout(pollJobStatus, 3000);
      }
    }

    async function resetAccount(email) {
      try {
        var res = await fetch('/v1/admin/accounts/' + encodeURIComponent(email) + '/reset', {
          method: 'POST',
          headers: getAuthHeaders()
        });
        if (res.ok) {
          showToast('?? ' + email + ' ????????', 'success');
          fetchPoolStats(false);
        } else {
          showToast('????', 'error');
        }
      } catch (e) {
        showToast(e.message, 'error');
      }
    }

    async function deleteAccount(email) {
      if (!confirm('?????? ' + email + ' ???????')) return;
      try {
        var res = await fetch('/v1/admin/accounts/' + encodeURIComponent(email), {
          method: 'DELETE',
          headers: getAuthHeaders()
        });
        if (res.ok) {
          showToast('?? ' + email + ' ??????', 'success');
          fetchPoolStats(false);
        } else {
          showToast('????', 'error');
        }
      } catch (e) {
        showToast(e.message, 'error');
      }
    }

    async function purgeDeadAccounts() {
      if (!confirm('???????? / ??????')) return;
      try {
        var res = await fetch('/v1/admin/purge-dead', {
          method: 'POST',
          headers: getAuthHeaders()
        });
        var data = await res.json();
        showToast(data.message || '????', 'info');
        fetchPoolStats(false);
      } catch (e) {
        showToast(e.message, 'error');
      }
    }

    async function sendChatTest() {
      var model = document.getElementById('play-model').value;
      var prompt = document.getElementById('play-prompt').value;
      var btn = document.getElementById('btn-send-play');
      var respBox = document.getElementById('play-response');

      btn.disabled = true;
      respBox.innerHTML = '<span style="color:#fbbf24;">??? Privatemode ????????????...</span>';

      try {
        var res = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            model: model,
            messages: [{ role: 'user', content: prompt }],
            stream: false
          })
        });

        if (!res.ok) {
          var errText = await res.text();
          respBox.innerHTML = '<span style="color:#f87171;">???? HTTP ' + res.status + ':\n' + errText + '</span>';
        } else {
          var data = await res.json();
          var content = data.choices && data.choices[0] && data.choices[0].message ? data.choices[0].message.content : JSON.stringify(data);
          respBox.textContent = content;
          showToast('2API ????!', 'success');
          fetchPoolStats(false);
        }
      } catch (err) {
        respBox.innerHTML = '<span style="color:#f87171;">???????: ' + err.message + '</span>';
      } finally {
        btn.disabled = false;
      }
    }

    function openImportModal() {
      document.getElementById('import-modal').classList.add('open');
    }
    function closeImportModal() {
      document.getElementById('import-modal').classList.remove('open');
    }

    async function submitManualAccount() {
      var email = document.getElementById('manual-email').value.trim();
      var pwd = document.getElementById('manual-pwd').value.trim();
      var key = document.getElementById('manual-key').value.trim();
      if (!email || !key) {
        showToast('???????? API Key', 'error');
        return;
      }
      try {
        var res = await fetch('/v1/register/manual', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ email: email, password: pwd, api_key: key })
        });
        if (res.ok) {
          showToast('?? ' + email + ' ????!', 'success');
          closeImportModal();
          fetchPoolStats(false);
        } else {
          var errData = await res.json();
          showToast('????: ' + (errData.detail || '????'), 'error');
        }
      } catch (err) {
        showToast('????: ' + err.message, 'error');
      }
    }

    function openSingleRecoverModal() {
      document.getElementById('recover-modal').classList.add('open');
    }
    function closeSingleRecoverModal() {
      document.getElementById('recover-modal').classList.remove('open');
    }

    async function submitSingleRecover() {
      var email = document.getElementById('recover-target-email').value.trim();
      if (!email) {
        showToast('??? Outlook ????', 'error');
        return;
      }
      closeSingleRecoverModal();
      document.getElementById('job-status-badge').textContent = '???? ' + email + '...';
      showToast('???????? ' + email + '...', 'info');

      try {
        var res = await fetch('/v1/register/recover-single', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ email: email })
        });
        if (res.ok) {
          var data = await res.json();
          showToast('?? ' + email + ' ??????????', 'success');
          fetchPoolStats(false);
        } else {
          var err = await res.json();
          showToast('????: ' + (err.detail || '????'), 'error');
        }
      } catch (e) {
        showToast('????: ' + e.message, 'error');
      }
    }

    window.addEventListener('DOMContentLoaded', function() {
      loadSavedAuthKey();
      fetchPoolStats(false);
      setInterval(function() { fetchPoolStats(false); }, 10000);
    });
  </script>
</body>
</html>"""

Path("app/templates/dashboard.html").write_text(html_body, encoding="utf-8")
print("Dashboard HTML generated successfully!")
