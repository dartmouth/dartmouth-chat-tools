# Visualizer Tool — Pilot Onboarding Guide

Welcome to the Dartmouth Chat Visualizer pilot! This guide will get you up and running in a few minutes.

---

## What Is the Visualizer?

The Visualizer is a tool built into Dartmouth Chat (DChat) that lets the AI render **interactive, visual content directly in the chat window**. Instead of just describing something in text, the AI can draw it for you — live, as it generates the response.

Things the Visualizer can create include:

- **Diagrams** — flowcharts, process maps, org charts, concept maps, architecture diagrams
- **Data charts** — bar charts, line charts, pie charts, scatter plots (powered by Chart.js)
- **Interactive widgets** — sliders, dropdowns, calculators, decision trees you can click through
- **Dashboards** — multi-panel layouts combining charts, stats, and tables
- **Interactive explainers** — step-by-step walkthroughs of a concept with clickable elements
- **Forms and tools** — quick input forms, converters, or planning templates

All visualizations automatically use the Dartmouth color palette and adapt to your light/dark mode setting.

---

## Prerequisite: Enable the iframe Setting

Before the Visualizer can render anything, you need to flip **one setting** in DChat:

1. Open **Dartmouth Chat** → [chat-preprod.dartmouth.edu](https://chat-preprod.dartmouth.edu)
2. Click your **profile icon** (bottom-left corner)
3. Select **Settings**
4. Go to the **Interface** tab
5. Find **"iframe Sandbox Allow Same Origin"** and **turn it ON** (toggle it so it is enabled)
6. Close the settings panel

> **Why is this needed?** The Visualizer renders content inside an iframe. This setting allows the iframe to communicate with the chat — which is what makes interactive features (like clicking an element to send a follow-up prompt) work. Without it, visualizations will not appear.

If you skip this step, you will see an empty box where the visualization should be.

---

## How to Trigger the Visualizer

You do not need any special syntax or commands. Just **ask the AI to visualize something** in natural language. The AI will recognize your intent and use the Visualizer tool automatically.

### Trigger phrases that work well

- "Visualize the structure of …"
- "Draw a flowchart for …"
- "Create a chart comparing …"
- "Map out the process for …"
- "Build a dashboard showing …"
- "Diagram the relationship between …"
- "Make an interactive explainer for …"

### What happens behind the scenes

1. The AI loads its design-system instructions (color palette, layout rules, etc.)
2. The AI mounts an empty visualization frame in the chat
3. The AI streams the HTML/SVG content into the frame — you see it paint live, token by token
4. The finished visualization is fully interactive right in the chat

---

## Starter Prompts to Try

Here are five prompts to get you started. Copy-paste any of them into DChat to see the Visualizer in action:

1. **Concept diagram**
   > "Visualize the structure of [a key concept from your field] as an interactive diagram"

2. **Comparison chart**
   > "Create an interactive chart comparing [X, Y, and Z] across [these dimensions]"

3. **Process flowchart**
   > "Draw a flowchart for [a process you manage or teach]"

4. **Dashboard**
   > "Build a dashboard showing [some data or metrics you care about]"

5. **Interactive explainer**
   > "Create an interactive explainer for [a topic you teach or present on]"

Feel free to use your own real-world tasks — the more specific you are, the better the result.

---

## Interactive Features

Visualizations are not just static images. They can be fully interactive:

- **Clickable elements** — some diagrams include nodes or buttons you can click. Clicking may send a follow-up prompt to the AI, letting you drill deeper into a topic without typing.
- **Hover effects** — elements may highlight or show tooltips on hover.
- **Form inputs** — sliders, dropdowns, checkboxes, and text fields can appear inside visualizations for calculators, filters, or decision tools.
- **State persistence** — some visualizations save your selections so they persist if you scroll away and come back.

---

## Data Analysis + Visualization: Using Code Execution

We are particularly interested in pairing the Visualizer with the **Code Execution** tool for data analysis tasks.

### The problem with raw data

If you upload a spreadsheet or paste a large dataset and ask the AI to "visualize this data," the AI has to embed all of that data directly into the visualization HTML. This means:

- The AI may truncate, round, or hallucinate numbers to fit everything in
- Large datasets produce enormous visualizations that are slow to stream
- Any calculations (averages, trends, aggregations) are done by the AI "in its head" rather than computed precisely

### The better approach: let Code Execution crunch the numbers

DChat also has a **Code Execution** tool that runs Python code in a sandboxed environment. When both tools are available, the AI can:

1. **Run Python code first** to read your uploaded file, perform calculations, compute aggregations, and extract just the numbers needed
2. **Then visualize only the results** — a clean chart with precise, computed values rather than a massive data dump

This is faster, more accurate, and produces cleaner visualizations.

### How to trigger this workflow

Enable the Code Execution tool in addition to the Visualization tool. When you upload a file and ask for a visualization, the AI should automatically use Code Execution to process the data before visualizing. But you can nudge it by being explicit:

> "Analyze the data in my spreadsheet and visualize the key trends"

> "Run the numbers on this CSV and create a chart showing the top 10 categories by revenue"

> "Calculate monthly averages from this dataset and chart them over time"

### What you need

- **Code Execution** must be enabled for your account (it is enabled by default)
- **Upload your file** by attaching it to the chat — uploaded files are accessible to the Code Execution tool at `/mnt/uploads/`
- Note that you should *not* toggle the Entire Document vs Focused Retrieval setting in the uploaded file settings. If you don't know what that is, don't worry about it. This doesn't need your input, the default should work.
- The AI can work with CSV, Excel, JSON, and other common data formats using Python libraries like pandas

### Example workflow

1. You attach `enrollment_data.csv` to the chat
2. You type: "Analyze this enrollment data and visualize trends by department over the last 5 years"
3. The AI runs Python code to read the CSV, group by department, compute yearly totals
4. The AI creates a clean line chart with the computed values

---

## Tips for Getting Good Results

- **Be specific.** "Visualize the admissions funnel from inquiry to enrollment with drop-off percentages" works better than "make a chart."
- **Iterate.** If the first result is not quite right, tell the AI what to change — "make the boxes bigger", "add a legend", "switch to a horizontal layout." It will regenerate.
- **Provide data.** If you want a data chart, give the AI actual numbers or paste in a table. Otherwise it will estimate or use placeholder data.
- **Try different types.** The same information can often be shown as a flowchart, a table, a chart, or an interactive widget. Experiment to find what works best.
- **Push the boundaries.** This is a pilot — we want to learn what works and what breaks. Try complex requests and see what happens.

---

## Known Limitations

- **One visualization per response.** The AI generates one visualization at a time. If you need multiple, ask for them in separate messages.
- **Streaming rendering.** You will see the visualization build progressively as the AI generates it. Occasionally the partially-rendered state may look odd before it finishes.
- **No external data fetching.** For security, visualizations cannot make network requests (no loading external APIs or images from the web). All data must be included directly.
- **Browser compatibility.** Visualizations work best in modern browsers (Chrome, Firefox, Safari, Edge). If something looks off, try a different browser.
- **Complex visualizations may need iteration.** Very intricate diagrams or large datasets may not render perfectly on the first try. Reprompting usually fixes issues.

---

## What to Keep Track Of

At the end of the pilot, we will send a short survey about your experience. To make it easier to answer when the time comes, we recommend keeping a light mental (or written) tally of the following as you go:

### Usage

- **Roughly how many times** you used the Visualizer over the two weeks — an approximate count is fine
- **What types of visualizations** you created — flowcharts, data charts, concept maps, interactive explainers, dashboards, forms/widgets, or something else

### Quality

- **How often things worked on the first try** — did the visualization render correctly right away, or did you usually need to reprompt?
- **What went wrong when it didn't work** — visualization didn't appear, layout was broken, data was wrong, interactive elements didn't respond, dark/light mode looked off, etc.
- **Whether reprompting fixed the issue** — could you recover by telling the AI what to fix?

### Standout moments

- **Your single most useful visualization** — what was the task and why did the visualization help? Consider saving a screenshot.
- **Your biggest frustration** — what limitation or failure was most annoying?
- **Anything that surprised you** — a use case you didn't expect to work but did, or something that should have been easy but wasn't

### Rollout readiness

- **How intuitive it felt without training** — could you figure it out from this guide alone, or did you need extra help?
- **What documentation or guidance you'd want** before recommending this to a colleague
- **Any concerns** about making this broadly available — accessibility, confusion, performance, misuse, etc.

> **Tip:** You don't need to keep detailed logs. Just noting a few highlights and pain points as they happen will make the end-of-pilot survey much easier to fill out.

---

## Reporting Feedback

During the pilot, we would love to hear about your experience:

- **What worked well?** — Save or screenshot visualizations you found particularly useful
- **What broke?** — Note when things did not render, looked wrong, or behaved unexpectedly
- **What was missing?** — Tell us about visualization types you wanted but could not get

A feedback survey will be sent at the end of the pilot period. In the meantime, feel free to share observations as you go.

---

## Quick Reference

| Item | Details |
|------|---------|
| **Platform** | [chat-preprod.dartmouth.edu](https://chat-preprod.dartmouth.edu) |
| **Required setting** | Settings → Interface → iframe Sandbox Allow Same Origin → **ON** |
| **How to trigger** | Ask the AI to "visualize", "chart", "diagram", "draw", or "map out" something |
| **Theme support** | Automatic — adapts to your light/dark mode preference |
| **Interactive?** | Yes — click, hover, and use form elements directly in the visualization |
| **Data security** | Visualizations run locally in your browser; no data is sent to external servers |

---

*Questions? Reach out to Simon. Happy visualizing!*
