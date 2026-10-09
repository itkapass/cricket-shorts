"""
archetypes.py — what KIND of video to make.
===========================================

A topic ("the deep sea") is not a video. The same topic makes ten different
videos depending on the angle: an unknown-fact drop, a myth correction, a
two-character joke, a quiet emotional beat. That angle is the archetype, and it
is the single biggest lever on whether a video gets watched.

WHY THIS IS ITS OWN MODULE
It is read by four places that must never disagree:
  - script_generator.py  — for the writing rules in the prompt
  - channels.py          — for routing videos to channels by category
  - concept_memory.py    — for tracking which angles are used up
  - the admin panel      — for the category filters and per-archetype counts
One definition, four consumers, no drift.

CONTENT SAFETY IS PART OF THE ARCHETYPE, NOT A SEPARATE FILTER
Each archetype carries its own `guardrails` string that goes into the prompt.
This is deliberate. A generic "be responsible" instruction is weak and easy for
a model to write around. A rule attached to the specific format — "dark humour
targets situations, institutions and the absurdity of being alive, never real
people, groups, tragedies or anyone's suffering" — is concrete and holds.

The empathy/social archetype has the strictest rules of all, because content
about poverty and hardship is exactly where automated video goes wrong: it
slides into poverty tourism, invented sob stories, or fake charity appeals. The
guardrails there forbid inventing individuals, forbid any call to donate, and
require that the subject be treated as a person rather than a prop.
"""

