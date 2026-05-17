// SPA shell — hash-based router, context bar wiring, section tab nav
// Phase 6 Prompt 2 (Milestone 5.2): Team Dashboard live.
//
// Architecture: docs/ui/05_framework_implementation_plan.md §2, §5

import { api } from './api.js';
import { init as dashboardInit }    from './screens/dashboard.js';
import { init as rosterInit }       from './screens/roster.js';
import { init as playerInit }       from './screens/player.js';
import { init as standingsInit }    from './screens/standings.js';
import { init as leadersInit }      from './screens/leaders.js';
import { init as transactionsInit } from './screens/transactions.js';
import { init as scheduleInit }     from './screens/schedule.js';
import { init as gamePreviewInit }  from './screens/game_preview.js';
import { init as gameRecapInit }    from './screens/game_recap.js';
import { init as frontOfficeInit }  from './screens/front_office.js';
import { init as faMarketInit }     from './screens/fa_market.js';
import { init as faPlayerInit }     from './screens/fa_player.js';

// ── Routes ────────────────────────────────────────────────────────────────────

const ROUTES = {
  '/team/dashboard':          async (params) => { const c = getContent(); c.innerHTML = ''; await dashboardInit(c); },
  '/team/roster':             async (params) => { const c = getContent(); c.innerHTML = ''; await rosterInit(c, params); },
  '/team/player/:id':         async (params) => { const c = getContent(); c.innerHTML = ''; await playerInit(c, params); },
  '/league/standings':        async (params) => { const c = getContent(); c.innerHTML = ''; await standingsInit(c, params); },
  '/league/leaders':          async (params) => { const c = getContent(); c.innerHTML = ''; await leadersInit(c, params); },
  '/league/transactions':     async ()       => { const c = getContent(); c.innerHTML = ''; await transactionsInit(c); },
  '/league/team/:id/roster':  () => {
    const c = getContent();
    c.innerHTML = '<div class="placeholder-card"><h2>Other Team Roster</h2><p>Coming in a later prompt (Milestone 5.9).</p></div>';
  },
  '/schedule':                async ()       => { const c = getContent(); c.innerHTML = ''; await scheduleInit(c); },
  '/schedule/game/:id/preview': async (params) => { const c = getContent(); c.innerHTML = ''; await gamePreviewInit(c, params); },
  '/schedule/game/:id/recap':   async (params) => { const c = getContent(); c.innerHTML = ''; await gameRecapInit(c, params); },
  '/front-office':                  async () => { const c = getContent(); c.innerHTML = ''; await frontOfficeInit(c); },
  '/front-office/fa-market':        async () => { const c = getContent(); c.innerHTML = ''; await faMarketInit(c); },
  '/front-office/fa-player/:id':    async (params) => { const c = getContent(); c.innerHTML = ''; await faPlayerInit(c, params); },
  '/placeholder':             () => renderPlaceholderScreen(),
  '/dynasty':                 () => renderPlaceholder('Dynasty', '(5.11)'),
};

const DEFAULT_ROUTE = '/team/dashboard';

// Which section tab is active for each route prefix
const TAB_FOR_PATH = {
  '/team':         'tab-team',
  '/league':       'tab-league',
  '/schedule':     'tab-schedule',
  '/front-office': 'tab-frontoffice',
  '/dynasty':      'tab-dynasty',
};

// ── Router ────────────────────────────────────────────────────────────────────

function currentPath() {
  const hash = location.hash;
  return hash ? hash.slice(1) : DEFAULT_ROUTE;  // strip leading '#'
}

