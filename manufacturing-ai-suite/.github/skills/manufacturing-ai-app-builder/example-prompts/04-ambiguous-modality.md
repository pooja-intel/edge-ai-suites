# Ambiguous modality — clarify before routing

**User (business objective):**
> I want to catch problems early on my production line before they become
> expensive failures.

**Orchestrator (Step 1 — clarify before routing):**
The objective doesn't say what feeds the decision, so ask a **business**
disambiguation (still no technology):
1. What kind of "problem" are you trying to catch — something you'd **see**
   (a visual defect, a misaligned part, a leak), something you'd **measure**
   (unusual vibration, pressure, temperature, power draw), or **both together**
   (e.g. a camera confirms what a sensor already flagged)?
2. Do you already have a camera pointed at the process, sensors wired up, or
   neither yet?
3. Quick demo, or a single-host Docker Compose solution?

**Discovery (Step 2):** route on the answer using
[`../references/SKILL_CATALOG.md`](../references/SKILL_CATALOG.md):
- visual-only defect → **`metro-ai-app-recipe`**
- measurement-only anomaly → **`manufacturing-app-recipe`** (`{{DEPLOYMENT}}=ts`)
  (or `time-series-analytics-user` if no dashboard/scaffold is wanted)
- both, correlated into one verdict → **`manufacturing-app-recipe`** (`{{DEPLOYMENT}}=multimodal`, or `vllm`/`agentic` for a narrative explanation)

If still unclear after question 1, present **two** candidate plans (e.g.
vision-only vs the full multimodal stack) and let the user pick, rather than
guessing which modality matters more.

**Plan (Step 4):** once the branch is chosen, propose the concrete
deliverable + skill + inferred technology and **wait for confirmation**
before building.

**Key behavior:** never guess "multimodal" just because both a camera and a
sensor exist somewhere in the process — only route to
`manufacturing-app-recipe`'s `multimodal`/`vllm`/`agentic` modes when the user
confirms both signals must combine into **one** decision. Clarify the
business intent first, route deterministically, then confirm.
