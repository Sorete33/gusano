/**
 * Cloudflare Worker that receives anonymous flyer uploads from the site and
 * commits them into the Sorete33/audiogusano-flyers repo, then kicks off the
 * deploy in Sorete33/gusano.
 *
 * Setup (Cloudflare dashboard -> Workers & Pages -> this worker -> Settings ->
 * Variables and Secrets):
 *   GITHUB_PAT      secret, PAT with `contents: write` on audiogusano-flyers and
 *                   `repository`/`contents: write` on gusano (needed for dispatch)
 *   FLYERS_REPO     var, "Sorete33/audiogusano-flyers"
 *   FLYERS_PATH     var, "flyers"            (optional)
 *   FLYERS_BRANCH   var, "main"              (optional)
 *   GUSANO_REPO     var, "Sorete33/gusano"   (optional)
 *   GUSANO_BRANCH   var, "master"            (optional)
 *   ALLOWED_ORIGIN  var, "https://audiogusano.neocities.org"  (optional)
 *
 * Then point the `flyer-upload` shortcode at this worker's URL:
 *   {{< flyer-upload url="https://<worker>.<subdomain>.workers.dev" >}}
 */

// Same list as sync_github.py / scripts/check-neocities-types.py. Neocities free
// tier refuses these on upload, and the deploy action silently filters them out
// before it ever contacts Neocities, so reject them here where it is visible.
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.svg'];

// Anything bigger is a mistake, and the Workers isolate would rather not know.
const MAX_BYTES = 8 * 1024 * 1024;

// Dispatch event type the deploy workflow listens for.
const DISPATCH_EVENT = 'flyer-uploaded';

function corsHeaders(env) {
  return {
    'Access-Control-Allow-Origin': env.ALLOWED_ORIGIN || 'https://audiogusano.neocities.org',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}

function json(body, status, env) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders(env) },
  });
}

/**
 * Mirrors slugify() in sync_github.py, so a name that was already uploaded keeps
 * resolving to the same file instead of landing twice under two spellings.
 * Python does NFKD -> drop non-ascii -> strip [^\w\s-] -> lowercase -> collapse
 * [- ]+ to '-'; the Unicode-mark strip is what handles the accented characters.
 */
function slugify(filename) {
  const dot = filename.lastIndexOf('.');
  const name = dot > 0 ? filename.slice(0, dot) : filename;
  const ext = dot > 0 ? filename.slice(dot).toLowerCase() : '';

  const cleaned = name
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')  // combining marks left by NFKD
    .replace(/[^\x00-\x7F]/g, '')      // drop what Python's ascii-ignore would
    .replace(/[^\w\s-]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, '-');

  // A name made entirely of accents/punctuation slugifies to nothing; fall back
  // to something stable rather than writing to a path called ".jpg".
  return (cleaned || 'flyer') + ext;
}

async function githubApi(env, url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${env.GITHUB_PAT}`,
      'User-Agent': 'Cloudflare-Worker-FlyerUpload',
      'Accept': 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = { message: text };
  }
  return { ok: response.ok, status: response.status, body };
}

/**
 * Commit one file to the flyers repo. GitHub's contents API needs the blob's
 * current `sha` to overwrite it, so a re-upload of the same slug has to fetch
 * it first rather than 422.
 */
async function commitFile(env, filePath, base64Content, commitMessage) {
  const contentsUrl = `https://api.github.com/repos/${env.FLYERS_REPO}/contents/${filePath}`;

  let existingSha = null;
  const existing = await githubApi(env, `${contentsUrl}?ref=${env.FLYERS_BRANCH}`, { method: 'GET' });
  if (existing.ok && existing.body && existing.body.sha) {
    existingSha = existing.body.sha;
  } else if (existing.status !== 404) {
    return { ok: false, error: `Could not check ${filePath}: HTTP ${existing.status}` };
  }

  const result = await githubApi(env, contentsUrl, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: commitMessage,
      content: base64Content,
      branch: env.FLYERS_BRANCH,
      ...(existingSha ? { sha: existingSha } : {}),
    }),
  });

  if (!result.ok) {
    return { ok: false, error: result.body?.message || `HTTP ${result.status}` };
  }
  return { ok: true, replaced: Boolean(existingSha), sha: result.body?.content?.sha };
}

/** Nudge the main site repo to run its sync + deploy workflow. */
async function triggerDeploy(env) {
  const response = await fetch(
    `https://api.github.com/repos/${env.GUSANO_REPO}/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_PAT}`,
        'User-Agent': 'Cloudflare-Worker-FlyerUpload',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_type: DISPATCH_EVENT }),
    }
  );
  if (!response.ok) {
    const text = await response.text();
    console.error('dispatch failed', response.status, text);
    return false;
  }
  return true;
}

export default {
  async fetch(request, env, ctx) {
    const cors = corsHeaders(env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: cors });
    }

    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405, env);
    }

    if (!env.GITHUB_PAT || !env.FLYERS_REPO) {
      return json({ error: 'Worker backend configuration error.' }, 500, env);
    }

    env.FLYERS_PATH = env.FLYERS_PATH || 'flyers';
    env.FLYERS_BRANCH = env.FLYERS_BRANCH || 'main';
    env.GUSANO_REPO = env.GUSANO_REPO || 'Sorete33/gusano';
    env.GUSANO_BRANCH = env.GUSANO_BRANCH || 'master';

    let file;
    try {
      const form = await request.formData();
      file = form.get('file');
    } catch (e) {
      console.error('formData failed', e);
      return json({ error: 'Expected a multipart upload.' }, 400, env);
    }

    if (!file || typeof file === 'string') {
      return json({ error: 'No file field in the upload.' }, 400, env);
    }

    const originalName = file.name || 'flyer';
    const ext = '.' + (originalName.split('.').pop() || '').toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return json({
        error: `Subí una imagen. "${ext || '?'}" no se puede publicar en Neocities.`,
        allowed: ALLOWED_EXTENSIONS,
      }, 415, env);
    }

    if (file.size > MAX_BYTES) {
      return json({ error: 'El archivo es demasiado grande (máx 8 MB).' }, 413, env);
    }

    const slug = slugify(originalName);
    const filePath = `${env.FLYERS_PATH}/${slug}`;

    // base64 in one shot: arrayBuffer() avoids the per-chunk concat that blows
    // up past a few MB.
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = '';
    const CHUNK = 0x8000;
    for (let i = 0; i < bytes.length; i += CHUNK) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
    }
    const base64Content = btoa(binary);

    const commit = await commitFile(env, filePath, base64Content, `Flyer: ${slug}`);
    if (!commit.ok) {
      console.error('commit failed', commit.error);
      return json({ error: 'No se pudo guardar el flyer.' }, 502, env);
    }

    // Fire and forget: the flyer is safely committed even if the dispatch drops.
    // ctx.waitUntil keeps the worker alive long enough to finish the request.
    ctx.waitUntil(triggerDeploy(env));

    return json({
      success: true,
      path: filePath,
      replaced: commit.replaced,
      name: originalName.replace(/\.[^.]+$/, ''),
    }, 200, env);
  }
};