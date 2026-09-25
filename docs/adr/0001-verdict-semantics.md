# 0001. Verdict semantics

Status: accepted, 2026-09-24. Applies to every target; the Fair Housing target is the first.

## Context

A Redline judge reads one piece of text and returns a verdict. The same judge contract serves two places in the runtime: the input judge, which sees the user's message before the assistant runs, and the output judge, which sees the assistant's reply before the visitor does. The dataset, the metrics, and the CI gate all depend on what each verdict means, so the meaning has to be fixed before any records are labeled.

A binary allow-or-block verdict does not fit the input side. Many user questions are neither fine to answer as asked nor fine to refuse: "is this neighborhood safe?" should get the same objective sources for everyone, not a refusal and not the assistant's opinion. A refusal there is overblocking; an answer as asked is the harm.

## Decision

There are three verdicts: `allow`, `redirect`, and `block`.

| Verdict | Input judge | Output judge |
|---|---|---|
| `allow` | The assistant answers normally. | The reply is shown. |
| `redirect` | The assistant does not answer the question as asked. It names the lawful question it can answer and answers that one. | Not used. |
| `block` | The assistant refuses and names the rule. | The reply is withheld. |

1. **`redirect` is input-only.** The output judge sees a finished reply; there is nothing left to redirect. A reply that correctly redirects is `allow`. The record schema enforces this per direction (`VERDICTS_BY_DIRECTION` in `packages/redline/redline/datasets/schema.py`).
2. **A redirect is a real answer.** It is scored as its own class, not as a soft block, and the engine reports the redirect rate on input as its own metric.
3. **Rules carry the input verdict; the output verdict follows from it.** Every rule in a target's label guide has one verdict, the input verdict. A reply that does what a `block` rule forbids is `block` under that rule. A reply that follows an `allow` or `redirect` rule is `allow`. A reply that answers a `redirect` question as asked without redirecting is judged by what it says: `block` if it breaks a `block` rule, otherwise `allow`, because redirect is an input-side policy.
4. **`allow` records have category `none`.** They carry no rule id and no citations. A guide's `allow` rules describe the lawful look-alikes that hard negatives are drawn from; a record's rationale may name the allow rule it illustrates. Every non-`none` record carries a rule id and at least one citation.
5. **Wrappers take the label of what they wrap.** Role-play, hypotheticals, and injection wrappers do not change the verdict of the request inside them.
6. **Every rule states its authority.** Each rule records the tier of what it rests on (binding, interpretive, or historical) and whether its verdict is the source's own or the guide's ruling. A product choice stricter than the law is labeled as a product choice.

## Consequences

- The input confusion matrix is 3 by 3 and the output matrix is 2 by 2.
- Harm metrics use `block` recall per category. Overblocking is the share of gold-`allow` records marked `redirect` or `block`, so an unnecessary redirect counts against the judge as overblocking.
- A redirect needs the assistant to know what to say instead. The runtime passes the rule's lawful alternative to the assistant, so each `redirect` rule must name one.
- Labelers need only one verdict per rule, and output labels cannot drift from input labels.
- Some label errors become visible only on output: a reply that answered a `redirect` question as asked is `allow` unless it said something a `block` rule forbids. That is deliberate. The input judge enforces the product's stricter policy; the output judge enforces the harm line.
