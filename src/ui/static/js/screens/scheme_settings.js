// Scheme Settings screen (T-10) — offense + defense scheme selection.
import { api } from '../api.js';

export async function init(container) {
  const data = await api.getSchemeSettings();
  if (!data.ok) {
    container.innerHTML = `<p class="error">Could not load scheme settings: ${data.error}</p>`;
    return;
  }
  container.innerHTML = _buildForm(data);

  container.querySelector('#btn-save-scheme').addEventListener('click', async () => {
    const offense = container.querySelector('#scheme-offense').value;
    const defense = container.querySelector('#scheme-defense').value;
    const r = await api.doUpdateScheme(offense, defense);
    const fb = container.querySelector('#scheme-feedback');
    fb.textContent = r.ok ? '✓ Scheme saved' : `Error: ${r.error}`;
    fb.className = `scheme-feedback ${r.ok ? 'text-success' : 'text-danger'}`;
  });
}

function _buildForm(data) {
  const offenseOpts = data.offense_options.map(o =>
    `<option value="${o.value}"${o.value === data.current_offense ? ' selected' : ''}>${o.label}</option>`
  ).join('');
  const defenseOpts = data.defense_options.map(o =>
    `<option value="${o.value}"${o.value === data.current_defense ? ' selected' : ''}>${o.label}</option>`
  ).join('');

  return `
    <div class="scheme-settings-screen">
      <h2 class="screen-title">Scheme Settings</h2>
      <p class="scheme-note text-muted">
        Your scheme affects player efficiency during games.
        Players whose attributes match your scheme receive a bonus to their Scheme-Adjusted Rating (SAR).
      </p>

      <div class="settings-group">
        <label class="settings-row">
          <span class="settings-label">Offensive Scheme</span>
          <select id="scheme-offense" class="select">${offenseOpts}</select>
        </label>
        <label class="settings-row">
          <span class="settings-label">Defensive Scheme</span>
          <select id="scheme-defense" class="select">${defenseOpts}</select>
        </label>
      </div>

      <div class="settings-actions">
        <button id="btn-save-scheme" class="btn btn-primary">Save Scheme</button>
        <span id="scheme-feedback" class="scheme-feedback"></span>
      </div>
    </div>
  `;
}