ARCHETYPES = {
    "informative": {
        "label": "Unknown Facts",
        "blurb": "A genuinely surprising true thing, explained fast.",
        "default_style": "stock_footage",
        "voice": "documentary_male",
        "rules": (
            "Lead with the single most surprising true detail, then explain WHY it is true. "
            "The explanation is the payoff — a fact with no mechanism behind it is trivia and "
            "viewers do not rewatch trivia. Use concrete numbers and physical comparisons."
        ),
        "guardrails": (
            "Every claim must be something you are confident is established public knowledge. "
            "If you are not sure a number is right, use a qualitative comparison instead of "
            "inventing a figure. Never attribute an invented statistic to a real company, "
            "institution or person."
        ),
    },
    "myth_busting": {
        "label": "Myth vs Fact",
        "blurb": "A widely believed thing that is not true, corrected.",
        "default_style": "stock_footage",
        "voice": "conversational",
        "rules": (
            "State the myth plainly first, in the words people actually use for it. Then correct "
            "it and explain where the belief came from — the origin is what makes this format "
            "satisfying rather than smug. End on what IS true."
        ),
        "guardrails": (
            "The myth must be labelled as a myth within the first two scenes, never left standing "
            "unqualified. Do not 'bust' anything genuinely contested by experts — pick things with "
            "settled answers. Never present a fringe position as the correction. Avoid medical, "
            "legal and financial myths entirely: being wrong there causes real harm."
        ),
    },
    "life_hack": {
        "label": "Daily Hacks",
        "blurb": "A small practical thing that makes a daily routine easier.",
        "default_style": "stock_footage",
        "voice": "conversational",
        "rules": (
            "One hack per video, shown as a concrete before-and-after. Say why it works, not just "
            "what to do — the mechanism is what makes someone remember it. It must be something a "
            "person could actually do today with things they already own."
        ),
        "guardrails": (
            "No hack involving electricity, gas, medication, dosages, food safety, driving, or "
            "anything that could injure someone if it went wrong. No 'life hacks' that are really "
            "just product ads. If a hack has a common failure mode, say so."
        ),
    },
    "relatable": {
        "label": "Relatable",
        "blurb": "The small universal experience nobody says out loud.",
        "default_style": "whiteboard_sketch",
        "voice": "young_casual",
        "rules": (
            "Find the specific version of a universal feeling. 'Being tired' is nothing; 'the way "
            "you rehearse a phone call before making it' is the video. Two characters work best: "
            "one does the thing, the other reacts."
        ),
        "guardrails": (
            "Relatable does not mean mocking. The joke is recognition, not the person. Nothing "
            "that punches at a group, a body type, a class, or a nationality."
        ),
    },
    "wholesome": {
        "label": "Wholesome",
        "blurb": "Warm, gentle, quietly encouraging.",
        "default_style": "whiteboard_sketch",
        "voice": "warm_female",
        "rules": (
            "Small and specific beats big and sweeping. One small kind moment lands; a general "
            "statement about kindness does not. Earn the warmth — do not just assert it."
        ),
        "guardrails": (
            "No toxic positivity, and never imply that someone's difficulty is their own fault for "
            "not thinking positively. Do not give mental health advice or present a feeling as a "
            "diagnosis."
        ),
    },
    "empathy": {
        "label": "Social & Human",
        "blurb": "Poverty, inequality, hardship — treated with care.",
        "default_style": "stock_footage",
        "voice": "british_calm",
        "rules": (
            "Explain a system or a structural reality, not an individual's misery. The viewer "
            "should come away understanding something they did not before, not just feeling bad. "
            "Concrete and specific; no sweeping generalisations about any country or group."
        ),
        "guardrails": (
            "THIS ARCHETYPE HAS THE STRICTEST RULES. Never invent a person, a family, or a story "
            "and present it as real. Never ask for donations or name a charity — you cannot verify "
            "one and a fraudulent appeal is a serious harm. Never use anyone's hardship as a "
            "punchline or a shock hook. Do not imply poverty is a personal failing. Do not name "
            "real living individuals. If the topic cannot be handled without a real person's "
            "story, choose a different angle."
        ),
    },
    "dark_humour": {
        "label": "Dark Humour",
        "blurb": "Bleak, deadpan, funny about how things actually are.",
        "default_style": "whiteboard_sketch",
        "voice": "british_calm",
        "rules": (
            "The humour comes from stating an uncomfortable truth flatly and refusing to soften "
            "it. Deadpan delivery, no wink. Short. The bleakness is the joke; cruelty is not."
        ),
        "guardrails": (
            "Target situations, systems, institutions and the general absurdity of being alive — "
            "NEVER real people, identifiable groups, protected characteristics, actual tragedies, "
            "recent deaths, or anyone's suffering. Nothing about self-harm, suicide, eating "
            "disorders, or addiction, in any framing, including as a joke. If the punchline needs "
            "a victim, it is the wrong punchline."
        ),
    },
    "sarcasm": {
        "label": "Sarcasm",
        "blurb": "Saying the opposite, obviously, about something absurd.",
        "default_style": "whiteboard_sketch",
        "voice": "british_calm",
        "rules": (
            "Pick something genuinely absurd and praise it with total sincerity. The gap between "
            "the tone and the content does all the work. Never break character to explain the joke."
        ),
        "guardrails": (
            "Sarcasm about a factual claim can be mistaken for the claim itself when clipped or "
            "screenshotted. Never be sarcastic about health, safety, science, or anything where "
            "someone acting on the literal reading could be harmed."
        ),
    },
    "absurd": {
        "label": "Absurd",
        "blurb": "A stupid premise followed with total commitment.",
        "default_style": "whiteboard_sketch",
        "voice": "energetic",
        "rules": (
            "One absurd premise, played completely straight and escalated. The comedy is in the "
            "commitment, not in signalling that it is silly. Escalate three times, then stop."
        ),
        "guardrails": (
            "Absurd claims must be self-evidently absurd, never plausible-sounding misinformation. "
            "No absurdist framing of real events."
        ),
    },
    "observational": {
        "label": "Observational",
        "blurb": "Stand-up style: noticing the thing everyone does.",
        "default_style": "whiteboard_sketch",
        "voice": "documentary_male",
        "rules": (
            "Open on the observation, immediately. No 'have you ever noticed'. Give a specific "
            "example, then a second one that escalates. End on the sharpest version."
        ),
        "guardrails": (
            "Observations about behaviour, not about groups of people. 'People do X' is fine; "
            "'[group] does X' is not."
        ),
    },

    # ── Sports-specific archetypes (added for the cricket/sports build) ──
    # Same shape as every archetype above: a label, a default style, a
    # default voice, writing rules, and guardrails. Routed to by
    # engine.sports_catalog.archetype_for() based on a topic's category.
    "records_and_stats": {
        "label": "Records & Stats",
        "blurb": "A real record, the number behind it, and why it's hard to beat.",
        "default_style": "sports_visual",
        "voice": "documentary_male",
        "rules": (
            "Open with the record itself, stated as a plain, confident fact — name, number, "
            "format. Then give ONE piece of context that makes the number land: how long it's "
            "stood, how far ahead of second place it is, or what it actually took to set it. "
            "End scene 4 or 5 with the engagement question this channel is built on: state one "
            "related record, then ask viewers to name a second, genuinely connected record in "
            "the comments — see the QUIZ CLOSE instructions below."
        ),
        "guardrails": (
            "Only state a specific number (runs, wickets, catches, dates) when it is in the "
            "RESEARCH NOTES provided. If no research notes are given for a number, describe it "
            "qualitatively ('the most of anyone who has ever played') instead of inventing a "
            "figure. A confidently wrong sports statistic is a real accuracy risk at automated "
            "scale, not a minor detail — this archetype is the one place in this project where "
            "getting a number right is the entire video."
        ),
    },
    "player_story": {
        "label": "Player Life Story",
        "blurb": "A real athlete's career arc — the debut, the breakthrough, the defining moment.",
        "default_style": "sports_visual",
        "voice": "documentary_male",
        "rules": (
            "Tell it as a short arc: where they started, the specific moment that changed "
            "things, and what it led to. One vivid, specific detail (a place, an age, a score) "
            "beats a general 'he worked hard and succeeded' summary every time."
        ),
        "guardrails": (
            "Stick to well-established public sporting facts — career stats, known public "
            "milestones, on-record quotes widely reported in sports media. Never invent a quote, "
            "a private conversation, or a motivation the player has not stated publicly. Treat "
            "every named athlete with respect — no mockery of appearance, personal life, or "
            "struggles outside their sporting career."
        ),
    },
    "where_are_they_now": {
        "label": "Where Are They Now",
        "blurb": "A retired player or forgotten team, and what became of them.",
        "default_style": "sports_visual",
        "voice": "documentary_male",
        "rules": (
            "Anchor on their playing peak in one sentence, then pivot to what they actually do "
            "now — coaching, commentary, administration, a completely different path. Specific "
            "beats vague: name the actual role if it's public knowledge, not just 'stayed "
            "involved in cricket'."
        ),
        "guardrails": (
            "Only state a current role or activity when it is well-established public "
            "information. If unsure of someone's current situation, say the career highlight "
            "and stay general about 'life after playing' rather than guessing at specifics."
        ),
    },
    "unsung_history": {
        "label": "Unsung Achievement",
        "blurb": "A genuinely impressive feat that never got the credit it deserved.",
        "default_style": "sports_visual",
        "voice": "conversational",
        "rules": (
            "Lead with why this deserves attention, not a slow build-up. The hook IS the "
            "injustice of it being forgotten — say that plainly, then deliver the achievement "
            "itself with real specifics."
        ),
        "guardrails": (
            "Do not exaggerate an achievement's significance beyond what's factually true to "
            "make the 'underrated' framing land harder. The feat has to actually be impressive "
            "on its own merits."
        ),
    },
    "history_deep_dive": {
        "label": "History Deep Dive",
        "blurb": "How a team, tournament, or rivalry actually came to be the way it is.",
        "default_style": "sports_visual",
        "voice": "british_calm",
        "rules": (
            "Structure as cause and effect: this happened, which is why that changed, which is "
            "why things are the way they are today. A history video with no throughline is just "
            "a list of dates — the throughline is the point."
        ),
        "guardrails": (
            "Stick to well-documented sporting history. For anything touching real political "
            "tension between countries (e.g. boycotts, isolation eras), state the sporting facts "
            "plainly and neutrally without taking a side on the underlying politics."
        ),
    },
    "rules_explainer": {
        "label": "Rules Explainer",
        "blurb": "One specific rule, explained clearly enough to settle an argument.",
        "default_style": "sports_visual",
        "voice": "conversational",
        "rules": (
            "State the rule precisely, the way the actual law reads, then give ONE concrete "
            "example of it happening in a real match so it's not just abstract text. If the rule "
            "is genuinely confusing or controversial, say why people get it wrong."
        ),
        "guardrails": (
            "Get the rule exactly right — do not simplify a rule into something that's actually "
            "incorrect. If research notes don't confirm an exact number or threshold, describe "
            "the mechanism without inventing the precise figure."
        ),
    },
    "business_and_governance": {
        "label": "Business & Governance",
        "blurb": "The money, structure and power behind the sport.",
        "default_style": "sports_visual",
        "voice": "documentary_male",
        "rules": (
            "Follow the money or the power, concretely: who decides, who gets paid, and why it "
            "works the way it does. Numbers make this format land — use real, well-known figures "
            "where available, described qualitatively otherwise."
        ),
        "guardrails": (
            "Do not state a specific financial figure (revenue, salary, contract value) unless "
            "it is in the RESEARCH NOTES or is extremely well-established public knowledge. "
            "Avoid implying corruption or wrongdoing by any named board, official or company "
            "without well-established, widely-reported facts behind it."
        ),
    },
    "quiz_challenge": {
        "label": "Quiz Challenge",
        "blurb": "A trivia-format video built entirely around the end-card engagement question.",
        "default_style": "sports_visual",
        "voice": "energetic",
        "rules": (
            "Scenes 1-3: build up one confirmed fact or record with real specifics. Scene 4: "
            "state it as the 'reveal'. FINAL SCENE (required): ask a second, genuinely related "
            "question the video has NOT answered, and give a clear instruction — 'Comment the "
            "answer if you know it' or 'Share this with a [sport] fan who'd know' — see the QUIZ "
            "CLOSE instructions below for the exact required fields."
        ),
        "guardrails": (
            "The quiz question must be genuinely answerable and genuinely related to the fact "
            "already given — not a random unrelated trivia question bolted on. Only use facts "
            "given in RESEARCH NOTES; if none are available for a strong quiz pairing, pick a "
            "structural/rules-based question instead of guessing a statistic."
        ),
    },
}

