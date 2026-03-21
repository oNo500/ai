import { index, json, pgTable, timestamp, uuid, varchar } from 'drizzle-orm/pg-core'

import { chatsTable } from './chat.schema'

export const chatMessagesTable = pgTable(
  'chat_messages',
  {
    id: uuid('id').primaryKey().notNull().defaultRandom(),
    chatId: uuid('chat_id')
      .notNull()
      .references(() => chatsTable.id, { onDelete: 'cascade' }),
    role: varchar('role', { enum: ['user', 'assistant', 'system'] }).notNull(),
    parts: json('parts').notNull().$type<unknown[]>(),
    attachments: json('attachments').notNull().default([]).$type<unknown[]>(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index('chat_messages_chat_id_idx').on(table.chatId),
    index('chat_messages_chat_id_created_at_idx').on(table.chatId, table.createdAt),
  ],
)

export type ChatMessage = typeof chatMessagesTable.$inferSelect
export type InsertChatMessage = typeof chatMessagesTable.$inferInsert
