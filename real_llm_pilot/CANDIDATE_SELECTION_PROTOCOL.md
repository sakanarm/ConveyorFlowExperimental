# MFEC Candidate Selection and Stopping Rule

## Objective

Select at most three final agents with empirically different workload-specific
ability profiles before any ConveyorFlow allocation-policy run is executed.
Model name, release number, price, latency, and token usage do not assign rank.

## Evidence observed before the stopping rule

- Gemini 3/3.5/3.8 Flash: homogeneous L3/L3 control candidates.
- Cross-family screen: GLM 5.3 Flash L3/L3; GPT-5 mini L2/L3; Claude Sonnet 5
  L2/L3.
- Minimax M2 extension: L3/L3.

## Final extension and stopping rule

Screen exactly one further candidate, `tencent-hy3`, on the same 30 probes and
unchanged rank gates. If it yields L1 on at least one workload, consider the
three-member team `tencent-hy3`, `gpt-5-mini`, and `glm-5.3-flash`. Otherwise,
stop model search and use the two-rank heterogeneous profile available from
`gpt-5-mini` and `glm-5.3-flash`, with a third predeclared duplicate or
resource-complementary L3 agent as required by the team-composition cell.

Do not screen additional MFEC aliases after `tencent-hy3` merely to obtain a
desired ordinal pattern. The absence of an L1 model is a design limitation to
report, not a result to optimize away.
