# Adding a second channel later (optional — most people skip this)

**This app is built for ONE YouTube channel.** Everything in `docs/00` through
`docs/09` sets up exactly that, and for almost everyone that's the whole
setup — skip this file entirely unless you specifically want a *second*,
separate channel running its own content strategy alongside your main one
(say, a channel for a different sport entirely, or a completely different
topic you want to run through the same pipeline).

The multi-channel machinery this doc uses was kept from an earlier,
broader version of this project's architecture — it still works, it's just
not part of the normal path for a cricket/sports channel, which is why this
doc comes after the main setup rather than inside it.

---

## What a second channel needs that your first one doesn't

Your one channel today shares nothing with a second one you might add —
each channel can have its own content persona, its own Gemini API key (so
they don't compete for the same free daily quota), and its own YouTube
login. None of this is required for a second channel to work — it will
happily share your existing key and quota — but it's worth doing if you
want the second channel posting at full volume too.

## Step 1: Add a second persona (only if the new channel needs a genuinely different content strategy)

This app ships with exactly one persona, `cricket_and_sports` (see
`engine/personas.py`). If your second channel is, say, a general sports
trivia channel with a different split or tone, add a second entry to the
`PERSONAS` dict in that file, following `cricket_and_sports` as the
template — then mirror it in `admin-panel/src/lib/personas.js` (`tools/selfcheck.py`
checks the two stay in sync). If your second channel is happy drawing from
the exact same cricket/sports content strategy, skip this step — one
persona can feed more than one channel.

## Step 2: Create the channel

Dashboard → **Channels** → **Add channel** → name it, pick its persona,
leave categories as the auto-filled defaults, **Publishing: Manual** to
start → **Save**.

> **Why "Manual" to start:** a channel needs its own YouTube login before it
> can auto-post (Step 4 below). Leave it on Manual for the first week,
> watch what comes out, then switch to Automatic once you're happy.

## Step 3: Give it its own free Gemini key (optional, ~10 min)

**Why this matters:** Gemini's free daily request allowance is **per Google
Cloud project**, not per API key — three keys created inside *one* Google
account all share the *same* project and the same daily pool. The only way
to get a genuinely separate allowance is a separate **Google account**.

1. Go to **aistudio.google.com**, signed into a different Google account
   than your main one (a plain new Gmail address works fine).
2. **Get API key** (left sidebar) → **Create API key** → copy it.
3. Add it as a GitHub repo secret with a suffix of your choosing, e.g.
   `GEMINI_API_KEY_SPORTS2`.
4. Back in **Channels**, edit the new channel and set its "secret suffix"
   field to `SPORTS2` — the same suffix mechanism already used for YouTube
   credentials.

Skip this and the new channel just shares your existing default key and
quota with your first channel — everything still works, just with one
shared daily allowance between the two.

## Step 4: Connect YouTube for the new channel (only when ready to go Automatic)

1. Google Cloud Console → a **new project** for this channel.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID → Desktop app**.
4. Copy the Client ID and Client Secret.
5. In an incognito window, signed into the Google account for *that*
   channel's YouTube:
   ```
   set YOUTUBE_CLIENT_ID=paste-it-here
   set YOUTUBE_CLIENT_SECRET=paste-it-here
   python -m engine.publisher --setup
   ```
6. It prints a refresh token. Add all three values as GitHub secrets with
   the matching suffix (`YOUTUBE_CLIENT_ID_SPORTS2`, etc.).
7. Back in **Channels**, switch the new channel's Publishing to **Automatic**.

Full step-by-step detail on this OAuth flow is in `docs/07_YOUTUBE_AND_CHANNELS.md`.

## Step 5: Let it invent its own topics

Dashboard → **Settings** → **Automatic Topic Rotation** — leave this field
**blank**. Every enabled channel already gets topics invented for it
automatically; this field only ever ADDS extra personas on top for a
persona that doesn't have a channel yet, so there's normally nothing to
type here even with two channels running.

---

That's the whole list. A second channel otherwise behaves exactly like
your first one: it shows up in Video Queue, gets its own approval workflow,
and follows its own `daily_cap`.
