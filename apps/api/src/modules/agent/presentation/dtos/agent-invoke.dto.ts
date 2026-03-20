import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger'
import { IsOptional, IsString } from 'class-validator'

export class AgentInvokeDto {
  @ApiProperty({ example: 'What is the current time?' })
  @IsString()
  message: string

  @ApiPropertyOptional({ example: 'session-123' })
  @IsString()
  @IsOptional()
  sessionId?: string

  @ApiPropertyOptional({ example: 'user-42' })
  @IsString()
  @IsOptional()
  userId?: string
}
