"""
image_license.py — no picture goes in a video unless its licence says so.
=============================================================================

WHAT PART 1E ASKS FOR

  "License filter required: only use Wikimedia/stock images confirmed CC0/
   CC-BY or clearly free-to-reuse license metadata. Reject anything without
   clear free-license metadata, EVEN ON WIKIMEDIA, since licensing is mixed
   there. This filter runs before an image is ever placed in a video."

That last clause is the important one, and it is also a real bug this fork
inherited. `engine/wikimedia_visuals.py` asks the Commons API for
`extmetadata` — which contains the licence — and then never reads it. It
filters on filename and image size only. So the licence has been arriving in
the response all along and being thrown away.

Wikimedia Commons is overwhelmingly free media, but "overwhelmingly" is not
"only": it carries fair-use files, logos under trademark, non-commercial-only
uploads, and files whose permission is disputed or pending deletion. A
YouTube channel that monetises cannot rely on an average.

HOW THE DECISION IS MADE
Allowlist, not blocklist. A licence has to be recognised and approved to
pass. An unrecognised licence string fails — including a new, perfectly
legitimate one — because the cost of being wrong in that direction is one
missing photo, and the cost of being wrong in the other is a copyright strike
on a channel.

ATTRIBUTION
CC-BY and CC-BY-SA require credit. `attribution_line()` builds it and the
pipeline writes it into the video description. CC0 and public domain need
none, and the line is still recorded so there is a permanent record of where
every image came from.

THE REST OF PART 1E
"Movie/event one-liners are text-only references, no copyrighted clips,
posters, or stills." That is enforced by `is_banned_subject()` below, which
refuses to search for a poster or a still at all, and by the script prompt.
"""
import re

# ─── Licences that genuinely permit reuse, including commercially ──────────
# Keys are matched case-insensitively against the licence strings Commons
# returns in extmetadata.LicenseShortName / UsageTerms / License.

_ALLOWED_PATTERNS = (
    r"\bcc0\b",
    r"public\s*domain",
    r"\bpd[- ]",                      # pd-old, pd-us, pd-art, pd-india...
    r"\bpd\b",
    r"\bcc[- ]by\b(?![- ]*nc)",       # cc-by, but NOT cc-by-nc
    r"\bcc[- ]by[- ]sa\b",
    r"\bcc[- ]sa\b",
    r"attribution[- ]sharealike",
    r"^attribution$",
    r"creative\s*commons\s*zero",
    r"gfdl",                          # free, with conditions we satisfy
    r"free\s*art\s*license",
    r"\bfal\b",
    r"open\s*government\s*licen[cs]e",
    r"\bogl\b",
    r"government\s*open\s*data",
)

# Anything matching these fails outright, even if an allowed pattern also
# matches. "CC BY-NC" contains "CC BY"; the NC is what matters.
_FORBIDDEN_PATTERNS = (
    r"\bnc\b", r"non[- ]commercial", r"noncommercial",
    r"\bnd\b", r"no[- ]derivat",
    r"fair\s*use", r"fairuse",
    r"all\s*rights\s*reserved",
    r"copyright(?!ed\s*free)",
    r"\bnon[- ]free\b", r"nonfree",
    r"trademark",
    r"with\s*permission", r"used\s*by\s*permission",
    r"screenshot",
    r"\bpromotional\b",
    r"press\s*(kit|photo|release)",
    r"\bunknown\b", r"\bunclear\b", r"\bdisputed\b", r"\bpending\b",
    r"delet(e|ion)",
)

# Subjects never searched for at all — Part 1E's "no copyrighted clips,
# posters, or stills". Refusing the SEARCH is stronger than filtering the
# results, because a correctly-licensed photo of a film poster is still a
# picture of a film poster.
_BANNED_SUBJECT_PATTERNS = (
    r"\bposter\b", r"\bfilm\s*still\b", r"\bmovie\s*still\b",
    r"\bscreenshot\b", r"\bscreen\s*grab\b", r"\balbum\s*cover\b",
    r"\bbook\s*cover\b", r"\bdvd\b", r"\bblu[- ]ray\b",
    r"\btrailer\b", r"\bscene\s*from\b", r"\blogo\b", r"\bwordmark\b",
)


def _matches_any(text: str, patterns) -> str | None:
    low = (text or "").lower()
    for p in patterns:
        if re.search(p, low):
            return p
    return None


