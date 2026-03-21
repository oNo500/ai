import { Inject, Injectable } from '@nestjs/common'
import { chatsTable } from '@workspace/database'
import { desc, eq } from 'drizzle-orm'

import { DB_TOKEN } from '@/app/database/db.port'

import type { DrizzleDb } from '@/app/database/db.port'
import type { ChatRepository } from '@/modules/chat/application/ports/chat.repository.port'
import type { Chat, InsertChat } from '@workspace/database'

@Injectable()
export class ChatRepositoryImpl implements ChatRepository {
  constructor(@Inject(DB_TOKEN) private readonly db: DrizzleDb) {}

  async findById(id: string): Promise<Chat | null> {
    const [chat] = await this.db.select().from(chatsTable).where(eq(chatsTable.id, id))
    return chat ?? null
  }

  async findByUserId(userId: string): Promise<Chat[]> {
    return this.db
      .select()
      .from(chatsTable)
      .where(eq(chatsTable.userId, userId))
      .orderBy(desc(chatsTable.createdAt))
  }

  async create(data: Omit<InsertChat, 'id' | 'createdAt'>): Promise<Chat> {
    const [chat] = await this.db.insert(chatsTable).values(data).returning()
    if (!chat) throw new Error('Failed to create chat')
    return chat
  }

  async update(
    id: string,
    data: Partial<Pick<InsertChat, 'title' | 'visibility'>>,
  ): Promise<Chat | null> {
    const [chat] = await this.db
      .update(chatsTable)
      .set(data)
      .where(eq(chatsTable.id, id))
      .returning()
    return chat ?? null
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.db.delete(chatsTable).where(eq(chatsTable.id, id)).returning()
    return result.length > 0
  }
}
