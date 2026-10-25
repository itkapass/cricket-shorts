# 19 — Backup scheduler on GitLab CI (optional)

**Read this only if you want a second, independent scheduler.** You do not need
it to run the channel. GitHub Actions is the primary scheduler and it works.

## What problem this solves

Two things can stop GitHub from running your scheduled jobs, neither of which
is your fault:

1. A GitHub Actions outage.
2. GitHub auto-disabling scheduled workflows after about 60 days with no
   repository activity, or your account hitting a usage cap.

`keepalive.yml` already handles #2 by committing to the repo on a schedule. This
file handles #1.

## What it is not

It is **not** a second copy of the app. `.gitlab-ci.yml` runs
`python -m engine.publish_approved` — the exact same code, from the same
repository. There is no second version to keep in sync.

## It is OFF by default, on purpose

Two schedulers publishing at once would double-post to your channel. The job
only runs when a CI/CD variable called `BACKUP_SCHEDULER_ENABLED` is set to
`true`. Until then the file sits there doing nothing.

## Setup (only when you want it)

1. Make a free account at gitlab.com.
2. **New project → Import project → Repository by URL**, and paste your GitHub
   repo URL. Tick **Mirror repository** so GitLab keeps itself up to date.
3. In the GitLab project: **Settings → CI/CD → Variables**. Add the same
   secrets you set in GitHub. At minimum:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
   - `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`
     (only if you use R2 — see docs/06)

   Mark every one of them **Masked** and **Protected**.
4. **Build → Pipeline schedules → New schedule.** Set it to hourly.
5. Leave `BACKUP_SCHEDULER_ENABLED` **unset** for now.

## Turning it on during a GitHub outage

Set `BACKUP_SCHEDULER_ENABLED` to `true` in GitLab's CI/CD variables.
**Turn off the GitHub `publish.yml` workflow at the same time** (Actions tab →
Publish Approved Videos → ⋯ → Disable workflow). Reverse both when GitHub is
back.

You can also press **Run pipeline** in GitLab at any time to publish one video
manually — that path ignores the variable and always works.
