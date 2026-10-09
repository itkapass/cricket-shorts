# 09 — How the content system works

This explains what decides a video's content, how facts get checked, and
the mechanic the whole channel is built around. Read this before tuning
anything.

---

## The three dials

A video is defined by three independent choices:

```
   TOPIC                ARCHETYPE                STRUCTURE
   what it's about      what kind of video       what shape it takes
   "most Test wickets"  "records & stats"     ×  "countdown"
```

Most automated video tools only have the first dial, which is why their
output all feels the same: same topic list, same voice, same shape, every
day. Three dials means many distinct video shapes per topic, before the
writing even starts.

---

## Dial 1 — Topic: the 85/15 cricket/sports split

Every topic is tagged `sport: "cricket"` or `"other_sport"`, and the app
keeps new topics close to **85% cricket / 15% other sports and
currently-achieving athletes** — both in the ~270 hand-written starter
topics (`engine/sports_catalog.py`) and in everything the AI invents on its
own afterward (`engine/topic_synthesizer.py`, which tags its own invented
ideas with the same split and a specific category — records, rules, player
stories, IPL, World Cup history, and sixteen others; see that file for the
full category list).

You never have to manage this ratio by hand — `engine/content_mix.py` reads
it automatically every run.

## Dial 2 — Archetype (what kind of video, and its guardrails)

| Archetype | What it is | Needs research grounding? | Ends in a quiz question? |
|---|---|:---:|:---:|
| **Records & Stats** | A record, the number, why it's hard to beat | Yes | Yes |
| **Player Story** | An athlete's career arc — debut, breakthrough, defining moment | Yes | |
| **Where Are They Now** | A retired player or forgotten team, today | Yes | |
| **Unsung Achievement** | A real accomplishment that never got its due | Yes | |
| **History Deep Dive** | A real past event or era, told with texture | Yes | |
| **Rules Explainer** | A law or rule of the game, explained with a real scenario | Yes | |
| **Business & Governance** | Boards, auctions, money, administration | Yes | |
| **Quiz Challenge** | Built entirely around the engagement question | Yes | Yes |
| **Informative** | A real mechanism or fact, explained fast | | |
| **Myth Busting** | A widely believed thing that isn't true | | |

Each archetype's writing rules AND content guardrails travel together in
the prompt — never a generic "be accurate" instruction bolted on after. The
guardrail that matters most in this app:

> *Records & Stats:* "Only state a specific number when it is in the
> RESEARCH NOTES provided. If no research notes are given for a number,
> describe it qualitatively instead of inventing a figure." A confidently
> wrong sports statistic, generated automatically at scale, is this
> project's single biggest real accuracy risk — see "Fact grounding" below
> for how research notes get there in the first place.

## Dial 3 — Structure (what shape it takes)

Nine narrative shapes (`engine/narrative.py`) — straight-through,
then-vs-now, escalating list, countdown, misdirect, and others — rotate
deterministically so consecutive videos never look identical even on the
same topic and archetype. See that file for the full list; nothing about
it is cricket-specific.

---

## Fact grounding: why the numbers can be trusted

Before writing a script for any "Yes" row in the table above,
`engine/research.py` searches Wikipedia for the topic and hands the writer
real, sourced extracts as "RESEARCH NOTES." The writer is instructed to
only state a specific number when it appears in those notes — otherwise it
describes the record qualitatively rather than guessing. This is what lets
an automated pipeline make claims like "most Test wickets ever" without
quietly inventing figures.

## The engagement mechanic this channel is built around

Every Records & Stats and Quiz Challenge video ends the same deliberate
way (`engine/engagement.py`): state one real, sourced fact — then ask a
**second, genuinely different, unanswered** question in the same spirit,
and close with an explicit call to action: *comment your answer if you
know it, or send this to a cricket fan who would.* That's the specific,
repeatable mechanic driving comments and shares, not a vague "like and
subscribe."

A dedicated visual card (the `sports_visual` render style's "quiz" scene)
displays the question on screen with a big ghosted "?" so it reads as a
deliberate pause, not just more narration.

## The visual layer

| Style | What it looks like | When it's used |
|---|---|---|
| **Sports Visual** (default) | Real matching footage for most scenes; a drawn stat card or quiz card for the scenes that need one | Every archetype in the table above |
| **Stock Footage** | Real b-roll from Pexels with a slow Ken Burns zoom | Informative / myth-busting topics with no stat or quiz scene |
| **Whiteboard Sketch** | A hand-drawn diagram that builds as it's explained | Available as a manual override |
| **Character Skit** | 2D animated characters who talk, blink, react | Available as a manual override — not used by any cricket/sports archetype by default |
| **Quote Card** | Minimal drifting gradient, captions carry everything | Available as a manual override |

**If no good real clip exists for a scene**, the app falls back to a still
photo animated with a Ken Burns effect — a slow zoom/pan over 5 seconds —
rather than a blank screen or an unrelated clip.

## Captions

- Break at punctuation, not every N words, so each card is a readable
  fragment.
- The word currently being spoken is highlighted, so captions feel alive
  rather than like a subtitle track.
- Timings come from the TTS engine itself, not from transcribing the audio
  back — numbers and hyphenated words stay intact and nothing gets
  misheard.

---

## Duplicate prevention: never the same video twice

Before a topic is allowed to generate, `engine/concept_memory.py` checks it
against every concept already made using three independent signals —
lexical (wording), topical (subject), and semantic (an AI embedding
similarity check) — so a near-duplicate is caught even when it's phrased
completely differently from the original. This is the AI itself doing the
"has this basically been said already?" judgment, not a human maintaining
a list.

## The performance loop: the channel gets smarter from its own results

Once videos are published, a daily job reads real view/like/comment counts
and uses them two ways:

1. **Smarter daily planning.** Each day's batch is split into predicted
   "winners" and "variety" (configurable ratio, default 50/50 — a 4-video
   day really is 2 and 2). "Predicted winner" starts as an editorial guess
   and is automatically replaced by real measured performance the moment
   it exists.
2. **Follow-ups from genuine standouts.** A video that clearly
   outperforms this channel's own recent average spawns 2 new, genuinely
   different (never a rename) follow-up topics on the same proven subject.

Full detail: `docs/18_ANALYTICS_AND_PERFORMANCE_LOOP.md`.

---

## What happens each run

```
1.  Pick topic, archetype, structure     (85/15 mix + winner/variety cadence)
2.  Load the concept ledger              (everything already made)
3.  Fetch Wikipedia research notes       (for the archetypes that need them)
4.  Write the storyboard                 (rules + guardrails + research + avoid-list)
5.  Check for repeats                    → skip BEFORE rendering
6.  Generate voice                       (always one of four male voices)
7.  Render                               (real footage / stat / quiz cards)
8.  Quality gates                        → reject broken renders automatically
9.  Upload to storage, queue for you
10. You approve / reject / export
11. Publish → record concept → delete file
12. (daily) Sync real stats, spawn follow-ups from standouts
```

Steps 5 and 8 exist so that by the time a video reaches you, it's neither a
repeat nor mechanically broken. Your review is for judging whether it's
*good* — the part no automated check can do.

## The honest bit about volume

The daily cap (`engine/channels.py` → `daily_cap_for()`, default 6) is set
with YouTube's own spam/quality review in mind, not the raw API quota,
which is far more generous than it used to be. Forcing volume past what
the content pipeline can genuinely keep distinct is precisely the pattern
that triggers YouTube's inauthentic-content review. Ten strong, accurate
videos a week will outperform sixty repetitive ones, and won't put your
channel at risk.
