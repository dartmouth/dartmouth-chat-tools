# Dartmouth Chat Tools

Tools and filter functions that extend Dartmouth Chat (Dartmouth's Open WebUI deployment).

## Data classification

**DISC**:
The Dartmouth Information Security Classification: Dartmouth's scheme for rating data from DISC 0 (Public) to DISC 3 (Highly Confidential).
_Avoid_: data level, risk level (used loosely)

**DISC level**:
One of DISC 0 (Public), DISC 1 (Internal Use Only), DISC 2 (Confidential), DISC 3 (Highly Confidential). Data covered by regulations like FERPA, HIPAA or PCI is always DISC 3.
_Avoid_: Low / Medium / High (the AI Data Sensitivity Guide's labels for levels 1–3)

**Regulated data**:
DISC 3 data that falls under an external regulation or contract: FERPA, HIPAA, PCI, GLBA or CUI. PII on its own is DISC 3 but not regulated data. Information Security must be consulted before using it with any AI tool, including local models.
_Avoid_: sensitive data (too vague)

**PII**:
Personal data that identifies someone beyond directory information, such as a birth date, home address, government ID, or financial or health details. DISC 3, but not regulated data on its own.
_Avoid_: personal data (too broad)

**Directory information**:
Name, Dartmouth email, NetID and title. DISC 1; not PII.

## Models

**Local model**:
A model hosted by Dartmouth. Approved for data up to DISC 3.
_Avoid_: on-prem model

**Cloud model**:
A model run by a commercial third-party provider. Approved for data up to DISC 2.
_Avoid_: external model, API model

**Task model**:
The model Dartmouth Chat uses for background work on a chat, such as titles, tags, follow-ups, search queries, memory and summarising long conversations. The DISC Risk Gate does not see what is sent to it.

**Model provider**:
The service that actually runs a model and receives the content sent to it, whether Dartmouth (for a local model) or a third party (for a cloud model).

## Privacy

**DISC Risk Gate**:
A filter that the user can switch on or off. On every request it checks everything about to be sent to the model provider, and asks the user to confirm when it finds regulated data (for any model) or DISC 3 data (for a cloud model).
_Avoid_: privacy watchdog

**Finding**:
One piece of content the DISC Risk Gate flagged, together with its DISC level and whether it is regulated data.
_Avoid_: hit, match, detection
