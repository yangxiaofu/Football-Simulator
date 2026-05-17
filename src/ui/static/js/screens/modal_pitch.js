// F-43 Pitch Meeting modal — informational; CTA opens F-44 Offer Builder.
import { openModal, closeModal } from '../modal.js';
import { api } from '../api.js';
import { openOfferModal } from './modal_offer.js';

export async function openPitchModal(playerId) {
  const data = await api.getPitchMeeting(playerId);
  if (!data || data.ok === false) {
    openModal({
      id: 'pitch-meeting', title: 'Pitch Meeting',
      contentHTML: `<p class="mdl-error">${_esc(data?.error ?? 'Failed to load.')}</p>`,
    });
    return;
  }

  const canOffer = !!data.can_offer;
  const body = `
    <div class="mdl-row"><span class="mdl-label">Player</span><span class="mdl-value">${_esc(data.player_name)} · ${_esc(data.position)} · OVR ${_esc(data.overall)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Asking salary</span><span class="mdl-value">${_esc(data.asking_salary)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Market (low / fair / premium)</span><span class="mdl-value">${_esc(data.market.low)} / ${_esc(data.market.fair)} / ${_esc(data.market.premium)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Interest</span><span class="mdl-value">${_esc(data.interest_label)}</span></div>
    <p class="mdl-note">"${_esc(data.interest_signal)}"</p>
    ${data.note ? `<p class="mdl-error">${_esc(data.note)}</p>` : ''}
    <div class="mdl-actions">
      <button class="btn btn-secondary" data-pm-cancel type="button">Cancel</button>
      <button class="btn btn-primary" data-pm-offer type="button" ${canOffer ? '' : 'disabled'}>Make Offer →</button>
    </div>`;

  openModal({
    id: 'pitch-meeting',
    title: 'Pitch Meeting',
    contentHTML: body,
    onMount: (el) => {
      el.querySelector('[data-pm-cancel]')?.addEventListener(
        'click', () => closeModal('pitch-meeting'));
      el.querySelector('[data-pm-offer]')?.addEventListener('click', () => {
        if (canOffer) openOfferModal(playerId);
      });
    },
  });
}

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
