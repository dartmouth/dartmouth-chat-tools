# Automations Pilot — Participant Guide

Welcome to the Automations pilot! You are one of the first people at Dartmouth to try out Automations, a new feature in Dartmouth Chat that lets you schedule recurring AI prompts that run automatically on a schedule.

This guide covers what you need to know and what we are asking you to pay attention to during the two-week pilot.

---

## What Are Automations?

Automations let you set up an AI prompt that runs on a schedule — daily, weekly, monthly, or custom. Each time the automation runs, it creates a real chat conversation you can browse and search like any other chat.

Think of it as a personal AI assistant that does a task for you on a recurring basis, without you having to remember to ask.

### What You Can Do

| Capability | Details |
|---|---|
| **Schedule prompts** | Set up daily, weekly, monthly, or custom recurrence |
| **Use any model** | Pick any model you have access to |
| **Use template variables** | Insert `{{CURRENT_DATE}}`, `{{CURRENT_TIME}}`, `{{CURRENT_DATETIME}}`, `{{USER_NAME}}` into your prompt |
| **View run history** | See every past execution with status and a link to the resulting chat |
| **See runs on Calendar** | Active automations appear as events on the Calendar view |
| **Test immediately** | Use "Run Now" to test without waiting for the schedule |
| **Pause and resume** | Toggle automations on/off without deleting them |

---

## Getting Started

### Find Automations

1. Open the **left sidebar** in Dartmouth Chat
2. Click the **Automations** icon (clock with circular arrows) at the top of the sidebar

### Create Your First Automation

