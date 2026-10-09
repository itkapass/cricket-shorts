"""
engagement.py — the end-of-video engagement question this channel is built
around.
=============================================================================

THE MECHANIC (asked for explicitly, in these words)
"after saying who holds the most wicket, runs and catches for test series in
the video, at the end of the video, we can ask who holds the most man of the
match in test series... comment the answer if you know or share the video to
the cricket lover if they knew the answer... this will automatically make
the video more engaging and will be a huge lead to share or comment"

WHY THIS IS ITS OWN MODULE
The instructions for it are long and specific enough to drown out the rest
of script_generator's system prompt if inlined there, and this exact
mechanic is referenced from three places — script_generator.py's JSON
schema, sports_visual.py's "quiz" scene_kind card, and archetypes.py's
guardrails for quiz_challenge/records_and_stats — so it earns being named
and owned in one place instead of copied three times.

WHAT MAKES A GOOD CLOSING QUESTION
- Genuinely related to the fact already stated in the video — a second,
  connected record in the SAME category, not a random unrelated trivia
  question bolted on for the sake of having one.
- Genuinely answerable — a real statistic, name, or rule; never invented.
- NOT answered anywhere in the video. The entire mechanic depends on the
  answer only existing in the viewer's head or in the comments below.
- Paired with one explicit, low-friction instruction: comment the answer,
  or share with a specific kind of person who would know it.

ONLY FOR archetypes.QUIZ_CLOSE_ARCHETYPES
Not every video ends this way — a rules explainer or a "where are they now"
video has its own honest way to close (see their own `rules` in
archetypes.py). Bolting a quiz onto every single video would make it feel
like a gimmick instead of a genuine payoff; it stays reserved for the two
formats built around it.
"""


def prompt_block(archetype: str) -> str:
    """Instructions for the mandatory closing engagement scene. Callers
    should only include this in a prompt when
    `archetype in engine.archetypes.QUIZ_CLOSE_ARCHETYPES` — it is written
    assuming the model has already been told this format ends this way by
    that archetype's own `rules` text, and adds the exact mechanical detail
    (field names, ordering, what never to do) that a format description
    alone would leave ambiguous."""
    return """

QUIZ CLOSE — REQUIRED FOR THIS FORMAT:
The FINAL scene must do all three of these, in order, inside one or two short
sentences of voice_text:
  1. Ask ONE follow-up question that is genuinely related to the fact this
     video already gave — the same category (e.g. if the video is about most
     Test wickets, ask about most Man of the Match awards in Tests, not an
     unrelated question about a different sport or a different format).
  2. NEVER answer it. If the video answers its own question, the mechanic is
     pointless — the answer must only exist in the viewer's head, or in the
     comments once someone posts it.
  3. Give ONE explicit, specific instruction for what to do with that —
     "Comment the answer if you know it" or "Share this with a [sport] fan
     who'd know" (pick whichever fits the question better; vary the exact
     wording video to video rather than reusing the same sentence every
     time — a channel that says the identical line on every video reads as
     a bot, which is the opposite of what this mechanic is for).

On this final scene ONLY, set "scene_kind": "quiz" and fill "quiz_question"
with just the question itself, in one short sentence, no CTA text in that
field — the CTA sentence belongs in voice_text alongside it.

Do not invent the question's answer or hint at it anywhere in the video. Do
not reuse a question this video already answered earlier. If you cannot
think of a genuinely related, genuinely unanswered question, ask about a
rule or structural fact connected to the topic instead of forcing a weak
statistical pairing — a slightly less punchy but honest question beats a
fabricated-sounding one.
"""


def normalize(storyboard: dict, archetype: str) -> dict:
    """Defensive post-processing for scene_kind, mutating and returning the
    same storyboard dict. Same spirit as script_generator's own icon/
    transition normalization: a model that ignores instructions should
    degrade the video quietly, never ship something broken.

    Three independent checks, each cheap and each safe to skip if it finds
    nothing to fix:
      1. At most one scene may be scene_kind "stat" (the guardrail says "at
         most ONE scene, the reveal") — extras are downgraded to "normal".
      2. Only the LAST scene may be scene_kind "quiz" — an earlier scene
         marked "quiz" is downgraded (a mid-video quiz card makes no sense;
         the mechanic is a closer by design).
      3. For QUIZ_CLOSE_ARCHETYPES specifically: if the final scene is
         marked "quiz" but its voice_text does not actually contain a
         question mark, the model produced a quiz-styled visual card with
         no real question driving it — worse than no card at all, so the
         label is dropped rather than shipped. The reverse case (a real
         closing question with no scene_kind set) is upgraded to "quiz" so
         it gets the visual treatment it earned.
    """
    from engine import archetypes as arch

    scenes = storyboard.get("scenes") or []
    if not scenes:
        return storyboard

    # (1) at most one "stat" scene.
    seen_stat = False
    for sc in scenes:
        if sc.get("scene_kind") == "stat":
            if seen_stat:
                sc["scene_kind"] = "normal"
            seen_stat = True

    # (2) only the final scene may be "quiz".
    last = scenes[-1]
    for sc in scenes[:-1]:
        if sc.get("scene_kind") == "quiz":
            print("[engagement] ⚠ A non-final scene was marked 'quiz' — "
                  "reverting to normal (the engagement question is a closer only).")
            sc["scene_kind"] = "normal"
            sc.pop("quiz_question", None)

    # (3) the final scene's "quiz" label must be backed by an actual question.
    if archetype in arch.QUIZ_CLOSE_ARCHETYPES:
        has_question_mark = "?" in (last.get("voice_text") or "")
        if last.get("scene_kind") == "quiz" and not has_question_mark:
            print("[engagement] ⚠ Final scene marked 'quiz' but voice_text has no "
                  "question — reverting scene_kind to normal for this video.")
            last["scene_kind"] = "normal"
            last.pop("quiz_question", None)
        elif has_question_mark and last.get("scene_kind") != "quiz":
            last["scene_kind"] = "quiz"

    return storyboard
