# Start here

**Read time: 10 minutes. Setup time: 30–45 minutes, once.**

## What you just downloaded

An app that writes, voices, renders, and (optionally) uploads YouTube
Shorts about cricket — records, player stories, rules, history, IPL,
"did you knows" — plus a 15% slice of other sports and athletes currently
on form. It runs itself on a schedule for free (GitHub Actions + Supabase +
free AI keys), and you review every video in a dashboard before it's
allowed to publish, unless you switch a channel to fully automatic.

A few things worth knowing before you start, because they shape everything
below:
- **One YouTube channel.** This app is built for a single channel, start to
  finish — not a multi-channel network.
- **Male voice, always.** Every format in this app uses one of four male
  neural voices. There is no female voice option anywhere in this app.
- **Every video ends with a question**, not just a fact — "most Test
  wickets ever: 800. Now name the player with the most Man of the Match
  awards... comment your answer, or send this to a cricket fan who'd know."
  That's the retention/share mechanic this whole channel is built around.
- **It never repeats itself on purpose.** New topics are checked against
  everything already made before being added to the queue.
- **It watches its own results.** Once videos are published, it checks
  which ones genuinely over-performed and invents new, related (never
  identical) follow-up topics from the ones that worked.

## Before you start: 6 free accounts (no credit card anywhere)

| Account | For | Get it at |
|---|---|---|
| GitHub | Hosts your code, runs the pipeline on a schedule, for free | github.com |
| Supabase | Your database + video storage | supabase.com |
| Google AI Studio | Free Gemini key — writes every script | aistudio.google.com |
| Groq | Free backup key — kicks in only if Gemini's daily quota runs out | console.groq.com |
| Pexels | Free real video clips for b-roll | pexels.com/api |
| Vercel | Hosts your dashboard, for free | vercel.com |

Have these open in tabs; you'll paste values back and forth. Everything
below assumes you have none of them set up yet.

---

## Step 1 — Put this code on GitHub

