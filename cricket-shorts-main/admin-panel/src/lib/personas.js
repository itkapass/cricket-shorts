// src/lib/personas.js
//
// The one place this list is allowed to live.
//
// WHY THIS FILE EXISTS
// This used to be defined directly inside ChannelsPage.jsx. It is a
// hand-copied mirror of engine/personas.py's PERSONAS dict — nothing
// enforces the two staying in sync, because the frontend has no way to
// import Python at build time. In the multi-persona build this app is
// forked from, that already caused a real bug: a newly added persona was
// unselectable in the dashboard with no error anywhere, because this copy
// was never updated alongside the Python side.
//
// THIS APP IS SINGLE-PERSONA, ON PURPOSE
// It ships with exactly one persona — cricket_and_sports — covering the
// full 85% cricket / 15% other-sport mix described in
// engine/sports_catalog.py and engine/content_mix.py. There is deliberately
// only one channel's worth of content strategy here; the multi-persona
// plumbing (PERSONAS_ONLY, "additional personas" on a channel, etc.) is
// kept working rather than ripped out, purely so a second persona/channel
// can be added later without re-wiring the dashboard — not because this
// app expects you to add one.
//
// If you DO add a second persona to engine/personas.py, add it HERE too —
// tools/selfcheck.py checks the two lists match.

export const PERSONAS = [
  ['', 'None — pick categories manually below'],
  ['cricket_and_sports', 'Cricket & Sports Shorts'],
]

// Personas only (no blank "None" entry) — for pickers where "not selecting
// a persona" and "explicitly wanting all/none" are meaningfully different
// choices, e.g. a "which channel" dropdown for a manual action.
export const PERSONAS_ONLY = PERSONAS.filter(([key]) => key)

export const PERSONAS_META = {
  cricket_and_sports: {
    categories: ['rules', 'records_stats', 'player_story', 'current_players',
      'where_are_they_now', 'unsung_history', 'team_history', 'world_cup', 'ipl',
      'governance_business', 'technology', 'iconic_matches', 'controversies',
      'training_science', 'womens_cricket', 'domestic_cricket', 'weather_pitch',
      'trivia_quiz', 'commentary', 'global_reach'],
    description: 'Cricket (85%) plus other sports and currently-achieving athletes (15%) — '
      + 'records, player stories, rules, history, IPL, and quiz-close trivia, grounded in real '
      + 'Wikipedia research for every factual claim. See engine/sports_catalog.py for the full '
      + 'category list and engine/content_mix.py for how the 85/15 split and daily cadence work.',
  },
}