1. Click the **+ Create Automation** button
2. Fill in:
   - **Title** — a short name for your automation (e.g., "Daily AI Briefing")
   - **Prompt** — the instruction to send to the AI each time it runs
   - **Model** — which AI model to use (see [Choosing a Model](#choosing-a-model) below)
   - **Schedule** — when and how often it should run
3. Click **Save**
4. Your automation is now active and will run at the next scheduled time

### Test It

After creating an automation, click **Run Now** to execute it immediately. This lets you verify the prompt and model produce useful output before waiting for the schedule.

### View Results

Each automation run creates a chat. You can find it in:
- The automation's **run history** (click the automation to see past runs)
- Your regular **chat list** in the sidebar
- The **Calendar** view (automations appear as events)

### Pause or Delete

- **Pause:** Toggle the automation off — it stays saved but will not run until you re-enable it
- **Delete:** Remove the automation entirely

---

## Choosing a Model

You can select any model you have access to. The model you choose determines what the automation can do.

### If Your Automation Needs Tools (Web Search, etc.)

**This is the most important thing to understand:** If your automation prompt benefits from tools like **Web Search**, **Image Generation**, or any custom tools, the base models (e.g., Claude Sonnet 4.6, GPT-5.5) do not have tools attached by default. You need to create a **Workspace Model** that wraps the base model and has the required tools enabled.

#### How to Create a Workspace Model with Tools

1. Go to **Workspace** → **Models** (left sidebar → Workspace)
2. Click **+ Create a Model**
3. Fill in:
   - **Name** — something descriptive, e.g., "Claude Sonnet + Web Search"
   - **Base Model** — select the underlying model (e.g., Claude Sonnet 4.6)
4. Scroll down to **Tools** and check the features you need:
   - ✅ **Web Search** — lets the model search the internet
   - ✅ **Image Generation** — lets the model generate images
   - ...
5. Click **Save**
6. Now go back to your automation and select this new Workspace Model instead of the base model

> **Why is this needed?** Automations run in the background without a UI, so the model must know in advance which tools it can use. Workspace Models let you "pre-configure" a model with specific tools and capabilities that will be available during every automation run.

#### Example: Daily Research Briefing with Web Search

1. Create a Workspace Model called "Claude + Web Search"
   - Base Model: Claude Sonnet 4.6
   - Tools: ✅ Web Search
2. Create an automation:
   - Model: **Claude + Web Search** (your new Workspace Model)
   - Schedule: Weekdays at 8:00 AM
   - Prompt:
     ```
     Summarize the most important AI developments in higher education
     from the past 24 hours. Focus on new tools, policy changes,
     research papers, and institutional announcements.
     Format as bullet points with source references.
     Today is {{CURRENT_DATE}}.
     ```

---

## Writing Good Automation Prompts

Since automations run without any human follow-up, your prompt needs to be **self-contained**. Here are some tips:

### Be Specific
Bad: `Tell me about AI news.`
Good: `Summarize the 5 most important AI developments in higher education from the past 24 hours. Format as bullet points with source links.`

### Use Template Variables
Include `{{CURRENT_DATE}}` or `{{CURRENT_DATETIME}}` so the model knows when it is running:
```
Generate discussion topics for this week's team meeting.
Today is {{CURRENT_DATE}}.
```

Available variables:

| Variable | Example output |
|---|---|
| `{{CURRENT_DATE}}` | 2026-05-08 |
| `{{CURRENT_TIME}}` | 12:56:19 |
| `{{CURRENT_DATETIME}}` | 2026-05-08 12:56:19 |
| `{{USER_NAME}}` | Your display name |

### Specify the Output Format
Tell the model exactly how you want the response structured — bullet points, numbered lists, tables, headings, etc.

### Keep It Single-Turn
Each automation run is a single prompt → single response. The model does not remember previous runs. Make each prompt self-contained.

---

## Suggested Use Cases to Try

### Daily Research Briefing
A weekday morning summary of developments in a topic you care about. Works best with a **Web Search-enabled** Workspace Model.

### Weekly Meeting Prep
A Monday morning automation that generates discussion topics or an agenda template for a recurring meeting.

### Personal Productivity
A daily prompt like "Generate my top 3 priorities for today based on common productivity frameworks" or "Give me a reflection prompt for end-of-day journaling."

### Monthly Review
A monthly automation that generates a checklist or set of review questions for a recurring process.

Feel free to create your own use cases — we are especially interested in what creative ideas emerge.

---

## What We Are Asking You to Do

Over the next two weeks, please:

1. **Create at least 2 automations** — one from the suggested use cases above, and one of your own design
2. **Use a Workspace Model with tools** for at least one automation — try Web Search or another tool to see how it affects output quality
3. **Use "Run Now"** to test your automations before relying on the schedule
4. **Check your automation results** regularly — via run history, chat list, or Calendar
5. **Note anything confusing, broken, or missing** — post feedback in the pilot channel or reach out to us directly

---

## What to Keep Track Of (for the Final Survey)

At the end of the pilot, we will ask you to fill out a short survey. Here are the things worth paying attention to:

### Setup experience
- Was creating an automation intuitive?
- Was the schedule picker easy to use?
- Did you understand when and how often your automation would run?

### Workspace Models and tools
- Was it clear that you needed a Workspace Model for tools?
- Was creating a Workspace Model straightforward?
- Did tools (e.g., Web Search) meaningfully improve the automation output?

### Output quality
- Were the AI responses useful without follow-up?
- Did you need to refine your prompt to get good results? How many iterations?
- Which use cases produced genuinely useful output vs. novelty?

### Finding results
- Could you easily find your automation results in the chat list?
- Was the Calendar integration helpful?
- Did automation-generated chats clutter your chat list?

### Reliability
- Did automations fire on schedule?
- Did you encounter any errors or missed runs?

### Missing features
- What would make Automations more useful? Think about:
  - Output delivery (email, channel post, webhook)
  - File/document attachments in prompts
  - Multi-turn conversations
  - Conditional execution (skip if nothing new)
  - Shared/team automations
  - Anything else

---

## Known Limitations

A few things to be aware of during the pilot:

| What | Details |
|---|---|
| **Prompt-only input** | Automations cannot attach files or reference knowledge bases directly. Paste key content into the prompt as a workaround. |
| **Single-turn only** | Each run is one prompt → one response. The model does not remember previous runs. |
| **No output routing** | Results go to your chat list only — no email, channel, or webhook delivery yet. |
| **Chat list clutter** | Each run creates a new chat. Use folders to organize automation-generated chats. |
| **No conditional logic** | Automations always run on schedule — they cannot skip based on external conditions. |
| **Code interpreter unavailable** | Automations cannot use the code interpreter (it requires frontend interaction). |
| **Credits** | Each automation run uses credits just like a normal chat. You are limited to 5 automations during the pilot. |
| **Timezone** | Scheduling uses your browser's timezone, which is detected automatically. If your automation runs at the wrong time, check that your computer's timezone is set correctly. |

---

## Quick Reference

| Action | How |
|---|---|
| Find Automations | Left sidebar → Automations icon |
| Create an automation | Automations → + Create Automation |
| Test an automation | Click the automation → Run Now |
| View run history | Click the automation → see past runs with status |
| Pause an automation | Toggle the automation off |
| Delete an automation | Click the automation → Delete |
| Find automation chats | Chat list in sidebar, or Calendar view |
| Create a Workspace Model | Workspace → Models → + Create a Model |
| Add tools to a Workspace Model | Model editor → Tools sections |
| Use a Workspace Model in automation | Automation editor → Model dropdown → select your Workspace Model |

---

## Need Help?

Reach out anytime during the pilot. You can also post questions directly in the pilot channel.
