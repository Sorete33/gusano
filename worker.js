/**
 * Cloudflare Worker for handling anonymous comments + live reactions (KV).
 * Place this code in a Cloudflare Worker, configure the environment variables,
 * bind a KV namespace named REACTIONS, and add your GitHub PAT as a secret
 * named GITHUB_PAT.
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*', // Replace with your domain for security
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

const ALLOWED_EMOJIS = [
  '👍', '❤️', '😂', '😮', '😢', '🔥',
  '🎧', '🎵', '🎶', '🎸', '🥁', '🎹', '🎤', '🎺', '🎷', '🎉', '👏',
];

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    // Live reactions: GET counts for a permalink
    if (request.method === 'GET' && url.pathname === '/reactions') {
      const permalink = url.searchParams.get('permalink');
      if (!permalink) {
        return json({ error: 'permalink is required' }, 400);
      }
      if (!env.REACTIONS) {
        return json({ error: 'KV not bound' }, 500);
      }
      const key = `reactions:${await md5(permalink)}`;
      const raw = await env.REACTIONS.get(key);
      const data = raw ? JSON.parse(raw) : {};
      return json(data, 200);
    }

    if (request.method !== 'POST') {
      return json({ error: 'Method not allowed' }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return json({ error: 'Invalid JSON' }, 400);
    }

    // Live reaction: increment a counter in KV (no rebuild needed)
    if (body && body.action === 'react') {
      const { permalink, commentId, emoji } = body;
      if (!permalink || !commentId || !emoji) {
        return json({ error: 'permalink, commentId and emoji are required' }, 400);
      }
      if (!ALLOWED_EMOJIS.includes(emoji)) {
        return json({ error: 'emoji not allowed' }, 400);
      }
      if (!env.REACTIONS) {
        return json({ error: 'KV not bound' }, 500);
      }

      const key = `reactions:${await md5(permalink)}`;
      // read-modify-write with a couple of retries for races
      for (let attempt = 0; attempt < 3; attempt++) {
        const raw = await env.REACTIONS.get(key);
        const data = raw ? JSON.parse(raw) : {};
        if (!data[commentId]) data[commentId] = {};
        data[commentId][emoji] = (data[commentId][emoji] || 0) + 1;
        await env.REACTIONS.put(key, JSON.stringify(data));
        return json({ success: true, count: data[commentId][emoji] }, 200);
      }
      return json({ error: 'Failed to update reaction' }, 500);
    }

    // --- Create a new comment (original flow) ---
    const { name, message, permalink, replyTo } = body;

    if (!message || !permalink) {
      return json({ error: 'Message and permalink are required.' }, 400);
    }

    const cleanName = sanitize(name || 'Anónimo').substring(0, 50);
    const cleanMessage = sanitize(message).substring(0, 1000);
    const cleanReplyTo = replyTo ? sanitize(String(replyTo)).substring(0, 64) : '';

    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const branch = env.GITHUB_BRANCH || 'master';
    const pat = env.GITHUB_PAT;

    if (!owner || !repo || !pat) {
      return json({ error: 'Worker backend configuration error.' }, 500);
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

    const response = await fetch(githubUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${pat}`,
        'User-Agent': 'Cloudflare-Worker-Comments',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
      },
      body: JSON.stringify({
        message: `Add comment by ${cleanName} on ${permalink}`,
        content: encodedContent,
        branch: branch
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error('GitHub API error:', errText);
      return json({ error: 'Failed to save comment to repository.' }, 502);
    }

    return json({ success: true }, 200);
  }
};

function json(data, status) {
  return new Response(JSON.stringify(data), {
    status: status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}

// Helper function to escape HTML
function sanitize(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

// Helper to calculate MD5 hash using Web Crypto API
async function md5(message) {
  const msgUint8 = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('MD5', msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
