// Cut-confirmation modal (reuses the generic modal framework).
import { openModal, closeModal, closeAllModals } from '../modal.js';
import { api } from '../api.js';

// cut = PlayerView.contract.cut { can_cut, player_id, player_name,
//                                 dead_cap, current_cap_space, note }
export function openCutModal(cut) {
  const body = `
    <p>Release <strong>${_esc(cut.player_name)}</strong>?</p>
    <div class="mdl-row"><span class="mdl-label">Dead cap created</span><span class="mdl-value">${_esc(cut.dead_cap)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Cap space (now)</span><span class="mdl-value">${_esc(cut.current_cap_space)}</span></div>
    <div class="mdl-error" data-cut-error hidden></div>
    <div class="mdl-actions">
      <button class="btn btn-secondary" data-cut-cancel type="button">Cancel</button>
      <button class="btn btn-primary" data-cut-confirm type="button">Confirm Cut</button>
    </div>`;

  openModal({
    id: 'cut-confirm',
    title: 'Release Player',
    contentHTML: body,
    onMount: (el) => {
      const errEl = el.querySelector('[data-cut-error]');
      el.querySelector('[data-cut-cancel]')?.addEventListener(
        'click', () => closeModal('cut-confirm'));

      el.querySelector('[data-cut-confirm]')?.addEventListener('click', async () => {
        const btn = el.querySelector('[data-cut-confirm]');
        btn.disabled = true; btn.textContent = 'Releasing…';
        const res = await api.doCutPlayer(cut.player_id);
        if (!res || res.ok === false) {
          btn.disabled = false; btn.textContent = 'Confirm Cut';
          if (errEl) { errEl.textContent = res?.error ?? 'Cut failed.'; errEl.hidden = false; }
          return;
        }
        closeAllModals();
        window.refreshContextBar?.();
        // Player is no longer on the roster — go back to the roster list.
        location.hash = '#/team/roster';
      });
    },
  });
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
