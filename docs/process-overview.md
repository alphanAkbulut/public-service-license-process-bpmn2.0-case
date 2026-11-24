# Process Overview

The process licenses *sıhhi* premises (shops, cafés, restaurants without alcohol service)
in an Istanbul district municipality, as implemented in the municipal software around
2014–2015. In practice the business was usually already operating when the owner applied,
so the workflow reads as **declaration → finalising inspection → final licence, or
cancellation and closure**. Stage numbers below match the structured v2 diagrams.

## 1. Registration and site survey

The Licensing & Inspection Directorate registers the application, checks documents and
outstanding debts, and takes the declaration form. In parallel, the Records Office receives
the application, and the Real Estate Unit surveys the premises: if the business is active,
a tax accrual is recorded and payment is collected separately by the cashier. The directorate
then reviews the survey and front-office work.

## 2. Technical opinions

Three reviews run in parallel:

- **Fire report**, requested only when the premises require one
- **Address determination** by the City Information Service, approved by the zoning director
  and the deputy mayor
- **Zoning status**, reviewed in two parallel branches (building inspection and mapping), each
  with a chief, a rapporteur and the zoning director, then approved by the deputy mayor;
  a rejection sends both branches back

## 3. Site inspection

The directorate starts the inspection. If the zoning status was rejected, the application is
cancelled and the applicant notified. Otherwise the premises are inspected. If deficiencies
are found, the business gets 15 days, then a second inspection; if they remain, the
application is cancelled.

## 4. Commission and fee

The licensing commission evaluates the file, the applicant is invited for the fee accrual,
and the cashier collects the licence fee.

## 5. Executive approval

The deputy mayor and then the mayor approve the licence. At each level the licence can be
cancelled; the directorate then informs about the cancellation and the file is either
resubmitted for approval or the cancellation becomes final.

## 6. Licensing

The rapporteur issues the final licence and the applicant is informed.

## Cancellation and closure (added in v2)

Because the business is usually operating, every cancellation ends with closure: the case
becomes a work order for the municipal police, who seal the premises on site and confirm the
closure in the system. This stage is not in the source diagram.

## Edge cases covered

- Business not active at the time of the site survey
- Tax accrual already recorded
- Fire report not required
- Rejection loops inside each zoning review branch and at deputy mayor level
- Zoning status rejected
- Deficiencies found at inspection, 15-day correction period and second inspection
- Cancellation at deputy mayor or mayor level, with resubmission
- No e-mail address registered for notifications
- Applicant withdrawal, handled as a case termination by an authorised user rather than as a
  step in the flow
