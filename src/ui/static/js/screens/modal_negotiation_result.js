// F-45 Negotiation Result modal. Top of the FA modal stack.
import { openModal, closeModal, closeAllModals } from '../modal.js';

// result = NegotiationResultView { ok, accepted, outcome, player_name,
//                                  cap_impact, message }
export function openResultModal(result) {
  const accepted = !!result.accepted;
  const cls = accepted ? 'mdl-banner--accepted' : 'mdl-banner--rejected';
  const head = accepted ? 'Signed' : 'Not Signed';
  const body = `
    <div class="mdl-banner ${cls}">${_esc(head)}: ${_esc(result.player_name)}</div>
    <p>${_esc(result.message)}</p>
    ${accepted ? `<div class="mdl-row"><span class="mdl-label">Cap impact</span><span class="mdl-value">${_esc(result.cap_impact)}</span></div>` : ''}
    <div class="mdl-actions">
      <button class="btn btn-primary" data-result-done type="button">Done</button>
    </div>`;

  openModal({
    id: 'negotiation-result',
    title: 'Negotiation Result',
    contentHTML: body,
    backdropDismissable: false,
    onClose: () => {
      // Closing F-45 unwinds the whole stack and returns to FA Market.
      closeAllModals();
      window.refreshContextBar?.();
      if (location.hash !== '#/front-office/fa-market') {
        location.hash = '#/front-office/fa-market';
      } else {
        window.reloadRoute?.();
      }
    },
    onMount: (el) => {
      el.querySelector('[data-result-done]')?.addEventListener(
        'click', () => closeModal('negotiation-result'));
    },
  });
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
