import { Module } from '@nestjs/common'

import { CHAT_MESSAGE_REPOSITORY } from '@/modules/chat/application/ports/chat-message.repository.port'
import { CHAT_REPOSITORY } from '@/modules/chat/application/ports/chat.repository.port'
import { ChatMessageService } from '@/modules/chat/application/services/chat-message.service'
import { ChatService } from '@/modules/chat/application/services/chat.service'
import { ChatMessageRepositoryImpl } from '@/modules/chat/infrastructure/repositories/chat-message.repository'
import { ChatRepositoryImpl } from '@/modules/chat/infrastructure/repositories/chat.repository'
import { ChatStreamController } from '@/modules/chat/presentation/controllers/chat-stream.controller'
import { ChatController } from '@/modules/chat/presentation/controllers/chat.controller'

@Module({
  controllers: [ChatController, ChatStreamController],
  providers: [
    ChatService,
    ChatMessageService,
    { provide: CHAT_REPOSITORY, useClass: ChatRepositoryImpl },
    { provide: CHAT_MESSAGE_REPOSITORY, useClass: ChatMessageRepositoryImpl },
  ],
})
export class ChatModule {}
