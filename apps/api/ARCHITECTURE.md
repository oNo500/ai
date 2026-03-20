# API Architecture

NestJS 后端架构规范。本文档描述目录结构、分层职责、context 间通信规则，是所有架构决策的唯一依据。

> **术语约定**：`context`（限界上下文）= `modules/` 下的一个目录，是业务边界的基本单元。NestJS 的 `Module` 是实现载体，不是架构概念。

---

## 目录结构

```
src/
├── app/                          # 横切基础设施，无任何业务语义
│   ├── config/                   # 环境变量、Swagger、安全配置
│   ├── database/                 # DrizzleModule（框架驱动层）
│   ├── events/                   # DomainEventsModule（框架驱动层）
│   ├── filters/                  # 全局异常处理
│   ├── interceptors/             # 请求/响应处理
│   ├── middleware/               # HTTP 中间件
│   └── logger/                  # 日志配置
│
├── modules/                      # 按限界上下文划分，严格禁止互相 import
│   ├── auth/                     # 登录、会话、OAuth（含 JwtAuthGuard、RolesGuard）
│   ├── identity/                 # 用户身份共享子域（User 基础数据）
│   ├── cache/                    # Redis 缓存，@Global()
│   ├── audit-log/                # 审计日志，@Global()
│   ├── health/                   # 健康检查
│   ├── scheduled-tasks/          # 定时任务
│   └── {context}/               # 一个限界上下文 = 一个目录
│
└── shared-kernel/                # 跨 context 共享契约，只放接口和技术基类
    ├── domain/
    │   ├── base-aggregate-root.ts
    │   ├── events/               # 领域事件基类
    │   └── value-objects/        # 跨 context 的 Value Object（Money、Address 等）
    ├── application/
    │   └── ports/                # 跨 context 共享的 Port 接口
    │       ├── cache.port.ts
    │       ├── audit-logger.port.ts
    │       └── user.port.ts      # 共享子域接口
    └── infrastructure/
        ├── dtos/                 # 分页、通用响应 DTO
        ├── decorators/           # 通用装饰器
        ├── enums/                # 全局错误码
        └── types/                # 跨 context 的纯 TypeScript 类型
```

---

## 限界上下文划分规则

### 归入已有 context

同时满足以下全部条件：

1. **操作同一聚合根**：新功能的核心操作对象是该 context 已有的聚合根
2. **不引入新的领域概念**：不需要定义新的实体或值对象，或新概念完全从属于已有聚合根
3. **不扩大职责边界**：用一句话描述该 context 的职责，加入新功能后这句话不需要改变

三条必须全部满足，缺一则考虑新建。

### 新建 context

满足以下任一条件，必须新建：

1. **独立聚合根**：有自己的聚合根，生命周期不依附于任何已有聚合根
2. **职责边界扩大**：加入已有 context 后，该 context 的单一职责描述无法成立
3. **与已有 context 仅通过 ID 关联**：两者之间只传递 ID，不共享领域对象

### 边界模糊时的判断步骤

1. 写下目标 context 当前的职责描述（一句话）
2. 把新功能加进去，重新描述职责
3. 描述变长或出现"和"字连接两个不同概念 → 新建 context
4. 描述不变 → 归入已有 context

**示例**：
```
auth 当前职责：管理用户登录、会话和 OAuth 认证
加入"通知"后：管理用户登录、会话、OAuth 认证和消息通知  ← 出现"和"连接异质概念
结论：新建 notification context
```

---

## 各层职责边界

| 层 | 职责 | 禁止 |
|---|---|---|
| `app/` | 框架配置、横切处理 | 业务逻辑、import `modules/` |
| `presentation/` | 接收请求、参数校验、调用 Service、返回响应 | 业务逻辑、直接访问 DB |
| `application/services/` | 编排业务流程、调用 Port | 直接注入 DB 客户端 |
| `domain/` | 业务规则、状态转换、领域事件 | 依赖任何外部库 |
| `infrastructure/` | 实现 Port 接口、DB 查询 | 业务判断逻辑 |
| `shared-kernel/` | 跨 context 接口契约、技术基类 | 业务规则、运行时状态、实现类 |

---

## Context 内部分层

```
modules/{context}/
├── domain/                      # 仅复杂场景创建，零外部依赖
│   ├── aggregates/              # 聚合根
│   ├── entities/                # 实体
│   ├── value-objects/           # 值对象
│   ├── enums/                   # 枚举（as const 模式）
│   ├── events/                  # 领域事件
│   ├── services/                # 领域服务（纯业务逻辑）
│   └── factories/               # 工厂（可选）
├── application/
│   ├── ports/                   # 接口定义，如 {context}.repository.port.ts
│   ├── services/                # 默认单文件；>10 个方法按场景拆分
│   └── listeners/               # Domain Event / Integration Event 监听器
├── infrastructure/
│   ├── repositories/            # 实现 ports 接口
│   └── adapters/                # 外部系统适配器（第三方 API、消息队列等）
├── presentation/
│   ├── controllers/
│   └── dtos/
└── {context}.module.ts
```

简单场景用贫血模型（无 domain/ 层），复杂场景按需引入 DDD。

---

## Context 间通信规则

