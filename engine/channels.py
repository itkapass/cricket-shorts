"""
channels.py — route each video to the right YouTube channel.
============================================================

WHY THIS IS A MODULE AND NOT A SETTING
You said the channel count cannot be fixed now. So nothing here hardcodes a
number. Channels are rows in the database; adding your fifth or fiftieth is a
form submission, not a code change or a redeploy.

THE QUOTA FACT THAT DRIVES THE DESIGN (UPDATED — read this before changing daily_cap)
YouTube changed how `videos.insert` is metered: since December 2025 an
upload costs just 1 unit (not the old 1,600), inside its own small dedicated
daily bucket (further separated from other API calls in a June 2026 change).
In practice that puts the real technical ceiling closer to ~100 uploads/day
per Google Cloud project rather than the old 6/day — but this project still
defaults FAR below that on purpose, for two reasons that have nothing to do
with the API quota:

  1. YOUR GOOGLE CLOUD PROJECT IS ALMOST CERTAINLY UNVERIFIED. Any OAuth
     project created after 28 July 2020 (yours will be) has its uploads
     forced to PRIVATE visibility until it passes Google's audit/
     verification process — a real, separate gate from the API quota, and
     the one that actually matters for a new setup. See docs/04 for what
     this means in practice and how to request verification.
  2. YOUTUBE'S OWN SPAM/QUALITY SYSTEMS, not the API, are what actually
     limits a brand-new channel suddenly posting dozens of similar Shorts a
     day — there's no single published number, only "be conservative early
     and build a steady, human-looking cadence" as YouTube's own creator
     guidance.

`daily_cap_for()` below defaults to 6/day and can be safely raised — see its
own docstring — but there is no reason to chase the theoretical ~100/day
ceiling; a steady, spaced-out cadence is the safer and more sustainable
choice for a new channel regardless of what the API alone would allow.

Give each channel its own Google Cloud project and each gets its own quota
pool. That is why every channel row carries its OWN client id, client secret
and refresh token rather than sharing one set — free to set up, and useful
mainly if you later add a genuinely second channel (this app ships with one).

CREDENTIALS NEVER TOUCH THE DATABASE
A channel row stores the NAME of the environment variables holding its
credentials, not the credentials. So the database holds
`YOUTUBE_REFRESH_TOKEN_SCIENCE` as a string, and the actual token lives only in
GitHub Secrets. If the database ever leaked, no channel would be compromised.

CATEGORY ROUTING
Each channel declares which content categories it accepts. A video is routed to
the first enabled channel accepting its category. Nothing matches, and it falls
through to manual export rather than being force-posted somewhere wrong.
"""
import os
import re

from engine.config import get
from engine import archetypes as _arch

# The content categories the pipeline can produce. A channel subscribes to any
# subset. Sourced directly from archetypes.py rather than duplicated here, so
# the two can never drift out of sync the way this list and the old v19
# archetype set eventually did.
CATEGORIES = _arch.archetype_names()

ENV_SUFFIX_RE = re.compile(r"^[A-Z0-9_]{1,40}$")


def _db():
    from supabase import create_client
    url, key = get("SUPABASE_URL"), get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")
    return create_client(url, key)


def load_channels(db=None, only_enabled: bool = True) -> list:
    try:
        db = db or _db()
        q = db.table("channels").select("*")
        if only_enabled:
            q = q.eq("is_enabled", True)
        return q.order("priority", desc=False).execute().data or []
    except Exception as e:
        print(f"[channels] ⚠ Could not load channels: {e}")
        return []


def gemini_key_for(channel: dict) -> str | None:
    """Resolves a channel's own Gemini API key, if it has one.

    Same env_suffix pattern as YouTube credentials: a channel with
    env_suffix 'SCIENCE' reads GEMINI_API_KEY_SCIENCE. A channel with no
    suffix, or whose specific key is not set, falls back to the shared
    GEMINI_API_KEY — so a single-channel setup needs no changes at all.

    WHY THIS MATTERS: Gemini's free tier is ~20 requests/day PER API KEY,
    which in practice means per Google account. Every channel sharing one
    key shares that one 20-request pool between them — three busy channels
    on one key hit the wall in a third of the time, exactly like three
    channels sharing one YouTube upload quota. A free Google AI Studio key
    from a second Google account gets a second independent 20/day pool at
    zero cost; see docs/07 for the two-minute steps.
    """
    suffix = (channel.get("env_suffix") or "").strip().upper()
    if suffix and not ENV_SUFFIX_RE.match(suffix):
        return get("GEMINI_API_KEY")
    var = f"GEMINI_API_KEY_{suffix}" if suffix else "GEMINI_API_KEY"
    return os.environ.get(var) or get(var) or get("GEMINI_API_KEY")


