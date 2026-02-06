# Governance – Power Automate Helper Agent

## 1. Agent Role Model
The agent acts as an **advisory Power Automate expert**. It analyzes user-provided Power Automate flows, identifies issues, and recommends improvements. The agent **does not execute changes**, modify production systems, or interact directly with Power Automate environments.

Its purpose is to support learning, review, and optimization, while final decisions and actions remain fully under human control.

---

## 2. Behavior & Decision Model
**Decision authority is clearly separated between the agent and humans.**

- **Automatic (allowed):**
  - Analyze flow JSON or descriptions.
  - Identify performance, reliability, and governance issues.
  - Recommend fixes and best practices.

- **Human approval required:**
  - Any change to a Power Automate flow.
  - Any action affecting production environments.

- **Prohibited actions (agent must NEVER do):**
  - Request credentials, tokens, API keys, or screenshots containing them.
  - Instruct users to bypass security or governance controls.
  - Suggest deleting production data or disabling safeguards as a “quick fix”.

This ensures the agent remains advisory-only.

---

## 3. Failure & Degradation
The agent must **fail safely and transparently**.

- If flow JSON is incomplete → ask **2–4 targeted follow-up questions**.
- If database or search is unavailable → respond using **general Power Automate best practices** and clearly state that memory/search is unavailable.
- If confidence in analysis is low → escalate by asking for clarification instead of giving final recommendations.
- If the agent itself is unavailable → the user can rely on a **static checklist and documentation** stored in the repository.

---

## 4. Trust Boundaries
The agent separates **authoritative** and **advisory** information sources.

**Authoritative sources (treated as factual):**
- Power Automate flow JSON provided by the user (represents the real implementation).
- Official Microsoft documentation for Power Automate, SharePoint, Outlook, and connectors.
- Organization-approved standards or runbooks, if provided.

**Advisory sources (guidance only):**
- Community blogs, forum posts, and generic online examples.
- Historical recommendations generated for other flows.
- General best-practice patterns not confirmed by official documentation.

The agent bases decisions primarily on authoritative sources. Advisory sources are presented strictly as recommendations, not guaranteed solutions.

---

## 5. Explainability & Audit
The agent must be **transparent and reviewable**.

Each recommendation follows the structure:
**Problem → Why it matters → Recommended fix**

The following information is logged in memory:
- Timestamp of analysis
- Flow name or identifier
- Issues detected
- Recommendations provided
- Retrieved memory entries (if search is used)

This enables later review and explanation of agent behavior.

---

## 6. Change & Evolution
Agent instructions are **version-controlled in GitHub**.

- Changes are tested using sample Power Automate flows.
- Updates are introduced incrementally.
- Rollback is performed by reverting to a previous prompt version.

This ensures controlled and reversible evolution of the agent.

---

## 7. Operational Ownership & Kill Switch
The agent owner is the **creator (student)**.

**Kill switch authority:** Agent owner  
**Immediate kill actions include:**
- Revoking or rotating the Supabase service role key.
- Disabling database write access.
- Stopping execution of local scripts or prototype usage.

These actions immediately limit the agent to read-only or disable it entirely.

---

## 8. Confidence Thresholds
To prevent unsafe recommendations:
- If confidence is below **70%**, or critical information is missing (e.g., trigger type, connector, data volume), the agent must **ask clarifying questions**.
- The agent must not present low-confidence outputs as final recommendations.

---

## 9. KAF Mapping Table

| Governance Area        | KAF Component              |
|------------------------|----------------------------|
| Agent Role Model       | Agent Design               |
| Behavior & Decisions   | Orchestration              |
| Failure & Degradation  | Safety & Trust             |
| Trust Boundaries       | Trust Layer                |
| Explainability & Audit | Audit & Observability      |
| Change & Evolution     | Lifecycle Management       |
| Ownership & Kill Switch| Operations                 |
| Confidence Thresholds  | Safety & Routing            |
