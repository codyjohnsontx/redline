# Redline

A public AI-safety lab: LLM-as-a-judge guardrails, an evaluation harness that measures them, and a playground where anyone can try to break them.

Redline guards three assistants with one shared evaluation engine:

- A Fair Housing real-estate assistant, judged against HUD's published guidance.
- Race Engineer, the motorsport setup assistant in Track Tuner.
- Attend, a dealership service inbox that drafts SMS replies.

Every guardrail is measured, not asserted: labeled datasets with train, validation, and test splits, per-category precision, recall, and F1, confusion matrices, overblocking replay, and a CI gate that fails when safety regresses.

Work in progress. The first slice is being planned now.

## License

Code is MIT licensed. See [LICENSE](LICENSE).
