# DISC Risk Gate: manual integration tests

Prompts and files for checking the DISC Risk Gate (`functions/disc_risk_gate.py`) in a real deployment (preprod first). The automated tests in `tests/functions/` fake the classifier and Open WebUI. These check what they can't: real Clef verdicts, the real `request` hook in the tool loop, the real confirmation dialog, and real tool results.

**Everything in `fixtures/` is synthetic.** SSNs use the never-issued 666 area or the well-known invalid 078-05-1120. Card numbers are the published Visa, Mastercard and Amex test numbers. People, IDs and addresses are made up. Do not replace them with real data, even on preprod.

## Setup

1. Install `disc_risk_gate.py` as a function and enable it. Check the valves: `classifier_model = cloudflare.clef`, `classifier_timeout = 10`, `classifier_max_input_tokens = 16384`.
2. Confirm the backend has `LITELLM_PROXY_BASE_URL` and `LITELLM_PROXY_API_KEY` set.
3. Pick two models and attach the gate to both, switched on by default:
   - **LOCAL**: a model tagged `local` (any case, e.g. `Local`).
   - **CLOUD**: any model not tagged `local`, e.g. one tagged `Cloud`.
   - Optional **WS-LOCAL**: a workspace model whose base model is LOCAL, with no tags of its own.
4. Set **Function Calling = Native** on these models. Without it, attachments go through RAG instead of `view_attachment`, and section C doesn't apply.
5. Enable the tools used in section C: Knowledge, Notes, Chats and Code Execution.
6. Run `python tests/manual/disc_risk_gate/make_large_fixtures.py` if the generated files are missing.

Use a new chat for each case unless the case says otherwise. Earlier messages are re-checked on every call, so leftover content would affect the next case.

## What to expect

**On the first message of every new chat**, before any classification happens, a separate reminder dialog appears: "Before you start: the DISC Risk Gate has limits," explaining that the gate is an additional layer of protection, not a replacement for your judgment or Information Security's guidance, with a link to `dartgo.org/dchat-data-sensitivity` that opens in a new tab. This shows once per chat regardless of whether the message contains anything sensitive, and shows again as its own dialog even when the findings dialog also fires on that same message (see case A13).

The findings dialog has up to two findings sections, each listing what it "appears to contain", followed by a "Why am I seeing this?" section (with a link to `dartgo.org/dchat-data-sensitivity` that opens in a new tab) and a closing note that the gate is an additional layer of protection, not a replacement for your judgment or Information Security's guidance, and can make mistakes:

- **Regulated data**: FERPA student record, Health information (HIPAA), Payment card data (PCI), Financial information (GLBA), Controlled Unclassified Information. Shown for both models. On CLOUD it also says "Regulated data is not approved for cloud models."
- **Highly confidential data (DISC 3) on a cloud model**: Government ID (e.g. SSN), PII (e.g. birth date, home address), Other highly confidential data. Shown on CLOUD only.

Each line reads "<category> in <location>". The possible locations are:

- `your message`
- `attached file <name>`
- `the result of tool <name>`
- `retrieved context`
- `your message or the retrieved context added to it`
- `an earlier reply`
- `the system prompt`

Short labels used in the tables below:

| Label | Meaning |
|---|---|
| **silent** | The reply arrives with no dialog. |
| **DIALOG(R)** | Dialog with only the Regulated data section. |
| **DIALOG(C)** | Dialog with only the DISC 3 on a cloud model section. |
| **DIALOG(R+C)** | Dialog with both sections. |
| **NOTICE** | Status line "The DISC Risk Gate couldn't check this request…", then the reply. |
| **BLOCKED-LONG** | Error "Some messages in this conversation are too long to be checked…", and no reply. |
| **REMINDER** | The one-time "Before you start" dialog, separate from any findings dialog. |

For every dialog, also check that the dialog never shows the value itself (SSN, card number, diagnosis, grade).

---

## A. Policy table (pasted text)

Paste the prompt as your message, once on LOCAL and once on CLOUD.

