// screens/player.js — thin wrapper over Pattern B detail template
import { initDetailScreen } from './detail.js';
import { api } from '../api.js';
import { openCutModal } from './modal_cut_confirm.js';
import { openRestructureModal } from './modal_restructure.js';

export async function init(container, params) {
  container.innerHTML = '<div class="loading-spinner" style="padding:var(--space-5);color:var(--text-muted)">Loading…</div>';
  const data = await api.getPlayer(params?.playerId);
  if (!data || data.ok === false) {
    container.innerHTML = `<div class="alert alert-danger" style="margin:var(--space-4)">Player error: ${String(data?.error ?? 'Unknown')}</div>`;
    return;
  }

  const h = data.header;
  const headerHTML = `
    <div class="player-photo-placeholder">🏈</div>
    <div class="player-identity">
      <div class="player-name">${_esc(h.full_name)}</div>
      <div class="player-meta">${_esc(h.position)} · ${_esc(h.team_name)} · Age ${h.age} · ${_esc(h.experience_label)}</div>
      <div class="player-meta">${_esc(h.draft_label)}${h.college ? ' · ' + _esc(h.college) : ''}</div>
      <div class="player-grades">
        <span>OVR <span class="grade-badge ${gradeCssClass(h.overall)}">${_esc(h.overall)}</span></span>
        <span>CLUTCH <span class="grade-badge ${gradeCssClass(h.clutch)}">${_esc(h.clutch)}</span></span>
      </div>
    </div>`;

  const tabs = [
    { key: 'overview',     label: 'Overview',     contentHTML: _buildOverview(data.overview) },
    { key: 'stats',        label: 'Stats',        contentHTML: _buildStats(data.stats) },
    { key: 'contract',     label: 'Contract',     contentHTML: _buildContract(data.contract) },
    { key: 'satisfaction', label: 'Satisfaction', contentHTML: _buildSatisfaction(data.satisfaction) },
    { key: 'history',      label: 'History',      contentHTML: _buildHistory(data.history) },
  ];

  initDetailScreen(container, {
    headerHTML, tabs, defaultTab: 'overview', actions: data.actions,
    onBack: () => history.back(),
    onAction: (key) => {
      if (key === 'cut_player') {
        openCutModal(data.contract.cut);
      } else if (key === 'restructure_contract') {
        openRestructureModal(data.contract.restructure);
      }
    },
  });
}

function _buildOverview(ov) {
  const attrs = ov.key_attributes.map(a =>
    `<div class="attr-label">${_esc(a.label)}</div><div class="attr-grade"><span class="grade-badge ${gradeCssClass(a.grade)}">${_esc(a.grade)}</span></div>`
  ).join('');

  const contractHTML = ov.contract_snapshot
    ? `<p style="margin:var(--space-2) 0 var(--space-1)"><strong>Contract:</strong> ${_esc(ov.contract_snapshot.summary_line)}</p>
       ${ov.contract_snapshot.years_remaining.map(y => `<div class="contract-year-row"><span>${y.season_year}</span><span>${_esc(y.cap_hit)} cap</span></div>`).join('')}
       <p style="font-size:var(--text-small);color:var(--text-muted)">Dead cap if cut: ${_esc(ov.contract_snapshot.dead_cap_if_cut)}</p>`
    : '<p style="color:var(--text-muted)">No active contract.</p>';

  const statsHTML = ov.season_summary
    ? `<p style="margin:var(--space-2) 0"><strong>This Season:</strong> ${_esc(ov.season_summary.stat_line)}</p>`
    : '<p style="color:var(--text-muted)">No stats this season.</p>';

  return `
    <section style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">KEY ATTRIBUTES</h3>
      <div class="attr-grid">${attrs}</div>
    </section>
    <section style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">CONTRACT</h3>
      ${contractHTML}
    </section>
    <section style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">SEASON STATS</h3>
      ${statsHTML}
    </section>
    <section>
      <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">SATISFACTION</h3>
      <p>${_esc(ov.satisfaction_status)}</p>
    </section>`;
}

