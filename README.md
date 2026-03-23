## AI Platform

[![Node.js](https://img.shields.io/badge/node-22-brightgreen)](https://nodejs.org) [![pnpm](https://img.shields.io/badge/pnpm-10-orange)](https://pnpm.io) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

> AI-First full-stack monorepo — NestJS REST API, Next.js admin frontend, Python LangGraph agent service, shared Drizzle ORM database layer.

### Workspace

| Package | Path | Port | Description |
|---|---|---|---|
| `@workspace/api` | `apps/api` | :3000 | NestJS 11 REST API, DDD, Drizzle ORM, JWT + OAuth2 |
| `@workspace/admin` | `apps/admin` | :3001 | Next.js 16 admin frontend, Turbopack, shadcn/ui |
| `agentic` | `agentic/` | :8000 | Python FastAPI + LangGraph agent service |
| `@workspace/database` | `packages/database` | — | Drizzle ORM schema definitions & migrations |
| `@workspace/schema` | `packages/schema` | — | Auto-generated OpenAPI TypeScript types (never hand-write) |
| `@workspace/ui` | `packages/ui` | — | Shared React 19 component library, Radix + shadcn + Tailwind 4 |
| `@workspace/icons` | `packages/icons` | — | Shared SVG icon set |

### Quick Start

> PostgreSQL must be running before starting the API.

```bash
pnpm install
docker compose -f docker/docker-compose.yml up -d
pnpm dev
```

### Common Commands

```bash
pnpm build        # build all packages
pnpm typecheck    # TypeScript check across all packages
pnpm lint         # lint all packages
```

### Workflows

#### Update Database Schema

```bash
pnpm --filter @workspace/database db:push      # development (push schema directly)
pnpm --filter @workspace/database db:generate  # production (generate migration files)
```

#### Regenerate API Types

```bash
pnpm --filter @workspace/schema api:gen
```

> API types are auto-generated from the OpenAPI spec. Never hand-write types that duplicate API responses.

#### Python Agent Service

```bash
cd agentic
uv run uvicorn src.main:app --reload
uv run pytest
```
