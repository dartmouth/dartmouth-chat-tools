# Channels Onboarding — RC&D Leadership Cohort

**Audience:** Research Computing & Data senior and associate directors
**Environment:** Preprod (https://chat-preprod.dartmouth.edu)
**Format:** Live guided walkthrough, ~20 minutes
**Facilitator:** Simon

---

## Pre-Session Admin Setup (before the meeting)

- [x] Ensure `ENABLE_CHANNELS=True` in preprod config
- [x] Create or verify a user group for the 4 RC&D leadership members
- [x] Grant `features.channels` permission to that group
- [x] Pre-create one standard channel: **#rcd-leadership** with read/write access for the RC&D group
- [x] Post a welcome message in #rcd-leadership so it is not empty when participants arrive
- [x] Verify at least one AI model is available for @mention (e.g., GPT-4o, Claude Sonnet)
- [x] Confirm all 4 participants can log into preprod

---

## Session Flow (20 minutes)

### Part 1 — Orient (3 min)

> **Goal:** Participants understand what Channels is and where to find it.

**Talking points:**
- Channels adds Slack-like real-time messaging directly inside Dartmouth Chat
- It lives in the **left sidebar** under the "Channels" section
- Three types of channels exist:
  - **Standard channels** (#) — visible to permitted users, created by admins
  - **Group channels** (🔒) — invite-only, anyone can create
  - **Direct messages** — 1-on-1 conversations
- Everything stays within Dartmouth Chat — same login, same data policies

**Do together:**
1. Open preprod and locate the **Channels** section in the sidebar
2. Click into **#rcd-leadership** — note the channel header, member count, and pin icon
3. **Enable browser notifications** — so they do not miss messages during the pilot:
   - Profile icon (bottom-left) → Settings → General → toggle **Notifications** to On → Allow browser permission
   - Optionally: Settings → Interface → toggle **Always Play Notification Sound**
   - Note: there are no per-channel notification controls; this is a global toggle

---

### Part 2 — Communicate (5 min)

> **Goal:** Participants send messages, reply in threads, and react.

**Do together:**
1. **Post a message** in #rcd-leadership — just say hello
2. **Reply in a thread** — click the reply icon on someone else's message and respond
3. **React to a message** — hover over a message, click the emoji icon, pick a reaction
4. **Pin a message** — hover over the welcome message, click the `...` menu, select Pin

**Point out:**
- Unread counts appear as badges on channels in the sidebar
- Threads keep side conversations organized without cluttering the main channel
- Pinned messages are accessible via the 📌 icon in the channel header

---

### Part 3 — Mention an AI Model (5 min)

> **Goal:** Participants see how AI models participate directly in channel conversations.

**Do together:**
1. Type `@` in the message input — note the suggestion list shows **users**, **models**, and **channels**
2. Select an AI model (e.g., `@gpt-4o` or `@claude-sonnet`)
3. Ask it a question right in the channel — e.g., *"@gpt-4o Summarize the key challenges of research data management in 3 bullet points"*
4. Watch the AI respond inline in the channel — visible to everyone

**Point out:**
- The AI only sees the **thread** it is mentioned in — not the rest of the channel. A top-level @mention means the model sees just that one message. Inside a thread, it sees up to 50 thread messages.
- You can also reply to a previous AI response to continue the conversation — no need to @mention again.

**Discussion prompt:**
- How could AI-in-channel be useful for your team? (brainstorming, drafting, quick research questions)

---

### Part 4 — Create Your Own (5 min)

> **Goal:** Participants create a group channel and a DM on their own.

**Do together:**
1. Click the **+** button next to "Channels" in the sidebar
2. Select **Group Channel** as the type
3. Name it something fun (e.g., `test-pilots`, `rc-sandbox`)
4. **Invite at least one other participant** as a member
5. Post a message in the new group channel

**Then on your own:**
1. Create a **Direct Message** with another participant
2. Send them a message — note the online/offline status indicator

**Point out:**
- Group channels are invite-only — non-members cannot see or access them
- You can manage members from the channel header (click the people icon)
- Only admins can create standard (public) channels; you can create group channels and DMs freely

---

### Part 5 — Wrap Up and Feedback (2 min)

> **Goal:** Set expectations for the pilot period and collect first impressions.

**Talking points:**
- This is the start of a 2-week pilot — please use channels naturally with your team
- **#rcd-leadership** is your home base — use it for real discussions, questions, AI experiments
- Things to notice and report back on:
  - Is the channel vs. chat distinction clear?
  - Are AI @mentions useful in a group context?
  - What is missing? (e.g., notifications, search, archiving)
  - Any confusing UX moments?

**Ask:**
- Pin a thread in #rcd-leadership titled "Feedback & Friction" where anyone can post observations during the pilot
- We will check in at the end of week 1 and do a final debrief at the end of week 2

---

## Quick Reference Card

| Action | How |
|---|---|
| Find channels | Left sidebar → Channels section |
| Post a message | Click into a channel, type in the input box, press Enter |
| Reply in a thread | Click the reply icon on any message |
| React to a message | Hover → emoji icon → pick reaction |
| Pin a message | Hover → `...` menu → Pin |
| View pinned messages | Channel header → 📌 icon |
| @mention a person | Type `@` → select from user list |
| @mention an AI model | Type `@` → select from model list |
| @mention a channel | Type `#` → select from channel list |
| Create a group channel | Sidebar → Channels + button → Group Channel |
| Create a DM | Sidebar → Channels + button → Direct Message |
| Manage members | Channel header → people icon |
| Upload a file | Drag and drop into the message input, or click the attachment icon |

---

## Known Limitations to Communicate

| Limitation | What to tell participants |
|---|---|
| AI context scope | The AI model only sees the **thread** it is mentioned in — not the rest of the channel. A top-level @mention means the model sees just that message. Inside a thread, it sees up to 50 messages. |
| No message edit history | Edited messages do not show previous versions. |
| No channel archiving | Channels can be deleted but not archived. Do not delete channels during the pilot. |
| Standard channel creation | Only admins can create public standard channels. Participants can create group channels and DMs. |
| Credit usage | AI responses in channels consume credits the same as regular chats. |
