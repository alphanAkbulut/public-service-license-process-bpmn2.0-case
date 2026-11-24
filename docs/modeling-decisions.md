# Modeling Decisions

## Scope

The model starts when the owner applies (the business is usually already operating) and ends when the final license is issued or, after a cancellation, the premises are closed. Activities outside that boundary are referenced only when they affect the process state.

## Abstraction level

The detailed model captures the operational activities, responsible roles and alternative paths required by the software flow. The repository overview groups these details into major stages so the complete process remains easy to follow.

## Gateways

Exclusive gateways represent decisions with one selected outcome, such as zoning approved or rejected, or whether an e-mail address is registered. Parallel gateways represent independent reviews that can proceed concurrently and must be reconciled before the process advances.

## Rework

Correction is modeled as an explicit loop. This keeps the normal path readable and shows where reassessment occurs.

## End states

Issued and cancelled are separate end states. They are not treated as interchangeable versions of completion.

Applicant withdrawal is not an end state of the process. If a business closes before its licence is finalised, an authorised user terminates the case in the system. This is a permission-based action available at any point, so it is not drawn in the flow.

## Assumptions

- The application is registered after a document and debt check; there is no rejection at intake.
- Fire, address and zoning reviews run in parallel.
- Inspection may lead to a 15-day correction period and a second inspection.
- Executive approval (deputy mayor, then mayor) follows the commission and fee collection.

These assumptions summarize the main process logic shown in the portfolio overview. The detailed model contains the activity-level rules used during analysis and implementation.