function matchRoute(path) {
  if (ROUTES[path]) return { handler: ROUTES[path], params: {} };
  const playerMatch = path.match(/^\/team\/player\/(\d+)$/);
  if (playerMatch) return { handler: ROUTES['/team/player/:id'], params: { playerId: parseInt(playerMatch[1]) } };
  const leagueTeamMatch = path.match(/^\/league\/team\/(\d+)\/roster$/);
  if (leagueTeamMatch) return { handler: ROUTES['/league/team/:id/roster'], params: { teamId: parseInt(leagueTeamMatch[1]) } };
  const gameMatch = path.match(/^\/schedule\/game\/(-?\d+)\/(preview|recap)$/);
  if (gameMatch) {
    const key = `/schedule/game/:id/${gameMatch[2]}`;
    return { handler: ROUTES[key], params: { gameId: parseInt(gameMatch[1]) } };
  }
  const faPlayerMatch = path.match(/^\/front-office\/fa-player\/(\d+)$/);
  if (faPlayerMatch) return { handler: ROUTES['/front-office/fa-player/:id'], params: { playerId: parseInt(faPlayerMatch[1]) } };
  if (path.match(/^\/placeholder(\/.*)?$/)) return { handler: ROUTES['/placeholder'], params: {} };
  return { handler: ROUTES[DEFAULT_ROUTE], params: {} };
}

function router() {
  const path = currentPath();
  if (!location.hash) {
    // Set hash without triggering another hashchange
    history.replaceState(null, '', '#' + DEFAULT_ROUTE);
  }
  const { handler, params } = matchRoute(path);
  handler(params);
  updateActiveTab(path);
}

// ── Content area ──────────────────────────────────────────────────────────────

function getContent() {
  return document.getElementById('content');
}

function renderPlaceholder(name, milestone) {
  const el = getContent();
  el.innerHTML = `
    <div class="placeholder-screen">
      <span class="placeholder-name">${name}</span>
      <span class="placeholder-milestone">${milestone}</span>
    </div>
  `;
}

function renderPlaceholderScreen() {
  const el = getContent();
  el.innerHTML = `
    <div class="fo-placeholder-screen">
      <h2>Coming Soon</h2>
      <p>This screen ships in a later milestone.</p>
    </div>
  `;
}

// ── Section tab highlighting ──────────────────────────────────────────────────

const TEAM_SUB_NAV = [
  { label: 'Dashboard',    route: '#/team/dashboard', active: true },
  { label: 'Roster',       route: '#/team/roster',    active: false },
  { label: 'Depth Chart',  route: null,               active: false },
  { label: 'Practice',     route: null,               active: false },
  { label: 'Cap',          route: null,               active: false },
  { label: 'Staff',        route: null,               active: false },
  { label: 'Scheme',       route: null,               active: false },
];

const LEAGUE_SUB_NAV = [
  { label: 'Standings',    route: '#/league/standings' },
  { label: 'Leaders',      route: '#/league/leaders' },
  { label: 'Transactions', route: '#/league/transactions' },
];

function updateActiveTab(path) {
  document.querySelectorAll('.section-tab').forEach(t => t.classList.remove('active'));

  let matchedTab = null;
  let matchedLen = 0;
  let matchedPrefix = '';
  for (const [prefix, tabId] of Object.entries(TAB_FOR_PATH)) {
    if (path.startsWith(prefix) && prefix.length > matchedLen) {
      matchedLen = prefix.length;
      matchedTab = tabId;
      matchedPrefix = prefix;
    }
  }
  if (matchedTab) {
    const el = document.getElementById(matchedTab);
    if (el) el.classList.add('active');
  }

  updateSubNav(matchedPrefix, path);
}

function updateSubNav(sectionPrefix, currentPath) {
  const rail = document.getElementById('sub-nav');
  if (!rail) return;

  if (sectionPrefix === '/team') {
    rail.innerHTML = TEAM_SUB_NAV.map(item => {
      const isActive = item.route && (
        ('#' + currentPath) === item.route ||
        (item.route === '#/team/roster' && currentPath.startsWith('/team/player/'))
      );
      const isDisabled = !item.route;
      const cls = ['sub-nav-item', isActive ? 'active' : '', isDisabled ? 'disabled' : ''].filter(Boolean).join(' ');
      const href = item.route ? `href="${item.route}"` : '';
      return `<a class="${cls}" ${href}>${item.label}</a>`;
    }).join('');
  } else if (sectionPrefix === '/league') {
    rail.innerHTML = LEAGUE_SUB_NAV.map(item => {
      const isActive = ('#' + currentPath) === item.route ||
        (item.route === '#/league/standings' && currentPath.startsWith('/league/team/'));
      const cls = ['sub-nav-item', isActive ? 'active' : ''].filter(Boolean).join(' ');
      return `<a class="${cls}" href="${item.route}">${item.label}</a>`;
    }).join('');
  } else if (sectionPrefix === '/front-office') {
    // front_office.js populates #sub-nav with mode-aware items on init.
    // shell.js must not overwrite it here — no-op while in this section.
  } else {
    rail.innerHTML = '';
  }
}

