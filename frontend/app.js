const API = 'http://localhost:8000/api/v1';

// ─── Sample Query Helper ─────────────────────────────────────────────────────
function setSample(inputId, chipEl) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.value = chipEl.textContent.trim();
  input.focus();
  // Highlight active chip
  const siblings = chipEl.closest('.sample-queries').querySelectorAll('.sample-chip');
  siblings.forEach(c => c.classList.remove('active'));
  chipEl.classList.add('active');
}

// ─── Tab Navigation ──────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    if (btn.dataset.tab === 'dashboard') loadDashboard();
  });
});

// ─── Spinner ─────────────────────────────────────────────────────────────────
const spinner = document.getElementById('spinner');
function showSpinner() { spinner.classList.remove('hidden'); }
function hideSpinner() { spinner.classList.add('hidden'); }

// ─── API helpers ─────────────────────────────────────────────────────────────
async function apiPost(path, body) {
  const res = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(API + path);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Health Check ─────────────────────────────────────────────────────────────
async function checkHealth() {
  const badge = document.getElementById('healthBadge');
  try {
    const data = await apiGet('/health');
    badge.className = 'health-badge ok';
    badge.innerHTML = `<span class="dot"></span> ${data.total_documents} docs · ${data.status}`;
  } catch {
    badge.className = 'health-badge err';
    badge.innerHTML = `<span class="dot"></span> Offline`;
  }
}
checkHealth();
setInterval(checkHealth, 30000);

// ─── Severity helpers ─────────────────────────────────────────────────────────
function severityClass(sev) {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'critical';
  if (s === 'high') return 'high';
  if (s === 'medium') return 'medium';
  return 'low';
}

function riskColor(score) {
  if (score >= 0.75) return 'critical';
  if (score >= 0.5)  return 'high';
  if (score >= 0.25) return 'medium';
  return 'low';
}

function riskLabel(level) {
  const labels = { critical: '🔴 CRITICAL', high: '🟠 HIGH', medium: '🟡 MEDIUM', low: '🟢 LOW' };
  return labels[level] || level;
}

// ─── SEARCH ───────────────────────────────────────────────────────────────────
async function doSearch() {
  const query = document.getElementById('searchQuery').value.trim();
  if (!query) return alert('Please enter a search query.');

  const body = {
    query,
    top_k: 8,
    use_hybrid: document.getElementById('useHybrid').checked,
  };
  const sev = document.getElementById('fSeverity').value;
  const status = document.getElementById('fStatus').value;
  const supplier = document.getElementById('fSupplier').value.trim();
  if (sev) body.severity = sev;
  if (status) body.shipment_status = status;
  if (supplier) body.supplier_id = supplier;

  showSpinner();
  try {
    const data = await apiPost('/search', body);
    renderSearchResults(data);
  } catch (e) {
    document.getElementById('searchResults').innerHTML = errorBox(e.message);
  } finally {
    hideSpinner();
  }
}

function renderSearchResults(data) {
  const el = document.getElementById('searchResults');
  if (!data.results || data.results.length === 0) {
    el.innerHTML = emptyState('No incidents found for this query.');
    return;
  }
  const meta = `<p class="meta-info">Found <strong>${data.total_found}</strong> incidents ·
    Method: <strong>${data.search_method}</strong> · ${data.latency_ms.toFixed(0)} ms</p>`;
  const cards = data.results.map(r => `
    <div class="incident-card">
      <div class="incident-header">
        <span class="incident-id">${r.id}</span>
        <span class="incident-rank">#${r.rank} · Score ${(r.score || 0).toFixed(3)}</span>
      </div>
      <div class="incident-content">${r.content.substring(0, 280)}${r.content.length > 280 ? '…' : ''}</div>
      <div class="meta-chips">
        ${r.severity ? `<span class="chip ${severityClass(r.severity)}">${r.severity.toUpperCase()}</span>` : ''}
        ${r.incident_type ? `<span class="chip">${r.incident_type}</span>` : ''}
        ${r.shipment_status ? `<span class="chip">${r.shipment_status}</span>` : ''}
        ${r.supplier_id ? `<span class="chip">Supplier: ${r.supplier_id}</span>` : ''}
        ${r.warehouse_location ? `<span class="chip">${r.warehouse_location}</span>` : ''}
        ${r.delivery_delay ? `<span class="chip score">⏱ ${r.delivery_delay}d delay</span>` : ''}
        ${r.inventory_level !== null ? `<span class="chip score">📦 ${Math.round(r.inventory_level)} units</span>` : ''}
        ${r.timestamp ? `<span class="chip score">${r.timestamp}</span>` : ''}
      </div>
    </div>`).join('');
  el.innerHTML = meta + cards;
}

document.getElementById('searchQuery').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

// ─── RECOMMENDATIONS ──────────────────────────────────────────────────────────
async function doRecommend() {
  const query = document.getElementById('recQuery').value.trim();
  if (!query) return alert('Please enter a query.');

  const body = {
    query,
    evaluate_quality: document.getElementById('evalQuality').checked,
  };
  const sev = document.getElementById('recSeverity').value;
  if (sev) body.severity = sev;

  showSpinner();
  try {
    const data = await apiPost('/recommendations', body);
    renderRecommendations(data);
  } catch (e) {
    document.getElementById('recResults').innerHTML = errorBox(e.message);
  } finally {
    hideSpinner();
  }
}

function renderRecommendations(data) {
  const el = document.getElementById('recResults');
  const rs = data.risk_assessment;
  const level = rs.risk_level;
  const score = rs.overall_score;
  const color = riskColor(score);

  const riskHtml = `
    <div class="risk-panel">
      <h3>Risk Assessment — ${riskLabel(level)}</h3>
      ${riskBar('Overall Risk', score, color)}
      ${riskBar('Supplier Risk', rs.supplier_risk, riskColor(rs.supplier_risk))}
      ${riskBar('Inventory Risk', rs.inventory_risk, riskColor(rs.inventory_risk))}
      ${riskBar('Shipment Risk', rs.shipment_risk, riskColor(rs.shipment_risk))}
      ${riskBar('Demand Risk', rs.demand_risk, riskColor(rs.demand_risk))}
      ${rs.risk_factors.length ? `
        <div class="section-title" style="margin-top:12px">Risk Factors</div>
        <ul class="list-items">${rs.risk_factors.map(f => `<li>${f}</li>`).join('')}</ul>
      ` : ''}
    </div>`;

  const meta = `<p class="meta-info">Confidence: ${(data.confidence_score * 100).toFixed(0)}% · ${data.latency_ms.toFixed(0)} ms
    ${data.evaluation_score !== null && data.evaluation_score !== undefined
      ? ` · LLM Judge: <strong>${(data.evaluation_score * 10).toFixed(1)}/10</strong> (${data.llm_judge_verdict})`
      : ''}</p>`;

  const summary = data.summary ? `<div class="summary-box">${data.summary}</div>` : '';

  const recs = (data.recommendations || []).map(r => `
    <div class="rec-card">
      <div class="rec-priority">Priority ${r.priority}</div>
      <div class="rec-action">${r.action}</div>
      <div class="rec-meta">
        <span>⏰ <strong>${r.timeline}</strong></span>
        <span>👤 <strong>${r.owner}</strong></span>
        <span>🎯 ${r.expected_impact}</span>
      </div>
    </div>`).join('');

  el.innerHTML = meta + riskHtml + summary + `<div class="section-title">Mitigation Recommendations</div>` + recs;
}

function riskBar(label, score, colorClass) {
  const pct = Math.round(score * 100);
  return `<div class="risk-row">
    <span class="risk-label">${label}</span>
    <div class="risk-bar-wrap"><div class="risk-bar ${colorClass}" style="width:${pct}%"></div></div>
    <span class="risk-value" style="color:var(--${colorClass === 'low' ? 'success' : colorClass === 'medium' ? 'navy' : colorClass === 'high' ? 'warning' : 'danger'})">${pct}%</span>
  </div>`;
}

document.getElementById('recQuery').addEventListener('keydown', e => {
  if (e.key === 'Enter') doRecommend();
});

// ─── MULTI-AGENT ─────────────────────────────────────────────────────────────
async function doAgentAnalysis() {
  const query = document.getElementById('agentQuery').value.trim();
  if (!query) return alert('Please enter a query.');

  const body = {
    query,
    include_all_agents: document.getElementById('allAgents').checked,
  };
  const supplier = document.getElementById('agentSupplier').value.trim();
  const warehouse = document.getElementById('agentWarehouse').value.trim();
  if (supplier) body.supplier_id = supplier;
  if (warehouse) body.warehouse_location = warehouse;

  showSpinner();
  try {
    const data = await apiPost('/agents/analyze', body);
    renderAgentResults(data);
  } catch (e) {
    document.getElementById('agentResults').innerHTML = errorBox(e.message);
  } finally {
    hideSpinner();
  }
}

function renderAgentResults(data) {
  const el = document.getElementById('agentResults');
  const color = riskColor(data.consolidated_risk_score);
  const pct = Math.round(data.consolidated_risk_score * 100);

  const meta = `<p class="meta-info">
    Agents: <strong>${data.agents_invoked.join(', ')}</strong> ·
    Consolidated Risk: <strong style="color:var(--${color === 'low' ? 'success' : color === 'medium' ? 'blue-500' : color === 'high' ? 'warning' : 'danger'})">${pct}%</strong> ·
    ${data.latency_ms.toFixed(0)} ms
  </p>`;

  const summary = data.summary ? `<div class="summary-box">${data.summary}</div>` : '';

  const agentCards = data.agent_results.map(a => `
    <div class="agent-card ${a.escalated ? 'escalated' : ''}">
      <div class="agent-header">
        <span class="agent-name">${a.agent_name}</span>
        <span class="agent-score" style="color:var(--${riskColor(a.risk_score) === 'low' ? 'success' : riskColor(a.risk_score) === 'medium' ? 'blue-500' : riskColor(a.risk_score) === 'high' ? 'warning' : 'danger'})">
          Risk: ${Math.round(a.risk_score * 100)}%
        </span>
      </div>
      ${a.escalated ? `<div class="escalation-badge">⚠ ESCALATED — ${a.escalation_reason || ''}</div>` : ''}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          <div class="section-title">Findings</div>
          <ul class="list-items">${a.findings.map(f => `<li>${f}</li>`).join('')}</ul>
        </div>
        <div>
          <div class="section-title">Recommendations</div>
          <ul class="list-items">${a.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
        </div>
      </div>
    </div>`).join('');

  const topRecs = (data.consolidated_recommendations || []).slice(0, 5).map((r, i) => `
    <div class="rec-card"><div class="rec-priority">Action ${i + 1}</div><div class="rec-action">${r}</div></div>
  `).join('');

  const escalations = (data.escalation_chain || []).length
    ? `<div class="escalation-chain">
        <div class="section-title">A2A Escalation Chain</div>
        ${data.escalation_chain.map(e => `<div class="escalation-item">⚡ ${e}</div>`).join('')}
       </div>` : '';

  const proactive = (data.proactive_alerts || []).length
    ? `<div class="section-title" style="margin-top:16px">Proactive Alerts</div>
       <div class="tag-list">${data.proactive_alerts.map(a => `<span class="tag">${a.replace('[ALERT]','').trim()}</span>`).join('')}</div>` : '';

  el.innerHTML = meta + summary
    + `<div class="section-title">Agent Results</div>` + agentCards
    + escalations
    + (topRecs ? `<div class="section-title">Consolidated Recommendations</div>` + topRecs : '')
    + proactive;
}

document.getElementById('agentQuery').addEventListener('keydown', e => {
  if (e.key === 'Enter') doAgentAnalysis();
});

// ─── DASHBOARD ────────────────────────────────────────────────────────────────
async function loadDashboard() {
  showSpinner();
  try {
    const data = await apiGet('/analytics/dashboard');
    renderDashboard(data);
  } catch (e) {
    document.getElementById('dashboardContent').innerHTML = errorBox(e.message);
  } finally {
    hideSpinner();
  }
}

function renderDashboard(d) {
  const el = document.getElementById('dashboardContent');
  const trendColor = d.disruption_trend === 'deteriorating' ? 'danger' : d.disruption_trend === 'improving' ? 'success' : 'warning';

  const stats = `
    <div class="dash-grid">
      <div class="dash-stat"><div class="stat-val">${d.total_incidents}</div><div class="stat-label">Total Incidents</div></div>
      <div class="dash-stat danger"><div class="stat-val">${d.critical_incidents}</div><div class="stat-label">Critical Incidents</div></div>
      <div class="dash-stat warning"><div class="stat-val">${d.average_delivery_delay.toFixed(1)}d</div><div class="stat-label">Avg Delivery Delay</div></div>
      <div class="dash-stat"><div class="stat-val">$${Math.round(d.average_transportation_cost).toLocaleString()}</div><div class="stat-label">Avg Transport Cost</div></div>
      <div class="dash-stat"><div class="stat-val">${d.recent_anomalies}</div><div class="stat-label">Recent High Delays</div></div>
      <div class="dash-stat ${trendColor}"><div class="stat-val">${d.disruption_trend}</div><div class="stat-label">Disruption Trend</div></div>
    </div>`;

  const suppliers = d.high_risk_suppliers.length
    ? `<div class="section-title">High Risk Suppliers</div>
       <div class="tag-list">${d.high_risk_suppliers.map(s => `<span class="tag chip critical">${s}</span>`).join('')}</div>` : '';

  const stockouts = d.stockout_risk_locations.length
    ? `<div class="section-title">Stockout Risk Locations</div>
       <div class="tag-list">${d.stockout_risk_locations.map(s => `<span class="tag chip high">${s}</span>`).join('')}</div>` : '';

  const incidentTypes = Object.entries(d.top_incident_types || {})
    .sort((a, b) => b[1] - a[1])
    .map(([t, c]) => `<span class="tag">${t}: <strong>${c}</strong></span>`).join('');

  const severityDist = Object.entries(d.severity_distribution || {})
    .map(([s, c]) => `<span class="tag chip ${severityClass(s)}">${s}: ${c}</span>`).join('');

  el.innerHTML = stats + suppliers + stockouts
    + `<div class="section-title">Incident Types</div><div class="tag-list">${incidentTypes}</div>`
    + `<div class="section-title">Severity Distribution</div><div class="tag-list">${severityDist}</div>`;
}

// ─── ANOMALIES ────────────────────────────────────────────────────────────────
async function loadAnomalies() {
  const contamination = parseFloat(document.getElementById('contamination').value) || 0.05;
  showSpinner();
  try {
    const data = await apiGet(`/analytics/anomalies?contamination=${contamination}`);
    renderAnomalies(data);
  } catch (e) {
    document.getElementById('anomalyContent').innerHTML = errorBox(e.message);
  } finally {
    hideSpinner();
  }
}

function renderAnomalies(data) {
  const el = document.getElementById('anomalyContent');
  const meta = `<p class="meta-info">Detected <strong>${data.total_anomalies}</strong> anomalies using ${data.detection_method}</p>`;

  const insights = (data.correlation_insights || []).map(i => `
    <div class="insight-item">
      <span class="insight-icon">🔍</span>
      <span class="insight-text">${i}</span>
    </div>`).join('');

  const anomalies = (data.anomalies || []).slice(0, 15).map(a => `
    <div class="anomaly-card">
      <span class="anomaly-score">Score: ${a.anomaly_score.toFixed(3)}</span>
      <div class="anomaly-desc">${a.description}</div>
      <div style="margin-bottom:8px">
        <span class="chip ${severityClass(a.severity)}">${a.severity}</span>
        ${a.timestamp ? `<span class="chip score">${a.timestamp}</span>` : ''}
        <span class="chip score">ID: ${a.incident_id}</span>
      </div>
      <div class="anomaly-features">
        ${a.anomalous_features.map(f => `<span class="anomaly-feature">${f}</span>`).join('')}
      </div>
    </div>`).join('');

  el.innerHTML = meta
    + (insights ? `<div class="section-title">Correlation Insights</div><div style="margin-bottom:16px">${insights}</div>` : '')
    + (anomalies ? `<div class="section-title">Anomalous Incidents</div>` + anomalies : '<p class="meta-info">No anomalies detected.</p>');
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function emptyState(msg) {
  return `<div class="empty-state"><div class="icon">🔍</div><p>${msg}</p></div>`;
}
function errorBox(msg) {
  return `<div class="error-box">⚠ Error: ${msg}</div>`;
}
