# Structured model (v2)

**Scope and date.** A software process map for the licensing of *sıhhi* premises in an
Istanbul district municipality, as practised around 2014–2015. User tasks are screens or
forms in the municipal software; physical work is shown only where the system records it.
Legal comparison as of November 2026: see [legal-basis.md](legal-basis.md).

The original diagram stays the primary artifact. v2 is a restructured, machine-readable
version of the **same process**: no step, decision or return path was removed or added
to the business logic. What changed is how it is organised and notated.

## How v2 is organised

| Level | File | What it shows |
| --- | --- | --- |
| 0 | `model/v2/00-overview.bpmn` | Six stages as call activities, the applicant as a separate pool, and the four cancellation outcomes |
| 1 | `01-register-and-survey.bpmn` | Registration, site survey, tax accrual, records office |
| 1 | `02-technical-opinions.bpmn` | Fire report, address determination and zoning query in parallel |
| 2 | `02a-zoning-opinions.bpmn` | Building inspection and mapping review branches, deputy mayor approval |
| 1 | `03-site-inspection.bpmn` | Zoning decision, site inspection, 15-day correction period, second inspection |
| 1 | `04-commission-and-fee.bpmn` | Commission evaluation, accrual, fee collection |
| 1 | `05-executive-approval.bpmn` | Deputy mayor and mayor approval, both cancellation paths, resubmission loops |
| 1 | `06-licensing.bpmn` | Licensing and applicant notification |
| 1 | `07-cancellation-and-closure.bpmn` | **Added, not in the source:** closure work order, on-site sealing, confirmation in the system |

Each stage starts where the previous one ends. The start and end events at those cut points
carry the milestone names listed in [v2-milestones.md](v2-milestones.md).

All files open in [Camunda Modeler](https://camunda.com/download/modeler/) or
[demo.bpmn.io](https://demo.bpmn.io/). They are generated from one source model,
`tools/v2/model.py`, by `tools/v2/build.py`, which also renders `diagrams/v2/*.svg` and checks
that every original step is mapped exactly once ([v2-traceability.md](v2-traceability.md)).

## Reading conventions

- **Lanes** carry the role. Task names are verb + object.
- Labels in *italics ending with "(label added)"* did not exist in the source. They name an
  existing path so the decision can be read; they do not add a path.
- Dotted notes on the diagrams mark interpretations and legal references.
- **Red elements with a dashed border were added**; they are not in the source diagram.
- A hand icon marks physical work outside the software (manual task); a person icon marks
  a screen in the software (user task).

## What changed compared with the source

**Organisation**

1. Split into an overview and seven detailed diagrams. Start and end events were added at
   the stage cut points.
2. Roles moved from text annotations and task names into lanes.
   "Ruhsat Müdürlüğü", "Ruhsat ve Denetim Müdürlüğü" and "Ruhsat ve Denetim Müdürü" share one
   lane (Licensing & Inspection Directorate). "İmar Müdürü" and "İmar ve Şehircilik Müdürü"
   share one lane. The second site inspection sits in its own Field Inspection Team lane,
   as its source annotation names that team.
3. Stage 2a has no lanes: both review branches pass through the same roles and their
   rejection loops would cross every lane. Roles stay in the task names, as in the source.
4. Labels are in English. Internal system names (payment project, mail service) are replaced
   by generic names.

**Notation only (same behaviour)**

5. E-mail steps drawn as script tasks are send tasks, in an Automated Notifications lane.
6. Where an arrow entered a task directly to form a loop or a join, an explicit merge
   gateway was added: the four review loops in 2a, the two resubmission loops in Stage 5,
   and the point where both inspection results lead to the commission (Stage 3).
7. Where a task had two outgoing arrows, a parallel gateway makes the split explicit
   (accrual and fee collection in Stage 4).
8. The small markers on the accrual and payment tasks are kept as escalation events,
   labelled "debt due: transfer to collection".
9. The four cancellation endings are error end events, so the overview can show each one
   as a distinct outcome.
10. Missing gateway questions and path labels were added (see "label added").

**Additions agreed with the author (November 2026)**

11. Stage C, cancellation and closure: the business is usually already operating, so every
    cancellation ends with a closure work order for the municipal police, on-site sealing
    and confirmation in the system. All four cancellation outcomes lead there.
12. Notes: as-is practice (open first, apply later); receipt and same-day declaration-based
    licence (Art. 6, 12); one-month inspection limit (Art. 13, also a group on the overview);
    final licence (Art. 13); commission and two-level approval as internal practice.
13. The Stage 1 start event is named "Application received (business may already be
    operating)".
14. Stage 4: commission rejection path (decision, notice, cancellation). Stage 3: automated
    deficiency notice before the 15-day period. Both confirmed by the author.

## Questions resolved with the author (November 2026)

All questions raised during restructuring are closed:

| Question | Resolution |
| --- | --- |
| Rejection path after the commission | Exists; added in Stage 4 (notice, cancellation, then Stage C) |
| Reviewer in the mapping branch ("Yapı Denetim Şefi") | Kept as drawn; a note explains that "Harita Şefi" may have been meant. These are municipal titles, not defined in the regulation |
| Escalation markers on accrual and payment | Read as "debt due: transfer to collection", based on the source note on accrual staff |
| Notice before the 15-day period | The system sends it automatically by SMS or e-mail; added in Stage 3 |
| Who requests the fire report | Licensing & Inspection Directorate (confirmed) |
| First gateway in Stage 1 | Read as "accrual already done?" from its only label |
| Applicant withdrawal | Not a step: an authorised user terminates the case in the system |

## Confidentiality

The model reflects a real municipal workflow. Internal system and project names, legal
references, document lists and fee rules are left out or generalised. Where the source was
ambiguous, the gap is shown as an open question instead of being filled with a guess.