| ID | Prompt | LOCAL | CLOUD | Expected categories |
|---|---|---|---|---|
| A1 | `Write a haiku about autumn leaves on the Dartmouth Green.` | silent | silent | none |
| A2 | `Draft a short intro email to Taylor Brooks (taylor.r.brooks@dartmouth.edu, NetID f00abc1), Associate Director of Research Computing.` | silent | silent | none (directory information) |
| A3 | `Fill in an I-9 summary for Jordan Avery, SSN 078-05-1120.` | silent | DIALOG(C) | Government ID |
| A4 | `Write a birthday card for my colleague Sam, born 1985-07-22, who lives at 17 Maple Ave, Hanover NH 03755.` | silent | DIALOG(C) | PII |
| A5 | `Student Liam Chen (ID D90000101) got a D in MATH 13 and is on academic probation. Draft a supportive note from his advisor.` | DIALOG(R) | DIALOG(R) | FERPA |
| A6 | `Patient Maria Lopez, 54, was diagnosed with type 2 diabetes and started metformin. Write her a plain-language care summary.` | DIALOG(R) | DIALOG(R) | HIPAA |
| A7 | `Check whether this card is valid: 4111 1111 1111 1111, exp 09/28, CVV 123.` | DIALOG(R) | DIALOG(R) | PCI |
| A8 | `Emma Wilson's parents reported an AGI of $61,350; she has a $3,500 subsidized loan. Explain her aid package.` | DIALOG(R) | DIALOG(R) | GLBA (FERPA possible) |
| A9 | Paste the contents of `fixtures/export_controlled_spec.txt` and ask `Summarise this.` | DIALOG(R) | DIALOG(R) | CUI |
| A10 | Paste `fixtures/board_strategy_memo.md` and ask `Turn this into talking points.` | silent | DIALOG(C) or silent | Other highly confidential data. **Probe:** record what happens. |
| A11 | Paste `fixtures/mixed_packet.md` and ask `Summarise this case.` | DIALOG(R) | DIALOG(R+C) | FERPA, PCI, PII, probably HIPAA. All in **one** dialog. |
| A12 | Repeat A3 on **WS-LOCAL**. | silent | — | A workspace model on a local base counts as local. |
| A13 | In a **brand-new** chat, run A3 on CLOUD. | — | REMINDER, then DIALOG(C) | Two separate dialogs on the same message: confirm the reminder first, then the findings dialog. |

## B. Attached files (`view_attachment`)

Attach the file, then send the prompt. With native tool calling the gate should be **silent on the first call**, because only the manifest has been sent so far. The dialog appears on the next call, after the model has read the file. The location must name the file.

| ID | Attach | Prompt | CLOUD | Location |
|---|---|---|---|---|
| B1 | `harmless_meeting_notes.md` | `Summarise the attached notes.` | silent | — |
| B2 | `staff_directory.csv` | `Who works in Research Computing?` | silent | — |
| B3 | `new_hire_onboarding.csv` | `Make a first-week checklist for each new hire in the attached file.` | DIALOG(C) | `attached file new_hire_onboarding.csv` |
| B4 | `course_roster_grades.csv` | `Which students in the attached roster need intervention, and why?` | DIALOG(R) | `attached file course_roster_grades.csv` |
| B5 | `clinic_visit_notes.txt` | `Rewrite the attached note for the patient in plain language.` | DIALOG(R) | `attached file clinic_visit_notes.txt` |
| B6 | `donation_payments.csv` | `Total the donations in the attached file by card brand.` | DIALOG(R) | `attached file donation_payments.csv` |
| B7 | `financial_aid_summary.txt` | `Explain this award letter to the student.` | DIALOG(R) | `attached file financial_aid_summary.txt` |
| B8 | `long_inventory_ssn_at_end.csv` | `Read the whole attached file, page by page, and list any rows that look unusual.` | silent on early pages, then DIALOG(C) once the model reaches the last page | `attached file long_inventory_ssn_at_end.csv` |
| B9 | `course_roster_grades.csv` **and** `donation_payments.csv` | `Read both attached files and tell me what each one is.` | DIALOG(R), with both files listed in **one** dialog once both have been read | both files |

## C. Prompts that make the model call tools

Some cases need **seed content** that contains test data. Create the seed with the gate **switched off** for that chat, then switch it back on (or start a new chat with it on) for the test prompt. The data then reaches the model only as a tool result.

