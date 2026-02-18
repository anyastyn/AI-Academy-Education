# Policy-as-Code — Runtime Rules for This Agent
This document lists the safety and governance rules that are **enforced at runtime** (not just written in docs).

The goal is simple:
- If a risky situation happens → the agent must behave safely
- The event must be logged for audit

---

## Rule Map (Rule → Code → Logging)

| Rule ID | Risk it prevents | IF (trigger) | THEN (system behavior) | Code location | What gets logged (Supabase) |
|---|---|---|---|---|---|
| R1_SECRET_INPUT | Secret leakage | Input contains token/password/API key | Refuse to process. Ask user to redact. Do not echo secret. | `run_agent_memory_demo.py` → `contains_secret()` | `messages.metadata.secret_detected=true`, `event_type="secret_detected"` |
| R2_PROMPT_INJECTION | Prompt injection / jailbreak | User tries “ignore instructions”, “reveal prompt”, “dump all docs/chunks” | Refuse. Explain you can answer normal governance/flow questions. | `run_agent_memory_demo.py` → (your injection check function) | `event_type="prompt_injection_attempt"` |
| R3_OUT_OF_SCOPE | Wrong use / policy guessing | Question is not about Power Automate + governance (connectors/DLP/environments/flow review) | Refuse politely + explain supported topics | `run_agent_memory_demo.py` → (your scope check function) | `event_type="out_of_scope"` |
| R4_LOW_CONFIDENCE_ABSTAIN | Hallucination | Retrieval is weak (top_score below threshold) OR docs don’t contain the answer | Say: “I cannot find this in the available documents.” Ask 1–2 clarifying Qs or suggest adding docs. | `run_agent_memory_demo.py` → retrieval scoring / threshold | `event_type="low_confidence_abstain"`, plus `top_score` |
| R5_DOC_DUMP_PREVENTION | Data exfiltration | User asks to reconstruct full documents (“paragraph 1…2…3…”) | Refuse. Offer summary instead. | `run_agent_memory_demo.py` → (same injection/exfil check) | `event_type="doc_exfiltration_attempt"` |

---

## Notes (simple explanations)

### Why “Policy-as-Code” matters
Because clients will ask:
> “How do we know the agent won’t leak secrets or invent policy?”

This is your answer:
- Rules are written in docs (this file)
- Rules are enforced in code (runtime)
- Every rule triggers a log entry (audit trail)

### Where logs live
All rule events are stored as **rows in** `public.messages` with structured metadata:
- `event_type` (what happened)
- `mode` (Q&A vs FLOW_REVIEW)
- optional scores (`top_score`)
- flags like `secret_detected=true`

### What humans still must do
The agent never deploys or changes flows. Humans review and apply changes in DEV first.
