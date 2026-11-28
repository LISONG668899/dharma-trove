import { createHash } from 'node:crypto'
import { readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { join, relative } from 'node:path'
import { S3Client, ListObjectsV2Command, PutObjectCommand } from '@aws-sdk/client-s3'

const dist = 'docs/.vitepress/dist'
const root = join(dist, 'canon')
const variables = ['CANON_R2_ACCOUNT_ID', 'CANON_R2_BUCKET', 'CANON_R2_ACCESS_KEY_ID', 'CANON_R2_SECRET_ACCESS_KEY']

if (process.env.CANON_R2_ENABLED !== '1') {
  console.log('Canon R2 disabled; retaining local static files.')
  process.exit(0)
}
for (const name of variables) {
  if (!process.env[name]) throw new Error(`Missing build variable: ${name}`)
}

const client = new S3Client({
  region: 'auto',
  endpoint: `https://${process.env.CANON_R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
  credentials: {
    accessKeyId: process.env.CANON_R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.CANON_R2_SECRET_ACCESS_KEY,
  },
  requestChecksumCalculation: 'WHEN_REQUIRED',
  responseChecksumValidation: 'WHEN_REQUIRED',
  maxAttempts: 5,
})
const bucket = process.env.CANON_R2_BUCKET

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = await Promise.all(entries.map(async entry => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return walk(path)
    if (!entry.isFile() || !entry.name.endsWith('.json')) throw new Error(`Unexpected canon asset: ${path}`)
    return [path]
  }))
  return files.flat()
}

const paths = (await walk(root)).sort()
if (paths.length === 0) throw new Error('Canon directory is empty')
const snapshot = createHash('sha256')
const files = []
for (const path of paths) {
  const name = relative(root, path).replaceAll('\\', '/')
  const body = await readFile(path)
  snapshot.update(name).update('\0').update(createHash('sha256').update(body).digest())
  files.push({ path, name, size: body.length })
}
const version = snapshot.digest('hex')
const prefix = `canon/${version}/`

async function listObjects() {
  const objects = new Map()
  let token
  do {
    const page = await client.send(new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix, ContinuationToken: token }))
    for (const object of page.Contents ?? []) objects.set(object.Key, object.Size)
    token = page.IsTruncated ? page.NextContinuationToken : undefined
  } while (token)
  return objects
}

const present = await listObjects()
const pending = files.filter(file => present.get(prefix + file.name) !== file.size)
console.log(`Canon R2: ${files.length} files, ${pending.length} to upload, snapshot ${version}`)
let cursor = 0
let completed = 0
await Promise.all(Array.from({ length: Math.min(20, pending.length) }, async () => {
  while (cursor < pending.length) {
    const file = pending[cursor++]
    await client.send(new PutObjectCommand({
      Bucket: bucket,
      Key: prefix + file.name,
      Body: await readFile(file.path),
      ContentType: 'application/json; charset=utf-8',
    }))
    if (++completed % 500 === 0) console.log(`Canon R2 uploaded ${completed}/${pending.length}`)
  }
}))

const verified = await listObjects()
if (files.some(file => verified.get(prefix + file.name) !== file.size)) {
  throw new Error('Canon R2 verification failed; keeping the static files and aborting deployment.')
}
await writeFile(join(dist, 'canon-version.json'), JSON.stringify({ version, files: files.length }))
await rm(root, { recursive: true })
console.log(`Canon R2 verified ${files.length} files; removed only the deployment copies.`)
