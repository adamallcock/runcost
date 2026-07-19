---
title: Contributing Redaction-Safe Billing Fixtures
date: 2026-07-18
type: guide
status: complete
---

# Contributing Redaction-Safe Billing Fixtures

RunCost welcomes reproducible billing edge cases, not private provider payloads. Start with:

```bash
python3 scripts/create_external_fixture.py \
  --name external-my-edge-case \
  --output fixtures/external-my-edge-case.json
```

The command creates a synthetic fixture and immediately validates Python and JavaScript behavior; the repository Go fixture bridge validates it in the full suite.
The repository also runs `python3 scripts/check_external_fixture_workflow.py` to prove a freshly generated fixture passes all three language implementations without manual edits.

## Review checklist

- Remove API keys, authorization headers, cookies, account, project, organization, invoice, and payment identifiers.
- Replace request, response, trace, run, batch, and file IDs with obvious synthetic values.
- Remove prompts, completions, tool arguments/results, uploaded content, and private URLs.
- Use `example.invalid` for illustrative links.
- Retain only the smallest usage counters and pricing context needed to reproduce the billing behavior.
- Cite a public pricing or API contract when the case depends on provider behavior.
- Review the expected ledger independently; never copy a provider total in place of RunCost's calculation.
- Run `python3 scripts/run_conformance.py --fixture <path>` before opening a contribution.

Fixtures should describe RunCost's behavior. They must not claim that another calculator loses or preserves data unless that project has been tested with a documented, reproducible adapter and its maintainers can review the claim.