```bash
cd cricket-shorts-studio          # the unzipped folder
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Make the repo **Public** — GitHub Actions gives public repos unlimited free
build minutes (private repos get a monthly cap). Your secrets stay private
regardless; only the code is public.

## Step 2 — Database (Supabase): schema + 6 migrations

1. supabase.com → **New project** → name it, pick a region, free plan.
2. **SQL Editor → New query** → open `supabase/schema.sql` from this
   project, copy it all in, **Run**.
3. Repeat step 2 for each of these, **in this exact order** (each one
   builds on the last — this is the step people most often half-do, so
   don't skip ahead):
   1. `supabase/migrations/002_channels_and_concepts.sql`
   2. `supabase/migrations/003_scheduling_and_manual_controls.sql`
   3. `supabase/migrations/004_real_captions_and_visual_source.sql`
   4. `supabase/migrations/005_push_subscriptions.sql`
   5. `supabase/migrations/006_channel_customization.sql`
   6. `supabase/migrations/007_cricket_sports_content_mix.sql`
4. **Storage → New bucket** → name `shorts-videos` → toggle **Public
   bucket ON** → **Save**.
5. **Project Settings → API** → copy your **Project URL**, **anon** key,
   and **service_role** key — you'll need all three shortly.
6. **Authentication → Users → Add user** → set an email + password. This
   is your login for the dashboard (Step 6).

*(Full detail, including what each migration adds, is in
`docs/01_SUPABASE_DATABASE_SETUP.md`.)*

## Step 3 — Free API keys

| Key | Where | Required? |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com → **Get API key** | Required |
| `GROQ_API_KEY` | console.groq.com/keys → **Create API Key** | Strongly recommended — free backup when Gemini's daily ~20 requests run out |
| `PEXELS_API_KEY` | pexels.com/api | Required — real video b-roll |

*(No action needed for the third free fallback, GitHub Models — it reuses
GitHub's own token automatically. See `docs/13_BACKUP_AI_PROVIDER.md`.)*

## Step 4 — Add everything as GitHub secrets

Repo → **Settings → Secrets and variables → Actions → New repository
secret**, one at a time:

```
GEMINI_API_KEY
GROQ_API_KEY
PEXELS_API_KEY
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY
```

## Step 5 — Deploy your dashboard (Vercel, free)

1. vercel.com → **Add New → Project** → pick your GitHub repo.
2. **Root Directory**: `admin-panel`.
3. **Environment Variables**: `VITE_SUPABASE_URL` and
   `VITE_SUPABASE_ANON_KEY` (same values as Step 2.5).
4. **Deploy**. You'll get a URL like `your-project.vercel.app` — that's
   your dashboard from now on, from any device.

*(Full detail: `docs/05_DEPLOY_THE_DASHBOARD.md`.)*

## Step 6 — Log in and add your channel

1. Open your Vercel URL, log in with the email/password from Step 2.6.
2. **Channels → Add channel** → name it, leave the persona as **Cricket &
   Sports Shorts**, leave **Publishing: Manual**, tick **Catch-all**,
   **Save**.

Manual means every video waits for your approval in **Video Queue** before
it can go anywhere — the right way to start so you see what the app
produces before anything is automatic.

## Step 7 — Generate your first videos

1. Repo → **Actions** tab → **Add Topics** → **Run workflow**. Takes about
   a minute — invents your first batch of topics (there are also 270+
   ready-made ones seeded automatically, so this isn't strictly required
   before your first video, just good to confirm it works).
2. **Actions → Generate Video Drafts → Run workflow**. Takes 8–15 minutes.
   Click into the run → **Summary** tab to see exactly what got made and by
   which AI.
3. Open your dashboard → **Video Queue → Pending Review**. Watch it.
   **Approve** the ones you like, **Reject** the rest.

## Step 8 — (Optional, when you're happy with the output) Turn on YouTube publishing

A **Manual** channel packages each approved video into a zip you upload
yourself. To make uploading automatic too:

1. `docs/04_AUTONOMOUS_YOUTUBE_PUBLISHING.md` and `docs/07_YOUTUBE_AND_CHANNELS.md`
   walk through the one-time Google Cloud OAuth setup (~20 minutes).
2. Once done, switch your channel's Publishing mode to **Automatic** in the
   dashboard.

## Step 9 — (Strongly recommended) Turn on alerts

Every failure in this pipeline is silent by default. Repo → **Actions →
Test Alerts → Run workflow** — if nothing arrives, set up Telegram per
`docs/08_ALERTS_AND_MONITORING.md` (5 minutes, free forever).

---

## What runs on its own from here

| When | What |
|---|---|
| Once a day | Invents new topics if the pool is running low, keeping the 85% cricket / 15% other-sport mix |
| 6 times a day | Writes and renders one video |
| Every hour | Checks if a video is due to publish (only if a channel is Automatic) |
| Once a day | Pulls real view/like/comment counts, and spawns follow-up topics from genuine standouts — see `docs/18_ANALYTICS_AND_PERFORMANCE_LOOP.md` |

You review videos whenever you like in **Video Queue**. Nothing reaches
YouTube without your approval unless you've switched a channel to
Automatic.

## If something looks wrong

- Repo → **Actions** → click the failed run → read the last 10–15 lines of
  the log. `docs/12_GITHUB_ACTIONS_EXPLAINED.md` explains every workflow in
  plain English.
- Repo → **Actions → Health Check → Run workflow** — tells you exactly
  what's configured and what isn't, in one run.
- `tools/selfcheck.py` (run locally: `python tools/selfcheck.py`) checks
  the app's own internal wiring is intact — useful if you've changed code.

## Going further

Everything above gets you one channel, posting on a schedule, reviewed by
you. When you want more:

| Want | Read |
|---|---|
| More storage (10 GB free instead of 1 GB) | `docs/06_CLOUDFLARE_R2_STORAGE.md` |
| Understand exactly how content gets decided (topics, formats, research grounding, the quiz mechanic) | `docs/09_CONTENT_SYSTEM.md` |
| Never paste SQL by hand again for future updates | `docs/14_AUTOMATIC_MIGRATIONS.md` |
| Mobile push notifications instead of/alongside Telegram | `docs/17_MOBILE_PUSH_NOTIFICATIONS.md` |
| A second channel later | `docs/10_THREE_CHANNEL_SETUP.md` |
| The full list of every doc | everything in `docs/`, numbered in the order most people need them |
