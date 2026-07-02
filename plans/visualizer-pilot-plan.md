# Visualizer Tool Pilot Plan

## Overview

A 2-week pilot with ~5 members of the AI advisory group to evaluate the Inline Visualizer tool in Dartmouth Chat. The goal is to understand utility, discover limitations, and identify considerations for broader rollout.

## Pilot Parameters

| Parameter | Value |
|-----------|-------|
| Duration | 2 weeks |
| Participants | ~5 AI advisory group members |
| Platform | Dartmouth Chat (already deployed) |
| Visualizer status | Already deployed and working |
| Exploration style | Open-ended |
| Feedback method | Survey + review of what participants built |

---

## Goals

1. **Usefulness** — Is the Visualizer tool valuable to the Dartmouth community? What types of tasks benefit most? What does it add that the Canvas feature doesn't cover?
2. **Limitations** — What breaks, confuses users, or produces poor results?
3. **Rollout considerations** — What documentation, training, settings, or guardrails are needed before wider availability?

---

## Pilot Design

### Phase 1: Kickoff (Day 1)

- [ ] Send participants a brief intro email/message covering:
  - What the Visualizer can do (inline SVG diagrams, Chart.js charts, interactive HTML widgets, conversational diagrams)
  - How to trigger it (ask the AI to "visualize", "chart", "diagram", "draw", "map out" something)
  - The one prerequisite setting: **iframe Sandbox Allow Same Origin** must be enabled in their Open WebUI Settings → Interface
  - Encouragement to try it across their real work — teaching, research, administrative, or personal projects
- [ ] Provide 3-5 starter prompts so participants can see what is possible immediately:
  1. "Visualize the structure of [a concept from their field]"
  2. "Create an interactive chart comparing X, Y, and Z"
  3. "Draw a flowchart for [a process they manage]"
  4. "Build a dashboard showing [some data they care about]"
  5. "Create an interactive explainer for [a topic they teach]"
- [ ] Confirm each participant can see visualizations rendering correctly (quick sanity check)

### Phase 2: Open Exploration (Days 2–12)

- Participants use the Visualizer in their normal DChat workflow — no constraints on what they try
- Encourage participants to:
  - Push boundaries (complex data, multi-step interactions, niche diagram types)
  - Note when things break or produce unexpected results
  - Save/screenshot visualizations they find particularly useful or particularly bad
  - Try the conversational aspect (clicking elements in a visualization to send follow-up prompts)
- Light-touch check-in at the end of Week 1 (brief message: "How is it going? Anything surprising?")

### Phase 3: Feedback Collection (Days 13–14)

- [ ] Send a structured survey (see below)
- [ ] Optionally: review participant chat histories (with permission) to see what they built and where things went wrong
- [ ] Hold a brief group debrief session (30 min) or 1-on-1 conversations

---

## Survey Design

### Section 1: Usage patterns

1. How many times did you use the Visualizer over the past two weeks? (rough estimate)
2. What types of visualizations did you create? (check all that apply)
   - Flowcharts / process diagrams
   - Data charts (bar, line, pie, etc.)
   - Concept maps / architecture diagrams
   - Interactive explainers
   - Dashboards with multiple components
   - Forms or interactive widgets
   - Other: ___
3. What was your most useful visualization? Describe the task and why it helped.

### Section 2: Quality and reliability

4. How often did the visualization render correctly on the first try? (Always / Usually / Sometimes / Rarely)
5. When things went wrong, what happened? (check all that apply)
   - Visualization did not appear at all
   - Layout was broken or unreadable
   - Data was incorrect or misleading
   - Interactive elements did not work
   - Dark/light mode looked wrong
   - Other: ___
6. Were you able to fix issues by reprompting? (Yes, easily / Sometimes / Rarely / No)

### Section 3: Value assessment

7. How useful is this tool for your work at Dartmouth? (1–5 scale)
8. Would you recommend this to colleagues? (Yes / Maybe / No)
9. What is the single best use case you discovered?
10. What is the biggest limitation you encountered?

### Section 4: Rollout readiness

11. How intuitive was the tool to use without training? (1–5 scale)
12. What documentation or guidance would you want before recommending this to others?
13. Are there any concerns about making this broadly available? (e.g., accessibility, misuse, confusion, performance)
14. Any other feedback?

---

## Known Considerations to Evaluate During Pilot

These are things we already know about and should specifically watch for:

### Technical

- **iframe setting requirement** — Users must enable "iframe Sandbox Allow Same Origin" in Settings → Interface. This is a friction point for rollout. How many participants struggle with this?
- **Script execution** — Visualizations can include `<script>` tags that run in the iframe. Security implications for broader rollout.
- **Streaming behavior** — Visualizations render token-by-token. Does this work well on slow connections or with large visualizations?
- **Browser compatibility** — Do visualizations render consistently across browsers participants use?

### Usability

- **Discoverability** — Do users naturally ask for visualizations, or do they need to be taught the trigger words?
- **Conversational diagrams** — The `sendPrompt()` bridge lets users click elements to send follow-up prompts. Do participants discover and use this?
- **Error recovery** — When a visualization fails, can users fix it by reprompting?

### Content and quality

- **Accuracy** — Are data visualizations accurate, or do they hallucinate data points?
- **Accessibility** — Do visualizations meet WCAG standards? Are they usable with screen readers?
- **Dartmouth branding** — The tool uses the Dartmouth color palette. Does this feel right?

### Policy and governance

- **Data sensitivity** — Are participants putting sensitive data into visualizations? What are the implications?
- **Content moderation** — Can the tool be used to generate inappropriate visual content?
- **Intellectual property** — Who owns visualizations created in DChat?

---

## Success Criteria

The pilot is successful if we can answer these questions:

1. ✅ What are the top 3 use cases where the Visualizer adds clear value?
2. ✅ What are the top 3 limitations or failure modes?
3. ✅ What is the minimum documentation/training needed for rollout?
4. ✅ Are there any blockers that must be resolved before wider availability?
5. ✅ What is the recommended rollout scope (e.g., all users, specific groups, opt-in)?

---

## Timeline

```
Week 1
  Day 1:  Kickoff — intro email, starter prompts, sanity check
  Day 5:  Mid-pilot check-in (async message)

Week 2
  Day 10: Reminder to wrap up exploration
  Day 13: Survey sent
  Day 14: Group debrief session
  Day 14+: Synthesize findings and write rollout recommendation
```

---

## Deliverables

1. **Pilot summary report** — Key findings organized by the four evaluation areas (usefulness, limitations, usability, policy)
2. **Rollout recommendation** — Go/no-go with conditions, suggested scope, and required preparation
3. **Documentation draft** — If rollout is recommended, a first draft of user-facing guidance
