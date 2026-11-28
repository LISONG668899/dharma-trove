// The static manifest belongs to this Pages deployment, including previews and rollbacks.
const CANON_PATH = /^\/canon\/(kangyur|tengyur|qianlong)\/(?:[\w-]+\/)*[\w-]+\.json$/

export async function readCanonAsset(env, url, method = 'GET') {
  if (!CANON_PATH.test(url.pathname)) return new Response(null, { status: 404 })
  const manifestURL = new URL('/canon-version.json', url)
  const manifest = await env.ASSETS.fetch(new Request(manifestURL))
  if (manifest.status === 404 || !manifest.headers.get('content-type')?.includes('json')) {
    return env.ASSETS.fetch(new Request(url, { method }))
  }
  if (!manifest.ok) return new Response('Canon manifest unavailable', { status: 503 })
  const { version } = await manifest.json()
  if (typeof version !== 'string' || !/^[a-f0-9]{64}$/.test(version) || !env.CANON_R2) {
    return new Response('Canon storage unavailable', { status: 503 })
  }
  const key = `canon/${version}/${url.pathname.slice('/canon/'.length)}`
  const object = method === 'HEAD' ? await env.CANON_R2.head(key) : await env.CANON_R2.get(key)
  if (!object) return new Response(null, { status: 404 })
  return new Response(method === 'HEAD' ? null : object.body, {
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'public, max-age=300',
      'etag': object.httpEtag,
    },
  })
}
