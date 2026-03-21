import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  ParseUUIDPipe,
  Post,
  Request,
} from '@nestjs/common'
import { ApiOperation, ApiTags } from '@nestjs/swagger'

import { ChatService } from '@/modules/chat/application/services/chat.service'
import { CreateChatDto } from '@/modules/chat/presentation/dtos/create-chat.dto'

import type { Chat } from '@workspace/database'

@ApiTags('chats')
@Controller('chats')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Get()
  @ApiOperation({ summary: 'List chats for the current user' })
  listChats(@Request() req: { user: { id: string } }): Promise<Chat[]> {
    return this.chatService.listChats(req.user.id)
  }

  @Post()
  @HttpCode(HttpStatus.CREATED)
  @ApiOperation({ summary: 'Create a new chat' })
  createChat(
    @Request() req: { user: { id: string } },
    @Body() dto: CreateChatDto,
  ): Promise<Chat> {
    return this.chatService.createChat(req.user.id, dto.title)
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete a chat' })
  deleteChat(
    @Request() req: { user: { id: string } },
    @Param('id', ParseUUIDPipe) id: string,
  ): Promise<void> {
    return this.chatService.deleteChat(id, req.user.id)
  }
}
