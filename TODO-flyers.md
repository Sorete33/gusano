# TODO — after the Dropbox → GitHub flyer migration

Written at the end of the 2026-10-13 session. Everything below is either
deferred, optional, or a known limitation. Nothing here is broken right now.

## Shipped and verified

- Flyer uploads go browser → Cloudflare Worker (`worker-flyers.js`) →
  `Sorete33/audiogusano-flyers` → `repository_dispatch` → `gusano` workflow →
  Neocities. A flyer reaches the live site in about a minute.
- `sync_github.py` replaced `sync_dropbox.py`; downloads use the git blob API
  because `urllib` refuses spaces and accents in URLs.
- `content/_index.md` points at the deployed worker.
- Gallery video `kuelgue` converted to animated WebP; the orphaned `.mp4` was
  swept from Neocities by cleanup.
- `cleanup: true` with `protected_files: "skins/*.wsz"`.
- Deploys are green again (they had been failing on a 400 since 02:31 that day).

## To do

### Neocities — check the storage number

The dashboard read **1.85 GB used of 1 GB** while the file browser showed about
**300 MB**. Deploys were failing with `400 too_large`.

It resolved itself on the next successful deploy once cleanup was enabled, so
the stale-counter theory I had never held up. But **look at the dashboard now**
and confirm it dropped. If it still reads ~1.85 GB, the counter really is stale
and this is worth a ticket to Neocities:

> My site's file browser shows ~300 MB but the dashboard reports 1.85 GB, and
> deploys fail with `400 too_large`. Can you reconcile `space_used` against
> `actual_space_used`?

Also: Supporter is **50 GB**, not 1 GB. The screenshot showed free-tier numbers,
so it is worth confirming at <https://neocities.org/supporter> whether the
account is actually on Supporter.

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

### Winamp skins can never be updated

`static/skins/*.wsz` is not in the deploy action's supported-type list, so the
three skins are **frozen** at whatever version is live. They serve fine and
`protected_files` stops cleanup deleting them, but editing one will never
deploy.

If you need to change a skin, upload it by hand from the Neocities dashboard.

### Gallery videos must stay WebP

`.mp4` is not on Neocities' free-tier whitelist. The WebP conversion was
deliberate so the gallery survives a downgrade to free tier — the WebP works on
every tier, the mp4 silently stops deploying and freezes.

The trade: 480px output is softer in the lightbox than the original mp4 was.
Regenerate at a higher width with `scripts/convert-flyer-videos.sh` if you
decide the sharpness matters more.

### `scripts/check-neocities-types.py` blocks media

It fails the build on anything outside the free-tier whitelist. That is the
point — it is the guard that would have caught the frozen videos earlier. But
it means **adding a `.mp4`, `.mp3`, `.mov` or `.webm` to `static/` will fail the
deploy** until the file is converted or removed. `FROZEN_OK` at the top of that
script is the allowlist for pre-existing files that are live but undeletable.

### Expect `git pull --rebase` before pushing

The workflow commits back to `master` after each deploy (flyer images plus
`data/flyers.yml`), so a flyer arriving while you have local work will reject
your push. Rebase and push again — it is normal, not a problem.

## If you ever need to move off Neocities

Not required — the quota problem resolved itself. But if you do:

- GitHub Pages has no file-type whitelist and 100 GB/month bandwidth.
- `baseURL` in `config/_default/hugo.toml` must change.
- `audiogusano.neocities.org` would go away; audio links and the
  `ALLOWED_ORIGIN` var in the Worker reference it.
- Orphaned files would accumulate the same way unless cleanup stays on.
- `.mp3` would finally be uploadable, so `scripts/sync-archive.py` could serve
  audio directly instead of relying on archive.org and catbox.

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

## Repos

- `Sorete33/gusano` — the site (Hugo). Deploys to Neocities.
- `Sorete33/audiogusano-flyers` — drop zone. Public, `main`, `flyers/` folder.
  Images only; anything else is skipped with a warning at sync time.