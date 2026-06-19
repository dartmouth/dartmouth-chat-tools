# Channels Pilot — Participant Guide

Welcome to the Channels pilot! You are one of the first people at Dartmouth to try out Channels, a new real-time messaging feature built directly into Dartmouth Chat.

This guide covers what you need to know and what we are asking you to pay attention to during the two-week pilot.

---

## What is Channels?

Channels adds Slack-like group messaging to Dartmouth Chat. Instead of only having 1-on-1 AI conversations, you can now have real-time discussions with other people — and bring AI models into those conversations.

### Channel Types

| Type | Icon | Who can create | Who can see it |
|---|---|---|---|
| **Standard channel** | # | Admins only | All users with Channels permission |
| **Group channel** | 🔒 | Anyone | Only invited members |
| **Direct message** | Profile photo | Anyone | Just the two participants |

---

## Getting Started

### Find Channels
Open the **left sidebar** in Dartmouth Chat. You will see a **Channels** section. Click it to expand the list. You should already see **#rcd-leadership**, which was created for this pilot.

### Post a Message
Click into any channel and type in the message box at the bottom. Press **Enter** to send.

### Reply in a Thread
Click the **reply icon** on any message to open a threaded reply. This keeps side conversations organized without cluttering the main channel.

### React to a Message
Hover over a message and click the **emoji icon** to add a reaction.

### Pin a Message
Hover over a message, click the **⋯** menu, and select **Pin**. Pinned messages are accessible from the 📌 icon in the channel header.

### Upload a File
Drag a file into the message input, or click the **attachment icon**.

### Enable Browser Notifications
So you do not miss messages from other pilot members, turn on browser notifications:

1. Click your **profile icon** (bottom-left) → **Settings**
2. Go to **General**
3. Toggle **Notifications** to **On** — your browser will ask for permission; click Allow
4. Optionally, go to **Interface** and toggle **Always Play Notification Sound** if you want an audio alert even when the tab is in the background

> **Note:** There are no per-channel notification controls yet. This toggle applies to all of Dartmouth Chat.

---

## Mentioning People, AI Models, and Channels

This is one of the most powerful features to try during the pilot.

### @mention a person
Type `@` and select a user from the list. They will see the message highlighted.

### @mention an AI model
Type `@` and select a model (e.g., **Claude Sonnet 4.6**, **GPT-OSS 120b**). Ask it a question right in the channel — the AI will respond inline, visible to everyone.

**Example:**
> @GPT-OSS 120b, We're planning a summer workshop series for researchers on using AI tools. Suggest 5 session topics that would be most valuable for faculty who are new to generative AI.

**How the AI sees your conversation:** When you @mention a model, it only sees the **thread** it is part of — not the rest of the channel. If you @mention a model in a top-level message, it sees that message alone. If you @mention it inside a thread, it sees the thread history (up to 50 messages). It does **not** see other threads or other messages in the channel.

You can also reply to a previous AI response to continue the conversation — the model will pick up the thread context automatically.

**Tip:** For best results, include relevant context directly in your message. Do not assume the model has read the rest of the channel.

