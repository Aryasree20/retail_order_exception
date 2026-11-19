# Evaluation report

## Scope
Implemented against the supplied Group 2 assignment and its four local data files.

## Automated checks
- Deterministic date-window computation: inclusive day 30; day 31 excluded.
- Supplied acceptance scenarios: C001, C002, C004, C007.
- Edge cases: unknown order, missing policy, contradictory delivery/customer claim, amount mismatch.
- Safety: no mutation of order/payment or inventory files; all recommendations require human approval.
- Schema: invalid recommendation enum is rejected by Pydantic.

Run `pytest -q` from the project root to reproduce. Record the actual terminal output in the submission/demo rather than claiming a result from an unrun environment.

## Limitations
The offline AutoGen review is a transparent deterministic specialist simulation, not a model-generated group chat. The optional AgentChat mode provides the real multi-agent team when a supported model endpoint and credentials are configured. The source data is fictional and no real customer/payment systems are connected.
