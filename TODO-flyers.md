# TODO — after the Dropbox → GitHub flyer migration

Written at the end of the 2026-10-13 session. Everything below is either
deferred, optional, or a known limitation. Nothing here is broken right now.

Updated the same day, once the Neocities account was confirmed as **Supporter**:
that removed the file-type whitelist, which changed what several sections below
used to say. Sections that are still true were deliberately left alone.

Updated again on 2026-10-16, when `/flyers/` was rebuilt — see "The /flyers/
archive" below.

## The /flyers/ archive

`/flyers/` used to be `{{< gallery "flyers-viejos" >}}` — the same
Swiper coverflow shortcode the homepage uses, pointed at a hand-kept
`data/flyers-viejos.yml`. That is gone. It was replaced by
`layouts/flyers/single.html`, which is a **horizontal full-screen deck**: one
cover at a time, swipe/scroll sideways to the next, nothing cropped. Prev/next
buttons, the mouse wheel, the arrow keys and touch swipe all page it.

**What it reads.** The recital pages themselves, plus `static/covers/`.
`data/flyers-viejos.yml` was deleted because 44 of its 47 entries turned out to
be byte-identical copies of images that already existed as page resources under
`content/recitales/**/featured.*` (checked with a perceptual hash, distance 0.0
on all 44). The archive was also incomplete: 47 listed against 77 real shows.
All 77 pages carry `title`, `date`, `espacios` and `bandas`, so they were
always a complete source of truth.

**How to add a flyer now.** Create `content/recitales/<venue>/<show>/index.md`
with a `featured.*` image. Nothing else. No data file, no script, no CI step.
For a flyer with no article, drop the file in `static/covers/` — the layout
lists that directory, so it appears on the next build.

**It is deliberately separate** from `layouts/shortcodes/gallery.html` and
`data/flyers.yml`. Those drive the homepage "Próximos eventos" carousel, are
written by `sync_github.py` from the upload drop zone, and were not touched.

### Why the lightbox is gone

### There are no popups at all now

The deck dropped GLightbox entirely (the homepage keeps its own, via
`gallery.html`). It was the sole cause of both popup bugs:

- **Tapping the cover opened the lightbox instead of paging.** The cover *was*
  an `<a>`, and the arrows were only a 40px fallback pinned 4px from the screen
  edge. Stacking was never at fault — `z-index:3` painted above the link.
- **Opening one cover then another showed the first one again.** GLightbox was
  initialised once over all 81, but the index passed to it was a position in
  the *filtered* set. Unfiltered the indices roughly lined up; the moment a
  filter was applied every index pointed at the wrong cover. GLightbox cannot
  express "these 3, in this order", so this was not patchable — it was dropped.

A plain fullscreen overlay replaced it briefly, and that was dropped too: the
deck already shows the flyer uncropped and as large as the viewport allows, so a
second full-screen view of the same image added a control without adding
anything. The cover is displayed inline at full size instead. **Nothing on this
page opens a modal any more**, which is also why `nozoom` (below) matters.

### Navigation

`scroll-snap-type: x proximity`, and **no pointer or touch handlers anywhere in
the file**. Touch momentum and trackpad work as the browser intends, which is
what stopped swipe and tap fighting over the same pixel. Two additions sit on
top of that, neither of which is a gesture handler and so neither can collide
with a tap:

- **Prev/next buttons.** The wheel and swipe are good but not obvious to
  everyone, and a mouse user has no reason to discover either. They live in
  `.fa-stage`, *outside* the scroller — an absolutely positioned child of a
  scroll container scrolls away with the content, so inside `.fa-deck` they
  would not hold still. They stop at the ends and disable, rather than wrapping,
  so the deck visibly runs out instead of silently jumping back to slide 1.
- **The wheel**, which pages one slide per gesture. See below.
- **`←`/`→`**, bound to the document: browsers only scroll a horizontal
  container with the inline arrows and only when it holds focus.

`proximity`, not `mandatory`: mandatory fights the user, traps them mid-deck and
breaks on short viewports.

### Slide geometry

Slides are `flex: 0 0 100%` with no gap, snapping `center`. The period between
them is exactly one `clientWidth`, so slide *k* is snapped at `k * stride` and
the counter is a plain division.

There was a version with a sliver of the neighbouring covers visible either
side, and it was removed — at full-width slides the sliver falls in the empty
margin beside a portrait flyer, so it mostly showed the *next slide's caption*
text rather than its artwork. Worth knowing the arithmetic if it is ever
revisited, because two different approaches were measured:

