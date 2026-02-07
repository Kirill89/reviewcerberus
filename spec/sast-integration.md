# Plan: Add Experimental OpenGrep SAST Integration

## Context

ReviewCerberus currently reviews code using only an LLM agent. Adding a SAST
pre-scan via [OpenGrep](https://github.com/opengrep/opengrep) (a Semgrep fork)
can provide the LLM with concrete security signals to verify or dismiss. This is
experimental, disabled by default, and enabled only with `--sast`.

**Key design decisions:**

- SAST runs **before** the agent as a pre-processing step
- Findings go into the **user message** (alongside diffs/commits)
- SAST skepticism guidance is appended to the **system prompt** — the original
  `full_review.md` is never modified
- Works naturally with `--verify` — SAST data flows through `user_message` and
  `system_prompt` which verification already receives (see
  `src/agent/verification/runner.py:20-27`)
- SAST errors are **fatal** — if `--sast` was requested and fails, the run fails
  (user explicitly opted in, they should know it's broken)

______________________________________________________________________

## Step 0: Validate OpenGrep CLI Assumptions ✅ DONE

Validated with opengrep 1.16.0 on macOS arm64:

1. **`--baseline-commit main`** — accepts branch names directly (uses
   `git cat-file -e` internally). No need for `git merge-base`. Only reports
   findings introduced by the current branch. ✅

2. **JSON output structure** — confirmed field names:

   - `results[].check_id` — rule ID (e.g.,
     `python.lang.security.audit.eval-detected.eval-detected`)
   - `results[].path` — file path
   - `results[].start.line`, `results[].end.line` — line range
   - `results[].extra.message` — description
   - `results[].extra.severity` — `"WARNING"`, `"ERROR"`, or `"INFO"`
   - `results[].extra.lines` — matched source code
   - Drop: `extra.metadata`, `extra.fingerprint`, `extra.metavars`,
     `extra.is_ignored`, `extra.validation_state`, `extra.engine_kind`
   - Drop top-level: `version`, `errors`, `paths`, `interfile_languages_used`,
     `skipped_rules`

3. **Exit codes** — ⚠️ different from semgrep convention:

   - **0** = success (with or without findings — findings don't change exit
     code)
   - **non-zero** (2, 123, 124, 125) = error
   - `--error` flag makes it exit 1 on findings, but we don't use it
   - This means we **can** use `check=True` in subprocess — non-zero always
     means a real error

4. **`--config auto`** — downloads ~1064 community rules from Semgrep Registry.
   Rules cached between runs. Second run ~4s. ✅

5. **Fallback** — not needed, `--baseline-commit` works with branch names. ✅

6. **Binary distribution** — all platforms are standalone binaries (no
   tarballs):

   - `opengrep_manylinux_x86` (Linux x86_64)
   - `opengrep_manylinux_aarch64` (Linux aarch64)
   - `opengrep_osx_x86` (macOS x86_64)
   - `opengrep_osx_arm64` (macOS arm64)

______________________________________________________________________

## Step 1: Create SAST Module — Installer

**New files:** `src/agent/sast/__init__.py`, `src/agent/sast/installer.py`

The `__init__.py` re-exports the public API (follow the pattern in
`src/agent/verification/__init__.py`).

The installer downloads the opengrep binary on demand with a pinned version:

- **Pinned version** as a constant (e.g., `OPENGREP_VERSION = "1.16.0"`)
- **Cache path:** `~/.cache/reviewcerberus/opengrep-v{VERSION}/opengrep`
- **Platform detection** via `platform.system()` + `platform.machine()` to pick
  the right binary from GitHub releases. All platforms are standalone binaries
  (no extraction needed):
  - `opengrep_manylinux_x86` (Linux x86_64)
  - `opengrep_manylinux_aarch64` (Linux aarch64)
  - `opengrep_osx_x86` (macOS x86_64)
  - `opengrep_osx_arm64` (macOS arm64)
- **Download URL:**
  `https://github.com/opengrep/opengrep/releases/download/v{VERSION}/{binary_name}`
- **Download method:** `urllib.request.urlretrieve` (stdlib, no extra deps)

The main function `ensure_opengrep_binary() -> str` checks these in order:

1. `OPENGREP_BINARY_PATH` env var (manual override)
2. Cached binary at the cache path (version-pinned, no system lookup to avoid
   version mismatch)
3. Download from GitHub releases

Include an `if __name__ == "__main__"` block so the Dockerfile can reuse the
same logic: `RUN python -m src.agent.sast.installer`.

**Verify:** Run `poetry run python -m src.agent.sast.installer` twice — first
downloads, second finds cached binary.

______________________________________________________________________

## Step 2: Create SAST Module — Scanner

**New file:** `src/agent/sast/scanner.py`

No need for a detailed dataclass or structured parsing — the output goes
straight to the LLM, which can understand any format. The goal is just to **keep
it short** for token efficiency.

One public function:

- `run_sast_scan(repo_path, target_branch) -> str | None` — the public entry
  point. Gets the binary via `ensure_opengrep_binary()`, passes `target_branch`
  directly to `--baseline-commit` (same approach as `get_file_diff.py:29` which
  passes `{target_branch}...HEAD` to git without computing merge-base). Runs
  `[binary, "scan", "--config", "auto", "--json", "--baseline-commit", target_branch, "."]`
  with `cwd=repo_path`. Use **`check=True`** — opengrep returns 0 even when
  findings exist (unlike git grep). Non-zero always means a real error.

  After getting JSON output, strip it down to only the fields the LLM needs and
  drop everything else. Fields to keep per finding (validated in Step 0):
  `check_id`, `path`, `start.line`, `end.line`, `extra.message`,
  `extra.severity`, `extra.lines`. Drop: `extra.metadata`, `extra.fingerprint`,
  `extra.metavars`, `extra.is_ignored`, `extra.validation_state`,
  `extra.engine_kind`. Drop top-level: `version`, `errors`, `paths`,
  `interfile_languages_used`, `skipped_rules`.

  Also return the finding count separately (or print it directly) for the
  progress display.

**Verify:** Call on a repo with a known vulnerability on a feature branch.
Confirm only new findings appear.

______________________________________________________________________

## Step 3: Add SAST Prompt Guidance

**New file:** `src/agent/prompts/sast_guidance.md`

This file is appended to the system prompt when `--sast` is used. The original
`full_review.md` stays untouched. Content should cover two themes:

1. **Be VERY skeptical of SAST findings** — verify independently, don't blindly
   report, explain reasoning, dismiss false positives silently

2. **Go beyond SAST** — focus on what SAST cannot detect: logic errors, race
   conditions, design problems, context-dependent security, side effects. SAST
   findings are supplementary hints, not the focus.

______________________________________________________________________

## Step 4: Wire SAST into Existing Code

Thread the SAST data through 5 existing files. Each gets one new optional
parameter — no existing behavior changes.

### 4a. `src/agent/formatting/build_review_context.py`

Add `sast_findings: str | None = None` param. If present, append it as an
additional section after the existing Commits/Changed Files/Diffs sections.

### 4b. `src/agent/prompts/__init__.py`

Add `include_sast_guidance: bool = False` param to `build_review_system_prompt`.
When true, load and append `sast_guidance.md` **before** additional_instructions
(so user instructions have final say). Follow the existing pattern at line
44-49.

### 4c. `src/agent/agent.py`

Add `include_sast_guidance: bool = False` param to `create_review_agent`. Pass
through to `build_review_system_prompt` (line 32).

### 4d. `src/agent/runner.py`

Add `sast_findings: str | None = None` param to `run_review`. Pass to
`build_review_context` (line 52) and derive `include_sast_guidance` from
`sast_findings is not None` for both `build_review_system_prompt` (line 55) and
`create_review_agent` (line 58-61).

### 4e. `src/main.py`

Add `--sast` flag in `parse_arguments()` (follow `--verify` pattern at line
41-45). In `main()`, after `print_changed_files_summary()` (line 133) and before
`run_review()` (line 148):

- **Lazy import** the sast module (avoids loading installer logic for normal
  runs)
- Call `run_sast_scan(repo_path, args.target_branch)` — returns trimmed string
  or `None`
- Print finding count: `🔍 SAST: Found N potential issues` or `No findings`
- Pass result directly as `sast_findings` to `run_review()`

**`--verify` compatibility:** No changes needed to the verification pipeline.
`review_result.user_message` and `review_result.system_prompt` already carry
SAST data through — see `src/main.py:161-167` where they're passed to
`run_verification()`.

**Verify:** Run `poetry run reviewcerberus --sast --target-branch main` and
confirm SAST findings appear in the review. Test `--sast --verify` too.

______________________________________________________________________

## Step 5: Write Tests

**New files:** `tests/agent/sast/__init__.py`, `test_scanner.py`,
`test_installer.py`

**Scanner tests** — test JSON trimming logic with sample opengrep output. Test
`run_sast_scan()` error paths with mocked `ensure_opengrep_binary` and
`subprocess.run` (follow mocking pattern from
`tests/agent/verification/test_runner.py`).

**Installer tests** — test platform detection logic, lookup order (mock
`shutil.which`, `Path.is_file`, env vars).

Run `make test` and `make lint` to verify.

______________________________________________________________________

## Step 6: Update GitHub Action

Thread the `--sast` flag through 4 action files (follow the existing `--verify`
pattern exactly):

- **`action/action.yml`** — add `sast` input with default `"false"` (alongside
  `verify` at line 57-59)
- **`action/src/config.ts`** — add `sast: boolean` to `ActionInputs` (line
  90-95), read via `core.getInput("sast") === "true"` in `getActionInputs()`
  (line 100-125)
- **`action/src/review.ts`** — add `sast: boolean` to `ReviewConfig` (line
  9-15), push `"--sast"` to Docker args when true (after `--verify` at line 71)
- **`action/src/index.ts`** — pass `sast: inputs.sast` in config object (line
  47-53)

Rebuild with `cd action && npm run build` and commit `dist/index.js`.

______________________________________________________________________

## Step 7: Update Dockerfile

Pre-install opengrep to avoid download on every container run. Add after
`COPY src ./src` and before `useradd`:

1. Set `PYTHONPATH` and `PATH` early (currently at lines 39-40, need to move up
   or duplicate) so the installer module can run
2. `RUN python -m src.agent.sast.installer`
3. Copy the downloaded binary to `/usr/local/bin/opengrep` so
   `shutil.which("opengrep")` finds it regardless of which user runs the
   container

This way the runtime `ensure_opengrep_binary()` hits lookup step 2
(`shutil.which`) and never downloads.

______________________________________________________________________

## Step 8: Update Documentation

### `README.md`

- Add `--sast` to CLI usage examples (after `--verify` at line 101)
- Add "SAST Integration (Experimental)" subsection in "What's Included" (after
  Verification Mode at line 143)
- Add `sast` row to GitHub Action inputs table (around line 280)
- Add action example with `sast: "true"` (after verification example at line
  300\)

### `DOCKERHUB.md`

- Add `--sast` to Command-Line Options (after `--verify` at line 118)

### `spec/project-description.md`

- Add SAST bullet to Core Features section

### `spec/implementation-summary.md`

- Add "14. SAST Integration (Experimental)" section covering design,
  architecture, binary management, prompt approach, error handling
- Update project structure tree to include `sast/` module

______________________________________________________________________

## Files Summary

### New files (7)

| File | Purpose |
| -- | -- |
| `src/agent/sast/__init__.py` | Module exports |
| `src/agent/sast/installer.py` | Binary download, caching, platform detection |
| `src/agent/sast/scanner.py` | Run opengrep, trim JSON output for LLM |
| `src/agent/prompts/sast_guidance.md` | Skepticism + go-beyond-SAST guidance |
| `tests/agent/sast/__init__.py` | Test package |
| `tests/agent/sast/test_scanner.py` | Test JSON trimming, error handling |
| `tests/agent/sast/test_installer.py` | Test platform detection, lookup order |

### Modified files (11)

| File | Change |
| -- | -- |
| `src/main.py` | Add `--sast` flag, SAST orchestration block |
| `src/agent/runner.py` | Add `sast_findings` param |
| `src/agent/agent.py` | Add `include_sast_guidance` param |
| `src/agent/formatting/build_review_context.py` | Append SAST section |
| `src/agent/prompts/__init__.py` | Load SAST guidance when enabled |
| `Dockerfile` | Pre-install opengrep, move ENV up |
| `action/action.yml` | Add `sast` input |
| `action/src/config.ts` | Add `sast` to ActionInputs |
| `action/src/review.ts` | Add `sast` to ReviewConfig, pass `--sast` flag |
| `action/src/index.ts` | Wire `sast` through config |
| `README.md` | Document SAST feature |

### Also update (docs)

| File | Change |
| -- | -- |
| `DOCKERHUB.md` | Add `--sast` to CLI options |
| `spec/project-description.md` | Add SAST to Core Features |
| `spec/implementation-summary.md` | Add section 14, update structure tree |

______________________________________________________________________

## Edge Cases & Error Handling

| Scenario | Behavior |
| -- | -- |
| opengrep download fails | Fatal error, run aborts |
| opengrep crashes (exit code != 0) | Fatal error, run aborts (`check=True`) |
| no findings | Print "No findings", review runs normally |
| JSON trimming fails | Fatal error, run aborts |
| `--sast` with `--verify` | Works — SAST data flows through automatically |
| `--sast` with `--instructions` | Both work — instructions appended after SAST guidance |
| `--sast` with `--json` | Works — SAST doesn't change output schema |
| no `--sast` flag | Zero impact — SAST module never imported |
| unsupported platform | Fatal error, run aborts |

______________________________________________________________________

## Verification Plan

1. **Step 0**: Manually test opengrep CLI assumptions
2. **Per-step**: Each step has its own verify checkpoint
3. **Unit tests**: `make test` passes
4. **Lint**: `make lint` passes (mypy, isort, black)
5. **Integration**: `poetry run reviewcerberus --sast --target-branch main`
6. **Combined flags**: `poetry run reviewcerberus --sast --verify`
7. **Action build**: `cd action && npm test && npm run build`
8. **Docker**: Build image, run with `--sast`, confirm opengrep pre-installed
