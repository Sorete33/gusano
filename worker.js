/**
 * Cloudflare Worker for handling anonymous comments + live reactions (KV).
 *
 * Deploy: wrangler deploy --config wrangler.comments.toml
 * Bindings: KV namespace named REACTIONS; secret GITHUB_PAT.
 *
 * DOCUMENTACION DE SEGURIDAD / PAT:
 *   El PAT de GitHub (GITHUB_PAT) debe ser FINE-GRAINED, con permisos unicamente:
 *     - contents: write
 *   sobre el repositorio Sorete33/audiogusano (branch master). No otorgar
 *   permisos adicionales (issues, pull requests, workflows, etc.) ni scopes
 *   clasicos. Rotar si se sospecha compromiso.
 *
 * CORS: solo se permiten los origenes listados en ALLOWED_ORIGINS.
 * Comentarios: el Worker guarda name/message/replyTo crudos y truncados;
 * la unica capa de escape es Hugo en build-time (sin safeHTML).
 */
const ALLOWED_ORIGINS = [
  'https://audiogusano.neocities.org',
  'http://localhost:1313',
];

const ALLOWED_EMOJIS = [
  '👍', '❤️', '😂', '😮', '😢', '🔥',
  '🎧', '🎵', '🎶', '🎸', '🥁', '🎹', '🎤', '🎺', '🎷', '🎉', '👏',
];

function corsHeadersFor(origin) {
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    return {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Max-Age': '86400',
      'Vary': 'Origin',
    };
  }
  return null;
}

function json(data, status, extraHeaders) {
  const headers = { 'Content-Type': 'application/json', ...(extraHeaders || {}) };
  return new Response(JSON.stringify(data), { status: status, headers: headers });
}

function validPermalink(p) {
  return typeof p === 'string' && p.length >= 1 && p.length <= 2048 && !/[\n\r]/.test(p);
}

function validCommentId(id) {
  return typeof id === 'string' && /^[a-zA-Z0-9_-]{1,128}$/.test(id);
}

async function md5(message) {
  const msgUint8 = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('MD5', msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function checkRateLimit(env, ip) {
  // KV no soporta CAS; contador aproximado, aceptable en sitio chico.
  if (!env.REACTIONS) return true;
  const key = `ratelimit:${ip}`;
  const now = Date.now();
  let data = null;
  try {
    const raw = await env.REACTIONS.get(key);
    data = raw ? JSON.parse(raw) : null;
  } catch (e) {
    data = null;
  }
  if (!data || typeof data.start !== 'number' || now - data.start > 60000) {
    data = { start: now, count: 0 };
  }
  if (data.count >= 5) {
    return false;
  }
  data.count += 1;
  try {
    await env.REACTIONS.put(key, JSON.stringify(data), { expirationTtl: 120 });
  } catch (e) {
    // no bloquear si KV falla
  }
  return true;
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get('Origin');
    const cors = corsHeadersFor(origin);

    // Rechazar origenes no permitidos (sin cabeceras CORS).
    if (origin && !cors) {
      return new Response(JSON.stringify({ error: 'Origin not allowed' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      if (!cors) {
        return new Response(null, { status: 403 });
      }
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);

    // Live reactions: GET counts for a permalink
    if (request.method === 'GET' && url.pathname === '/reactions') {
      const permalink = url.searchParams.get('permalink');
      if (!permalink || !validPermalink(permalink)) {
        return json({ error: 'permalink is required' }, 400, cors);
      }
      if (!env.REACTIONS) {
        return json({ error: 'KV not bound' }, 500, cors);
      }
      const key = `reactions:${await md5(permalink)}`;
      const raw = await env.REACTIONS.get(key);
      const data = raw ? JSON.parse(raw) : {};
      const res = json(data, 200, cors);
      // Cache-Control: no-store
      res.headers.set('Cache-Control', 'no-store');
      return res;
    }

    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405, cors);
    }

    // Rate limiting por IP
    const ip = request.headers.get('CF-Connecting-IP')
      || (request.headers.get('X-Forwarded-For') || '').split(',')[0].trim()
      || 'unknown';
    const allowed = await checkRateLimit(env, ip);
    if (!allowed) {
      return json({ error: 'Too many requests' }, 429, cors);
    }

    // Limite de body
    const cl = request.headers.get('Content-Length');
    if (cl && parseInt(cl, 10) > 16384) {
      return json({ error: 'Payload too large' }, 413, cors);
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json({ error: 'Invalid JSON' }, 400, cors);
    }

    // Live reaction: increment a counter in KV (no rebuild needed)
    if (body && body.action === 'react') {
      const { permalink, commentId, emoji } = body;
      if (!validPermalink(permalink) || !validCommentId(commentId) || !emoji) {
        return json({ error: 'permalink, commentId and emoji are required' }, 400, cors);
      }
      if (!ALLOWED_EMOJIS.includes(emoji)) {
        return json({ error: 'emoji not allowed' }, 400, cors);
      }
      if (!env.REACTIONS) {
        return json({ error: 'KV not bound' }, 500, cors);
      }

      const key = `reactions:${await md5(permalink)}`;
      // KV no soporta CAS; race conditions posibles, aceptable en sitio chico.
      const raw = await env.REACTIONS.get(key);
      const data = raw ? JSON.parse(raw) : {};
      if (!data[commentId]) data[commentId] = {};
      data[commentId][emoji] = (data[commentId][emoji] || 0) + 1;
      await env.REACTIONS.put(key, JSON.stringify(data));
      return json({ success: true, count: data[commentId][emoji] }, 200, cors);
    }

    // --- Create a new comment ---
    const { name, message, permalink, replyTo } = body || {};

    if (!message || !validPermalink(permalink)) {
      return json({ error: 'Message and permalink are required.' }, 400, cors);
    }

    const cleanName = String(name || 'Anónimo').slice(0, 50);
    const cleanMessage = String(message).slice(0, 1000);
    let cleanReplyTo = '';
    if (replyTo) {
      const r = String(replyTo);
      if (/^[a-zA-Z0-9_-]{1,64}$/.test(r)) {
        cleanReplyTo = r;
      }
    }

    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const branch = env.GITHUB_BRANCH || 'master';
    const pat = env.GITHUB_PAT;

    if (!owner || !repo || !pat) {
      return json({ error: 'Worker backend configuration error.' }, 500, cors);
    }

    const timestamp = Date.now();
    const dateString = new Date().toISOString();
    const commentData = {
      name: cleanName,
      message: cleanMessage,
      date: dateString,
    };
    if (cleanReplyTo) {
      commentData.replyTo = cleanReplyTo;
    }

    const fileContent = JSON.stringify(commentData, null, 2);
    const encodedContent = btoa(unescape(encodeURIComponent(fileContent)));

    const permalinkHash = await md5(permalink);
    const filePath = `data/comments/${permalinkHash}/comment-${timestamp}.json`;

    const githubUrl = `https://api.github.com/repos/${owner}/${repo}/contents/${filePath}`;

    const safePermalink = String(permalink).replace(/[\n\r]/g, ' ');
    const safeName = String(cleanName).replace(/[\n\r]/g, ' ');
    const commitMessage = `Add comment by ${safeName} on ${safePermalink}`;

    const response = await fetch(githubUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${pat}`,
        'User-Agent': 'Cloudflare-Worker-Comments',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
      },
      body: JSON.stringify({
        message: commitMessage,
        content: encodedContent,
        branch: branch
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error('GitHub API error:', errText);
      return json({ error: 'Failed to save comment to repository.' }, 502, cors);
    }

    return json({ success: true }, 200, cors);
  }
};
