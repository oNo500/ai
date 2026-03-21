import { index, pgTable, text, timestamp, uuid, varchar } from 'drizzle-orm/pg-core'

import { usersTable } from '../identity/users.schema'

export const chatsTable = pgTable(
  'chats',
  {
    id: uuid('id').primaryKey().notNull().defaultRandom(),
    title: text('title').notNull(),
    userId: text('user_id')
      .notNull()
      .references(() => usersTable.id, { onDelete: 'cascade' }),
    visibility: varchar('visibility', { enum: ['public', 'private'] })
      .notNull()
      .default('private'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index('chats_user_id_idx').on(table.userId)],
)

export type Chat = typeof chatsTable.$inferSelect
export type InsertChat = typeof chatsTable.$inferInsert