def _youtube_var_status(channel: dict) -> tuple:
    """Returns (creds_dict_or_None, missing_var_names). Shared by
    credentials_for() (unchanged yes/no contract, so nothing calling it
    breaks) and missing_credentials_for() below, which exists specifically
    so a publish failure can say WHICH secret is missing instead of the
    generic, unhelpful 'credentials missing' — that used to mean opening
    this file and reading the log just to find out it was one specific
    variable (e.g. YOUTUBE_CLIENT_SECRET_COMEDY) that was never added,
    among three that all sound alike.
    """
    suffix = (channel.get("env_suffix") or "").strip().upper()
    if suffix and not ENV_SUFFIX_RE.match(suffix):
        print(f"[channels] ⚠ Ignoring unsafe env_suffix on '{channel.get('name')}': {suffix!r}")
        return None, [f"(invalid env_suffix: {suffix!r})"]

    def var(base):
        return f"{base}_{suffix}" if suffix else base

    cid = os.environ.get(var("YOUTUBE_CLIENT_ID")) or get(var("YOUTUBE_CLIENT_ID"))
    secret = os.environ.get(var("YOUTUBE_CLIENT_SECRET")) or get(var("YOUTUBE_CLIENT_SECRET"))
    token = os.environ.get(var("YOUTUBE_REFRESH_TOKEN")) or get(var("YOUTUBE_REFRESH_TOKEN"))

    missing = [
        var(n) for n, v in (
            ("YOUTUBE_CLIENT_ID", cid),
            ("YOUTUBE_CLIENT_SECRET", secret),
            ("YOUTUBE_REFRESH_TOKEN", token),
        ) if not v
    ]
    if missing:
        return None, missing
    return {"client_id": cid, "client_secret": secret, "refresh_token": token}, []


def credentials_for(channel: dict) -> dict | None:
    """Resolves a channel's OAuth credentials from the environment.

    A channel with env_suffix 'SCIENCE' reads YOUTUBE_CLIENT_ID_SCIENCE etc.
    A channel with an empty suffix reads the unsuffixed names, so a single
    existing channel keeps working with no migration.
    """
    creds, missing = _youtube_var_status(channel)
    if missing:
        print(f"[channels] ⚠ Channel '{channel.get('name')}' is missing secrets: {', '.join(missing)}")
    return creds


def missing_credentials_for(channel: dict) -> list:
    """Just the list of missing secret names (empty list if nothing's
    missing) — for callers that want to SAY which one, not just fail."""
    _, missing = _youtube_var_status(channel)
    return missing


def persona_keys_for(channel: dict) -> list:
    """A channel's full persona list: its primary persona_key plus any
    additional_persona_keys, deduplicated, in order.

    WHY THIS EXISTS: a channel used to accept exactly one persona. That was
    a real limitation for a broader multi-persona app, where "explain
    something new" could naturally span several personas at once rather than
    just one. This app ships with a single persona (cricket_and_sports), so
    a channel built fresh from this fork has nothing to add here — but the
    mechanism is kept intact for a future second channel/persona, so every
    place that used to check `channel.get("persona_key") == some_key` still
    checks membership in this list instead, letting a channel genuinely draw
    from several personas' topic invention if more are ever added.

    The primary persona_key field is kept exactly as it was (still the one
    shown prominently, still what a brand-new channel has after picking one
    persona in the dropdown) — additional_persona_keys is purely additive,
    so a channel that never uses it behaves identically to before this existed.
    """
    keys = []
    primary = channel.get("persona_key")
    if primary:
        keys.append(primary)
    for k in (channel.get("additional_persona_keys") or []):
        if k and k not in keys:
            keys.append(k)
    return keys


def route(category: str, channels: list = None, db=None, persona_key: str = None) -> dict | None:
    """Picks the channel a video should publish to.

    Tries persona first when the video has one: a tech-explainer channel and a
    top-10-facts channel can both legitimately accept the "informative"
    archetype, and archetype alone cannot tell them apart — only the persona
    can. Falls back to archetype-only matching for videos with no persona,
    which is every video from before this existed, so nothing already set up
    breaks.

    Returns None when nothing accepts it — the caller should then fall back to
    manual export. Silently posting an unmatched video to whichever channel
    happens to be first would be worse than not posting it.
    """
    channels = channels if channels is not None else load_channels(db=db)
    if not channels:
        return None

    if persona_key:
        # Membership in the channel's FULL persona list (primary +
        # additional), not just equality with the primary — this is what
        # actually makes a multi-persona channel receive videos from all of
        # its personas, not only the one that happens to be "primary".
        persona_match = [c for c in channels if persona_key in persona_keys_for(c)]
        if persona_match:
            return persona_match[0]

    for ch in channels:
        accepted = ch.get("categories") or []
        if isinstance(accepted, str):
            accepted = [c.strip() for c in accepted.split(",") if c.strip()]
        if category in accepted:
            return ch

    catchall = [c for c in channels if c.get("is_catchall")]
    return catchall[0] if catchall else None


def publishable_channels(db=None) -> list:
    """Channels that are enabled, set to auto-publish, AND have working
    credentials. A channel missing its secrets is reported once here rather
    than failing later inside the upload call."""
    out = []
    for ch in load_channels(db=db):
        if ch.get("publish_mode") != "auto":
            continue
        if credentials_for(ch):
            out.append(ch)
    return out


