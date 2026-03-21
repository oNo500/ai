import { ForbiddenException, Inject, Injectable, NotFoundException } from '@nestjs/common'

import { CHAT_REPOSITORY } from '@/modules/chat/application/ports/chat.repository.port'
import { ErrorCode } from '@/shared-kernel/infrastructure/enums/error-code'

import type { ChatRepository } from '@/modules/chat/application/ports/chat.repository.port'
import type { Chat } from '@workspace/database'

@Injectable()
export class ChatService {
  constructor(
    @Inject(CHAT_REPOSITORY)
    private readonly chatRepository: ChatRepository,
  ) {}

  async listChats(userId: string): Promise<Chat[]> {
    return this.chatRepository.findByUserId(userId)
  }

  async getChat(id: string, userId: string): Promise<Chat> {
    const chat = await this.chatRepository.findById(id)
    if (!chat) throw new NotFoundException({ code: ErrorCode.CHAT_NOT_FOUND })
    if (chat.userId !== userId) throw new ForbiddenException({ code: ErrorCode.CHAT_FORBIDDEN })
    return chat
  }

  async createChat(userId: string, title?: string): Promise<Chat> {
    return this.chatRepository.create({
      userId,
      title: title ?? 'New Chat',
      visibility: 'private',
    })
  }

  async deleteChat(id: string, userId: string): Promise<void> {
    await this.getChat(id, userId)
    await this.chatRepository.delete(id)
  }
}
