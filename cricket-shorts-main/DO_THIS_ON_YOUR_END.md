# Do this on your end — cricket-shorts

In order. The first two are the ones that are actively costing you videos
right now.

---

## ① Fix the YouTube token — 2 minutes, do this first

Your dashboard is showing:

> *"The YouTube refresh token was rejected (invalid_grant)."*

Your Google OAuth consent screen is in **Testing** mode. Google expires refresh
tokens after **7 days** in that mode. Your channel will keep stopping every
week until you change this one setting.

1. [console.cloud.google.com](https://console.cloud.google.com) → pick your project
2. **APIs & Services** → **OAuth consent screen**
3. You will see **Publishing status: Testing**. Click **PUBLISH APP** → confirm.
4. It now reads **In production**. Tokens stop expiring on a clock.

You do **not** need Google's verification review. That is only for apps with
outside users; you are the only user of your own app.

Then make one fresh token and update the secret:

```
python -m engine.publisher --setup
```

Copy the refresh token it prints into the `YOUTUBE_REFRESH_TOKEN` secret.
**This time it will keep working.**

---

## ② Run the new database migration — 1 minute

Nothing in the analytics fixes works until this runs. It adds the columns the
feedback loop needs and repairs the videos currently stuck in your queue.

1. Supabase → **SQL Editor** → **New query**
2. Paste all of `supabase/migrations/009_performance_feedback_fixes.sql`
3. **Run**

Safe to run on your existing database. Every statement is `IF NOT EXISTS` or an
idempotent `UPDATE`. It deletes nothing.

**What it fixes immediately:** the `UPDATE videos SET approved_at = COALESCE(...)`
line unsticks every auto-approved video currently sitting behind your
hand-approved ones. Those should start publishing on the next run.

> If you have automatic migrations set up (`docs/14`), pushing this repo runs it
> for you. Running it by hand anyway is harmless.

---

## ③ Re-authorise YouTube for analytics — 2 minutes

Retention is the single most useful number you have — your Studio shows 58.7%
and 54.8% on two videos, and that gap matters far more than the view counts
next to it. The app could not see any of it.

Reading it needs one extra OAuth scope (`yt-analytics.readonly`), and **an
existing token does not gain a scope retroactively** — Google fixes a refresh
token's scopes at consent time.

So after step ① you need to run `--setup` **once more** and update the secret
again. Do step ① first (publish the consent screen), *then* this, or you will
be back here in 7 days.

Until you do, the app falls back to views/likes/comments only. It keeps
working, it just learns less.

---

## ④ Add an OpenRouter key — 2 minutes, free, no card

The fallback chain is now Gemini → Groq → GitHub Models → **OpenRouter**.

1. [openrouter.ai/keys](https://openrouter.ai/keys) → sign in → **Create key**
2. GitHub repo → Settings → Secrets and variables → Actions → **New repository
   secret**
3. Name: `OPENROUTER_API_KEY`. Paste the key.

One key reaches several genuinely free models, and the code tries each in turn,
so one retired model name cannot take the whole link offline.

---

## ⑤ Check that Gemini is actually being used again

After the next generation run, open the run → the **Generate** step → look for:

```
[model_registry] Selected model: gemini-2.5-flash (known free tier)
```

Then check the new videos in your dashboard. The badge should say **written by
gemini**, not **written by groq/backup**.

If it still says groq, open `docs/13_BACKUP_AI_PROVIDER.md` → the "Gemini never
works" section, which now lists exactly what to look for in the log.

---

## ⑥ Drain the backlog

You have a pile of videos that were generated and never published, because of
the queue bug in Area 1. Step ② unsticks them, but at `publish_per_run = 1` and
one upload every few hours they will take a while to clear.

For **one week only**, in the dashboard → Settings:

```
publish_per_run = 2
```

Then set it back to 1. Leaving it at 2 permanently would push you past your
daily cap and into YouTube 403s.

Check how big the backlog is first — Supabase → SQL Editor:

```sql
SELECT status, COUNT(*) FROM videos GROUP BY status;
```

---

## ⑦ Optional: the GitLab backup scheduler

`.gitlab-ci.yml` is in the repo and is **disabled by default** so it cannot
double-post. Only set it up if you want protection against a GitHub Actions
outage. Instructions: `docs/19_BACKUP_SCHEDULER_GITLAB.md`.

---

# What you do NOT need to do

- **Don't touch Cloudflare R2.** Already built, already wired, already deleting
  published videos. Nothing to change.
- **Don't recreate your Supabase project.** Migration 009 is additive.
- **Don't change `max_videos_daily`.** Generation was never the bottleneck;
  publishing was.
- **Don't delete and re-upload the repo.** Just replace the files — every
  change is inside `engine/`, `.github/workflows/` and
  `supabase/migrations/`.

---

# What to watch over the next two weeks

| Where | What you are looking for |
|---|---|
| Dashboard video cards | the badge changing from **groq/backup** to **gemini** |
| Actions → any run → Summary tab | a line starting *"Performance learning:"* |
| Supabase → `insight_log` | rows appearing once you have ~8 measured videos |
| Supabase → `video_stats` | `avg_view_percentage` filling in (after step ③) |
| Your Shorts' comments | the first comments the channel has ever had |

That last one is the real test. 39 videos, 0 comments, was the clearest
evidence that the CTA was only reaching two of the formats. If comments start
appearing, Area 3 is genuinely fixed.

**Do not expect the performance loop to do anything in week one.** It needs
about 8 measured videos before it says anything at all, and that is
deliberate — biasing the whole channel on a handful of videos' worth of noise
would be worse than not learning. The Summary tab will tell you where it is:
*"Performance learning: 5 measured videos so far — need about 8 before any
pattern is trustworthy."*
