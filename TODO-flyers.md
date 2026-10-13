# TODO — after the Dropbox → GitHub flyer migration

Written at the end of the 2026-10-13 session. Everything below is either
deferred, optional, or a known limitation. Nothing here is broken right now.

Updated the same day, once the Neocities account was confirmed as **Supporter**:
that removed the file-type whitelist, which changed what several sections below
used to say. Sections that are still true were deliberately left alone.

## Shipped and verified

- Flyer uploads go browser → Cloudflare Worker (`worker-flyers.js`) →
  `Sorete33/audiogusano-flyers` → `repository_dispatch` → `gusano` workflow →
  Neocities. A flyer reaches the live site in about a minute.
- `sync_github.py` replaced `sync_dropbox.py`; downloads use the git blob API
  because `urllib` refuses spaces and accents in URLs.
- `content/_index.md` points at the deployed worker.
- **`.mp4` uploads work end to end.** The account is Neocities Supporter, which
  removes the upload whitelist. But that alone was not enough: the deploy action
  filtered unsupported extensions out locally before contacting Neocities, and
  the `neocities_supporter` input that disables that filter first appears in
  **v3**. So `deploy.yml` moved `@v1` → `@v3` (which also renamed `api_token` to
  `api_key`) and passes `neocities_supporter: true`. No conversion: mp4 deploys
  as mp4 and `gallery.html` renders it as a `<video>`. Verified with a real clip
  that came back byte-identical (matching md5) from Neocities as `video/mp4`.
- `cleanup: true` with `protected_files: "skins/*.wsz"`.
- Deploys are green again (they had been failing on a 400 since 02:31 that day).
- Gallery video `kuelgue` is still an animated WebP from before the Supporter
  upgrade. That was deliberate at the time, and it is **not** a rule any more —
  see "Videos" below.

## To do

### Neocities — check the storage number — RESOLVED

The dashboard read **1.85 GB used of 1 GB** while the file browser showed about
**300 MB**. Deploys were failing with `400 too_large`.

It resolved itself on the next successful deploy once cleanup was enabled, so
the stale-counter theory had never held up. The open question at the time was
whether the account was actually on Supporter: the screenshot showed free-tier
numbers, and Supporter is **50 GB**, not 1 GB.

**Confirmed Supporter.** That closes this — no ticket needed. Worth one glance
at the dashboard to confirm the counter dropped, but nothing depends on it.

### Cloudflare Pages — disconnect it

A Pages project is connected to `Sorete33/gusano`, so every push triggers a
second, unrelated build (`npx wrangler deploy`). The site is built by GitHub
Actions and deployed to Neocities; Pages serves no purpose here and only
produces confusing logs.

Dashboard: Workers & Pages → the Pages project → disconnect the Git
integration. Not something wrangler can do cleanly from the CLI.

### Cloudflare Workers Builds — pin wrangler

If that Pages build is kept, it resolves `npx wrangler` unpinned (currently
4.150.0) with no lockfile, so the version can change under you. Add a root
`package.json` with wrangler as a devDependency and commit `package-lock.json`.

If Pages is disconnected, ignore this entirely — deploying the Worker directly
with `npx wrangler deploy` does not need it.

## Known limitations (working as designed)

### Winamp skins now deploy

This used to read "can never be updated", because `.wsz` was not in the deploy
action's supported-type list and editing a skin silently did nothing. **That is
no longer true.** `neocities_supporter: true` bypasses the filter, and the deploy
preview now lists all three skins in the upload set:

```
'skins/skin.wsz', 'skins/Old_Mac-OS.wsz', 'skins/Black_SlanXP2.wsz'
```

`protected_files: "skins/*.wsz"` is kept anyway — it costs nothing and stops
cleanup sweeping them if one ever falls out of `static/`.

### Videos

`.mp4` uploads as `.mp4`, with no conversion. `gallery.html` renders it as a
`<video autoplay loop muted playsinline>` with `data-type="video"` for the
lightbox. Capped at **10 MB**, which is a worker memory limit rather than a
policy one — see "Gotchas" below.

`kuelgue` is still an animated WebP, converted back when the account was on the
free tier. **It cannot be converted back:** the original `.mp4` was swept from
Neocities by cleanup during the migration, so there is no source left. Restoring
it would mean re-uploading the mp4 through the button.

### `scripts/check-neocities-types.py` no longer blocks media

It used to fail the build on anything outside the free-tier whitelist. It still
runs on every deploy, but `deploy.yml` passes `--supporter`, which downgrades
the failure to a report and exits 0. The guard only bites if the account ever
drops off Supporter — which is exactly when you would want it. Drop the flag
from the workflow if that happens and the build fails loudly again.

