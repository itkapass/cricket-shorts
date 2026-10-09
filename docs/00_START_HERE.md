# Start here

The complete first-time setup guide lives at the project root:
**[`START_HERE_AFTER_DOWNLOAD.md`](../START_HERE_AFTER_DOWNLOAD.md)**.

This `docs/` folder is the reference library — one file per topic, numbered
roughly in the order most people need them (`01` database, `02` API keys,
`03` local rendering, and so on through `18`). The root guide links to the
specific one you need at each step; come back here whenever you want more
detail than that guide gives, or to look something up later.

## Running commands

Always from the project folder (the one **containing** `engine`), and
always with `-m`:

```
python -m engine.publisher --setup
python -m engine.orchestrator
python -m engine.health_check
python tools/selfcheck.py
```

## Checking everything works

Repo → **Actions** → **Health Check** → **Run workflow**. It tells you
exactly what's configured and what isn't.