def daily_cap_for(channel: dict) -> int:
    """Per-channel daily upload cap.

    The YouTube Data API's real ceiling here is generous — videos.insert has
    cost 1 unit (not the old 1600) since Dec 2025, inside its own ~100-unit/
    day bucket, so quota alone would allow dozens of uploads a day. That is
    NOT the number to design around. Two things are:

      1. A brand-new (unverified) Google Cloud OAuth project forces every
         upload to PRIVATE until Google's audit/verification passes — a
         one-time gate, not a daily one, but it means "raise the cap" never
         fixes a beginner's "my videos aren't going public" problem.
      2. YouTube's own spam/quality systems watch posting cadence on young
         channels. Several Shorts an hour from a brand-new channel reads as
         automation and risks a review flag, regardless of API quota.

    Default of 6/day keeps a single channel comfortably inside a steady,
    human-looking cadence (this app's own publish.yml spaces uploads across
    the day using this number). The clamp tops out at 20 so a channel that
    has built real history and wants to push harder can raise `daily_cap`
    in the dashboard without a code change — but there is deliberately no
    path to "treat the ~100-unit bucket as the target."
    """
    try:
        return max(1, min(int(channel.get("daily_cap") or 6), 20))
    except (TypeError, ValueError):
        return 6


def published_today(channel_id, db=None) -> int:
    from datetime import datetime, timezone, timedelta
    try:
        db = db or _db()
        # YouTube's quota resets at midnight Pacific. Approximating with a
        # rolling 24h window is intentionally conservative — it can only ever
        # under-publish, never over-publish into a 403.
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        rows = (
            db.table("videos").select("id")
            .eq("channel_id", channel_id).eq("status", "published")
            .gte("published_at", since).execute().data
        ) or []
        return len(rows)
    except Exception as e:
        print(f"[channels] ⚠ Could not count today's uploads: {e}")
        return 0


def min_gap_minutes(channel: dict) -> int:
    """The minimum spacing between two uploads on the same channel.

    WHY THIS EXISTS

    The publish workflow runs every 30 minutes and published one video every
    time it found one approved. So a channel capped at 4 videos/day did not
    post 4 videos across the day — it posted all 4 inside the first two
    hours, then sat silent for twenty-two. That is bad on two counts:

      1. AUDIENCE. Shorts are surfaced over hours, not minutes. Four uploads
         inside two hours compete with each other for the same slice of
         impressions instead of each getting its own window, and the channel
         is invisible for the rest of the day.
      2. PATTERN. A burst followed by total silence, every single day, is a
         far more machine-looking signature than a steady cadence.

    The gap is DERIVED from the daily cap rather than being another number to
    keep in sync by hand — 4/day becomes one every 6 hours automatically. Set
    `publish_min_gap_minutes` in Settings to override it explicitly.
    """
    override = _setting_int("publish_min_gap_minutes", 0)
    if override > 0:
        return override
    cap = daily_cap_for(channel)
    # A whole day divided by the cap. 4/day -> 360 min. 6/day -> 240 min.
    return max(30, (24 * 60) // max(cap, 1))


def _setting_int(key: str, default: int) -> int:
    try:
        rows = _db().table("settings").select("value").eq("key", key).execute().data or []
        return int(rows[0]["value"]) if rows else default
    except Exception:
        return default


def minutes_since_last_publish(channel_id, db=None):
    """How long since this channel last published, in minutes.

    Returns None if it has never published — which must be treated as
    "go ahead", not "wait", or a brand-new channel would never start.
    """
    from datetime import datetime, timezone
    try:
        db = db or _db()
        q = db.table("videos").select("published_at").eq("status", "published")
        if channel_id:
            q = q.eq("channel_id", channel_id)
        rows = q.order("published_at", desc=True).limit(1).execute().data or []
        if not rows or not rows[0].get("published_at"):
            return None
        last = rows[0]["published_at"].replace("Z", "+00:00")
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_dt).total_seconds() / 60.0
    except Exception as e:
        print(f"[channels] ⚠ Could not read last publish time: {e}")
        return None


def ready_to_publish(channel: dict, db=None) -> tuple:
    """(is_ready, human_readable_reason). Checks spacing, not credentials."""
    gap = min_gap_minutes(channel)
    since = minutes_since_last_publish((channel or {}).get("id"), db=db)
    if since is None:
        return True, "no previous upload on this channel"
    if since >= gap:
        return True, f"last upload was {int(since)} min ago (gap is {gap} min)"
    wait = int(gap - since)
    hrs, mins = divmod(wait, 60)
    pretty = f"{hrs}h {mins}m" if hrs else f"{mins}m"
    return False, (
        f"last upload was only {int(since)} min ago; this channel posts one "
        f"every {gap} min. Next slot in {pretty}."
    )


def describe(channel: dict) -> str:
    cats = channel.get("categories") or []
    if isinstance(cats, str):
        cats = [c.strip() for c in cats.split(",")]
    return (
        f"{channel.get('name')} "
        f"[{channel.get('publish_mode')}] "
        f"cap={daily_cap_for(channel)}/day "
        f"every {min_gap_minutes(channel)}min "
        f"categories={', '.join(cats) or 'none'}"
    )
