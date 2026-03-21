'use client'

import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'

import { env } from '@/config/env'
import { getToken } from '@/lib/token'

import type { UIMessage } from 'ai'

export type { UIMessage as Message }

export function useAgentChat() {
  const { messages, status, error, sendMessage, stop, setMessages } = useChat({
    transport: new DefaultChatTransport({
      api: `${env.NEXT_PUBLIC_API_URL}/api/agent/stream/client`,
      headers: () => {
        const token = getToken()
        return token ? { Authorization: `Bearer ${token}` } : ({} as Record<string, string>)
      },
    }),
  })

  const isLoading = status === 'submitted' || status === 'streaming'

  async function send(text: string) {
    if (!text.trim() || isLoading) return
    await sendMessage({ role: 'user', parts: [{ type: 'text', text }] })
  }

  return { messages, isLoading, error, sendMessage: send, stop, setMessages }
}
