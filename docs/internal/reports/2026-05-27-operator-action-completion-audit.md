---
title: Operator Action Completion Audit
date: 2026-05-27
type: report
status: final
---

# Operator Action Completion Audit

This audit records the remaining completion gates after the repo-side
Milestone 8, publication-readiness, and public-beta hardening work. The current
goal allows the work to be considered complete when the remaining steps require
operator action such as credentials, registry settings, or explicit publish
approval.

## Verified Local Evidence

Validated in this workspace:

- `npm test`
- `npm run check:packages`
- `npm run check:release`
- `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json`
- `git diff --check`
- `python3 -m py_compile scripts/check_go_fixtures.py scripts/check_public_api_registry.py scripts/check_python_type_surface.py scripts/generate_contract_docs.py scripts/check_generated_contract_docs.py scripts/check_project_hygiene.py`

Live evidence captured:

- `fixtures/source-files/alpha-smoke-live-direct-2026-05-27.json`
- `docs/internal/reports/2026-05-27-alpha-smoke-live-direct.md`

The live direct run passed:

- `anthropic_prompt_caching`
- `openrouter_cost_compare`
- `multi_provider_discount`

Public beta hardening evidence now exists for:

- generated schema docs;
- generated caveats;
- generated public API registry;
- source-data update process;
- contribution docs;
- support matrix;
- warnings and limitations;
- dependency-light publishing story.

## Remaining Gates

These strict checks intentionally still fail because they require external
operator action:

```bash
python3 scripts/check_project_completion_gates.py --require-milestone8
python3 scripts/check_project_completion_gates.py --require-public-beta
```

Remaining gate classification:

| Gate | Status | Why this is operator-action |
|---|---|---|
| `milestone8_live_smoke_openai_responses` | pending external evidence | `OPENAI_API_KEY` is not available under checked Keychain service names or environment variables. |
| `milestone8_live_smoke_vercel_streaming` | pending external evidence | Requires `OPENAI_API_KEY` plus optional Node packages `ai` and `@ai-sdk/openai`; the key and packages are not available in the current operator environment. |
| `milestone8_live_smoke_langchain_agent` | pending external evidence | Requires `OPENAI_API_KEY` plus optional Python packages `langchain_openai` and `langchain_core`; the key and packages are not available in the current operator environment. |
| `milestone8_product_truth_loop` | partial | The loop exists and passed for the current reviewed smoke evidence; completing it for all scenarios depends on the missing OpenAI, Vercel, LangChain, and invoice evidence. |
| `milestone8_invoice_dashboard_real_comparison` | pending external evidence | Requires an operator-provided real provider dashboard, invoice, usage export, or OpenAI Costs Admin API access plus matching RunCost ledger input. |
| `milestone9_pypi_trusted_publishing` | pending external evidence | Requires registry-side PyPI project/trusted-publisher configuration for `runcost-ai`. |
| `milestone9_npm_trusted_publishing` | pending external evidence | Requires registry-side npm package/trusted-publisher configuration for `runcost`. |
| `milestone9_actual_registry_publish` | deferred by user | The goal explicitly says to leave packages unpublished for now. |

## Keychain And Dependency Check

Checked Keychain service names:

- `OPENAI_API_KEY`
- `openai_api_key`
- `codex-openai-api-key`
- `codex_openai_api_key`
- `openai-platform-api-key`
- `OPENAI_ADMIN_KEY`

None were available through `security find-generic-password -s <service> -w`.

Optional framework packages checked:

- Node: `ai`, `@ai-sdk/openai`
- Python: `langchain_openai`, `langchain_core`

None were installed in the current workspace environment.

## Completion Position

All repo-side harnesses, contracts, docs, generated artifacts, package checks,
release-readiness checks, and locally available live evidence have been
completed. The remaining strict gate failures require operator credentials,
operator registry setup, operator-provided billing evidence, or explicit
operator approval to publish.
