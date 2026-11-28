import { readCanonAsset } from '../../lib/canon-r2.js'

export async function onRequest({ request, env }) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response(null, { status: 405, headers: { allow: 'GET, HEAD' } })
  }
  return readCanonAsset(env, new URL(request.url), request.method)
}
