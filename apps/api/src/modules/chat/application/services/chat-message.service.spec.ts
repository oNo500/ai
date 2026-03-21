import { vi } from 'vitest'

import { createChatMocks } from '@/__tests__/unit/factories/mock-factory'
import { ChatMessageService } from '@/modules/chat/application/services/chat-message.service'

import type { ChatMessage } from '@workspace/database'

const BASE_MSG: ChatMessage = {
  id: 'msg-1',
  chatId: 'chat-1',
  role: 'user',
  parts: [{ type: 'text', text: 'Hello' }],
  attachments: [],
  createdAt: new Date(),
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

describe('chatMessageService', () => {
  let service: ChatMessageService
  let mocks: ReturnType<typeof createChatMocks>
  let fetchSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    mocks = createChatMocks()
    mocks.configService.get.mockReturnValue('http://agentic:8000')
    service = new ChatMessageService(mocks.chatMessageRepository, mocks.configService)
  })

  afterEach(() => {
    fetchSpy?.mockRestore()
  })

  describe('getMessages', () => {
    it('returns messages for chatId', async () => {
      mocks.chatMessageRepository.findByChatId.mockResolvedValue([BASE_MSG])

      const result = await service.getMessages('chat-1')

      expect(result).toEqual([BASE_MSG])
      expect(mocks.chatMessageRepository.findByChatId).toHaveBeenCalledWith('chat-1')
    })
  })

  describe('streamMessage', () => {
    it('saves user message before streaming', async () => {
      mocks.chatMessageRepository.create.mockResolvedValue(BASE_MSG)
      mocks.chatMessageRepository.findByChatId.mockResolvedValue([BASE_MSG])

      fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(makeAgUiSseBody([{ type: 'RUN_STARTED' }, { type: 'RUN_FINISHED' }]), {
          status: 200,
        }),
      )

      const chunks: Uint8Array[] = []
      for await (const chunk of service.streamMessage('chat-1', 'Hello', 'text/event-stream')) {
        chunks.push(chunk)
      }

      expect(mocks.chatMessageRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({ chatId: 'chat-1', role: 'user' }),
      )
    })

    it('saves assistant message after stream ends', async () => {
      const userMsg = { ...BASE_MSG, role: 'user' as const }
      const assistantMsg = { ...BASE_MSG, id: 'msg-2', role: 'assistant' as const }

      mocks.chatMessageRepository.create
        .mockResolvedValueOnce(userMsg)
        .mockResolvedValueOnce(assistantMsg)
      mocks.chatMessageRepository.findByChatId.mockResolvedValue([userMsg])

      fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(
          makeAgUiSseBody([
            { type: 'TEXT_MESSAGE_CONTENT', messageId: 'm1', delta: 'Hi there' },
            { type: 'RUN_FINISHED' },
          ]),
          { status: 200 },
        ),
      )

      const chunks: Uint8Array[] = []
      for await (const chunk of service.streamMessage('chat-1', 'Hello', 'text/event-stream')) {
        chunks.push(chunk)
      }

      expect(mocks.chatMessageRepository.create).toHaveBeenLastCalledWith(
        expect.objectContaining({
          chatId: 'chat-1',
          role: 'assistant',
          parts: [{ type: 'text', text: 'Hi there' }],
        }),
      )
    })

    it('passes complete history to agentic service', async () => {
      const history: ChatMessage[] = [
        { ...BASE_MSG, id: 'msg-1', role: 'user', parts: [{ type: 'text', text: 'First message' }] },
        { ...BASE_MSG, id: 'msg-2', role: 'assistant', parts: [{ type: 'text', text: 'Response' }] },
        { ...BASE_MSG, id: 'msg-3', role: 'user', parts: [{ type: 'text', text: 'Hello' }] },
      ]
      mocks.chatMessageRepository.create.mockResolvedValue(BASE_MSG)
      mocks.chatMessageRepository.findByChatId.mockResolvedValue(history)

      fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
        new Response(makeAgUiSseBody([{ type: 'RUN_FINISHED' }]), { status: 200 }),
      )

      const chunks: Uint8Array[] = []
      for await (const chunk of service.streamMessage('chat-1', 'Hello', 'text/event-stream')) {
        chunks.push(chunk)
      }

      const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
      const body = JSON.parse(init.body as string) as { messages: unknown[] }
      expect(body.messages).toHaveLength(3)
    })
  })
})
