// Restructure modal (reuses the generic modal framework).
import { openModal, closeModal, closeAllModals } from '../modal.js';
import { api } from '../api.js';

// rv = PlayerView.contract.restructure { can_restructure, player_id,
//   player_name, current_season, base_salary, max_convertible,
//   current_cap_hit, years:[{season_year,base_salary,prorated_bonus,cap_hit}], note }
export function openRestructureModal(rv) {
  const rows = (rv.years || []).map(y =>
    `<tr><td>${y.season_year}</td><td>${_esc(y.base_salary)}</td><td>${_esc(y.prorated_bonus)}</td><td>${_esc(y.cap_hit)}</td></tr>`
  ).join('');

  const body = `
    <div class="mdl-row"><span class="mdl-label">Player</span><span class="mdl-value">${_esc(rv.player_name)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Current-year cap hit</span><span class="mdl-value">${_esc(rv.current_cap_hit)}</span></div>
    <table class="mdl-schedule">
      <thead><tr><th>Year</th><th>Base</th><th>Bonus</th><th>Cap Hit</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="mdl-form" style="margin-top:var(--space-4)">
      <div class="mdl-field">
        <label for="rs-amt">Convert to bonus ($) — max ${rv.max_convertible.toLocaleString()}</label>
        <input id="rs-amt" type="number" min="1" max="${d_int(rv.max_convertible)}" value="${d_int(Math.floor(rv.max_convertible / 2))}">
      </div>
    </div>
    <div class="mdl-error" data-rs-error hidden></div>
    <div class="mdl-actions">
      <button class="btn btn-secondary" data-rs-cancel type="button">Cancel</button>
      <button class="btn btn-primary" data-rs-submit type="button">Restructure</button>
    </div>`;

  openModal({
    id: 'restructure',
    title: 'Restructure Contract',
    contentHTML: body,
    size: 'lg',
    onMount: (el) => {
      const errEl = el.querySelector('[data-rs-error]');
      el.querySelector('[data-rs-cancel]')?.addEventListener(
        'click', () => closeModal('restructure'));

      el.querySelector('[data-rs-submit]')?.addEventListener('click', async () => {
        const amt = parseInt(el.querySelector('#rs-amt').value, 10);
        if (!Number.isFinite(amt) || amt <= 0 || amt > rv.max_convertible) {
          if (errEl) {
            errEl.textContent = `Amount must be 1–${rv.max_convertible.toLocaleString()}.`;
            errEl.hidden = false;
          }
          return;
        }
        const btn = el.querySelector('[data-rs-submit]');
        btn.disabled = true; btn.textContent = 'Restructuring…';
        const res = await api.doRestructureContract(
          rv.player_id, { amount_to_convert: amt });
        if (!res || res.ok === false) {
          btn.disabled = false; btn.textContent = 'Restructure';
          if (errEl) { errEl.textContent = res?.error ?? 'Restructure failed.'; errEl.hidden = false; }
          return;
        }
        closeAllModals();
        window.refreshContextBar?.();
        window.reloadRoute?.();   // re-render the player card with new cap
      });
    },
  });
}

function d_int(v) { return parseInt(v, 10) || 0; }

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