// ── Context bar ───────────────────────────────────────────────────────────────

async function loadContextBar() {
  try {
    const info = await api.getAppInfo();
    if (info.ok === false) {
      console.error('get_app_info error:', info.error);
      return;
    }

    document.getElementById('ctx-team-name').textContent = info.name ?? '—';
    document.getElementById('ctx-team-abbr').textContent = info.abbr ?? '';
    document.getElementById('ctx-week-label').textContent = info.week_label ?? '';
    document.getElementById('ctx-cap-space').textContent = (info.cap_space ?? '—') + ' cap';

    // Phase badge
    const badge = document.getElementById('ctx-phase-badge');
    if (badge) {
      const phase = (info.phase ?? 'regular').toLowerCase();
      badge.textContent = phaseLabel(phase);
      badge.className = 'badge badge-phase ' + phaseCssClass(phase);
    }
  } catch (err) {
    console.error('Context bar load failed:', err);
  }
}

function phaseLabel(phase) {
  const map = {
    regular: 'REG', playoffs: 'PLAYOFFS', preseason: 'PRE', offseason: 'OFF',
  };
  return map[phase] ?? phase.toUpperCase();
}

function phaseCssClass(phase) {
  const map = {
    regular: 'phase-reg', playoffs: 'phase-playoffs',
    preseason: 'phase-pre', offseason: 'phase-off',
  };
  return map[phase] ?? 'phase-off';
}

// ── Mutations: Continue / advance-week wiring (Phase 6 P5) ────────────────────

// Exposed for in-content Continue buttons (e.g. Game Recap) so the
// advance-week logic lives in exactly one place.
window.refreshContextBar = loadContextBar;

// Re-run the current route handler (used after a modal mutation so the
// underlying screen re-renders with committed state).
window.reloadRoute = router;

let _advanceInFlight = false;

window.runAdvanceWeek = async function runAdvanceWeek(onProgress) {
  if (_advanceInFlight) return false;  // single-flight guard (UI side)
  _advanceInFlight = true;
  try {
    const r = await api.doAdvanceWeek(onProgress);
    if (r.ok === false) {
      console.error('advance_week failed:', r.error);
      return false;
    }
    await loadContextBar();
    const userGameId = r.result && r.result.user_game_id;
    if (userGameId != null) {
      location.hash = `#/schedule/game/${userGameId}/recap`;
    } else {
      router();  // stay on current screen, re-render with new state
    }
    return true;
  } finally {
    _advanceInFlight = false;
  }
};

function wireContinueButton() {
  const btn = document.getElementById('btn-continue');
  if (!btn) return;
  btn.disabled = false;
  btn.removeAttribute('data-tooltip');
  btn.removeAttribute('title');
  btn.addEventListener('click', async () => {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Advancing…';
    const ok = await window.runAdvanceWeek((p, m) => {
      btn.textContent = m ? `${m}` : 'Advancing…';
    });
    btn.textContent = original;
    btn.disabled = false;
    if (ok === false) {
      const note = document.getElementById('ctx-saved');
      if (note) note.textContent = '⚠ Advance failed';
    }
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────

window.addEventListener('hashchange', router);

window.addEventListener('DOMContentLoaded', async () => {
  await loadContextBar();
  wireContinueButton();
  router();
});