**Context 之间严禁互相 import，只有两种合法通信方式。**

### Port 契约（同步，需要返回值）

适用：一个 context 需要查询另一个 context 的数据。

```
接口定义在 shared-kernel/application/ports/
实现在拥有该能力的 context，@Global() 导出 token
消费方通过 @Inject(TOKEN) 注入，不 import 实现方
```

### Event 契约（异步，触发副作用）

适用：一个 context 的动作需要触发另一个 context 的响应。

```
事件类定义在发布方的 domain/events/
发布方 emit 事件，不知道谁消费
消费方在自己的 application/listeners/ 中 @OnEvent() 监听
```

### 决策规则

```
需要返回值（同步查询）    →  Port 契约
触发副作用（异步响应）    →  Event 契约
多个 context 强依赖同一概念  →  提取为共享子域（独立 context）
出现双向依赖             →  context 边界划错，先合并再重新拆分
```

---

## 共享子域

当一个业务概念被 ≥3 个 context 依赖时，它不属于任何单一 context，应提取为独立的共享子域。

**判断方法**：把拥有该概念的 context 删掉，其他 context 对这个概念的需求是否还存在？存在则说明该概念是共享子域。

**示例**：`User` 身份数据被 auth、order、analytics 等多个 context 使用，不属于 auth，应作为 `identity` context 独立存在。

---

## @Global() 使用边界

只有以下 context 可以使用 `@Global()`，其他 context 禁止使用：

| Context | Token | 理由 |
|---|---|---|
| `DrizzleModule` (app/) | `DB_TOKEN` | 所有 context 都需要 DB |
| `cache` | `CACHE_PORT` | 基础设施能力，多 context 使用 |
| `audit-log` | `AUDIT_LOGGER` | 横切关注点，所有写操作需要 |
| `DomainEventsModule` (app/) | — | 框架级事件系统 |

所有 `@Global()` 必须在 `AppModule` 中统一 import 一次。

Guard 的注册方式：实现在 `modules/auth/presentation/guards/`，通过 `APP_GUARD` token 在 `AppModule` 全局注册，其他 context 直接使用 `@UseGuards()` 装饰器，不 import auth。

```typescript
// app.module.ts
providers: [
  { provide: APP_GUARD, useClass: JwtAuthGuard },
  { provide: APP_GUARD, useClass: RolesGuard },
]
```

---

## shared-kernel 准入规则

放入 shared-kernel 的内容必须同时满足：

1. **Rule of Three**：≥3 个 context 使用，且使用方式完全相同
2. **零业务语义**：不含任何业务规则，不因 context 产生分支
3. **只放契约**：接口、基类、通用 DTO，禁止放实现类

---

## 测试规范

### 测试分层

| 层 | 测试类型 | 工具 |
|---|---|---|
| `application/services/`、`domain/` | 单元测试（`.spec.ts`） | Vitest + `@golevelup/ts-vitest` |
| `presentation/controllers/`、`infrastructure/repositories/` | E2E 测试（`.e2e-spec.ts`） | Vitest + Supertest + 真实 DB |

Controller 和 Repository 不写单元测试，E2E 是它们唯一的覆盖方式。`domain/` 对象不 mock，直接实例化。

### 文件位置

单元测试与源文件就近放置（`foo.ts` + `foo.spec.ts` 同目录）。E2E 测试统一放在 `src/__tests__/`。

### TDD

严格遵循 Red-Green-Refactor，禁止先写实现再补测试。测试从 `application/services/` 开始驱动，port 接口按需补充，实现跟着测试走。

### Mock

用 `createMock<T>()` mock port 接口。优先用 `new` 直接实例化 service，仅当依赖 NestJS DI（`ConfigService`、`JwtService` 等）时才使用 `Test.createTestingModule`。各 context 的 mock provider 数组统一维护在 `src/__tests__/unit/factories/mock-factory.ts`。

### Fixture

领域对象 fixture 统一维护在 `src/__tests__/unit/factories/domain-fixtures.ts`，通过聚合根工厂方法或 `reconstitute` 构造，不依赖 DTO 或数据库。

### E2E 隔离

E2E 测试数据通过 `globalThis.e2ePrefix`（时间戳前缀）隔离，防止并发 suite 间污染。

---

## 禁止行为

- 禁止 context 间直接 import
- 禁止 `app/` import `modules/`
- 禁止 Service 层直接注入数据库客户端（必须通过 Repository Port）
- 禁止 Controller 包含业务逻辑
- 禁止 `domain/` 层依赖外部库
- 禁止简单 CRUD 强行创建 `domain/` 层
- 禁止非基础设施 context 使用 `@Global()`
- 禁止 shared-kernel 放实现类
- 禁止 Service 超过 10 个方法不拆分
- 禁止先写实现再补测试（TDD NON-NEGOTIABLE）
- 禁止对 Controller 和 Repository 写单元测试（应由 E2E 覆盖）
- 禁止在测试中 mock `domain/` 层对象（直接实例化）
- 禁止任何 `eslint-disable`、`@ts-ignore`、类型断言绕过
- 导入路径必须使用 `@/*` 绝对路径别名
- 私有字段使用 `#` 语法，不使用 `_` 前缀
