---
title: RunCost Integration Case Study Template
date: 2026-07-18
type: guide
status: active
---

# RunCost Integration Case Study Template

Use this template for a public, sanitized integration story. A useful case study
shows what was reconciled and what remained uncertain; it is not a testimonial
request.

## Integration summary

- Project or pseudonymous workload:
- Language and framework:
- Provider surfaces:
- RunCost version and catalog version:
- Evaluation date:
- Maintainer/reviewer:

## Problem before RunCost

Describe the exact failure mode: hand-written formulas, cached/reasoning usage
being dropped, batch failures disappearing, a provider/dashboard disagreement,
or uncertainty about historical/service-tier prices.

## Minimal integration

Include the smallest sanitized code snippet and name the RunCost entrypoint.
State whether prices came from the external resolver, a pinned upstream adapter,
or user-owned cards.

## Evidence

| Measure | Before | RunCost | Provider/export truth | Residual |
| --- | ---: | ---: | ---: | ---: |
| Calls or batch items |  |  |  |  |
| Input/cache/output/tool units |  |  |  |  |
| Total cost |  |  |  |  |

Attach or link only sanitized fixtures. Remove prompts, outputs, credentials,
account/project IDs, invoice IDs, request IDs, and any customer or tenant data.

## What changed

- Billing dimensions recovered:
- Warnings that prevented false confidence:
- Time saved or formula/code removed:
- Operational decision enabled:

## Limitations

List unpriced components, tolerated residuals, source age, estimation rather
than invoice truth, and any provider fields that were unavailable. Do not claim
invoice accuracy from fixtures alone.

## Reproduction

Provide the public fixture or generator command and the exact check command,
for example:

```bash
python3 scripts/create_external_fixture.py --help
python3 scripts/run_conformance.py path/to/sanitized-fixture.json
```

## Publication approval

- [ ] Payload and metadata were reviewed for secrets and private content.
- [ ] All metrics can be reproduced from the attached sanitized evidence.
- [ ] Provider and upstream source links are current as of the evaluation date.
- [ ] Limitations are adjacent to the corresponding claims.
- [ ] The project owner approved naming; otherwise the case remains anonymous.
