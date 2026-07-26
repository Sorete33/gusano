/**
 * Cloudflare Worker for handling anonymous comments
 * Place this code in a Cloudflare Worker, configure the environment variables,
 * and add your GitHub PAT as a secret named GITHUB_PAT.
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*', // Replace with your domain (e.g., https://audiogusano.neocities.org) for security
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export default {
  async fetch(request, env, ctx) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }

    try {
      const body = await request.json();
      const { name, message, permalink, replyTo } = body;

      // Basic validation
      if (!message || !permalink) {
        return new Response(JSON.stringify({ error: 'Message and permalink are required.' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
        });
      }

      // Sanitize inputs to prevent basic HTML injection
      const cleanName = sanitize(name || 'Anónimo').substring(0, 50);
      const cleanMessage = sanitize(message).substring(0, 1000);
      const cleanReplyTo = replyTo ? sanitize(String(replyTo)).substring(0, 64) : '';

      // Environment Variables (Set these in Cloudflare Dashboard)
      const owner = env.GITHUB_OWNER; // e.g. "your-username"
      const repo = env.GITHUB_REPO;   // e.g. "gusano-master"
      const branch = env.GITHUB_BRANCH || 'master';
      const pat = env.GITHUB_PAT;     // Personal Access Token (stored as Secret)

      if (!owner || !repo || !pat) {
        return new Response(JSON.stringify({ error: 'Worker backend configuration error.' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
        });
      }

      // Generate comment file name and contents
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

      // Compute MD5 of permalink to organize comments in folders
      const permalinkHash = await md5(permalink);
      const filePath = `data/comments/${permalinkHash}/comment-${timestamp}.json`;

      // Commit to GitHub via API
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
        return new Response(JSON.stringify({ error: 'Failed to save comment to repository.' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
        });
      }

      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });

    } catch (err) {
      console.error(err);
      return new Response(JSON.stringify({ error: 'Internal Server Error' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
      });
    }
  }
};

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
