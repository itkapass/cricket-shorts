# Tool 1: Supabase Setup Guide (Database & Storage)

Follow these steps to set up your free Supabase database in under 3 minutes (100% Free, no credit card required).

---

### Step 1: Create your Free Account
1. Go to [https://supabase.com](https://supabase.com) and click **Start your project** (Sign up with GitHub or Email).
2. Click **New Project**:
   * **Name:** `shorts-studio` (or any name you like)
   * **Database Password:** Enter a secure password (save it somewhere).
   * **Region:** Pick the region closest to you.
   * **Pricing Plan:** Free Plan.
3. Click **Create new project** and wait ~1 minute for it to finish initializing.

---

### Step 2: Run the Database Schema, THEN every migration in order
This is the one step beginners most often half-do, so read this carefully:
`supabase/schema.sql` creates the base tables, but this app needs six more
files on top of it — each one adds something specific (channels, scheduling,
real captions, push alerts, and the cricket/sports content system itself).
Skipping any of them leaves the app half-wired with a confusing error later.

1. In your Supabase project dashboard, click **SQL Editor** in the left sidebar (icon looks like `>_`).
2. Click **New query** (or `+`).
3. Open `supabase/schema.sql` in this project folder, copy everything in it,
   paste into the SQL Editor, click the green **Run** button. Expect
   `Success. No rows returned.`
4. Click **New query** again and repeat step 3 for EACH of these files, in
   this exact order (each one depends on the one before it):
   1. `supabase/migrations/002_channels_and_concepts.sql`
   2. `supabase/migrations/003_scheduling_and_manual_controls.sql`
   3. `supabase/migrations/004_real_captions_and_visual_source.sql`
   4. `supabase/migrations/005_push_subscriptions.sql`
   5. `supabase/migrations/006_channel_customization.sql`
   6. `supabase/migrations/007_cricket_sports_content_mix.sql`
5. That's 7 runs total. Every one of them is safe to run twice by accident
   (they all check "does this already exist?" first), so if you lose track
   of which ones you've done, just run all 7 again in order — nothing breaks.

> Once your app is live, **docs/14** explains how to let GitHub Actions run
> any new migration for you automatically, so this manual copy-paste is a
> one-time thing you only do for this initial setup.

---

### Step 3: Create the Video Storage Bucket
1. In your Supabase left sidebar, click **Storage** (bucket icon).
2. Click **New bucket**.
3. Set **Bucket name** to: `shorts-videos`
4. Toggle **Public bucket** to **ON** (Enabled).
5. Click **Save bucket**.

---

### Step 4: Copy Your API Keys
1. In your Supabase dashboard, click the **Project Settings** (gear icon at the bottom left).
2. Click **API** under Configuration.
3. Copy the following 3 values:
   * **Project URL** (e.g. `https://xyzabcdefgh.supabase.co`)
   * **anon (public)** key
   * **service_role (secret)** key

---

### Step 5: Save Keys in your Project Files
* Open `admin-panel/.env` and paste:
  ```env
  VITE_SUPABASE_URL=https://your-project-url.supabase.co
  VITE_SUPABASE_ANON_KEY=your-anon-public-key
  ```
* Open `.env` (in project root) and paste:
  ```env
  SUPABASE_URL=https://your-project-url.supabase.co
  SUPABASE_ANON_KEY=your-anon-public-key
  SUPABASE_SERVICE_KEY=your-service-role-secret-key
  ```

**Never share either `.env` file** — not zipped, not screenshotted, not pasted
anywhere, including into an AI chat. `service_role` in particular bypasses every
permission check in your database. If one ever does get exposed, rotate it
(Project Settings → API → regenerate) rather than just deleting the file.

---

### Step 6: Create your Admin Panel login
`supabase/schema.sql` locks every table down to `auth.role() = 'authenticated'` —
before, the policies were named like they were restricted but actually granted full
read/write to anyone holding the public anon key (which your deployed site exposes by
design). Now you need a real account to log in:
1. Left sidebar → **Authentication** → **Users** → **Add user**.
2. Set an email + password — this is the one account you'll use to log into the
   Admin Panel. This project is built for a single owner, not multiple accounts.
3. That's it — no separate config. The Admin Panel's `/login` page uses this directly.