`FROZEN_OK` (the `.wsz` allowlist) is now moot, since skins deploy normally.

### Expect `git pull --rebase` before pushing

The workflow commits back to `master` after each deploy (flyer images plus
`data/flyers.yml`), so a flyer arriving while you have local work will reject
your push.

Stronger than that, and worth knowing: **it fails the workflow run too**, not
just your push. A run that loses this race exits 1 with `non-fast-forward` at
the end, and the commit-back never lands. The deploy itself already succeeded by
that point, so the files are live on Neocities but missing from the repo until
the next run. The next run re-syncs and commits them, so it self-heals — but
avoid pushing to `master` while an upload is in flight.

## Gotchas

Four things that cost real time, none of which were obvious.

### Deletions never auto-deploy

Only the *upload* path fires a `repository_dispatch`, and only from the worker.
The flyers repo has no workflows of its own, so deleting a file from it triggers
**nothing** — the file stays live on Neocities until a deploy runs anyway.

```
# delete flyers/<file> from Sorete33/audiogusano-flyers, then:
gh workflow run deploy.yml --repo Sorete33/gusano
```

Without that manual dispatch, you wait for the monthly cron on the 1st.

### `wrangler.toml` `name` must match the url in `_index.md`

They were briefly out of sync (`...-flyer-worker` in `wrangler.toml` vs
`...-flyers` in `content/_index.md`). The failure mode is nasty: **deploying to
a name that does not exist creates a brand new worker and reports success**
rather than erroring. So `wrangler deploy` looked green while the live worker
kept serving old code, and uploads failed with a stale error message.

If uploads behave oddly, ask which code is actually running:

```
curl -X POST -F "file=@x.txt" https://<the url in _index.md>
```

The `allowed` list in the response tells you which version is live.

### Videos are capped at 10 MB, and that is memory

`worker-flyers.js` allows 10 MB for video and 8 MB for images. The video ceiling
is not a policy choice — holding one upload costs roughly 5–7× its size at once
(the FormData copy, `arrayBuffer()`, the latin1 string, the base64 string, the
JSON body and the fetch buffer) inside a 128 MB Workers isolate. ~15 MB is where
it starts dying, so 10 MB leaves headroom. Raising it much further trades a
clean 413 for a `memory exceeded` error.

### The deploy action must stay on v3

`neocities_supporter` does not exist in v1 or v2 — I checked v1.1.21 and v2.0.4.
Without it the action filters `.mp4` out locally and the Supporter account
never helps. Downgrading the action silently reinstates the freeze.

## If you ever need to move off Neocities

Not required — the quota problem resolved itself, and the account is Supporter
anyway. But if you do:

- GitHub Pages has no file-type whitelist and 100 GB/month bandwidth.
- `baseURL` in `config/_default/hugo.toml` must change.
- `audiogusano.neocities.org` would go away; audio links and the
  `ALLOWED_ORIGIN` var in the Worker reference it.
- Orphaned files would accumulate the same way unless cleanup stays on.
- Audio is already served directly from archive.org and catbox, so
  `scripts/sync-archive.py` is unaffected by the whitelist question.

## Worker environment

Set in the Cloudflare dashboard, not in `wrangler.toml`:

| Name | Type | Value |
|---|---|---|
| `GITHUB_PAT` | Secret | token with `contents:write` on audiogusano-flyers **and** dispatch rights on gusano |
| `FLYERS_REPO` | Var | `Sorete33/audiogusano-flyers` |
| `GUSANO_REPO` | Var | `Sorete33/gusano` |
| `ALLOWED_ORIGIN` | Var | `https://audiogusano.neocities.org` |

Also in `wrangler.toml` now: `FLYERS_PATH`, `FLYERS_BRANCH`, `GUSANO_BRANCH`.

**A failed dispatch is silent.** The Worker commits the flyer first and only
then tries to dispatch, inside `ctx.waitUntil()`. If the token lacks
`Workflows: Read and write` on gusano, the upload still returns
`{"success":true}` but no deploy runs. When testing an upload, always check
**both** the flyers repo commit *and* the Actions tab on gusano.

## Monthly cron

`deploy.yml` runs `17 4 1 * *` as a safety net for dropped dispatches. Uploads
normally reach the site in about a minute via `repository_dispatch`, so the
cron is not load-bearing. Change it to `0 */3 * * *` if you would rather have
the old behaviour back.

Note this is now the *only* thing that will act on a **deletion** — see
"Deletions never auto-deploy" under Gotchas.

## Repos

- `Sorete33/gusano` — the site (Hugo). Deploys to Neocities.
- `Sorete33/audiogusano-flyers` — drop zone. Public, `main`, `flyers/` folder.
  Images and `.mp4`; anything else is skipped with a warning at sync time.