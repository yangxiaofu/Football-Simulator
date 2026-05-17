// screens/detail.js — Pattern B reusable detail template
// options = { headerHTML, tabs:[{key,label,contentHTML}], defaultTab,
//             actions:[{label,action_key,enabled,tooltip}], onBack?, onAction? }
// onAction(actionKey) is invoked when an ENABLED action button is clicked.

export function initDetailScreen(container, options) {
  const { headerHTML, tabs, defaultTab, actions, onBack, onAction } = options;
  let activeTab = defaultTab ?? tabs[0]?.key ?? '';

  function render() {
    const tabNav = tabs.map(t =>
      `<button class="tab-btn${activeTab === t.key ? ' tab-btn--active' : ''}" data-tab="${_esc(t.key)}">${_esc(t.label)}</button>`
    ).join('');

    const tabContent = tabs.map(t =>
      `<div class="player-tab-content${activeTab === t.key ? '' : ' hidden'}" data-tab-content="${_esc(t.key)}">${t.contentHTML}</div>`
    ).join('');

    // Enabled actions are clickable + carry data-action-key; disabled ones
    // keep the tooltip pattern (CSS ::after works on disabled buttons).
    const actionBtns = actions.map(a => a.enabled
      ? `<button class="btn btn-primary" data-action-key="${_esc(a.action_key)}" title="${_esc(a.tooltip)}">${_esc(a.label)}</button>`
      : `<button class="btn btn-secondary" disabled data-tooltip="${_esc(a.tooltip)}" title="${_esc(a.tooltip)}">${_esc(a.label)}</button>`
    ).join('');

    const backBar = onBack
      ? `<div class="detail-back-bar"><button class="btn-back">← Back</button></div>`
      : '';

    container.innerHTML = `
      <div class="detail-screen" style="display:flex;flex-direction:column;height:100%;overflow:hidden;">
        ${backBar}
        <div class="player-header">${headerHTML}</div>
        <div class="tab-nav" style="display:flex;gap:0;border-bottom:1px solid var(--border);background:var(--bg-surface);flex-shrink:0;">${tabNav}</div>
        <div class="player-body" style="flex:1;overflow:hidden;">${tabContent}</div>
        <div class="player-action-row">${actionBtns}</div>
      </div>`;

    if (onBack) {
      container.querySelector('.btn-back')?.addEventListener('click', onBack);
    }

    if (typeof onAction === 'function') {
      container.querySelectorAll('[data-action-key]').forEach(btn => {
        btn.addEventListener('click', () => onAction(btn.dataset.actionKey));
      });
    }

    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.tab;
        container.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('tab-btn--active', b.dataset.tab === activeTab));
        container.querySelectorAll('[data-tab-content]').forEach(div => div.classList.toggle('hidden', div.dataset.tabContent !== activeTab));
      });
    });
  }

  render();
}

function _esc(str) {
  if (str == null) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
