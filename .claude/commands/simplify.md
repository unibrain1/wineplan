---
description: Review recently modified code for clarity, reuse, and standards alignment without changing behavior
---

# Simplify

Review the recently modified code for opportunities to simplify, improve clarity, reduce redundancy,
and align with project coding standards — without changing any behavior. Focus only on files changed
in the current session unless instructed otherwise.

Use the Agent tool with `subagent_type: "code-simplifier:code-simplifier"` to perform the review
and apply refinements. The `code-simplifier` agent comes from an installed plugin and is not defined
locally in `.claude/agents/` — if it is unavailable, fall back to the generic `Agent` tool with a
prompt that asks for the same review.
