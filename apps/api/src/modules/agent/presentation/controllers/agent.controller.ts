import { Body, Controller, HttpCode, HttpStatus, Post, Req, Res } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import { ApiOperation, ApiTags } from '@nestjs/swagger'
import { type Request, type Response } from 'express'

import { AgentInvokeDto } from '@/modules/agent/presentation/dtos/agent-invoke.dto'

import type { Env } from '@/app/config/env.schema'

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
        accept: req.headers['accept'] ?? 'text/event-stream',
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

    const reader = upstream.body!.getReader()
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        res.write(decoder.decode(value, { stream: true }))
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
      headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
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

    const reader = upstream.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    try {
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

          try {
            const event = JSON.parse(json) as { type: string; delta?: string }

            if (event.type === 'TEXT_MESSAGE_CONTENT' && event.delta !== undefined) {
              res.write(`0:${JSON.stringify(event.delta)}\n`)
            } else if (event.type === 'RUN_FINISHED') {
              res.write(`e:${JSON.stringify({ finishReason: 'stop' })}\n`)
              res.write(`d:${JSON.stringify({ finishReason: 'stop' })}\n`)
            }
          } catch {
            // malformed JSON — skip
          }
        }
      }
    } finally {
      res.end()
    }
  }
}
