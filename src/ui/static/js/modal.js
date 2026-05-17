// modal.js — generic stacked modal framework (Phase 6 P7b).
//
// GENERIC ON PURPOSE: zero FA-specific code. Reused by Trade (P8),
// Draft Decision (P9), Intervention, etc. Pass a config; get a modal.
//
// openModal({ id, title, contentHTML, parent, onMount, onClose,
//             backdropDismissable, closeOnEsc, size })
// closeModal(id?)      // id omitted → closes the TOP modal only
// closeAllModals()
// getModalStack()      // [{id}] — debug/tests
//
// Stack: each modal renders its own scrim+dialog into #modal-root, z-index
// increasing per level. ESC / backdrop close the TOP modal only. Focus is
// trapped in the top modal; on close focus returns to the opener element.
//
// z-index tiers mirror src/utils/constants.py (UI_ZINDEX_MODAL_BASE /
// UI_ZINDEX_MODAL_STACK_STEP / UI_MODAL_FADE_MS). pywebview JS can't import
// Python — keep these in sync if the Python values change.

const Z_BASE = 1000;
const Z_STEP = 10;
const FADE_MS = 150;

const _stack = [];   // [{ id, scrim, dialog, opener, onClose, backdropDismissable, closeOnEsc }]

function _root() {
  return document.getElementById('modal-root');
}

function _focusable(container) {
  return Array.from(container.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter(el => el.offsetParent !== null || el === document.activeElement);
}

function _top() {
  return _stack.length ? _stack[_stack.length - 1] : null;
}

export function getModalStack() {
  return _stack.map(m => ({ id: m.id }));
}

export function openModal(cfg) {
  const {
    id,
    title = '',
    contentHTML = '',
    onMount,
    onClose,
    backdropDismissable = true,
    closeOnEsc = true,
    size = 'md',           // 'md' (default) | 'lg'
  } = cfg || {};

  if (!id) throw new Error('openModal requires an id');
  if (_stack.some(m => m.id === id)) return;  // already open — no-op

  const level = _stack.length;
  const zScrim = Z_BASE + level * Z_STEP;

  const scrim = document.createElement('div');
  scrim.className = 'modal-scrim modal-scrim--stacked';
  scrim.style.zIndex = String(zScrim);
  scrim.setAttribute('data-modal-id', id);

  const titleId = `modal-title-${id}`;
  const dialog = document.createElement('div');
  dialog.className = 'modal' + (size === 'lg' ? ' modal--lg' : '');
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');
  dialog.setAttribute('aria-labelledby', titleId);
  dialog.innerHTML = `
    <div class="modal-header">
      <span class="modal-title" id="${titleId}">${_esc(title)}</span>
      <button class="modal-close" type="button" aria-label="Close" data-modal-close>&times;</button>
    </div>
    <div class="modal-body">${contentHTML}</div>`;

  scrim.appendChild(dialog);
  _root().appendChild(scrim);

  const entry = {
    id, scrim, dialog,
    opener: document.activeElement,
    onClose, backdropDismissable, closeOnEsc,
  };
  _stack.push(entry);

  // Backdrop click → close this modal (only when it's the top + dismissable).
  scrim.addEventListener('mousedown', (e) => {
    if (e.target === scrim && entry.backdropDismissable && _top() === entry) {
      closeModal(id);
    }
  });
  // ✕ close button(s).
  dialog.querySelectorAll('[data-modal-close]').forEach(btn =>
    btn.addEventListener('click', () => closeModal(id)));

  // Fade in.
  scrim.classList.add('modal-scrim--enter');
  requestAnimationFrame(() => scrim.classList.remove('modal-scrim--enter'));

  if (typeof onMount === 'function') onMount(dialog);

  // Initial focus: first focusable, else the dialog itself.
  const f = _focusable(dialog);
  (f[0] || dialog).focus?.();
  if (!f.length) dialog.setAttribute('tabindex', '-1');

  return dialog;
}

export function closeModal(id) {
  if (!_stack.length) return;
  let idx = _stack.length - 1;            // default: top
  if (id) {
    idx = _stack.findIndex(m => m.id === id);
    if (idx === -1) return;
  }
  const entry = _stack[idx];
  _stack.splice(idx, 1);

  entry.scrim.classList.add('modal-scrim--leave');
  const sc = entry.scrim;
  setTimeout(() => sc.remove(), FADE_MS);

  try { if (typeof entry.onClose === 'function') entry.onClose(); }
  finally {
    const restore = entry.opener;
    if (restore && typeof restore.focus === 'function') {
      // Return focus to whoever opened it (or the new top modal).
      const t = _top();
      if (t) (_focusable(t.dialog)[0] || t.dialog).focus?.();
      else restore.focus();
    }
  }
}

export function closeAllModals() {
  while (_stack.length) closeModal();
}

// Global key handling: ESC closes top; Tab is trapped within the top modal.
document.addEventListener('keydown', (e) => {
  const t = _top();
  if (!t) return;
  if (e.key === 'Escape' && t.closeOnEsc) {
    e.preventDefault();
    closeModal();
    return;
  }
  if (e.key === 'Tab') {
    const f = _focusable(t.dialog);
    if (!f.length) { e.preventDefault(); return; }
    const first = f[0], last = f[f.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || !t.dialog.contains(active))) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && (active === last || !t.dialog.contains(active))) {
      e.preventDefault(); first.focus();
    }
  }
});

function _esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
