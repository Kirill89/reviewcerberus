# Part 1: Action Testing Infrastructure

## Context

Local e2e integration test pipeline using `act` that validates the entire action
flow — real Docker, real Python CLI, just mocked external services (LLM + GitHub
API). Uses a temporary git repo with predictable content for stable,
reproducible test runs.

**Zero changes to action source code.** External mocks only.

## Architecture

```
Host machine (single process — tsx run.ts)
├── Mock Ollama server (:42000)     ← review Docker container talks to this
├── Mock GitHub API server (:43000)  ← action JS code talks to this
└── act (cwd = temp repo)
    └── job container (network="host", --bind)
        ├── actions/checkout (bind-mounted temp repo)
        ├── ./action (copied action.yml + dist/)
        │   ├── Octokit → http://<MOCK_HOST>:43000 (via GITHUB_API_URL)
        │   └── docker run kirill89/reviewcerberus:VERSION
        │       └── Python CLI → http://<MOCK_HOST>:42000 (via OLLAMA_BASE_URL)
        └── Output: review of app.py, comments "posted" to mock
```

`MOCK_HOST` is platform-aware: `host.docker.internal` on macOS, `172.17.0.1`
(docker bridge gateway) on Linux.

Everything lives in a self-contained `act-test/` folder at the repo root with
its own `package.json` and dependencies.

## Folder structure

```
act-test/
├── package.json          # deps: express, tsx, vitest, eslint, prettier, typescript
├── tsconfig.json
├── vitest.config.ts
├── eslint.config.js
├── .prettierrc
├── run.ts                # orchestrator (build, temp repo, mocks, act)
├── mock-servers.ts       # Express mock Ollama + GitHub API (imported by run.ts)
├── verify.test.ts        # vitest assertions on recorded requests
└── fixtures/
    ├── pull_request_event.json
    ├── test-file.py             # known file committed on feature branch
    └── workflow.yml.template    # act workflow template with {{MOCK_HOST}}/{{OLLAMA_PORT}} placeholders
```

## `run.ts` — orchestrator

TypeScript script run with `tsx`. Imports mock servers directly (no child
process).

01. **Build action**: `npm run build` in `action/`
02. **Build Docker image**: reads version from `pyproject.toml`, tags image
03. **Create temp git repo**:
    - `main` branch: `README.md` + `pyproject.toml` (copied from repo root)
    - `test-branch`: adds `app.py` (from `fixtures/test-file.py`)
    - `origin` = `.` (self) so `git fetch origin main:main` works
    - `action/` dir copied (not committed) — `action.yml` + `dist/`
04. **Generate workflow**: reads `fixtures/workflow.yml.template`, replaces
    `{{MOCK_HOST}}` and `{{OLLAMA_PORT}}`, writes to temp repo
05. **Delete stale `.mock-requests.json`**
06. **Start mock servers**: `await startMockServers()` — imported from
    `mock-servers.ts`, resolves when both servers are listening (no sleep
    needed)
07. **Run act** from temp repo dir with `--bind`, `--env GITHUB_API_URL=...`,
    `--env GITHUB_REPOSITORY=test-owner/test-repo`, `-P ubuntu-latest=...`
08. **Stop mock servers**: `await stopMockServers()` — graceful `server.close()`
09. **Clean up temp repo**: `rm -rf`
10. **Exit** with act's exit code (vitest runs separately via `npm test`)

## Mock servers (`mock-servers.ts`)

TypeScript + Express. Two servers in one module, imported directly by `run.ts`
(no separate process). Exports `startMockServers()`, `stopMockServers()`,
`OLLAMA_PORT`, and `GITHUB_PORT`.

**Ollama mock (:42000):**

- `POST /api/chat` → canned response with `message.tool_calls` (not
  `message.content`) — LangChain `create_agent` with `response_format` uses
  ToolStrategy (tool calling)
- Handles `stream: true` (ChatOllama default) with NDJSON format
- Body parser limit `5mb` (system prompts + diffs exceed Express default 100kb)

**GitHub API mock (:43000):**

- `GET /repos/:owner/:repo/issues/:number/comments` → `[]`
- `POST /repos/:owner/:repo/issues/:number/comments` → `201`
- `POST /repos/:owner/:repo/pulls/:number/reviews` → `200`
- `POST /repos/:owner/:repo/pulls/:number/comments` → `201`
- `POST /graphql` → `reviewThreads` → empty nodes, `resolveReviewThread` → ok
- Catch-all via `.use()` middleware (Express 5 removed wildcard `*` routes)

**Request recording:**

- Records every request to `.mock-requests.json` immediately after handling
  (flush on each request)

## Verification (`verify.test.ts`)

Vitest test that reads `.mock-requests.json` and asserts:

- `POST /api/chat` was called (Ollama)
- GraphQL `reviewThreads` query was called
- Summary comment was created (`POST /repos/.../issues/.../comments`)
- Review was created (`POST /repos/.../pulls/.../reviews`)

## Running

```bash
make test          # runs pytest + action tests + act integration test
```

The `test` Makefile target runs all tests in sequence: `poetry run pytest -v`,
`cd action && npm test`, `cd act-test && npm ci && npm test`. The act-test
`npm test` script runs `tsx run.ts && vitest run`.

## CI

Single unified workflow in `.github/workflows/ci.yml` with three jobs:

- **lint**: `make install` + `make lint` (Python + TypeScript
  linting/formatting)
- **test**: installs `act` via curl, then `make install` + `make test` (pytest +
  action vitest + act e2e) + checks `action/dist/` is up to date
- **check-version**: verifies version from `pyproject.toml` is not already on
  PyPI

## Files

| File | Purpose |
| -- | -- |
| `act-test/package.json` | Own deps + test/lint/format scripts |
| `act-test/tsconfig.json` | TypeScript config |
| `act-test/vitest.config.ts` | Vitest config |
| `act-test/eslint.config.js` | ESLint flat config |
| `act-test/.prettierrc` | Prettier config |
| `act-test/run.ts` | Orchestrator (build, temp repo, mocks, act) |
| `act-test/mock-servers.ts` | Mock Ollama + GitHub API (Express, imported by run.ts) |
| `act-test/verify.test.ts` | Verify recorded API requests |
| `act-test/fixtures/workflow.yml.template` | Act workflow template with placeholders |
| `act-test/fixtures/pull_request_event.json` | PR event payload |
| `act-test/fixtures/test-file.py` | Known diff content |

**No action source code changes.**

## Gotchas

1. **act ignores step/job-level `env` for actions** — use `--env` flag instead
2. **`GITHUB_REPOSITORY` must be passed via `--env`** — without it, act in a
   temp repo produces empty owner/repo in API URLs
3. **LangChain ToolStrategy** — mock must return `message.tool_calls`, not
   `message.content`
4. **ChatOllama streams by default** — mock must handle NDJSON
5. **Express 5** — wildcard `*` routes removed; use `.use()`
6. **Express body parser limit** — default 100kb too small for LLM requests
7. **Docker-in-Docker filesystem** — `act --bind` needed so review container and
   act container share the same host filesystem
8. **Platform-aware networking** — macOS Docker Desktop uses
   `host.docker.internal`, Linux uses docker bridge gateway `172.17.0.1`;
   `run.ts` detects `process.platform` to choose the right host
