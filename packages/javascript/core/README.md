# RunCost

RunCost is a small, dependency-free cost ledger for LLM and agent API calls.

It turns provider SDK responses, framework usage objects, or normalized usage
ledgers into a componentized cost ledger: input, cached input, output,
reasoning, tool and feature units, discounts, price sources, and warnings.

```js
import { calculateCost, fromResponse } from "runcost";
```

The JavaScript package is part of the polyglot RunCost release train. Python,
JavaScript/TypeScript, and Go are validated against shared fixtures.

Full documentation, examples, schemas, and the release process live in the
GitHub repository:

<https://github.com/adamallcock/runcost>
