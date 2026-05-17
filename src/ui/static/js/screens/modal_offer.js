// F-44 Offer Builder modal — opens on top of F-43 (modal-over-modal).
import { openModal, closeModal } from '../modal.js';
import { api } from '../api.js';
import { openResultModal } from './modal_negotiation_result.js';

export async function openOfferModal(playerId) {
  const data = await api.getOfferBuilder(playerId);
  if (!data || data.ok === false) {
    openModal({
      id: 'offer-builder', title: 'Offer Builder',
      contentHTML: `<p class="mdl-error">${_esc(data?.error ?? 'Failed to load.')}</p>`,
    });
    return;
  }

  const d = data.defaults;
  const body = `
    <div class="mdl-row"><span class="mdl-label">Player</span><span class="mdl-value">${_esc(data.player_name)} · ${_esc(data.position)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Market (low / fair / premium)</span><span class="mdl-value">${_esc(data.market.low)} / ${_esc(data.market.fair)} / ${_esc(data.market.premium)}</span></div>
    <div class="mdl-row"><span class="mdl-label">Cap available</span><span class="mdl-value">${_esc(data.cap_available)}</span></div>
    <div class="mdl-form" style="margin-top:var(--space-4)">
      <div class="mdl-field"><label for="of-years">Years</label><input id="of-years" type="number" min="${d_int(data.bounds.min_years)}" max="${d_int(data.bounds.max_years)}" value="${d_int(d.years)}"></div>
      <div class="mdl-field"><label for="of-aav">AAV ($)</label><input id="of-aav" type="number" min="1" value="${d_int(d.aav)}"></div>
      <div class="mdl-field"><label for="of-sb">Signing bonus ($)</label><input id="of-sb" type="number" min="0" value="${d_int(d.signing_bonus)}"></div>
      <div class="mdl-field"><label for="of-gm">Guaranteed ($)</label><input id="of-gm" type="number" min="0" value="${d_int(d.guaranteed_money)}"></div>
    </div>
    <div class="mdl-error" data-of-error hidden></div>
    <div class="mdl-actions">
      <button class="btn btn-secondary" data-of-cancel type="button">Cancel</button>
      <button class="btn btn-primary" data-of-submit type="button">Submit Offer</button>
    </div>`;

  openModal({
    id: 'offer-builder',
    parent: 'pitch-meeting',
    title: 'Offer Builder',
    contentHTML: body,
    size: 'lg',
    onMount: (el) => {
      const errEl = el.querySelector('[data-of-error]');
      el.querySelector('[data-of-cancel]')?.addEventListener(
        'click', () => closeModal('offer-builder'));

      el.querySelector('[data-of-submit]')?.addEventListener('click', async () => {
        const years = parseInt(el.querySelector('#of-years').value, 10);
        const aav = parseInt(el.querySelector('#of-aav').value, 10);
        const sb = parseInt(el.querySelector('#of-sb').value, 10);
        const gm = parseInt(el.querySelector('#of-gm').value, 10);

        const err = _validate(years, aav, sb, gm, data.bounds);
        if (err) { _showErr(errEl, err); return; }

        const btn = el.querySelector('[data-of-submit]');
        btn.disabled = true; btn.textContent = 'Submitting…';
        const res = await api.doSignFreeAgent(playerId, {
          years, aav, signing_bonus: sb, guaranteed_money: gm,
        });
        if (!res || res.ok === false) {
          btn.disabled = false; btn.textContent = 'Submit Offer';
          _showErr(errEl, res?.error ?? 'Offer failed.');
          return;
        }
        openResultModal(res);   // F-45 on top
      });
    },
  });
}

function _validate(years, aav, sb, gm, b) {
  if (!Number.isFinite(years) || years < b.min_years || years > b.max_years)
    return `Years must be ${b.min_years}–${b.max_years}.`;
  if (!Number.isFinite(aav) || aav <= 0) return 'AAV must be greater than 0.';
  const total = aav * years;
  if (!Number.isFinite(sb) || sb < 0) return 'Signing bonus is invalid.';
  if (sb > total * b.max_signing_bonus_pct)
    return `Signing bonus exceeds ${Math.round(b.max_signing_bonus_pct * 100)}% of total value.`;
  if (!Number.isFinite(gm) || gm < 0) return 'Guaranteed money is invalid.';
  if (gm > total * b.max_guaranteed_pct)
    return `Guaranteed money exceeds ${Math.round(b.max_guaranteed_pct * 100)}% of total value.`;
  return null;
}

function _showErr(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.hidden = false;
}

function d_int(v) { return parseInt(v, 10) || 0; }

function _esc(s) {
  if (s == null) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
