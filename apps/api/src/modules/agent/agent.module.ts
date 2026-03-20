import { Module } from '@nestjs/common'

import { AgentController } from '@/modules/agent/presentation/controllers/agent.controller'

/**
 * Agent module
 *
 * Proxies requests to the Python agentic service and exposes
 * AG-UI and Vercel AI Stream compatible SSE endpoints.
 */
@Module({
  controllers: [AgentController],
})
export class AgentModule {}
