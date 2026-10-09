"""
research.py — verified factual grounding for the "getting the number right"
archetypes (records_and_stats, player_story, rules_explainer, etc).
=============================================================================

WHY THIS IS A SEPARATE MODULE FROM pulse.py
pulse.py answers "what is currently being talked about" (Google News
headlines) so the WRITER can sound quietly aware of the moment — it
explicitly instructs the model to NEVER state a headline as a fact.

This module answers a completely different question — "what is actually
TRUE about this subject" — real records, real dates, real structures — so
number-heavy archetypes have something real to draw from instead of the
model's own (frequently wrong, frequently outdated) memory of a statistic.
Cricket record books change constantly and a confidently-wrong number is
exactly the failure mode archetypes.py's guardrails were written to prevent
("Only state a specific number... when it is in the RESEARCH NOTES
provided").

SOURCE: Wikipedia, keyless, no signup, no rate-limit headaches
Wikipedia is not perfect, but it is: (a) free with zero setup, (b) kept
current by a large, active editor base for exactly the kind of subject this
project covers (cricket records, players, boards, rules), and (c) licensed
CC BY-SA, so short paraphrased facts drawn from it for a narrated video are
on solid ground. This module never feeds verbatim sentences into a script —
script_generator.py's prompt separately instructs the model to write its own
words from these notes, never to quote them.

DEGRADES TO NOTHING, SAFELY
Every network call here is wrapped and timed out. On any failure this
returns [] — exactly like pulse.py — and the archetype guardrails already
say what to do with no notes: describe the fact qualitatively instead of
inventing a number. A research failure makes a video slightly vaguer, never
wrong, and never blocks a generation run.
"""
import re
import urllib.parse
import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT = 12
MAX_PAGES = 2              # at most 2 Wikipedia pages fetched per topic
MAX_EXTRACT_CHARS = 2200   # keeps prompt size sane while leaving room for real specifics
USER_AGENT = "CricketShortsStudio/1.0 (free educational short-form video project)"


def _search_titles(query: str, limit: int = 3) -> list:
    """Returns up to `limit` Wikipedia page titles best matching `query`, best
    match first. [] on any failure — the caller treats that exactly like
    "nothing found", not an error."""
    try:
        resp = requests.get(
            WIKIPEDIA_API,
            params={
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": limit, "format": "json", "srprop": "",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return [r["title"] for r in data.get("query", {}).get("search", [])]
    except Exception as e:
        print(f"[research] ⚠ Wikipedia search failed for {query!r}: {e}")
        return []


def _fetch_extract(title: str) -> dict:
    """Returns {"title", "extract", "url"} for one page, or {} on failure or
    if the page has no usable text (a disambiguation stub, a redirect to
    nowhere, etc)."""
    try:
        resp = requests.get(
            WIKIPEDIA_API,
            params={
                "action": "query", "prop": "extracts", "explaintext": 1,
                "exsectionformat": "plain", "titles": title, "format": "json",
                "redirects": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                continue
            extract = (page.get("extract") or "").strip()
            if not extract:
                continue
            extract = re.sub(r"\n{3,}", "\n\n", extract)[:MAX_EXTRACT_CHARS]
            real_title = page.get("title", title)
            url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(real_title.replace(" ", "_"))
            return {"title": real_title, "extract": extract, "url": url}
    except Exception as e:
        print(f"[research] ⚠ Wikipedia extract failed for {title!r}: {e}")
    return {}


def fetch_research_notes(topic_name: str, topic_description: str = "", archetype: str = "") -> list:
    """Returns up to MAX_PAGES {"title", "extract", "url"} dicts of real,
    sourced background for `topic_name`, or [] on any failure/no-match.

    [] is a completely fine outcome — every archetype guardrail that reads
    RESEARCH NOTES already says what to do without them (go qualitative,
    never invent a figure). Nothing here can block a generation run.

    `archetype` is accepted (not currently branched on) so callers can pass
    it through uniformly with pulse.fetch_pulse()'s signature; kept for
    future archetype-specific search tuning without changing every caller.
    """
    query = topic_name if not topic_description else f"{topic_name} {topic_description.split('.')[0]}"
    titles = _search_titles(query, limit=MAX_PAGES + 1)

    notes, seen = [], set()
    for title in titles:
        if len(notes) >= MAX_PAGES:
            break
        if title in seen:
            continue
        seen.add(title)
        page = _fetch_extract(title)
        if page:
            notes.append(page)

    if notes:
        print(f"[research] ✓ {len(notes)} source page(s) grounded for '{topic_name}': "
              f"{', '.join(n['title'] for n in notes)}")
    else:
        print(f"[research] No Wikipedia grounding found for '{topic_name}' — "
              f"writer will describe numbers qualitatively instead of stating a figure.")
    return notes


def prompt_block(notes: list) -> str:
    """Formats research notes as the RESEARCH NOTES prompt section the
    archetype guardrails in archetypes.py refer to by name. Keep this
    function's output and that guardrail wording in sync — they describe the
    same mechanism from two different files."""
    if not notes:
        return ""

    sections = "\n\n".join(f"[{n['title']}]\n{n['extract']}" for n in notes)
    return f"""

RESEARCH NOTES (real, sourced background — Wikipedia, {len(notes)} page(s)):
{sections}

HOW TO USE THESE NOTES:
Only state a specific number, date, name or record as fact if it appears in
the notes above. Paraphrase in your own words — never copy a sentence
verbatim. If the notes don't cover a number you want to use, describe it
qualitatively instead of inventing a figure. Records change — if a note
reads oddly, looks outdated, or contradicts itself, prefer the safer
qualitative phrasing over repeating it as certain.
"""


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Preview the Wikipedia research grounding for a topic")
    p.add_argument("topic")
    p.add_argument("--description", default="")
    a = p.parse_args()

    found = fetch_research_notes(a.topic, a.description)
    for n in found:
        print(f"\n=== {n['title']} ({n['url']}) ===")
        print(n["extract"][:500] + ("..." if len(n["extract"]) > 500 else ""))
    if found:
        print(prompt_block(found))