DEFAULT_ARCHETYPE = "informative"

# Archetypes that read better as animated dialogue than as narration over
# footage. The orchestrator uses this when a topic does not pin a style.
DIALOGUE_ARCHETYPES = {"relatable", "wholesome", "dark_humour", "sarcasm", "absurd", "observational"}

# Topics too sensitive to pair with a comedic archetype. Checked before
# generation, so the combination never reaches the model at all.
SENSITIVE_TOPIC_MARKERS = (
    "death", "suicide", "abuse", "war", "genocide", "famine", "disease",
    "cancer", "addiction", "trafficking", "refugee", "disaster", "shooting",
    "assault", "poverty", "starvation", "terror",
)
COMEDIC_ARCHETYPES = {"dark_humour", "sarcasm", "absurd", "relatable"}

# Archetypes whose guardrails explicitly depend on real, sourced background
# ("only state a number when it is in the RESEARCH NOTES provided") — for
# these, brief.py fetches engine.research's Wikipedia grounding before the
# brief is even written, and script_generator.py folds the same notes into
# the script-writing prompt. Every other archetype writes from the topic
# alone, same as before this mechanism existed — fetching research nobody
# asked for just adds an unnecessary network call and prompt bloat.
RESEARCH_GROUNDED_ARCHETYPES = {
    "records_and_stats", "player_story", "where_are_they_now",
    "unsung_history", "history_deep_dive", "rules_explainer",
    "business_and_governance", "quiz_challenge",
}