function _buildStats(st) {
  const history = st.season_history.length
    ? st.season_history.map(s =>
        `<div class="stat-season-row">
          <strong>${s.season_year}</strong> · ${_esc(s.team_abbr)} · ${_esc(s.stat_line)}
          ${s.awards.length ? ' · <em>' + s.awards.join(', ') + '</em>' : ''}
        </div>`).join('')
    : '<p style="color:var(--text-muted)">No season history yet.</p>';

  const career = Object.entries(st.career_totals).map(([k,v]) =>
    `<div class="ts-row"><span class="ts-label">${_esc(k)}</span><span class="ts-value">${_esc(v)}</span></div>`
  ).join('');

  return `
    <section style="margin-bottom:var(--space-4)">
      <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">SEASON HISTORY</h3>
      ${history}
    </section>
    ${career ? `<section><h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">CAREER TOTALS</h3>${career}</section>` : ''}`;
}

function _buildContract(ct) {
  if (!ct.has_contract) return '<p style="color:var(--text-muted)">No active contract.</p>';
  const years = ct.years.map(y =>
    `<div class="contract-year-row">
      <span>${y.season_year}</span>
      <span>${_esc(y.base_salary)} base</span>
      <span>${_esc(y.cap_hit)} cap</span>
      <span style="color:var(--text-muted)">${_esc(y.dead_cap)} dead</span>
    </div>`).join('');
  return `
    <div class="ts-row"><span class="ts-label">Type</span><span class="ts-value">${_esc(ct.contract_type)}</span></div>
    <div class="ts-row"><span class="ts-label">AAV</span><span class="ts-value">${_esc(ct.aav)}</span></div>
    <div class="ts-row"><span class="ts-label">Total Value</span><span class="ts-value">${_esc(ct.total_value)}</span></div>
    <div class="ts-row"><span class="ts-label">Years</span><span class="ts-value">${ct.total_years}</span></div>
    <div class="ts-row"><span class="ts-label">Signed</span><span class="ts-value">${ct.signed_season}</span></div>
    <div style="margin-top:var(--space-3)">${years}</div>`;
}

function _buildSatisfaction(sat) {
  const events = sat.events.length
    ? sat.events.map(e =>
        `<div class="sat-event-row">
          <span style="color:var(--text-muted)">Wk ${e.week}</span>
          <span class="sat-delta ${e.delta >= 0 ? 'positive' : 'negative'}">${e.delta >= 0 ? '+' : ''}${e.delta}</span>
          <span>${_esc(e.reason)}</span>
          <span style="margin-left:auto;color:var(--text-muted)">${e.new_score}</span>
        </div>`).join('')
    : '<p style="color:var(--text-muted)">No events this season.</p>';
  return `
    <div class="ts-row" style="margin-bottom:var(--space-3)">
      <span class="ts-label">Status</span>
      <span class="ts-value">${_esc(sat.tier_label)}</span>
    </div>
    <div class="ts-row" style="margin-bottom:var(--space-3)">
      <span class="ts-label">Score</span>
      <span class="ts-value">${sat.current_score}/100</span>
    </div>
    <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin-bottom:var(--space-2)">EVENTS</h3>
    ${events}`;
}

function _buildHistory(hist) {
  const timeline = hist.timeline.length
    ? hist.timeline.map(t => `<div class="stat-season-row">${_esc(t.label)}</div>`).join('')
    : '<p style="color:var(--text-muted)">No notable events yet.</p>';
  return `
    <div class="ts-row"><span class="ts-label">Draft</span><span class="ts-value">${_esc(hist.draft_info)}</span></div>
    ${hist.college ? `<div class="ts-row"><span class="ts-label">College</span><span class="ts-value">${_esc(hist.college)}</span></div>` : ''}
    <div class="ts-row"><span class="ts-label">Seasons</span><span class="ts-value">${hist.seasons_played}</span></div>
    <div class="ts-row"><span class="ts-label">Pro Bowls</span><span class="ts-value">${hist.career_pro_bowls}</span></div>
    <div class="ts-row"><span class="ts-label">All-Pro</span><span class="ts-value">${hist.career_all_pro}</span></div>
    <div class="ts-row"><span class="ts-label">Peak OVR</span><span class="ts-value">${_esc(hist.peak_overall)}</span></div>
    <h3 style="font-size:var(--text-body);font-weight:600;color:var(--text-secondary);margin:var(--space-3) 0 var(--space-2)">TIMELINE</h3>
    ${timeline}`;
}

function gradeCssClass(grade) {
  const map = {'A+':'ap','A':'a','A-':'am','B+':'bp','B':'b','B-':'bm','C+':'cp','C':'c','C-':'cm','D+':'dp','D':'d','F':'f'};
  return 'grade-' + (map[grade] ?? 'f');
}

function _esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
