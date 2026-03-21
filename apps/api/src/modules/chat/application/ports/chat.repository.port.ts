import type { Chat, InsertChat } from '@workspace/database'

export interface ChatRepository {
  findById(id: string): Promise<Chat | null>
  findByUserId(userId: string): Promise<Chat[]>
  create(data: Omit<InsertChat, 'id' | 'createdAt'>): Promise<Chat>
  update(id: string, data: Partial<Pick<InsertChat, 'title' | 'visibility'>>): Promise<Chat | null>
  delete(id: string): Promise<boolean>
}

export const CHAT_REPOSITORY = Symbol('CHAT_REPOSITORY')
