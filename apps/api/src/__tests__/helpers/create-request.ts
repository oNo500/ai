import request from 'supertest'

import type { INestApplication } from '@nestjs/common'
import type { Test as SuperTestType } from 'supertest'
import type TestAgent from 'supertest/lib/agent'

export function createRequest(app: INestApplication): TestAgent<SuperTestType> {
  return request(app.getHttpServer() as never)
}

export function createAuthRequest(app: INestApplication, token: string): TestAgent<SuperTestType> {
  return request.agent(app.getHttpServer() as never).set('Authorization', `Bearer ${token}`) as unknown as TestAgent<SuperTestType>
}
