// F-42 FA Player Card — Pattern B thin wrapper
import { api } from '../api.js';
import { initDetailScreen } from './detail.js';
import { openPitchModal } from './modal_pitch.js';

export async function init(container, params) {
  const playerId = params?.playerId;
  if (!playerId) {
    container.innerHTML = '<div class="error-card">No player ID specified.</div>';
    return;
  }

  const data = await api.getFaPlayer(playerId);
  if (data.ok === false) {
    container.innerHTML = `<div class="error-card">${data.error}</div>`;
    return;
  }

  const h = data.header;
  const headerHTML = `
    <div class="player-id-block">
      <span class="player-name">${_esc(h.full_name)}</span>
      <span class="player-pos-team">${_esc(h.position)} · <em>Free Agent</em></span>
      <span class="player-meta">${h.age} yrs · ${_esc(h.experience_label)} · ${_esc(h.draft_label)}</span>
    </div>
    <div class="player-grades">
      <span class="grade-pill grade-${_gradeCss(h.overall)}">OVR ${_esc(h.overall)}</span>
      ${h.clutch ? `<span class="grade-pill">CLUTCH ${_esc(h.clutch)}</span>` : ''}
    </div>`;

  const tabs = [
    { key: 'overview',         label: 'Overview',         contentHTML: _buildOverview(data) },
    { key: 'stats',            label: 'Stats',            contentHTML: _buildStats(data) },
    { key: 'career',           label: 'Career History',   contentHTML: _buildCareer(data) },
    { key: 'market_interest',  label: 'Market Interest',  contentHTML: _buildMarket(data) },
    { key: 'contract_history', label: 'Contract History', contentHTML: _buildContractHistory(data) },
  ];

  initDetailScreen(container, {
    headerHTML,
    tabs,
    defaultTab: 'overview',
    actions: data.actions ?? [],
    onBack: () => { location.hash = '#/front-office/fa-market'; },
    onAction: async (key) => {
      if (key === 'pitch_meeting') {
        openPitchModal(playerId);
      } else if (key === 'add_to_watchlist') {
        const r = await api.doAddToWatchlist(playerId);
        if (r && r.ok !== false) window.reloadRoute?.();  // flips ★ label
      }
    },
  });
}

function _buildOverview(data) {
  const ov = data.overview;
  const attrsHTML = (ov.key_attributes ?? []).map(a =>
    `<div class="attr-line"><span>${_esc(a.label)}</span><span class="grade-${_gradeCss(a.grade)}">${_esc(a.grade)}</span></div>`
  ).join('');
  const seasonHTML = ov.season_summary
    ? `<div class="card">
         <div class="card__header">Current Season</div>
         <div class="card__body"><p>GP: ${ov.season_summary.games_played} · ${_esc(ov.season_summary.stat_line)}</p></div>
       </div>`
    : '';
  return `
    <div class="overview-grid">
      <div class="card"><div class="card__header">Key Attributes</div><div class="card__body">${attrsHTML}</div></div>
      <div class="card">
        <div class="card__header">Asking Salary</div>
        <div class="card__body">
          <span class="salary-estimate">${_esc(ov.asking_salary ?? '—')}</span>
          <p class="salary-note">Estimated market value</p>
        </div>
      </div>
      ${seasonHTML}
    </div>`;
}

function _buildStats(data) {
  const s = data.stats;
  if (!s?.current_season) return '<p class="card__empty" style="padding:var(--space-4)">No stats this season.</p>';
  const cs = s.current_season;
  return `<div style="padding:var(--space-4)"><p>Season ${cs.season_year} · GP: ${cs.games_played}</p><p>${_esc(cs.stat_line)}</p></div>`;
}

function _buildCareer(data) {
  const h = data.history;
  if (!h) return '<p class="card__empty" style="padding:var(--space-4)">No career data available.</p>';
  return `
    <div style="padding:var(--space-4)">
      <p>${h.seasons_played ?? 0} seasons · Peak OVR ${_esc(h.peak_overall ?? '—')} · Pro Bowls: ${h.career_pro_bowls ?? 0}</p>
      <p>${_esc(h.draft_info)}</p>
    </div>`;
}

function _buildMarket(data) {
  const m = data.market_interest;
  const teamsHTML = (m.top_preferred_teams ?? []).map(t =>
    `<div class="team-line">${_esc(t.name)} (${_esc(t.abbr)})</div>`
  ).join('') || '<p class="card__empty">No destination data available.</p>';
  return `
    <div style="padding:var(--space-4)">
      <div class="interest-tier tier-${m.interest_tier}">${_esc(m.interest_label)} Interest</div>
      <p class="interest-signal">"${_esc(m.interest_signal)}"</p>
      <h4 style="margin:var(--space-3) 0 var(--space-2)">Top Preferred Destinations</h4>
      ${teamsHTML}
    </div>`;
}

function _buildContractHistory(data) {
  const rows = data.contract_history ?? [];
  if (!rows.length) return '<p class="card__empty" style="padding:var(--space-4)">No prior contracts on record.</p>';
  return `<div style="padding:var(--space-4)">` + rows.map(r =>
    `<div class="contract-hist-row">
       <strong>${_esc(r.team_name)}</strong> · ${_esc(r.seasons)} · ${_esc(r.aav)} · ${_esc(r.type)}
     </div>`
  ).join('') + '</div>';
}

function _gradeCss(grade) {
  const map = { 'A+': 'ap', 'A': 'a', 'A-': 'am', 'B+': 'bp', 'B': 'b', 'B-': 'bm',
                'C+': 'cp', 'C': 'c', 'C-': 'cm', 'D+': 'dp', 'D': 'd', 'F': 'f' };
  return map[grade] ?? 'c';
}

function _esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
