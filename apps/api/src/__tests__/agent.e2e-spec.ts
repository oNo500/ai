import { createTestApp } from './helpers/create-app'
import { registerAndLogin } from './helpers/create-authenticated-request'
import { createAuthRequest, createRequest } from './helpers/create-request'

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
  let token: string
  let fetchSpy: MockInstance<typeof fetch>

  const auth = () => createAuthRequest(app, token)

  beforeAll(async () => {
    app = await createTestApp()
    const prefix = globalThis.e2ePrefix ?? `e2e-${Date.now()}`
    token = await registerAndLogin(app, `${prefix}-agent@test.com`, 'Password123', 'AgentUser')
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
      const res = await auth()
        .post('/api/agent/stream')
        .send({ threadId: 't1', runId: 'r1', messages: [], state: {}, tools: [], context: [], forwardedProps: null })
        .expect(200)

      expect(res.headers['content-type']).toMatch(/text\/event-stream/)
    })

    it('proxies AG-UI events as-is', async () => {
      const res = await auth()
        .post('/api/agent/stream')
        .send({ threadId: 't1', runId: 'r1', messages: [], state: {}, tools: [], context: [], forwardedProps: null })

      expect(res.text).toContain('RUN_STARTED')
      expect(res.text).toContain('TEXT_MESSAGE_CONTENT')
      expect(res.text).toContain('RUN_FINISHED')
    })

    it('forwards threadId and runId to agentic service', async () => {
      await auth()
        .post('/api/agent/stream')
        .send({ threadId: 't1', runId: 'r1', messages: [], state: {}, tools: [], context: [], forwardedProps: null })

      const calls = fetchSpy.mock.calls as [string, RequestInit][]
      const [, init] = calls[0]!
      const body = JSON.parse(init.body as string) as Record<string, unknown>
      expect(body.threadId).toBe('t1')
      expect(body.runId).toBe('r1')
    })

    it('returns 401 without token', async () => {
      await createRequest(app)
        .post('/api/agent/stream')
        .send({ threadId: 't1', runId: 'r1', messages: [], state: {}, tools: [], context: [], forwardedProps: null })
        .expect(401)
    })
  })
})
