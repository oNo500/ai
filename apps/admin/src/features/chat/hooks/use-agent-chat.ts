'use client'

import { HttpAgent } from '@ag-ui/client'
import { useCallback, useEffect, useRef, useState } from 'react'

import { env } from '@/config/env'
import { getToken } from '@/lib/token'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface ToolCallState {
  id: string
  name: string
  status: 'running' | 'done'
}

export function useAgentChat(chatId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [toolCalls, setToolCalls] = useState<ToolCallState[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | undefined>()
  const agentRef = useRef<HttpAgent | null>(null)

  useEffect(() => {
    if (!chatId) return
    const token = getToken()
    fetch(`${env.NEXT_PUBLIC_API_URL}/api/chats/${chatId}/messages`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((data: { id: string, role: string, parts: { type: string, text?: string }[] }[]) => {
        setMessages(
          data.map((m) => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.parts.filter((p) => p.type === 'text').map((p) => p.text ?? '').join(''),
          })),
        )
      })
      .catch(() => {
        //
      })
  }, [chatId])

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: text }
    const assistantId = crypto.randomUUID()

    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: 'assistant', content: '' }])
    setToolCalls([])
    setIsLoading(true)
    setError(undefined)

    const token = getToken()
    const agent = new HttpAgent({
      url: `${env.NEXT_PUBLIC_API_URL}/api/chats/${chatId}/messages/stream`,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    agentRef.current = agent

    try {
      await agent.runAgent(
        { runId: crypto.randomUUID() },
        {
          onRunErrorEvent: ({ event }) => {
            setError(new Error(event.message))
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: `[Error: ${event.message}]` } : m,
              ),
            )
          },
          onTextMessageContentEvent: ({ event }) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + event.delta } : m,
              ),
            )
          },
          onToolCallStartEvent: ({ event }) => {
            setToolCalls((prev) => [
              ...prev,
              { id: event.toolCallId, name: event.toolCallName, status: 'running' },
            ])
          },
          onToolCallEndEvent: ({ event }) => {
            setToolCalls((prev) =>
              prev.map((tc) => (tc.id === event.toolCallId ? { ...tc, status: 'done' } : tc)),
            )
          },
        },
      )
    } catch (error_) {
      if ((error_ as Error).name !== 'AbortError') {
        const message = error_ instanceof Error ? error_.message : 'Failed to connect to agent'
        setError(new Error(message))
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: `[Error: ${message}]` } : m,
          ),
        )
      }
    } finally {
      setIsLoading(false)
      agentRef.current = null
    }
  }, [isLoading, chatId])

  const stop = useCallback(() => {
    agentRef.current?.abortController.abort()
  }, [])

  return { messages, toolCalls, isLoading, error, sendMessage, stop }
}
