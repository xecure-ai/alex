## Part 6 Code Review (Steps 1–2 complete)

### Scope reviewed
- `backend/tagger/` (`agent.py`, `lambda_handler.py`, `templates.py`, `test_local.py`, `test_lambda.py`, `package_docker.py`, `pyproject.toml`)
- `backend/planner/` orchestrator scaffold (`lambda_handler.py`, `templates.py`, `test_local.py`, `pyproject.toml`)
- Terraform for Part 6: `terraform/lambda_part6.tf`
- Shared DB package interfaces used by agents (`backend/database/src/*.py`)

### What’s working well
- **Idiomatic Agents SDK usage**: `Agent`, `Runner`, `trace`, and `LitellmModel` are used as in the gameplan, with structured outputs for the tagger.
- **Validation-first approach**: Pydantic models ensure allocations sum to 100 and conform to schema; conversion to DB shape strips zero values.
- **Separation of concerns**: Prompt/instructions in `templates.py`; business logic in `agent.py`; Lambda glue in `lambda_handler.py`.
- **Packaging for Lambda**: Docker-based packaging avoids binary incompatibility; installs the shared DB package as editable.
- **Local and deployed tests**: Useful smoke tests for local run and deployed Lambda invocation.

### Issues and risks (prioritized)
1) Terraform handler mismatch blocks deployment
   - In `terraform/lambda_part6.tf` the handler is `lambda_handler_simple.lambda_handler` but the file is `lambda_handler.py`.
   - Impact: Terraform-created function won’t start (Handler not found).

2) Schema mismatch: tagger sector keys vs DB schema
   - Tagger uses sector keys `government` and `corporate` in `SectorAllocation`; DB `SectorType` allows `treasury`, `corporate`, `mortgage`, `government_related`, etc. (`government` is not allowed).
   - Impact: `InstrumentCreate` validation will fail when writing to DB.

3) Region naming inconsistency
   - Tagger uses `global_market`; DB expects `global`. You map it during conversion, which is okay, but templates still instruct `global_market`.
   - Impact: Extra mapping surface; align names to reduce drift.

4) Tagger Lambda timeout likely too low
   - Current timeout is 60s. Bedrock + DB updates across multiple instruments can exceed this.
   - Impact: Timeouts under realistic load.

5) Lambda invoke result handling
   - `planner/lambda_handler.py` `invoke_lambda_agent` returns the raw invoke payload, and `invoke_tagger` returns `json.dumps(result)` without unwrapping `body`.
   - Impact: Callers receive nested `{statusCode, body}` rather than the actual result, making downstream use awkward.

6) Mutable default in Pydantic models (planner)
   - `AccountInfo.positions: List[PositionInfo] = []` uses a mutable default.
   - Impact: Shared state bugs across instances.

7) Packaging command flags
   - Inside the Lambda base image, `pip --platform manylinux2014_x86_64` is unnecessary and sometimes problematic without `--implementation/--python-version`.
   - Impact: Potential pip resolution quirks; complexity with little benefit since we’re already in the correct container.

8) IAM scoping (will matter as more agents land)
   - Policies in `lambda_part6.tf` are broad (`Resource = "*"` for Bedrock/RDS Data). Acceptable for bring-up; should be narrowed.

9) Concurrency for tagging
   - `tag_instruments` classifies sequentially.
   - Impact: Slower throughput on batches; easy win via `asyncio.gather`.

10) Deployment ergonomics
   - Terraform references a zip that may not exist yet; `source_code_hash` uses a ternary, but `filename` is still required.
   - Impact: First `terraform apply` can fail if packaging wasn’t run; needs clearer workflow or a guard.

### Recommended actions
- [ ] Fix Terraform handler for tagger
  - File: `terraform/lambda_part6.tf`
  - Change handler to `lambda_handler.lambda_handler`.

- [ ] Align tagger sectors with DB schema
  - File: `backend/tagger/agent.py`
  - Update `SectorAllocation` field names to match `backend/database/src/schemas.py::SectorType` (e.g., use `treasury`, `corporate`, `mortgage`, `government_related`; remove `government`).
  - File: `backend/tagger/templates.py`
  - Update sector list in the prompt to the same names.
  - File: `backend/tagger/agent.py`
  - Update `classification_to_db_format` mapping to those exact keys.
  - Add/adjust a unit test to ensure `classification_to_db_format` produces an `InstrumentCreate` that passes validation and can be written via `db.instruments.create_instrument`.

- [ ] Normalize region key to `global`
  - Prefer renaming the field in `RegionAllocation` to `global` and update the prompt accordingly; remove the special-case mapping.

- [ ] Increase tagger Lambda timeout
  - File: `terraform/lambda_part6.tf`
  - Set `timeout = 180` and consider `memory_size = 1024` if needed for faster cold starts.

- [ ] Unwrap Lambda invoke responses in planner
  - File: `backend/planner/lambda_handler.py`
  - In `invoke_lambda_agent`, if response payload contains `body`, return `json.loads(payload['body'])`; otherwise return payload directly.
  - Have `invoke_tagger/invoke_reporter/invoke_charter/invoke_retirement` return the unwrapped dicts (not stringified JSON) and let the agent decide how to present/log them.

- [ ] Fix mutable default in Pydantic model
  - File: `backend/planner/lambda_handler.py`
  - Change `positions: List[PositionInfo] = []` to `positions: List[PositionInfo] = Field(default_factory=list)`.

- [ ] Simplify packaging flags
  - File: `backend/tagger/package_docker.py`
  - Remove `--platform manylinux2014_x86_64` from pip since we’re already inside the Lambda base image; keep `--only-binary=:all:` if needed; or drop both for simplicity.

- [ ] Concurrency for classification
  - File: `backend/tagger/agent.py`
  - Implement `asyncio.gather` over `classify_instrument` calls in `tag_instruments` with bounded concurrency (e.g., semaphore of 4–8) to reduce latency for batches.

- [ ] Tighten IAM when stabilizing
  - File: `terraform/lambda_part6.tf`
  - Scope Bedrock permissions to the specific model ARN; RDS Data to the cluster ARN; S3 to the specific bucket ARN(s).

- [ ] Developer workflow guardrails
  - Docs: Add a short note to `guides/6_agents.md` (or `README`) explaining: run `uv run package_docker.py` before `terraform apply` so the zip exists; or switch to Terraform `external`/`null_resource` to build before deploy.

### Minor nits
- Consistent default model: unify `BEDROCK_MODEL_ID` defaults across planner/tagger with a single value from gameplan, but keep it env-driven.
- Logging: prefer structured JSON logs for Lambdas; include key fields (agent, symbol count, job_id).
- Tests: Add one small test that validates the planner’s `invoke_lambda_agent` unwrapping logic on a mocked payload containing `statusCode`/`body`.

### Overall assessment
Solid foundation. The tagger is close to production-ready once the sector/region schema alignment is fixed and the Terraform handler is corrected. Planner scaffolding aligns with the architecture and should integrate smoothly as additional agents land. Address the above items to reduce deployment friction and prevent validation/runtime errors.


