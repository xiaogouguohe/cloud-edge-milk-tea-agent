/**
 * 前端 API 日志插件 - 访问日志 + 回源日志
 * 每条日志一行，字段通过 \t 分隔
 * 访问日志写入 logs/frontend_access.log，回源日志写入 logs/frontend_backend.log
 */
import type { Plugin } from 'vite'
import { createWriteStream } from 'node:fs'
import { mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
import type { IncomingMessage, ServerResponse } from 'node:http'

const LOGS_DIR = join(__dirname, '..', 'logs')
mkdirSync(LOGS_DIR, { recursive: true })
const ACCESS_STREAM = createWriteStream(join(LOGS_DIR, 'frontend_access.log'), { flags: 'a' })
const BACKEND_STREAM = createWriteStream(join(LOGS_DIR, 'frontend_backend.log'), { flags: 'a' })

const BACKEND_TARGET = 'http://localhost:8000'

function ts(): string {
  return new Date().toISOString().slice(0, -1)
}

function safe(s: string | undefined): string {
  if (s == null) return ''
  return String(s).replace(/\t/g, ' ').replace(/\n/g, ' ').replace(/\r/g, '')
}

function field(s: string | undefined): string {
  const v = safe(s ?? '')
  return v ? v : '-'
}

function genReqId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`
}

function logAccess(
  reqId: string,
  method: string,
  path: string,
  status: number,
  durationMs: number,
  userAgent: string = ''
): void {
  const parts = [field(reqId), ts(), field(method), field(path), field(String(status)), field(userAgent), field(String(durationMs))]
  ACCESS_STREAM.write(parts.join('\t') + '\n')
}

function logBackend(
  reqId: string,
  target: string,
  operation: string,
  status: string,
  durationMs: number,
  error: string = ''
): void {
  const parts = [field(reqId), ts(), field(target), field(operation), field(status), field(String(durationMs)), field(error)]
  BACKEND_STREAM.write(parts.join('\t') + '\n')
}

function readBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = []
    req.on('data', (chunk) => chunks.push(chunk))
    req.on('end', () => resolve(Buffer.concat(chunks)))
    req.on('error', reject)
  })
}

export function apiLoggerPlugin(): Plugin {
  return {
    name: 'api-logger',
    configureServer(server) {
      server.middlewares.use(async (req: IncomingMessage, res: ServerResponse, next) => {
        const start = Date.now()
        const reqId = (req.headers['x-request-id'] as string) || (req.headers['X-Request-Id'] as string) || genReqId()
        const method = req.method || 'GET'
        const path = req.url || '/'
        const userAgent = req.headers['user-agent'] || ''

        if (!path.startsWith('/api')) {
          res.once('finish', () => {
            const durationMs = Date.now() - start
            logAccess(reqId, method, path, res.statusCode || 200, durationMs, userAgent)
          })
          return next()
        }

        // /api 请求：代理到 8000 并打回源日志
        const tBackend = Date.now()
        try {
          const body = method !== 'GET' && method !== 'HEAD' ? await readBody(req) : undefined
          const headers: Record<string, string> = {}
          for (const [k, v] of Object.entries(req.headers)) {
            if (v && k.toLowerCase() !== 'host' && k.toLowerCase() !== 'x-request-id') {
              headers[k] = Array.isArray(v) ? v[0] : v
            }
          }
          headers['X-Request-Id'] = reqId

          const upstream = await fetch(`${BACKEND_TARGET}${path}`, {
            method,
            headers,
            body,
          })

          const durationBackend = Date.now() - tBackend
          const status = upstream.ok ? 'success' : 'error'
          const errMsg = upstream.ok ? '' : `HTTP ${upstream.status}`
          logBackend(reqId, 'supervisor-api', path, status, durationBackend, errMsg)

          res.statusCode = upstream.status
          upstream.headers.forEach((v, k) => res.setHeader(k, v))
          const buf = Buffer.from(await upstream.arrayBuffer())
          res.end(buf)
        } catch (e) {
          const durationBackend = Date.now() - tBackend
          logBackend(reqId, 'supervisor-api', path, 'error', durationBackend, String(e))
          res.statusCode = 502
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ error: 'Proxy to backend failed' }))
        }

        const durationMs = Date.now() - start
        logAccess(reqId, method, path, res.statusCode, durationMs, userAgent)
      })
    },
  }
}