**Want the AI to search the web or use other tools?** See [Using AI Models with Tools in Channels](#using-ai-models-with-tools-in-channels) below.

### #mention a channel
Type `#` and select a channel to create a cross-reference link.

---

## Using AI Models with Tools in Channels

When you @mention a base model (e.g., Claude Sonnet 4.6, GPT-5.5), it responds using only its built-in "knowledge". If you want the model to **search the web**, **generate images**, or use any other tool, you need to @mention a **Workspace Model** that has those tools enabled.

This is the same approach used in [Automations](automations-onboarding-participant.md) — equip a Workspace Model with tools, then @mention it in a channel.

### How to Create a Workspace Model with Tools

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
6. Now go to any channel, type `@`, and select your new Workspace Model

> **Why is this needed?** Base models do not have tools attached by default. Workspace Models let you "pre-configure" a model with specific tools and capabilities that will be available whenever you @mention it — in channels, automations, or regular chats.

### Example: Research Question in a Channel Thread

1. Create a Workspace Model called "Claude + Web Search"
   - Base Model: Claude Sonnet 4.6
   - Tools: ✅ Web Search
2. In a channel thread, @mention it:
   > @Claude + Web Search, We're evaluating new tools for research data management. What are the top 3 platforms that universities adopted in the past year? Include links to announcements or reviews.
3. The model will search the web and respond inline — visible to everyone in the thread

---

## Creating Your Own Channels

You can create **group channels** and **direct messages** yourself:

1. Click the **+** button next to "Channels" in the sidebar
2. Choose the type:
   - **Group Channel** — invite-only, you pick the members
   - **Direct Message** — 1-on-1 conversation with another user
3. Give it a name (for group channels) and invite members
4. Start chatting!

> **Note:** Only admins can create standard (public) channels. If you need one, just ask.

---

## What We Are Asking You to Do

Over the next two weeks, please:

1. **Use Channels for real conversations** — team coordination, sharing links, asking questions, brainstorming with AI
2. **Try the AI @mention feature** at least a few times — see how it works in a group context
3. **Try @mentioning a Workspace Model with tools** — create a Workspace Model with Web Search enabled and @mention it in a channel to see how tool-equipped models work in group conversations
4. **Create at least one group channel or DM** to test the creation flow
5. **Note anything confusing, broken, or missing** — post it in the pinned "Feedback & Friction" thread in #rcd-leadership, or reach out to us directly anytime

---

## What to Keep Track Of (for the Final Survey)

At the end of the pilot, we will ask you to fill out a short survey. Here are the things worth paying attention to as you use Channels so you are ready:

### Usage patterns
- How often are you using Channels? Daily, a few times a week, less?
- Which channel type do you use most — standard, group, or DM?
- What are you using it for — discussion, AI queries, file sharing, quick messages?

### AI @mentions
- When you @mention an AI model, are the responses useful?
- Does the thread-scoped context work well enough, or do you find yourself repeating information the model should already know?
- Do you prefer asking the AI in a channel thread (where others can see) or in a separate 1-on-1 chat?

### Workspace Models and tools
- Was it clear that you could use a Workspace Model with tools in a channel?
- Was creating a Workspace Model straightforward?
- Did tools (e.g., Web Search) meaningfully improve the AI responses in channel conversations?

### UX and clarity
- Is the difference between standard channels, group channels, and DMs obvious?
- Can you find what you need without help — creating channels, managing members, pinning messages?
- Is anything confusing or hard to discover?

### Comparison to existing tools
- How does Channels compare to Slack or Teams for your workflow?
- Does it replace any existing communication, complement it, or feel redundant?

### Missing features
- What would make Channels more useful? Think about:
  - Notifications (push, email digest)
  - Search across channel messages
  - Channel archiving
  - Message edit history
  - Threading improvements
  - Anything else

---

## Known Limitations

A few things to be aware of during the pilot:

| What | Details |
|---|---|
| **AI context** | AI models only see the **thread** they are mentioned in — not the rest of the channel. Include context in your @mention for best results. |
| **No archiving** | Channels can be deleted but not archived. Please do not delete any channels during the pilot. |
| **No edit history** | You can edit messages, but previous versions are not saved. |
| **Credits** | AI responses in channels use credits just like regular chats. |
| **Tools** | AI models only have access to tools if you @mention a Workspace Model that has those tools enabled. Base models do not have tools by default. |

---

## Quick Reference

| Action | How |
|---|---|
| Find channels | Left sidebar → Channels section |
| Post a message | Type in the input box, press Enter |
| Reply in a thread | Click the reply icon on a message |
| React | Hover → emoji icon |
| Pin a message | Hover → ⋯ menu → Pin |
| View pinned messages | Channel header → 📌 icon |
| @mention a person | Type `@` → select user |
| @mention an AI model | Type `@` → select model |
| @mention a model with tools | Create a Workspace Model with tools enabled, then `@` → select it |
| #mention a channel | Type `#` → select channel |
| Create a group channel | Sidebar → Channels + button → Group Channel |
| Create a DM | Sidebar → Channels + button → Direct Message |
| Manage members | Channel header → people icon |
| Upload a file | Drag and drop, or click attachment icon |

---

## Need Help?

Reach out anytime during the pilot. You can also post questions directly in **#rcd-leadership**.
