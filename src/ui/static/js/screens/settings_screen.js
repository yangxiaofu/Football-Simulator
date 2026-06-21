// Settings screen — user preferences (sim speed, autopilot).
import { api } from '../api.js';

export async function init(container) {
  const data = await api.getSettings();
  if (!data.ok) {
    container.innerHTML = `<p class="error">Could not load settings: ${data.error}</p>`;
    return;
  }
  const s = data.settings;

  container.innerHTML = `
    <div class="settings-screen">
      <h2 class="screen-title">Settings</h2>

      <div class="settings-group">
        <label class="settings-row">
          <span class="settings-label">Autosave</span>
          <span class="settings-value text-muted">Always enabled — every action is saved automatically.</span>
        </label>

        <label class="settings-row">
          <span class="settings-label">Sim Speed</span>
          <select id="setting-sim-speed" class="select">
            <option value="normal" ${s.sim_speed === 'normal'  ? 'selected' : ''}>Normal</option>
            <option value="fast"   ${s.sim_speed === 'fast'    ? 'selected' : ''}>Fast</option>
            <option value="instant"${s.sim_speed === 'instant' ? 'selected' : ''}>Instant</option>
          </select>
        </label>

        <label class="settings-row">
          <span class="settings-label">Autopilot</span>
          <span class="settings-desc">Skip press-conference prompts when advancing weeks.</span>
          <input type="checkbox" id="setting-autopilot" ${s.autopilot ? 'checked' : ''}>
        </label>
      </div>

      <div class="settings-actions">
        <button id="btn-save-settings" class="btn btn-primary">Save Settings</button>
        <span id="settings-feedback" class="settings-feedback"></span>
      </div>
    </div>
  `;

  container.querySelector('#btn-save-settings').addEventListener('click', async () => {
    const newSettings = {
      sim_speed: container.querySelector('#setting-sim-speed').value,
      autopilot: container.querySelector('#setting-autopilot').checked,
    };
    const r = await api.doSaveSettings(newSettings);
    const fb = container.querySelector('#settings-feedback');
    fb.textContent = r.ok ? '✓ Saved' : `Error: ${r.error}`;
    fb.className = `settings-feedback ${r.ok ? 'text-success' : 'text-danger'}`;
  });
}
