import { Inject, Injectable } from '@nestjs/common'
import { chatMessagesTable } from '@workspace/database'
import { asc, eq } from 'drizzle-orm'

import { DB_TOKEN } from '@/app/database/db.port'

import type { DrizzleDb } from '@/app/database/db.port'
import type { ChatMessageRepository } from '@/modules/chat/application/ports/chat-message.repository.port'
import type { ChatMessage, InsertChatMessage } from '@workspace/database'

@Injectable()
export class ChatMessageRepositoryImpl implements ChatMessageRepository {
  constructor(@Inject(DB_TOKEN) private readonly db: DrizzleDb) {}

  async findByChatId(chatId: string): Promise<ChatMessage[]> {
    return this.db
      .select()
      .from(chatMessagesTable)
      .where(eq(chatMessagesTable.chatId, chatId))
      .orderBy(asc(chatMessagesTable.createdAt))
  }

  async create(data: Omit<InsertChatMessage, 'id' | 'createdAt'>): Promise<ChatMessage> {
    const [message] = await this.db.insert(chatMessagesTable).values(data).returning()
    if (!message) throw new Error('Failed to create chat message')
    return message
  }
}
