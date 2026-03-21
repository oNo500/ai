import { ForbiddenException, NotFoundException } from '@nestjs/common'

import { createChatMocks } from '@/__tests__/unit/factories/mock-factory'
import { ChatService } from '@/modules/chat/application/services/chat.service'

import type { Chat } from '@workspace/database'

const CHAT: Chat = {
  id: 'chat-1',
  title: 'Test Chat',
  userId: 'user-1',
  visibility: 'private',
  createdAt: new Date(),
}

describe('chatService', () => {
  let service: ChatService
  let mocks: ReturnType<typeof createChatMocks>

  beforeEach(() => {
    mocks = createChatMocks()
    service = new ChatService(mocks.chatRepository)
  })

  describe('listChats', () => {
    it('returns chats for the given user', async () => {
      mocks.chatRepository.findByUserId.mockResolvedValue([CHAT])

      const result = await service.listChats('user-1')

      expect(result).toEqual([CHAT])
      expect(mocks.chatRepository.findByUserId).toHaveBeenCalledWith('user-1')
    })
  })

  describe('getChat', () => {
    it('not found → NotFoundException', async () => {
      mocks.chatRepository.findById.mockResolvedValue(null)

      await expect(service.getChat('chat-1', 'user-1')).rejects.toThrow(NotFoundException)
    })

    it('wrong user → ForbiddenException', async () => {
      mocks.chatRepository.findById.mockResolvedValue({ ...CHAT, userId: 'other-user' })

      await expect(service.getChat('chat-1', 'user-1')).rejects.toThrow(ForbiddenException)
    })

    it('success → returns chat', async () => {
      mocks.chatRepository.findById.mockResolvedValue(CHAT)

      const result = await service.getChat('chat-1', 'user-1')

      expect(result).toEqual(CHAT)
    })
  })

  describe('createChat', () => {
    it('creates chat with provided title', async () => {
      mocks.chatRepository.create.mockResolvedValue({ ...CHAT, title: 'My Chat' })

      const result = await service.createChat('user-1', 'My Chat')

      expect(result.title).toBe('My Chat')
      expect(mocks.chatRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({ userId: 'user-1', title: 'My Chat' }),
      )
    })

    it('uses default title when none provided', async () => {
      mocks.chatRepository.create.mockResolvedValue(CHAT)

      await service.createChat('user-1')

      expect(mocks.chatRepository.create).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'New Chat' }),
      )
    })
  })

  describe('deleteChat', () => {
    it('not found → NotFoundException', async () => {
      mocks.chatRepository.findById.mockResolvedValue(null)

      await expect(service.deleteChat('chat-1', 'user-1')).rejects.toThrow(NotFoundException)
    })

    it('wrong user → ForbiddenException', async () => {
      mocks.chatRepository.findById.mockResolvedValue({ ...CHAT, userId: 'other-user' })

      await expect(service.deleteChat('chat-1', 'user-1')).rejects.toThrow(ForbiddenException)
    })

    it('success → deletes chat', async () => {
      mocks.chatRepository.findById.mockResolvedValue(CHAT)
      mocks.chatRepository.delete.mockResolvedValue(true)

      await service.deleteChat('chat-1', 'user-1')

      expect(mocks.chatRepository.delete).toHaveBeenCalledWith('chat-1')
    })
  })
})
