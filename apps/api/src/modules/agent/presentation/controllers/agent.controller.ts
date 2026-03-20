import { EventType, TextMessageContentEventSchema } from '@ag-ui/core'
import { formatDataStreamPart } from '@ai-sdk/ui-utils'
import { Body, Controller, HttpCode, HttpStatus, Post, Req, Res } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import { ApiOperation, ApiTags } from '@nestjs/swagger'

import { AgentInvokeDto } from '@/modules/agent/presentation/dtos/agent-invoke.dto'

import type { Env } from '@/app/config/env.schema'
import type { Request, Response } from 'express'

/**
 * AgentController — proxies requests to the Python agentic service.
 *
 * POST /agent/stream        — transparent AG-UI SSE passthrough (admin frontend)
 * POST /agent/stream/client — converts AG-UI events to Vercel AI Stream format (C-end clients)
 */
@ApiTags('agent')
@Controller('agent')
export class AgentController {
  readonly #agenticUrl: string

  constructor(configService: ConfigService<Env, true>) {
    this.#agenticUrl = configService.get('AGENTIC_URL', { infer: true })
  }

  @Post('stream')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Transparent AG-UI SSE stream (admin)' })
  async stream(@Body() dto: AgentInvokeDto, @Req() req: Request, @Res() res: Response) {
    const upstream = await fetch(`${this.#agenticUrl}/stream/agui`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'accept': req.headers.accept ?? 'text/event-stream',
      },
      body: JSON.stringify({
        message: dto.message,
        session_id: dto.sessionId,
        user_id: dto.userId ?? 'default',
      }),
    })

    res.setHeader('Content-Type', 'text/event-stream')
    res.setHeader('Cache-Control', 'no-cache')
    res.setHeader('Connection', 'keep-alive')
    res.flushHeaders()

    const reader = upstream.body!.getReader() as ReadableStreamDefaultReader<Uint8Array>
    const decoder = new TextDecoder()

    try {
      for (;;) {
        const result = await reader.read()
        if (result.done) break
        res.write(decoder.decode(result.value, { stream: true }))
      }
    } finally {
      res.end()
    }
  }

  @Post('stream/client')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Vercel AI Stream format (C-end clients)' })
  async streamClient(@Body() dto: AgentInvokeDto, @Res() res: Response) {
    const upstream = await fetch(`${this.#agenticUrl}/stream/agui`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'accept': 'text/event-stream' },
      body: JSON.stringify({
        message: dto.message,
        session_id: dto.sessionId,
        user_id: dto.userId ?? 'default',
      }),
    })

    res.setHeader('Content-Type', 'text/plain; charset=utf-8')
    res.setHeader('X-Vercel-AI-Data-Stream', 'v1')
    res.setHeader('Cache-Control', 'no-cache')
    res.setHeader('Connection', 'keep-alive')
    res.flushHeaders()

    const reader = upstream.body!.getReader() as ReadableStreamDefaultReader<Uint8Array>
    const decoder = new TextDecoder()
    let buffer = ''

    try {
      for (;;) {
        const result = await reader.read()
        if (result.done) break

        buffer += decoder.decode(result.value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part.split('\n').find((l) => l.startsWith('data: '))
          if (!dataLine) continue

          const json = dataLine.slice('data: '.length).trim()
          if (!json) continue

          const eventType = parseAgUiEventType(json)
          if (!eventType) continue

          if (eventType === EventType.TEXT_MESSAGE_CONTENT) {
            const event = TextMessageContentEventSchema.safeParse(JSON.parse(json))
            if (event.success && event.data.delta !== undefined) {
              res.write(`${formatDataStreamPart('text', event.data.delta)}\n`)
            }
          } else if (eventType === EventType.RUN_FINISHED) {
            res.write(`${formatDataStreamPart('finish_step', { isContinued: false, finishReason: 'stop' })}\n`)
            res.write(`${formatDataStreamPart('finish_message', { finishReason: 'stop', usage: { promptTokens: 0, completionTokens: 0 } })}\n`)
          }
        }
      }
    } finally {
      res.end()
    }
  }
}

function parseAgUiEventType(json: string): EventType | null {
  try {
    const parsed: unknown = JSON.parse(json)
    if (typeof parsed === 'object' && parsed !== null && 'type' in parsed) {
      const type = (parsed as Record<string, unknown>).type
      if (Object.values(EventType).includes(type as EventType)) {
        return type as EventType
      }
    }
    return null
  } catch {
    return null
  }
}
