import { integer, pgTable, timestamp, unique, uuid } from 'drizzle-orm/pg-core'

import { chatMessagesTable } from './chat-message.schema'

export const messageEvalsTable = pgTable(
  'message_evals',
  {
    id: uuid('id').primaryKey().notNull().defaultRandom(),
    messageId: uuid('message_id')
      .notNull()
      .references(() => chatMessagesTable.id, { onDelete: 'cascade' }),
    score: integer('score').notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true })
      .notNull()
      .defaultNow()
      .$onUpdate(() => new Date()),
  },
  (table) => [unique('message_evals_message_id_unique').on(table.messageId)],
)

export type MessageEval = typeof messageEvalsTable.$inferSelect
export type InsertMessageEval = typeof messageEvalsTable.$inferInsert
