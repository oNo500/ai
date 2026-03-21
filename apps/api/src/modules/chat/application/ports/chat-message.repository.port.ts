import type { ChatMessage, InsertChatMessage } from '@workspace/database'

export interface ChatMessageRepository {
  findByChatId(chatId: string): Promise<ChatMessage[]>
  create(data: Omit<InsertChatMessage, 'id' | 'createdAt'>): Promise<ChatMessage>
}

export const CHAT_MESSAGE_REPOSITORY = Symbol('CHAT_MESSAGE_REPOSITORY')
