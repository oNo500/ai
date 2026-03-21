import { ApiProperty } from '@nestjs/swagger'
import { IsNotEmpty, IsString } from 'class-validator'

export class StreamMessageDto {
  @ApiProperty({ example: 'What is the weather today?' })
  @IsString()
  @IsNotEmpty()
  message: string
}
