import { relations } from 'drizzle-orm'

import {
  usersTable,
  accountsTable,
  sessionsTable,
  chatsTable,
  chatMessagesTable,
  messageEvalsTable,
} from './schemas'

/**
 * Users table relations
 */
export const usersRelations = relations(usersTable, ({ many }) => ({
  // 1:N with accounts
  accounts: many(accountsTable),
  // 1:N with sessions
  sessions: many(sessionsTable),
}))

/**
 * Accounts table relations
 */
export const accountsRelations = relations(accountsTable, ({ one }) => ({
  user: one(usersTable, {
    fields: [accountsTable.userId],
    references: [usersTable.id],
  }),
}))

/**
 * Sessions table relations
 */
export const sessionsRelations = relations(sessionsTable, ({ one }) => ({
  user: one(usersTable, {
    fields: [sessionsTable.userId],
    references: [usersTable.id],
  }),
}))

/**
 * Chats table relations
 */
export const chatsRelations = relations(chatsTable, ({ one, many }) => ({
  user: one(usersTable, {
    fields: [chatsTable.userId],
    references: [usersTable.id],
  }),
  messages: many(chatMessagesTable),
}))

/**
 * Chat messages table relations
 */
export const chatMessagesRelations = relations(chatMessagesTable, ({ one }) => ({
  chat: one(chatsTable, {
    fields: [chatMessagesTable.chatId],
    references: [chatsTable.id],
  }),
  eval: one(messageEvalsTable, {
    fields: [chatMessagesTable.id],
    references: [messageEvalsTable.messageId],
  }),
}))

/**
 * Message evals table relations
 */
export const messageEvalsRelations = relations(messageEvalsTable, ({ one }) => ({
  message: one(chatMessagesTable, {
    fields: [messageEvalsTable.messageId],
    references: [chatMessagesTable.id],
  }),
}))

/**
 * Users table — extend with chats relation
 */
export const usersChatsRelations = relations(usersTable, ({ many }) => ({
  chats: many(chatsTable),
}))
