// Load Franchise screen — lists all .db saves and lets the user open one.
import { api } from '../api.js';

export async function init(container) {
  container.innerHTML = '<div class="loading-spinner">Scanning saves…</div>';
  const data = await api.getSaveFiles();

  if (!data.ok) {
    container.innerHTML = `<div class="error-card"><p>Could not scan saves directory: ${data.error}</p></div>`;
    return;
  }

  if (data.saves.length === 0) {
    container.innerHTML = `
      <div class="placeholder-card">
        <h2>No Franchises Found</h2>
        <p>Create one from the command line:</p>
        <pre>python generate.py saves/my_team.db --season 2024</pre>
        <p>Then return here to load it.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="load-franchise-screen">
      <h2 class="screen-title">Load Franchise</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>Team</th>
            <th>Season</th>
            <th>Week</th>
            <th>Last Opened</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${data.saves.map(s => `
            <tr>
              <td>${_esc(s.team_name)}</td>
              <td>${s.season}</td>
              <td>${s.week === 0 ? 'Offseason' : `Week ${s.week}`}</td>
              <td class="text-muted">${_esc(s.mtime_iso)}</td>
              <td>
                <button class="btn btn-primary btn-sm" data-save-path="${_esc(s.path)}">Load</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  container.querySelectorAll('[data-save-path]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const path = btn.dataset.savePath;
      btn.disabled = true;
      btn.textContent = 'Loading…';
      const result = await api.doLoadFranchise(path);
      if (!result.ok) {
        alert(`Failed to load franchise: ${result.error}`);
        btn.disabled = false;
        btn.textContent = 'Load';
        return;
      }
      window.onFranchiseLoaded?.(result);
    });
  });
}

function _esc(str) {
  return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