- Narrowing the slides (`calc(100% - 2 * peek)`) does work: the period becomes
  shorter than the deck, so the neighbours genuinely intrude. Measured 48px per
  side on a 1376px deck, 24px on a 470px one.
- Adding `margin-inline` to full-width slides does **not**: the period then
  equals the deck width, the neighbours end up exactly one deck-width away, and
  what looks like a peek is just empty gutter — measured at zero visible
  sliver. That was the first attempt.

The consequence for the counter: with slides narrowed, slide *k* is centred at
`scrollLeft = k * stride - peek`, so the index is a division. Note the **minus**
— it was a plus in the first draft, which put every counter a whole slide out.

Four things worth remembering:

- **`measureDeck()` reads a rendered slide's width, never the CSS.** The peek
  width came from an unregistered custom property, and those come back out of
  `getComputedStyle` as their unresolved token stream — `parseFloat` on
  `clamp(1.5rem, 4vw, 3rem)` is `NaN`, which silently collapsed `stride` to the
  full deck width. A measured slide width is exact whatever the CSS expresses,
  and with the peek gone it simply resolves to `clientWidth`.
- **Wheel has to page, not scroll.** `scrollLeft += deltaY` looks right but
  `scroll-snap` then drags the result back to the nearest snap point, which for
  a small delta is the slide you were already on — the wheel appears dead.
  Accumulating past a 60px threshold and stepping by exactly one stride always
  lands on a snap point. `preventDefault` runs unconditionally there, which also
  stops the browser's own wheel translation double-scrolling on top of it.
  Horizontal wheel is left alone and handled natively.
- **`overflow-anchor: none` on the deck is load-bearing.** Shuffling reorders
  all 81 children at load and the browser's scroll anchoring compensates by
  leaving the deck parked on a random slide (observed at offset 9305 and 18610
  on different runs). `deck.scrollLeft = 0` is the belt to that braces.
- **The counter is driven by `scrollLeft`, not an IntersectionObserver.**
  Observers and `requestAnimationFrame` both only deliver when the browser
  produces a frame, which after a programmatic scroll with the page idle can be
  arbitrarily late — the counter then sits on the wrong slide. Images still load
  via observers; loading tolerates late delivery in a way a visibly-wrong
  counter does not.

### `nozoom` is load-bearing too

Blowfish's `footer.html` runs `mediumZoom()` over `img:not(.nozoom)` on every
page. Without `nozoom` on the deck images, a plain tap on a cover opens the
theme's zoom overlay — a third popup, after the two this rebuild removed. Every
deck image carries the class.

The deck also carries its own muted background. Slides are far wider than a
portrait flyer, so without it the fixed hero collage shows straight through the
empty margins and competes with the artwork.

### The download button

Per cover, next to "Escuchar el recital": a download glyph plus the word
"Descargar". `download` works here because Neocities is same-origin — on a
cross-origin URL the attribute is silently ignored and the image would just
open. Filenames come from `urlize` of the show title plus the real extension,
e.g. `entrance-cinica-y-base-en-sala-biaus.webp`.

### Order is random, and that is deliberate

Every page load reshuffles, so a refresh shows a different run of flyers.

The shuffle is **client-side, not Hugo's `shuffle`**. That distinction is the
whole point. `shuffle` randomises at *build* time, so it only changes the order
when the site is rebuilt — refreshing would show the same sequence. The old
gallery used it, paired with a per-deploy `?v={{ now.Unix }}` cache-buster, so
every band upload reshuffled the gallery *and* invalidated all 32 MB of images.
Doing it in JS costs nothing and has no such coupling.

The JSON still arrives in `ByDate.Reverse` order and every slide carries its
date, so going back to chronological is a matter of deleting one `shuffle()`
call. There is no sort control today.

The shuffle reorders the existing DOM nodes rather than re-rendering, so nothing
is emitted twice and the slides stay server-rendered.

### Artist names are matched loosely on purpose

`bandas` in the front matter is not normalised. It contains `Nicolas Benaghi`
and `Nicolás Benaghi` as two different entries, plus `Yula`/`YULA`,
`Cínica`/`Cinica`, `DRAMA`/`Drama`, `Maquinaria Divina`/`Maquinaria divina`,
and a probable typo, `Sabojate`/`Sabotaje`. Matching therefore happens in JS
with a case- and accent-insensitive `norm()`, so those collapse into one
artist — searching `benaghi` returns all 11 shows rather than 10.

`anchorize` is used in the template for exactly one thing: deciding which
spelling wins the dedupe in the `<datalist>`. It never decides what counts as
the same artist, so the two normalisers cannot disagree.

