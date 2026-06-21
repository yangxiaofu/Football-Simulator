// Help screen — static content, no API call required.

export async function init(container) {
  container.innerHTML = `
    <div class="help-screen">
      <h2 class="screen-title">Help</h2>

      <details open>
        <summary class="help-summary">Getting Started</summary>
        <div class="help-body">
          <p>Create a new franchise from the command line:</p>
          <pre>python generate.py saves/my_team.db --season 2024</pre>
          <p>Then open it via <strong>Title Screen → Load Franchise</strong>.</p>
          <p>Use the section tabs at the top to navigate: <strong>Team</strong>, <strong>League</strong>, <strong>Schedule</strong>, <strong>Front Office</strong>, and <strong>Dynasty</strong>.</p>
          <p>Press <strong>Continue ▶</strong> in the context bar to advance to the next game week.</p>
        </div>
      </details>

      <details>
        <summary class="help-summary">Managing Your Roster</summary>
        <div class="help-body">
          <p>Sign free agents from <strong>Front Office → FA Market</strong>. Review contract details in the player card before making an offer.</p>
          <p>Cut players from the Roster screen. Releasing a player before June 1 applies the full dead-cap hit in the current year.</p>
          <p>Propose trades from <strong>Front Office → Trade Center</strong>. Use the Trade Builder to assemble an offer — the AI evaluates fairness in real time.</p>
          <p>Set your draft board rankings in <strong>Front Office → Scouting → Draft Board</strong> before the Draft Room opens.</p>
        </div>
      </details>

      <details>
        <summary class="help-summary">Glossary</summary>
        <div class="help-body">
          <dl class="glossary">
            <dt>SAR</dt>
            <dd>Scheme-Adjusted Rating — a player's effective rating after applying your current offensive or defensive scheme fit bonus (range: ±8 points).</dd>

            <dt>Letter Grade</dt>
            <dd>Displayed player rating from F (below 60) to A+ (97–99). Raw numbers are never shown — only grades.</dd>

            <dt>Cap Space</dt>
            <dd>Remaining salary cap. Recalculated after every contract action. Displayed in the context bar.</dd>

            <dt>Legacy Score</dt>
            <dd>Your coach's cumulative dynasty rating, based on championships, win rate, and draft success. Tracked in <strong>Dynasty → Legacy Tracker</strong>.</dd>

            <dt>Combine</dt>
            <dd>Pre-draft athletic testing event. Risers and fallers affect prospect interest and board rankings.</dd>

            <dt>WAR Room Reaction</dt>
            <dd>Narrative beat generated after each of your draft picks, reflecting league reaction to your selection.</dd>

            <dt>Scouted Rating</dt>
            <dd>Your scouts' estimate of a prospect's true ability. More scouting hours = more accurate grades.</dd>
          </dl>
        </div>
      </details>

      <details>
        <summary class="help-summary">Keyboard Shortcuts</summary>
        <div class="help-body">
          <ul class="shortcut-list">
            <li><kbd>Escape</kbd> — Close the top-most modal</li>
            <li><kbd>Enter</kbd> — Confirm the focused action in a modal</li>
          </ul>
        </div>
      </details>
    </div>
  `;
}
