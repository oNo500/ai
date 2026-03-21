import { Body, Controller, HttpCode, HttpStatus, Post, Req, Res } from '@nestjs/common'
import { ConfigService } from '@nestjs/config'
import { ApiOperation, ApiTags } from '@nestjs/swagger'

import { AgentInvokeDto } from '@/modules/agent/presentation/dtos/agent-invoke.dto'

import type { Env } from '@/app/config/env.schema'
import type { Request, Response } from 'express'

/**
 * AgentController — proxies AG-UI requests to the Python agentic service.
 *
 * POST /agent/stream — transparent AG-UI SSE passthrough
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
  @ApiOperation({ summary: 'Transparent AG-UI SSE stream' })
  async stream(@Body() dto: AgentInvokeDto, @Req() req: Request, @Res() res: Response) {
    const upstream = await fetch(`${this.#agenticUrl}/stream/agui`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'accept': req.headers.accept ?? 'text/event-stream',
      },
      body: JSON.stringify(dto),
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
}