def is_banned_subject(query: str) -> bool:
    """True if we must not even search for this. See _BANNED_SUBJECT_PATTERNS."""
    hit = _matches_any(query, _BANNED_SUBJECT_PATTERNS)
    if hit:
        print(f"[image_license] ✗ Refusing to search for '{query}' — it asks for "
              f"copyrighted artwork (matched /{hit}/). Part 1E: movie and event "
              f"references are text-only.")
        return True
    return False


def extract_license(extmetadata: dict) -> dict:
    """Pulls the licence fields out of a Commons `extmetadata` block.

    Commons is inconsistent about which of these fields is populated, so all
    of them are read and concatenated for matching. A file with none of them
    is treated as having no licence information at all, which fails.
    """
    md = extmetadata or {}

    def val(key):
        v = md.get(key)
        if isinstance(v, dict):
            v = v.get("value")
        return re.sub(r"<[^>]+>", " ", str(v or "")).strip()

    return {
        "short_name": val("LicenseShortName"),
        "usage_terms": val("UsageTerms"),
        "license": val("License"),
        "artist": val("Artist"),
        "credit": val("Credit"),
        "attribution_required": val("AttributionRequired").lower() == "true",
        "restrictions": val("Restrictions"),
        "description_url": val("DescriptionUrl"),
    }


def check(extmetadata: dict, file_title: str = "") -> dict:
    """The gate. Returns {"allowed": bool, "reason": str, "license": str, ...}.

    `allowed` is True ONLY if a recognised free licence is present and no
    forbidden marker is. Everything else — including an empty or unreadable
    licence block — is False.
    """
    info = extract_license(extmetadata)
    blob = " | ".join(filter(None, [
        info["short_name"], info["usage_terms"], info["license"],
        info["restrictions"],
    ]))

    if not blob.strip():
        return {
            "allowed": False,
            "reason": ("no licence information in the file's metadata at all. "
                       "Commons licensing is mixed, so an unlabelled file is "
                       "rejected rather than assumed free."),
            "license": "", "attribution": "", "info": info,
        }

    forbidden = _matches_any(blob, _FORBIDDEN_PATTERNS)
    if forbidden:
        return {
            "allowed": False,
            "reason": (f"licence '{blob[:90]}' matched a forbidden marker "
                       f"(/{forbidden}/) — not free for commercial reuse."),
            "license": blob[:120], "attribution": "", "info": info,
        }

    allowed = _matches_any(blob, _ALLOWED_PATTERNS)
    if not allowed:
        return {
            "allowed": False,
            "reason": (f"licence '{blob[:90]}' is not on the approved list. "
                       f"This is an allowlist on purpose: an unrecognised "
                       f"licence fails, even if it is in fact free."),
            "license": blob[:120], "attribution": "", "info": info,
        }

    if info["restrictions"]:
        return {
            "allowed": False,
            "reason": (f"licence is free but carries a restrictions note: "
                       f"'{info['restrictions'][:90]}'. Not worth the risk."),
            "license": blob[:120], "attribution": "", "info": info,
        }

    return {
        "allowed": True,
        "reason": f"free licence confirmed: {info['short_name'] or blob[:60]}",
        "license": info["short_name"] or blob[:120],
        "attribution": attribution_line(info, file_title),
        "info": info,
    }


def attribution_line(info: dict, file_title: str = "") -> str:
    """The credit line written into the YouTube description.

    Produced for every allowed image, not only the ones that legally require
    it — a complete record of where every picture came from costs one line
    and settles any later question instantly.
    """
    bits = []
    name = (file_title or "").replace("File:", "").strip()
    if name:
        bits.append(name)
    if info.get("artist"):
        bits.append(f"by {info['artist'][:80]}")
    if info.get("short_name"):
        bits.append(f"({info['short_name']})")
    url = info.get("description_url")
    if url:
        bits.append(url)
    return " ".join(bits).strip()


def filter_candidates(candidates: list) -> list:
    """Keeps only images whose licence passes. Logs every rejection with its
    reason, because a silent filter is impossible to debug when a video comes
    out with no pictures in it.

    `candidates` are dicts carrying at least `extmetadata` and `title` — the
    shape engine/wikimedia_visuals._image_info() returns once it is fixed to
    keep the metadata it already requests.
    """
    kept, rejected = [], 0
    for c in candidates or []:
        verdict = check(c.get("extmetadata"), c.get("title", ""))
        if verdict["allowed"]:
            c["license"] = verdict["license"]
            c["attribution"] = verdict["attribution"]
            kept.append(c)
        else:
            rejected += 1
            print(f"[image_license] ✗ {c.get('title', '?')}: {verdict['reason']}")
    if rejected:
        print(f"[image_license] Rejected {rejected} image(s) on licence, kept "
              f"{len(kept)}.")
    return kept