# Archetypes whose FINAL scene must be the "state a fact, ask a related but
# unanswered follow-up, tell viewers to comment or share it" engagement
# mechanic (engine/engagement.py). This is the core, explicitly-requested
# engagement lever for this channel — see engagement.py's module docstring
# for the exact mechanic and why it exists.
QUIZ_CLOSE_ARCHETYPES = {"records_and_stats", "quiz_challenge"}

# This build is a single, cricket/sports-only channel (see sports_catalog.py
# and personas.py) — the nine v19 general-purpose archetypes at the top of
# this file (relatable, wholesome, empathy, dark_humour, sarcasm, absurd,
# observational, life_hack) were written for a completely different kind of
# channel (comedy skits, wholesome quote cards) and would look completely
# off-brand mixed into a sports-facts feed. `sports_catalog.archetype_for()`
# only ever returns names from this set — this constant is the matching
# SAFETY NET for the rotation fallback in orchestrator.py, so a topic that
# somehow reaches generation with no pinned archetype (a bug, a hand-typed
# topic, a future edge case) still rotates through something on-brand
# instead of accidentally becoming a whiteboard comedy skit about cricket.
SPORTS_ARCHETYPES = [
    "records_and_stats", "player_story", "where_are_they_now", "unsung_history",
    "history_deep_dive", "rules_explainer", "business_and_governance",
    "quiz_challenge", "informative", "myth_busting",
]


def archetype_names():
    return list(ARCHETYPES.keys())


def get_archetype(name: str) -> dict:
    return ARCHETYPES.get(name, ARCHETYPES[DEFAULT_ARCHETYPE])


def is_combination_allowed(topic_text: str, archetype: str) -> tuple:
    """Blocks comedic archetypes on sensitive subjects.

    Returns (allowed, reason). This runs BEFORE the model is called, because
    the reliable way to avoid a joke about a famine is to never ask for one.
    Filtering afterwards means the text existed, and something eventually
    ships it.
    """
    if archetype not in COMEDIC_ARCHETYPES:
        return True, ""
    low = (topic_text or "").lower()
    for marker in SENSITIVE_TOPIC_MARKERS:
        if marker in low:
            return False, (
                f"'{marker}' is too sensitive to pair with the "
                f"'{ARCHETYPES.get(archetype, {}).get('label', archetype)}' format."
            )
    return True, ""


def suggest_style(archetype: str, fallback: str = "stock_footage") -> str:
    return get_archetype(archetype).get("default_style", fallback)


def prompt_block(archetype: str) -> str:
    """The archetype's writing rules and guardrails, formatted for the prompt."""
    a = get_archetype(archetype)
    return (
        f"CONTENT FORMAT: {a['label']} — {a['blurb']}\n\n"
        f"HOW TO WRITE THIS FORMAT:\n{a['rules']}\n\n"
        f"NON-NEGOTIABLE LIMITS FOR THIS FORMAT:\n{a['guardrails']}"
    )
