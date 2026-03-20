'use client'

import { useCallback, useRef, useState } from 'react'

import { env } from '@/config/env'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export interface ToolCall {
  id: string
  name: string
  status: 'running' | 'done'
}

interface AgUiEvent {
  type: string
  messageId?: string
  delta?: string
  toolCallId?: string
  toolCallName?: string
}

export function useAgentChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(async (text: string, sessionId?: string) => {
    if (!text.trim() || isLoading) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    const assistantId = crypto.randomUUID()

    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: 'assistant', content: '' }])
    setToolCalls([])
    setIsLoading(true)

    abortRef.current = new AbortController()

    try {
      const res = await fetch(`${env.NEXT_PUBLIC_API_URL}/api/agent/stream`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'accept': 'text/event-stream' },
        body: JSON.stringify({ message: text, sessionId }),
        signal: abortRef.current.signal,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue

          const json = dataLine.slice('data: '.length).trim()
          if (!json) continue

          let event: AgUiEvent
          try {
            event = JSON.parse(json) as AgUiEvent
          } catch {
            continue
          }

          if (event.type === 'RUN_ERROR') {
            const errMsg = (event as unknown as { message?: string }).message ?? 'Unknown error'
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: `[Error: ${errMsg}]` } : m,
              ),
            )
          } else if (event.type === 'TEXT_MESSAGE_CONTENT' && event.delta) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + event.delta! } : m,
              ),
            )
          } else if (event.type === 'TOOL_CALL_START' && event.toolCallId && event.toolCallName) {
            setToolCalls((prev) => [
              ...prev,
              { id: event.toolCallId!, name: event.toolCallName!, status: 'running' },
            ])
          } else if (event.type === 'TOOL_CALL_END' && event.toolCallId) {
            setToolCalls((prev) =>
              prev.map((tc) => (tc.id === event.toolCallId ? { ...tc, status: 'done' } : tc)),
            )
          }
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: '[Error: failed to connect to agent]' } : m,
          ),
        )
      }
    } finally {
      setIsLoading(false)
    }
  }, [isLoading])

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { messages, toolCalls, isLoading, sendMessage, stop }
}
