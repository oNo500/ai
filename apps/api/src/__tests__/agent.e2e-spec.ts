import { createTestApp } from './helpers/create-app'
import { createRequest } from './helpers/create-request'

import type { INestApplication } from '@nestjs/common'
import type { MockInstance } from 'vitest'

// Stub global fetch so no real HTTP calls are made in tests
function makeAgUiSseBody(events: object[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  const lines = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join('')
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(lines))
      controller.close()
    },
  })
}

const RUN_STARTED = { type: 'RUN_STARTED', threadId: 't1', runId: 'r1' }
const MSG_START = { type: 'TEXT_MESSAGE_START', messageId: 'm1', role: 'assistant' }
const MSG_CONTENT = { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm1', delta: 'Hello!' }
const MSG_END = { type: 'TEXT_MESSAGE_END', messageId: 'm1' }
const RUN_FINISHED = { type: 'RUN_FINISHED', threadId: 't1', runId: 'r1' }

describe('agent E2E tests', () => {
  let app: INestApplication
  let fetchSpy: MockInstance<typeof fetch>

  beforeAll(async () => {
    app = await createTestApp()
  })

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        makeAgUiSseBody([RUN_STARTED, MSG_START, MSG_CONTENT, MSG_END, RUN_FINISHED]),
        { status: 200, headers: { 'content-type': 'text/event-stream' } },
      ),
    )
  })

  afterEach(() => {
    fetchSpy.mockRestore()
  })

  afterAll(async () => {
    await app.close()
  })

  describe('pOST /api/agent/stream', () => {
    it('returns 200 with text/event-stream content type', async () => {
      const res = await createRequest(app)
        .post('/api/agent/stream')
        .send({ message: 'Hello' })
        .expect(200)

      expect(res.headers['content-type']).toMatch(/text\/event-stream/)
    })

    it('proxies AG-UI events as-is', async () => {
      const res = await createRequest(app)
        .post('/api/agent/stream')
        .send({ message: 'Hello' })

      expect(res.text).toContain('RUN_STARTED')
      expect(res.text).toContain('TEXT_MESSAGE_CONTENT')
      expect(res.text).toContain('RUN_FINISHED')
    })

    it('forwards sessionId and userId to agentic service', async () => {
      await createRequest(app)
        .post('/api/agent/stream')
        .send({ message: 'Hi', sessionId: 'sess-1', userId: 'user-42' })

      const calls = fetchSpy.mock.calls as [string, RequestInit][]
      const [, init] = calls[0]!
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.session_id).toBe('sess-1')
      expect(body.user_id).toBe('user-42')
    })
  })

  describe('pOST /api/agent/stream/client', () => {
    it('returns Vercel AI Stream format', async () => {
      const res = await createRequest(app)
        .post('/api/agent/stream/client')
        .send({ message: 'Hello' })

      expect(res.headers['x-vercel-ai-data-stream']).toBe('v1')
      // TEXT_MESSAGE_CONTENT -> 0: prefix
      expect(res.text).toContain('0:"Hello!"')
      // RUN_FINISHED -> e: and d: lines
      expect(res.text).toContain('e:')
      expect(res.text).toContain('d:')
    })

    it('does not emit RUN_STARTED or TEXT_MESSAGE_START as 0: lines', async () => {
      const res = await createRequest(app)
        .post('/api/agent/stream/client')
        .send({ message: 'Hello' })

      // Only TEXT_MESSAGE_CONTENT events should produce 0: lines
      const zeroLines = res.text.split('\n').filter((l: string) => l.startsWith('0:'))
      expect(zeroLines).toHaveLength(1)
      expect(zeroLines[0]).toBe('0:"Hello!"')
    })
  })
})
