"""
personas.py — this app's one channel, described as a domain.
=================================================================

WHY THIS FILE LOOKS SO MUCH SMALLER THAN THE PROJECT IT WAS FORKED FROM
The app this was built from ran several unrelated channels — a tech
explainer, a Tamil-quotes channel, a comedy channel — each its own persona
in a shared dict, because that project's whole point was "any domain, any
number of channels." This app is the opposite on purpose: ONE channel, ONE
domain (cricket first, other sports second — see sports_catalog.py for the
85/15 split), built and tuned specifically for it. Keeping the multi-persona
MACHINERY (personas, topic_synthesizer, channels) costs nothing and means
adding a genuinely second channel later — a football-only spinoff, say — is
still just "add a persona and a channel row," not a rewrite. But the
CONTENT of this file is exactly one persona, because that is exactly what
was asked for.

WHERE THE TOPIC IDEAS ACTUALLY COME FROM
`seed_topics` below is a sample drawn from engine.sports_catalog's 270+
hand-written starter topics — not the whole list, just enough for
topic_synthesizer.py to learn "what this domain's ideas look like" before it
starts inventing new ones forever (see that file's own module docstring).
The real starter pool is sports_catalog.all_topics(), seeded directly into
the topics table by engine/seed_topics.py — this persona's job is ongoing
invention, not the first 270.

ADDING A SECOND CHANNEL LATER
Copy this dict entry, change the fields, add it to PERSONAS, and it appears
on the Channels page immediately — the machinery was never actually specific
to sports, only the content in this one entry is.
"""
from engine import sports_catalog

PERSONAS = {
    "cricket_and_sports": {
        "label": "Cricket & Sports Shorts",
        "description": (
            "This channel's entire domain, in one persona. Cricket is the anchor — "
            "national and international news, old and current, IPL and other leagues, "
            "players past and present, the laws and rules, team and tournament history, "
            "achievements loud and unsung, and genuine 'did you know' facts — at roughly "
            "85% of everything made. The remaining 15% covers OTHER sports and their "
            "athletes: not just history, but players CURRENTLY on their own achieving "
            "track right now (a rising star mid-career, not only retired legends). "
            "engine/sports_catalog.py is the starter idea bank behind this description; "
            "engine/content_mix.py is what actually enforces the 85/15 ratio and the "
            "daily mix of 'likely big reach' videos against 'variety' videos run to run — "
            "this persona only has to describe the domain honestly, not do that math "
            "itself."
        ),
        "seed_topics": sports_catalog.seed_examples(n=40),
        "preferred_archetypes": [
            "records_and_stats", "player_story", "quiz_challenge", "where_are_they_now",
            "unsung_history", "history_deep_dive", "rules_explainer",
            "business_and_governance", "informative", "myth_busting",
        ],
        "preferred_render_style": "sports_visual",
        # FALLBACK ONLY — not a pin. This used to be read as if it were a
        # fixed, unconditional voice for every single video this persona
        # makes (orchestrator.py checked it BEFORE the tone-based
        # voice_profile_for_tone() lookup), which is the actual reason every
        # video sounded identical regardless of the Settings dropdown or the
        # video's own tone: this one value always won. orchestrator.py now
        # checks the tone-based mapping FIRST and only falls back to this
        # value for a tone it doesn't recognise — so this is now genuinely a
        # fallback, and real per-tone variety (see voice_engine.py's
        # TONE_VOICE_MAP) is what actually plays on most videos.
        "preferred_voice": "indian_male",
        "default_temperature": 0.8,
        "flavor_instructions": (
            "This channel lives or dies on being genuinely, verifiably correct about real "
            "sport — a confidently wrong record or rule is the single fastest way to lose "
            "viewer trust and get called out in the comments. Never invent a statistic, "
            "date, or named achievement; if research notes are not available for a number, "
            "say it qualitatively instead ('one of the fastest ever', not a made-up figure).\n"
            "Treat every named athlete, team, board, and country with genuine respect — this "
            "is a facts-and-achievement channel, not a comedy or takedown channel. "
            "Controversies get covered factually and neutrally (see the myth_busting and "
            "controversies-category guardrails), never as mockery.\n"
            "Real footage and real photos are what make this format work — always describe "
            "the specific, named, findable subject of a scene (a player, a ground, a "
            "tournament, a concrete action) rather than an abstract idea; see "
            "engine/styles/sports_visual.py and engine/visual_fetcher.py's sports chain for "
            "how that visual gets found.\n"
            "For records_and_stats and quiz_challenge videos specifically: the closing "
            "engagement question (engine/engagement.py) is not optional decoration — it is "
            "the single biggest lever this channel has for comments and shares, so give it "
            "genuine thought every time rather than a token afterthought.\n"
            "WRITE LIKE A PERSON TALKING, NOT A REPORT. This channel's audience is mostly "
            "everyday cricket fans in India, not sports journalists. Say it the way a friend "
            "who follows cricket closely would tell you a great fact over chai, or the way a "
            "good teacher explains a bit of history — plain, warm, a little excited, never "
            "stiff or 'textbook'. Avoid formal/academic/corporate words entirely (e.g. "
            "'utilize', 'significant', 'demonstrate', 'subsequently', 'in conclusion') — use "
            "the simple everyday word instead ('use', 'big', 'show', 'then'). Short sentences. "
            "Contractions are fine and usually better ('didn't', 'it's'). If a word wouldn't "
            "come up in a normal conversation at a cricket ground, don't use it here."
        ),
    },
}

DEFAULT_PERSONA = "cricket_and_sports"


def persona_keys():
    return list(PERSONAS.keys())


def get_persona(key: str) -> dict | None:
    return PERSONAS.get(key)


def persona_labels() -> dict:
    return {k: v["label"] for k, v in PERSONAS.items()}


def flavor_prompt_block(persona_key: str) -> str:
    """Persona writing instructions, formatted for the brief/script prompt."""
    p = get_persona(persona_key)
    if not p:
        return ""
    return f"\nCHANNEL VOICE: {p['label']}\n{p['flavor_instructions']}\n"
