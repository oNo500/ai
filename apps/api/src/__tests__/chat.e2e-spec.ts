import { vi } from 'vitest'

import { createTestApp } from './helpers/create-app'
import { registerAndLogin, withToken } from './helpers/create-authenticated-request'
import { createRequest } from './helpers/create-request'

import type { INestApplication } from '@nestjs/common'
import type { MockInstance } from 'vitest'

interface ChatResponse {
  id: string
  title: string
  userId: string
  visibility: string
  createdAt: string
}

interface MessageResponse {
  id: string
  chatId: string
  role: string
  parts: unknown[]
  createdAt: string
}

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

describe('chat E2E', () => {
  let app: INestApplication
  let token: string
  let fetchSpy: MockInstance<typeof fetch>

  beforeAll(async () => {
    app = await createTestApp()
    const email = `${globalThis.e2ePrefix}-chat@example.com`
    token = await registerAndLogin(app, email, 'Password123!')
  })

  afterAll(async () => {
    await app.close()
  })

  describe('POST /api/chats', () => {
    it('creates a chat and returns 201', async () => {
      const res = await withToken(createRequest(app), token)
        .post('/api/chats')
        .send({ title: 'Test Chat' })
        .expect(201)

      const body = res.body as ChatResponse
      expect(body.id).toBeDefined()
      expect(body.title).toBe('Test Chat')
      expect(body.visibility).toBe('private')
    })

    it('uses default title when not provided', async () => {
      const res = await withToken(createRequest(app), token)
        .post('/api/chats')
        .send({})
        .expect(201)

      expect((res.body as ChatResponse).title).toBe('New Chat')
    })

    it('returns 401 without token', async () => {
      await createRequest(app).post('/api/chats').send({ title: 'x' }).expect(401)
    })
  })

  describe('GET /api/chats', () => {
    it('returns list of chats for the authenticated user', async () => {
      await withToken(createRequest(app), token).post('/api/chats').send({ title: 'Chat A' })
      await withToken(createRequest(app), token).post('/api/chats').send({ title: 'Chat B' })

      const res = await withToken(createRequest(app), token).get('/api/chats').expect(200)

      const chats = res.body as ChatResponse[]
      expect(Array.isArray(chats)).toBe(true)
      expect(chats.length).toBeGreaterThanOrEqual(2)
    })

    it('returns 401 without token', async () => {
      await createRequest(app).get('/api/chats').expect(401)
    })
  })

  describe('DELETE /api/chats/:id', () => {
    it('deletes a chat owned by the user', async () => {
      const createRes = await withToken(createRequest(app), token)
        .post('/api/chats')
        .send({ title: 'To Delete' })

      const chatId = (createRes.body as ChatResponse).id

      await withToken(createRequest(app), token).delete(`/api/chats/${chatId}`).expect(204)
    })

    it('returns 403 when deleting another user\'s chat', async () => {
      const otherEmail = `${globalThis.e2ePrefix}-chat2@example.com`
      const otherToken = await registerAndLogin(app, otherEmail, 'Password123!')

      const createRes = await withToken(createRequest(app), otherToken)
        .post('/api/chats')
        .send({ title: 'Other User Chat' })
      const chatId = (createRes.body as ChatResponse).id

      await withToken(createRequest(app), token).delete(`/api/chats/${chatId}`).expect(403)
    })
  })

  describe('GET /api/chats/:chatId/messages', () => {
    let chatId: string

    beforeAll(async () => {
      const res = await withToken(createRequest(app), token)
        .post('/api/chats')
        .send({ title: 'Messages Test' })
      chatId = (res.body as ChatResponse).id
    })

    it('returns empty array for new chat', async () => {
      const res = await withToken(createRequest(app), token)
        .get(`/api/chats/${chatId}/messages`)
        .expect(200)

      expect(res.body).toEqual([])
    })

    it('returns 401 without token', async () => {
      await createRequest(app).get(`/api/chats/${chatId}/messages`).expect(401)
    })

    it('returns 403 for another user\'s chat', async () => {
      const otherEmail = `${globalThis.e2ePrefix}-chat3@example.com`
      const otherToken = await registerAndLogin(app, otherEmail, 'Password123!')

      await withToken(createRequest(app), otherToken)
        .get(`/api/chats/${chatId}/messages`)
        .expect(403)
    })
  })

  describe('POST /api/chats/:chatId/messages/stream', () => {
    let chatId: string

    beforeEach(async () => {
      const res = await withToken(createRequest(app), token)
        .post('/api/chats')
        .send({ title: 'Stream Test' })
      chatId = (res.body as ChatResponse).id

      fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(
          makeAgUiSseBody([
            { type: 'RUN_STARTED', threadId: chatId, runId: 'r1' },
            { type: 'TEXT_MESSAGE_START', messageId: 'm1', role: 'assistant' },
            { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm1', delta: 'Hello!' },
            { type: 'TEXT_MESSAGE_END', messageId: 'm1' },
            { type: 'RUN_FINISHED', threadId: chatId, runId: 'r1' },
          ]),
          { status: 200, headers: { 'content-type': 'text/event-stream' } },
        ),
      )
    })

    afterEach(() => {
      fetchSpy.mockRestore()
    })

    it('returns 200 with text/event-stream', async () => {
      const res = await withToken(createRequest(app), token)
        .post(`/api/chats/${chatId}/messages/stream`)
        .send({ threadId: chatId, runId: 'r1', messages: [{ role: 'user', content: 'Hi' }], state: {}, tools: [], context: [], forwardedProps: null })
        .expect(200)

      expect(res.headers['content-type']).toMatch(/text\/event-stream/)
    })

    it('persists user and assistant messages in DB after stream', async () => {
      await withToken(createRequest(app), token)
        .post(`/api/chats/${chatId}/messages/stream`)
        .send({ threadId: chatId, runId: 'r1', messages: [{ role: 'user', content: 'Hi' }], state: {}, tools: [], context: [], forwardedProps: null })

      const historyRes = await withToken(createRequest(app), token)
        .get(`/api/chats/${chatId}/messages`)
        .expect(200)

      const messages = historyRes.body as MessageResponse[]
      expect(messages.length).toBe(2)
      expect(messages[0]!.role).toBe('user')
      expect(messages[1]!.role).toBe('assistant')
    })

    it('passes full history to agentic service on second message', async () => {
      // First message
      await withToken(createRequest(app), token)
        .post(`/api/chats/${chatId}/messages/stream`)
        .send({ threadId: chatId, runId: 'r1', messages: [{ role: 'user', content: 'First' }], state: {}, tools: [], context: [], forwardedProps: null })

      fetchSpy.mockRestore()
      fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(
          makeAgUiSseBody([{ type: 'RUN_FINISHED' }]),
          { status: 200 },
        ),
      )

      // Second message
      await withToken(createRequest(app), token)
        .post(`/api/chats/${chatId}/messages/stream`)
        .send({ threadId: chatId, runId: 'r2', messages: [{ role: 'user', content: 'Second' }], state: {}, tools: [], context: [], forwardedProps: null })

      const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
      const body = JSON.parse(init.body as string) as { messages: unknown[] }
      // Should include: first user, first assistant, second user = 3
      expect(body.messages.length).toBe(3)
    })

    it('returns 401 without token', async () => {
      await createRequest(app)
        .post(`/api/chats/${chatId}/messages/stream`)
        .send({ threadId: chatId, runId: 'r1', messages: [], state: {}, tools: [], context: [], forwardedProps: null })
        .expect(401)
    })
  })
})
