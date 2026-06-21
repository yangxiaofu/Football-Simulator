// Promise wrapper over window.pywebview.api
// Every screen imports { api } from './api.js' and calls typed methods.
// No scattered window.pywebview.api.* calls anywhere else in the codebase.

// pywebview injects window.pywebview = { api: {} } before calling _createApi().
// Caching that reference captures the empty stub. Instead, track readiness with
// a boolean and always dereference window.pywebview.api at call time.

let _ready = false;

async function bridge() {
  if (!_ready) {
    await new Promise((resolve) => {
      // Check if _createApi already ran (api has actual methods)
      if (window.pywebview?.api && Object.keys(window.pywebview.api).length > 0) {
        resolve();
      } else {
        // pywebviewready fires after _createApi populates the api object
        window.addEventListener('pywebviewready', () => setTimeout(resolve, 0), { once: true });
      }
    });
    _ready = true;
    console.log('[api.js] bridge ready, keys:', Object.keys(window.pywebview.api));
  }
  return window.pywebview.api;
}

export const api = {
  async getAppInfo() {
    return (await bridge()).get_app_info();
  },

  async getDashboard() {
    return (await bridge()).get_dashboard();
  },

  async getRoster(teamId = null) {
    return (await bridge()).get_roster(teamId);
  },

  async getPlayer(playerId) {
    return (await bridge()).get_player(playerId);
  },

  async getStandings(view = 'division') {
    return (await bridge()).get_standings(view);
  },

  async getLeaders(category = 'passing') {
    return (await bridge()).get_leaders(category);
  },

  async getTransactions() {
    return (await bridge()).get_transactions();
  },

  // --- Phase 6 P5: Schedule / Preview / Recap ---

  async getSchedule() {
    return (await bridge()).get_schedule();
  },

  async getGamePreview(gameId = null) {
    return (await bridge()).get_game_preview(gameId);
  },

  async getGameRecap(gameId) {
    return (await bridge()).get_game_recap(gameId);
  },

  async getFrontOffice() {
    return (await bridge()).get_front_office();
  },

  async getFaMarket() {
    return (await bridge()).get_fa_market();
  },

  async getFaPlayer(playerId) {
    return (await bridge()).get_fa_player(playerId);
  },

  async getTaskStatus(taskId) {
    return (await bridge()).get_task_status(taskId);
  },

  // --- Phase 6 P5: mutations (submit + poll to completion) ---

  async doAdvanceWeek(onProgress) {
    const r = await (await bridge()).do_advance_week();
    if (r && r.ok === false) return r;
    return pollTask(r.task_id, onProgress);
  },

  async doSimGame(gameId, onProgress) {
    const r = await (await bridge()).do_sim_game(gameId);
    if (r && r.ok === false) return r;
    return pollTask(r.task_id, onProgress);
  },

  // --- Phase 6 P7b: FA modal reads + synchronous contract mutations ---
  // These run inline server-side (O(1)); no task_id / polling.

  async getPitchMeeting(playerId) {
    return (await bridge()).get_pitch_meeting(playerId);
  },

  async getOfferBuilder(playerId) {
    return (await bridge()).get_offer_builder(playerId);
  },

  async doAddToWatchlist(playerId) {
    return (await bridge()).do_add_to_watchlist(playerId);
  },

  async doSignFreeAgent(playerId, offer) {
    return (await bridge()).do_sign_free_agent(playerId, offer);
  },

  async doCutPlayer(playerId, postJune1 = false) {
    return (await bridge()).do_cut_player(playerId, postJune1);
  },

  async doRestructureContract(playerId, newTerms) {
    return (await bridge()).do_restructure_contract(playerId, newTerms);
  },

  // --- Phase 6 P8: Scouting + Trade reads ---
  async getScoutDashboard() {
    return (await bridge()).get_scout_dashboard();
  },
  async getProspectList(filters = null) {
    return (await bridge()).get_prospect_list(filters);
  },
  async getProspectCard(prospectId) {
    return (await bridge()).get_prospect_card(prospectId);
  },
  async getScoutAssignments() {
    return (await bridge()).get_scout_assignments();
  },
  async getDraftBoard() {
    return (await bridge()).get_draft_board();
  },
  async getTradeHub() {
    return (await bridge()).get_trade_hub();
  },
  async getTradeBlock() {
    return (await bridge()).get_trade_block();
  },
  async getIncomingOffers() {
    return (await bridge()).get_incoming_offers();
  },
  async getAllTeams() {
    return (await bridge()).get_all_teams();
  },
  async getTradeBuilderContext(theirTeamId) {
    return (await bridge()).get_trade_builder_context(theirTeamId);
  },
  async getTradePreview(myPlayerIds, myPickCodes, theirPlayerIds, theirPickCodes, theirTeamId) {
    return (await bridge()).get_trade_preview(
      myPlayerIds || [], myPickCodes || [],
      theirPlayerIds || [], theirPickCodes || [],
      theirTeamId,
    );
  },

  // --- Phase 6 P8: Scouting + Trade mutations ---
  async doProposeTrade(theirTeamId, myAssets, theirAssets) {
    return (await bridge()).do_propose_trade(theirTeamId, myAssets, theirAssets);
  },
  async doRespondToTrade(tradeId, response) {
    return (await bridge()).do_respond_to_trade(tradeId, response);
  },
  async doCounterTrade(tradeId, myAssets, theirAssets) {
    return (await bridge()).do_counter_trade(tradeId, myAssets, theirAssets);
  },
  async doAddToTradeBlock(playerId) {
    return (await bridge()).do_add_to_trade_block(playerId);
  },
  async doRemoveFromTradeBlock(playerId) {
    return (await bridge()).do_remove_from_trade_block(playerId);
  },
  async doAssignScout(scoutId, prospectIds) {
    return (await bridge()).do_assign_scout(scoutId, prospectIds);
  },
  async doSetBoardRank(prospectId, newRank) {
    return (await bridge()).do_set_board_rank(prospectId, newRank);
  },

  // Draft Room (F-60) — Prompt 9a
  async getDraftRoom() {
    return (await bridge()).get_draft_room();
  },
  async getAvailableBoard() {
    return (await bridge()).get_available_board();
  },
  async doInitializeDraft() {
    return (await bridge()).do_initialize_draft();
  },
  async doMakePick(prospectId) {
    return (await bridge()).do_make_pick(prospectId);
  },
  async doSimAiPicks(untilUserPick = false) {
    return (await bridge()).do_sim_ai_picks(untilUserPick);
  },

  // Season Review (F-10) — Prompt 10
  async getSeasonReview() {
    return (await bridge()).get_season_review();
  },

  // Playoff Bracket + Super Bowl Recap (S-08, S-11) — Prompt 10b
  async getPlayoffBracket() {
    return (await bridge()).get_playoff_bracket();
  },
  async getSuperBowlRecap() {
    return (await bridge()).get_super_bowl_recap();
  },

  // Milestone 5.10c: Combine Results (F-34), Post-Draft Review (F-62), Past Season (D-04)
  async getCombineResults() {
    return (await bridge()).get_combine_results();
  },
  async getPostDraftReview() {
    return (await bridge()).get_post_draft_review();
  },
  async getPastSeason(year) {
    return (await bridge()).get_past_season({ season_year: year });
  },

  // Milestone 5.11: Dynasty Section (D-01, D-02, D-03, D-05, D-06, D-07)
  async getDynastyHub() {
    return (await bridge()).get_dynasty_hub();
  },
  async getFranchiseHistory() {
    return (await bridge()).get_franchise_history();
  },
  async getSeasonArchive() {
    return (await bridge()).get_season_archive();
  },
  async getAwardsHistory() {
    return (await bridge()).get_awards_history();
  },
  async getLegacyTracker() {
    return (await bridge()).get_legacy_tracker();
  },
  async getRetiredPlayer(playerId) {
    return (await bridge()).get_retired_player({ player_id: playerId });
  },

  // Milestone 5.12: Title Screen / Load Franchise / Settings / Scheme
  async getSaveFiles() {
    return (await bridge()).get_save_files();
  },
  async doLoadFranchise(path) {
    return (await bridge()).do_load_franchise(path);
  },
  async getSettings() {
    return (await bridge()).get_settings();
  },
  async doSaveSettings(settings) {
    return (await bridge()).do_save_settings(settings);
  },
  async getSchemeSettings() {
    return (await bridge()).get_scheme_settings();
  },
  async doUpdateScheme(offense, defense) {
    return (await bridge()).do_update_scheme(offense, defense);
  },
};

// Polling constants mirror src/utils/constants.py
// (UI_TASK_POLL_INTERVAL_MS / UI_TASK_POLL_TIMEOUT_MS). pywebview JS cannot
// import Python; keep these in sync if the Python values change.
const POLL_MS = 400;
const POLL_TIMEOUT_MS = 120000;

// Poll get_task_status until the task reports a result or an error.
// Resolves with {result, ...} on success or {ok:false, error} on failure.
export async function pollTask(taskId, onProgress) {
  const started = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const st = await api.getTaskStatus(taskId);
    if (st && st.ok === false) return st;
    if (typeof onProgress === 'function') {
      onProgress(st.progress ?? 0, st.message ?? '');
    }
    if (st.error) return { ok: false, error: st.error };
    if (st.done && st.result !== null) {
      return { ok: true, result: st.result };
    }
    if (Date.now() - started > POLL_TIMEOUT_MS) {
      return { ok: false, error: 'Timed out waiting for the task.' };
    }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}
