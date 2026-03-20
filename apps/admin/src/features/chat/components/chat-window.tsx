'use client'

import { Button } from '@workspace/ui/components/button'
import { Input } from '@workspace/ui/components/input'
import { useRef, useState } from 'react'

import { MessageList } from '@/features/chat/components/message-list'
import { ToolCallIndicator } from '@/features/chat/components/tool-call-indicator'
import { useAgentChat } from '@/features/chat/hooks/use-agent-chat'

export function ChatWindow() {
  const { messages, toolCalls, isLoading, sendMessage, stop } = useAgentChat()
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault()
    if (!input.trim()) return
    void sendMessage(input)
    setInput('')
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} />
      <ToolCallIndicator toolCalls={toolCalls} />
      <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t p-4">
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={isLoading}
          className="flex-1"
        />
        {isLoading
          ? (
              <Button type="button" variant="outline" onClick={stop}>
                Stop
              </Button>
            )
          : (
              <Button type="submit" disabled={!input.trim()}>
                Send
              </Button>
            )}
      </form>
    </div>
  )
}
