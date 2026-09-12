#	Chain	Stage	What it does
1	Intent Decomposition	Confirm	Converts user's natural-language idea into a structured agent specification
2	System Prompt Generation	Forge	Creates the agent's production system prompt
3	Tool Schema Generation	Forge	Determines what tools the agent needs and creates their schemas
4	Guardrail Generation	Forge	Creates safety/security rules and probes
5	Few-Shot Example Generation	Forge	Creates example conversations to guide agent behavior
6	Attack Generation	Red Team	Generates adversarial attacks
7	Attack Execution	Red Team	Sends those attacks against the target agent
8	Attack Judgment	Red Team	Determines whether each attack succeeded
9	Guardrail Patcher	Harden	Repairs the agent based on failures
10	Ground-Truth Evaluation	Verify	Tests factual/task accuracy against known answers
11	Consistency Evaluation	Verify	Checks whether the agent behaves consistently
12	Goal-Completion & Alignment	Verify	Checks whether the agent actually accomplishes its intended job
13	Policy & Builder-Policy Generation	Shield	Creates operational policies, boundaries and abuse controls
14	Test-Set & Probe Generation	Support	Creates independent evaluation cases and guardrail probes