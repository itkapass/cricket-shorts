// src/lib/mediaOptions.js
//
// Voice and render-style options for the Channels page's "these related
// voices/videos for this channel" controls (voice_override,
// render_style_override). Mirrors engine/voice_engine.py's VOICE_PROFILES
// and engine/styles/STYLES — kept here as ONE shared list for the same
// reason lib/personas.js exists: a second hand-copied list is exactly how
// the Tamil-persona dropdown bug happened before. If either list changes
// on the backend, update here too — there's only one place to remember now.
//
// MALE VOICES ONLY, DELIBERATELY. This app's one standing voice rule is "a
// MALE voice everywhere — female voices are unwanted." voice_engine.py
// still defines a couple of female profiles (inherited from the broader
// build this was forked from, used there by a character-skit style this
// app doesn't use), but they are left OUT of this dropdown on purpose so a
// channel override can never pick one. Every archetype this app actually
// uses (see engine/archetypes.py's SPORTS_ARCHETYPES) already defaults to
// one of the voices below.

export const VOICES = [
  ['', 'Use the channel\u2019s persona default (male)'],
  ['documentary_male', 'Documentary — male (Guy)'],
  ['conversational', 'Conversational — male (Andrew)'],
  ['energetic', 'Energetic — male (Christopher)'],
  ['british_calm', 'Calm — British male (Ryan)'],
]

export const RENDER_STYLES = [
  ['', 'Use the persona/archetype default'],
  ['sports_visual', 'Sports Visual — real footage + stat/quiz cards (this app\u2019s default)'],
  ['stock_footage', 'Stock Footage — real b-roll with a Ken Burns zoom'],
  ['whiteboard_sketch', 'Whiteboard Sketch — hand-drawn diagram, builds scene by scene'],
  ['character_skit', 'Character Skit — animated 2D characters'],
  ['quote_card', 'Quote Card — minimal text-forward card'],
]
