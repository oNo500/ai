import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  ParseUUIDPipe,
  Post,
  Req,
  Res,
} from '@nestjs/common'
import { ApiOperation, ApiTags } from '@nestjs/swagger'

import { AgentInvokeDto } from '@/modules/agent/presentation/dtos/agent-invoke.dto'
import { ChatMessageService } from '@/modules/chat/application/services/chat-message.service'
import { ChatService } from '@/modules/chat/application/services/chat.service'

import type { ChatMessage } from '@workspace/database'
import type { Request, Response } from 'express'

@ApiTags('chats')
@Controller('chats/:chatId/messages')
export class ChatStreamController {
  constructor(
    private readonly chatService: ChatService,
    private readonly chatMessageService: ChatMessageService,
  ) {}

  @Get()
  @ApiOperation({ summary: 'Get message history for a chat' })
  async getMessages(
    @Req() req: Request & { user: { id: string } },
    @Param('chatId', ParseUUIDPipe) chatId: string,
  ): Promise<ChatMessage[]> {
    await this.chatService.getChat(chatId, req.user.id)
    return this.chatMessageService.getMessages(chatId)
  }

  @Post('stream')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Send a message and stream the AG-UI response' })
  async stream(
    @Req() req: Request & { user: { id: string } },
    @Res() res: Response,
    @Param('chatId', ParseUUIDPipe) chatId: string,
    @Body() dto: AgentInvokeDto,
  ): Promise<void> {
    await this.chatService.getChat(chatId, req.user.id)

    const lastUserMessage = [...(dto.messages ?? [])]
      .reverse()
      .find((m): m is { role: string; content: string } =>
        typeof m === 'object' && m !== null && (m as { role: string }).role === 'user',
      )
    const userText = lastUserMessage?.content ?? ''

    res.setHeader('Content-Type', 'text/event-stream')
    res.setHeader('Cache-Control', 'no-cache')
    res.setHeader('Connection', 'keep-alive')
    res.flushHeaders()

    try {
      for await (const chunk of this.chatMessageService.streamMessage(
        chatId,
        userText,
        req.headers.accept ?? 'text/event-stream',
      )) {
        res.write(chunk)
      }
    } finally {
      res.end()
    }
  }
}
