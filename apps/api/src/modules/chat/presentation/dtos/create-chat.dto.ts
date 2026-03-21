import { ApiPropertyOptional } from '@nestjs/swagger'
import { IsIn, IsOptional, IsString } from 'class-validator'

export class CreateChatDto {
  @ApiPropertyOptional({ example: 'My first chat' })
  @IsString()
  @IsOptional()
  title?: string

  @ApiPropertyOptional({ enum: ['private', 'public'], default: 'private' })
  @IsIn(['private', 'public'])
  @IsOptional()
  visibility?: 'private' | 'public'
}