| ID | Seed (gate off) | Test prompt (gate on, CLOUD) | Expected tool | CLOUD | Location |
|---|---|---|---|---|---|
| C1 | Create a knowledge base "Advising" containing `course_roster_grades.csv`. Attach it to the chat or the model. | `Using the Advising knowledge base, which students are on academic probation?` | `query_knowledge_files` / `search_knowledge_files` | DIALOG(R) | `the result of tool query_knowledge_files` (or the search tool) |
| C2 | Same knowledge base as C1. | `Open the roster file in my Advising knowledge base and show me Emma Wilson's row.` | `view_knowledge_file` / `view_file` | DIALOG(R) | tool or attached file name |
| C3 | In any chat: `Write a note titled "Onboarding - Jordan" with: Jordan Avery, SSN 078-05-1120, DOB 1990-03-14, starts 2026-11-03.` | `Find my onboarding note for Jordan and remind me when they start.` | `search_notes` → `view_note` | DIALOG(C) | `the result of tool view_note` (possibly `search_notes` too) |
| C4 | A chat titled "Probation follow-up" where you pasted case A5. | `Search my previous chats for the probation follow-up and summarise what we decided.` | `search_chats` → `view_chat` | DIALOG(R) | `the result of tool view_chat` |
| C5 | Attach `course_roster_grades.csv`. | `Use Python to load the attached roster and print every student whose final grade is D or E, with their advisor note.` | `execute_code` | DIALOG(R) after the code runs | `the result of tool execute_code` |
| C6 | — | `Create an automation that runs every Monday and drafts a check-in email to Liam Chen (ID D90000101), who is on academic probation in MATH 13.` | `create_automation` | DIALOG(R) **before** the tool call, because the data is in your message | `your message` |
| C7 | Run C6 with the gate off, and let the automation fire. | — | — | **No dialog.** An automation has no session, so it passes unchecked. This is by design. | — |
| C8 | — | `Search the web for Dartmouth's FERPA policy and summarise what counts as an education record.` | `search_web` / `fetch_url` | silent. Public policy text isn't a student record. | — |
| C9 | Attach `harmless_meeting_notes.md`. | `Read the attached notes, then search my notes for anything about onboarding and combine them into one to-do list.` (Run after C3's seed exists.) | `view_attachment` + `search_notes`/`view_note` | silent after the first tool, DIALOG(C) after the note is read | `the result of tool view_note` only |

## D. Retrieved context (RAG)

Set Function Calling to **Default** (not Native) on a copy of the CLOUD model, or use a knowledge base in full-context mode.

| ID | Setup | Prompt | CLOUD | Location |
|---|---|---|---|---|
| D1 | Attach `course_roster_grades.csv` to the chat (RAG mode). | `Who is on academic probation?` | DIALOG(R) | `your message or the retrieved context added to it` (or `retrieved context` if `RAG_SYSTEM_CONTEXT` is on) |
| D2 | Same, but with `harmless_meeting_notes.md`. | `When is the HPC maintenance window?` | silent | — |
| D3 | A model whose **system prompt** contains `Escalate billing issues to card 4111 1111 1111 1111.` | `hi` | DIALOG(R) | `the system prompt` |

## E. Dialog behaviour

Use case A3 on CLOUD for each row.

| ID | Action | Expected |
|---|---|---|
| E1 | Click **Confirm** | The reply arrives as normal. |
| E2 | Click **Cancel** | Error "Cancelled by the DISC Risk Gate (https://dartgo.org/dchat-disc-risk-gate). Nothing was sent to the model. Switch to a local model…". The error bubble renders plain text only (no markdown, no HTML), so the URL is shown in full rather than as a clickable link. Your message stays in the chat. Check the provider or LiteLLM logs: no completion call was made. |
| E3 | Close the dialog with Escape or by clicking outside it | Same as E2. |
| E4 | Open the dialog, then close the tab. Reopen the chat. | Same as E2, and no reply is generated. |
| E5 | Open the dialog and leave it alone until the event call times out | Same as E2. |
| E6 | Switch the gate off in the chat's integrations menu, then resend | silent. The classifier is not called (check LiteLLM spend logs). |
| E7 | Run case A5 on CLOUD and click Cancel | The cancel message mentions Information Security. |
| E8 | On a findings dialog, click "Learn more about data sensitivity" under "Why am I seeing this?". | Opens `dartgo.org/dchat-data-sensitivity` in a **new tab**; the chat and the dialog stay open behind it. |

## E2. The first-message reminder

| ID | Steps | Expected |
|---|---|---|
| E2-1 | Start a brand-new chat and send `hi` (any model). | REMINDER appears before the reply, even though `hi` is harmless. |
| E2-2 | In that same chat, send `hi` again. | silent. The reminder does not repeat in the same chat. |
| E2-3 | Start a second new chat and send `hi`. | REMINDER appears again, for the new chat. |
| E2-4 | On the REMINDER, click **Cancel** (or close it). | Error "Cancelled by the DISC Risk Gate (https://dartgo.org/dchat-disc-risk-gate). Nothing was sent to the model…", shown as plain text with the URL spelled out (the error bubble doesn't render markdown or HTML). Your message stays in the chat. No completion call was made. |
| E2-5 | Resend after E2-4. | silent (for the reminder) — it already fired for this chat, even though it was cancelled. The message is classified normally from here. |
| E2-6 | Use a **Temporary Chat**. | silent. Temporary chats don't get the reminder. |
| E2-7 | Restart the backend, then send `hi` in a chat that already saw the reminder. | REMINDER appears again. The "already shown" list is in-memory only and doesn't survive a restart. |
| E2-8 | On the REMINDER, click "Learn more about data sensitivity". | Opens `dartgo.org/dchat-data-sensitivity` in a **new tab**; the chat and the dialog stay open behind it. |

## F. Prompting again and chat history

| ID | Steps | Expected |
|---|---|---|
| F1 | Run A3 on CLOUD and confirm. Then send `Thanks! Now make it shorter.` | A dialog again on the second turn, because the SSN is still in the history. Location: `your message`. |
| F2 | Run B3 on CLOUD and confirm, so the model makes one or more further tool calls in the same turn. | A dialog before **each** provider call that still includes the file content. |
| F3 | Run A3 on CLOUD with the gate **off** and let it reply. Switch the gate on and send `Thanks.` | A dialog: earlier messages are checked too. The location may include `an earlier reply` if the model repeated the SSN. |
| F4 | Run A3 on LOCAL. Then switch the same chat to CLOUD and send `continue`. | silent on LOCAL, then DIALOG(C) after switching. |

## G. Failures and limits

Change one valve at a time and **restore it afterwards**.

| ID | Change | Prompt | Expected |
|---|---|---|---|
| G1 | `classifier_model = cloudflare.nope` | A3 on CLOUD | NOTICE, and the reply arrives. The backend log shows a warning with the status and error type only. |
| G2 | `classifier_timeout = 0.01` | A3 on CLOUD | NOTICE, and the reply arrives. |
| G3 | Unset `LITELLM_PROXY_BASE_URL` (or point it somewhere unreachable) and restart | A3 on CLOUD | NOTICE, and the reply arrives. |
| G4 | — | Paste `fixtures/under_limit_paste.txt`, then ask `How many rows mention Steele 101?` | silent |
| G5 | — | Paste `fixtures/too_long_paste.txt`, then ask the same question | BLOCKED-LONG. This calls Clef and checks the `input_tokens` cap. |
| G6 | — | Paste `fixtures/way_too_long_paste.txt` | BLOCKED-LONG straight away, without calling the classifier. |
| G7 | After G5, switch the gate off and resend | — | The request goes through. |
| G8 | G5 again, but make sure G2's timeout change is restored first | — | Still BLOCKED-LONG. A long message must never fail open. |

## H. False-positive probes

All of these should be **silent on CLOUD**. Record any that prompt.

1. `Explain what FERPA protects, with examples of education records.`
2. `What is the format of a US Social Security number, and why are numbers starting with 666 never issued?`
3. `Write a short story where a detective finds a card number written on a napkin.`
4. `Summarise the Wikipedia article on HIPAA for a staff training slide.`
5. `Generate fake test data: 5 rows with name, email and favourite colour.`
6. `My NetID is f00abc1 and my office is in Baker 105. How do I reset my Duo device?`
7. `Make a seating chart for my 12-person team offsite. Names: Taylor, Morgan, Casey, Riley, Jordan, Sam, Alex, Pat, Chris, Dana, Lucas, Ava.`
8. `Our department's FY27 operating budget is $2.4M. Draft a one-paragraph summary for the website.`

## I. No sensitive values in the logs

After running sections A to G, search the backend logs for the test values. Each search must return **nothing**:

```sh
kubectl logs <open-webui-pod> --since=2h | grep -E '078-05-1120|666-12-3456|4111 1111 1111 1111|metformin|D90000101|Maria Lopez'
```

Expect only lines such as `DISC Risk Gate: classifier returned 400 (invalid_request_error) after 0.31s`. Also check LiteLLM's logs if they record request bodies. The gate sends the content there by design, so this check is about retention policy, not about a bug in the gate.

## Known gaps (not failures)

- **Task model calls aren't covered** (ADR 0001). Title, tag and follow-up generation still send the first message to the task model before the gate runs.
- **Automations and API calls aren't checked** (C7). There is nobody to ask.
- **The gate is advisory.** Confirm sends the data.

## Recording results

For each case, record: ID, model, dialog shown (yes/no), categories, locations, the time from Send to the dialog or first token, and anything surprising. Clef probabilities can't be seen in the UI. For borderline cases (A8, A10, the H probes), call `/api/v1/systemone` directly with the question set from `disc_risk_gate.py` to see the scores.
