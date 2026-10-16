const USERNAME = "newsradar";

function unauthorized() {
  return new Response("NewsRadar preview authentication required.\n", {
    status: 401,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "text/plain; charset=utf-8",
      "WWW-Authenticate": 'Basic realm="NewsRadar Preview", charset="UTF-8"',
      "X-Robots-Tag": "noindex, nofollow, noarchive",
    },
  });
}

async function secureEqual(actual, expected) {
  const encoder = new TextEncoder();
  const [actualHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(actual)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const left = new Uint8Array(actualHash);
  const right = new Uint8Array(expectedHash);
  let difference = left.length ^ right.length;
  for (let index = 0; index < Math.min(left.length, right.length); index += 1) {
    difference |= left[index] ^ right[index];
  }
  return difference === 0;
}

export default {
  async fetch(request, env) {
    if (!env.PREVIEW_PASSWORD) {
      return new Response("Preview authentication is not configured.\n", {
        status: 503,
        headers: { "Cache-Control": "no-store" },
      });
    }

    const actual = request.headers.get("Authorization") || "";
    const expected = `Basic ${btoa(`${USERNAME}:${env.PREVIEW_PASSWORD}`)}`;
    if (!(await secureEqual(actual, expected))) {
      return unauthorized();
    }

    return env.ASSETS.fetch(request);
  },
};
