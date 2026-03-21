import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger'
import { IsArray, IsOptional, IsString } from 'class-validator'

export class AgentInvokeDto {
  @ApiProperty()
  @IsString()
  threadId: string

  @ApiProperty()
  @IsString()
  runId: string

  @ApiPropertyOptional()
  @IsString()
  @IsOptional()
  parentRunId?: string

  @ApiPropertyOptional()
  @IsOptional()
  state?: unknown

  @ApiPropertyOptional({ type: [Object] })
  @IsArray()
  @IsOptional()
  messages?: unknown[]

  @ApiPropertyOptional({ type: [Object] })
  @IsArray()
  @IsOptional()
  tools?: unknown[]

  @ApiPropertyOptional({ type: [Object] })
  @IsArray()
  @IsOptional()
  context?: unknown[]

  @ApiPropertyOptional()
  @IsOptional()
  forwardedProps?: unknown
}