The artist field is a search input rather than a `<select>` on purpose: of 102
distinct artists, **74 appear in exactly one show**, so a dropdown would be
mostly dead options. It filters on `change`/Enter, not on every keystroke, so a
half-typed name never blanks the gallery.

### `static/covers/` is now only the no-article flyers

55 of its 59 files were deleted, along with the 31.6 MB they took up. The four
that remain — `flaco.jpeg`, `bad.webp`, `la peste.webp`, `memoria.jpg` — are
Chivilcoy dates with no recital page. They render through the same slide markup
but skip the blur-up, since static files cannot go through Hugo Pipes.

Note that **`static/covers/` is no longer where old flyers live.** If you go
looking for a past show's artwork there and it is not one of those four, it is
not missing: it is `content/recitales/<venue>/<show>/featured.*`, which is also
what `data/shows.yml` points its `cover:` fields at.

### Four rendering bugs the old gallery had

Worth knowing, because they are easy to reintroduce:

- **Hard crop.** `.flyer-card` was a fixed `300×420` box with
  `object-fit: cover`. Flyer ratios run from 0.56 to 3.00, and `tigran.jpg` is a
  1024×341 landscape banner — it lost ~76% of its width. The deck uses
  `contain` and never crops.
- **~32 MB per page load**, because the grid served the originals. The deck
  shows the **untouched original**, which is already deployed for every recital
  page, so it adds nothing to the build or to the Neocities upload. Generating
  a "deck-sized" variant would mean creating ~15 MB of files that duplicate
  what is already there. A 480px WebP thumbnail sits underneath as an instant
  blur-up placeholder (median 41 KB), and an observer warmed 120% ahead pulls
  the next original in early.
- **`?v={{ now.Unix }}` on every image.** A cache-buster keyed to build time,
  so every deploy invalidated all 32 MB for every visitor — and uploads deploy
  about a minute apart. The deck has no cache-buster.
- **`loading="lazy"` inside a Swiper wrapper.** Swiper translates its track with
  CSS transforms, so off-screen lazy images never approach the viewport and
  never load — which is what "some covers are not showing" actually was. Lazy
  loading is safe again in the deck because the slides are in ordinary scroll
  flow.

### Three layout traps hit while building it, all easy to repeat

- A percentage `height` on a grid item inside `place-items: center` resolves
  against a **content-sized row**, not the container. The row grew to the
  image's intrinsic 1080×1440 and the cover overflowed instead of scaling. The
  slide media and its images are `position: absolute` with `margin: auto` now.
- Once the caption goes `flex-direction: column` on mobile, `flex: 1 1 22rem`
  becomes a *height* basis and the text block claims 352px.
- **`break` inside a `forEach` callback is a `SyntaxError`.** `break` is legal
  only inside a real iteration statement or `switch`; a `forEach` *call* is a
  function call. One of these silently killed the whole script — nothing on the
  page worked, and it only surfaced by running `node --check` over the emitted
  inline script. Worth doing on any page with a hand-written inline script.

`content/flyers/index.md` sets `layoutBackgroundHeaderSpace: false`. The theme
normally reserves 200px so content clears the fixed hero backdrop; the deck
wants that height. The header's own height is measured in JS and written to
`--fa-chrome`, because the theme header changes height with the logo and
between its mobile and desktop menus, and is built out of divs with no
`<header>` element to query.

### The /flyers/ hero is a WebP now

`content/flyers/featured.png` (2.8 MB) became `featured.webp` (147 KB). The
original was not just large, it was *counterproductive*: it is only 896×630,
and blowfish's `hero/background.html` does `.Resize "1200x"`, which **upscales**
it into a 5.4 MB `featured_hu_*.png`. One blurred backdrop was costing 8.1 MB.
It is now 0.35 MB. `heroStyle: background` and the front matter are unchanged —
the hero partial finds it on its own via `GetMatch "*feature*"`.

## Shipped and verified

- **`/flyers/` is a standalone full-bleed archive grid** — see above.
- **`scripts/check-links.py` was silently not checking `data/flyers.yml`.**
  Its regex was `^\s*link\s*:`, which cannot match how `sync_github.py` writes
  that file (`- link: /path`, key inline after the list dash). It only ever
  worked on `flyers-viejos.yml`, where `link:` sat on its own indented line.
  Fixed to `^\s*-?\s*link\s*:`. It also now derives the archive links from the
  recital `featured.*` resources and reports any recital page that has none,
  since those render no tile.
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