import type { ToolCall } from '@/features/chat/hooks/use-agent-chat'

interface ToolCallIndicatorProps {
  toolCalls: ToolCall[]
}

export function ToolCallIndicator({ toolCalls }: ToolCallIndicatorProps) {
  if (toolCalls.length === 0) return null

  return (
    <div className="flex flex-col gap-1 px-4 py-2">
      {toolCalls.map((tc) => (
        <div key={tc.id} className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            className={`h-2 w-2 rounded-full ${tc.status === 'running' ? 'animate-pulse bg-blue-500' : 'bg-green-500'}`}
          />
          <span>{tc.name}</span>
          <span>{tc.status === 'running' ? 'running…' : 'done'}</span>
        </div>
      ))}
    </div>
  )
}
