import { Inject, Injectable } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import { EventType } from '@ag-ui/core'

import { CHAT_MESSAGE_REPOSITORY } from '@/modules/chat/application/ports/chat-message.repository.port'

import type { ChatMessageRepository } from '@/modules/chat/application/ports/chat-message.repository.port'
import type { Env } from '@/app/config/env.schema'
import type { ChatMessage } from '@workspace/database'

@Injectable()
export class ChatMessageService {
  readonly #agenticUrl: string

  constructor(
    @Inject(CHAT_MESSAGE_REPOSITORY)
    private readonly chatMessageRepository: ChatMessageRepository,
    configService: ConfigService<Env, true>,
  ) {
    this.#agenticUrl = configService.get('AGENTIC_URL', { infer: true })
  }

  async getMessages(chatId: string): Promise<ChatMessage[]> {
    return this.chatMessageRepository.findByChatId(chatId)
  }

  async *streamMessage(
    chatId: string,
    userText: string,
    accept: string,
  ): AsyncGenerator<Uint8Array> {
    const userMessage = await this.chatMessageRepository.create({
      chatId,
      role: 'user',
      parts: [{ type: 'text', text: userText }],
      attachments: [],
    })

    const history = await this.chatMessageRepository.findByChatId(chatId)
    const agUiMessages = history.map((m) => ({
      id: m.id,
      role: m.role,
      content: (m.parts as Array<{ type: string; text?: string }>)
        .filter((p) => p.type === 'text')
        .map((p) => p.text ?? '')
        .join(''),
    }))

    const upstream = await fetch(`${this.#agenticUrl}/stream/agui`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept },
      body: JSON.stringify({
        thread_id: chatId,
        run_id: crypto.randomUUID(),
        messages: agUiMessages,
        state: {},
        tools: [],
        context: [],
        forwarded_props: null,
      }),
    })

    const reader = upstream.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let assistantContent = ''

    try {
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break

        yield value

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue
          const json = dataLine.slice('data: '.length).trim()
          if (!json) continue
          try {
            const event = JSON.parse(json) as { type: string; delta?: string }
            if (event.type === EventType.TEXT_MESSAGE_CONTENT && event.delta) {
              assistantContent += event.delta
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } finally {
      if (assistantContent) {
        await this.chatMessageRepository.create({
          chatId,
          role: 'assistant',
          parts: [{ type: 'text', text: assistantContent }],
          attachments: [],
        })
      }
      void userMessage
    }
  }
}
