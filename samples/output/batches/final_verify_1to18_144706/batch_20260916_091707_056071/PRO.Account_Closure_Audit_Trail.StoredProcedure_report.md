# Account Closure Audit Trail — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Account_Closure_Audit_Trail` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 13 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure manages the audit trail and status updates for loan account closures, ensuring that accounts are correctly transitioned through various statuses based on their outstanding balance and dispute status.

## Process Flow

1. Read the SysDayMatrix table to get the date for the process.
2. Update the PRO.LoanAccountCal table to set the account status and closure date based on various conditions.
3. Insert closure decisions into the #ClosureDecisions table.
4. Merge closure decisions into the PRO.ClosureRegister table.
5. Insert records into the PRO.CollectionsQueue table for accounts with escalation reasons.
6. Insert audit log entries into the PRO.AccountStatusAuditLog table for account status transitions.
7. Update the PRO.ACLRUNNINGPROCESSSTATUS table to mark the account closure audit trail process as completed and increment the process count.
8. Read from the PRO.LoanAccountCal table to check for specific closure conditions.
9. Read from the #ClosureDecisions table to retrieve closure decisions for further processing.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert escalation records | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for escalation. |
| Insert audit log entries (AccountId) | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into the PRO.AccountStatusAuditLog table. |
| Insert closure decisions [1] | `AccountId, NewStatus, Reason` | Insert closure decisions into the #ClosureDecisions temporary table for accounts that are pending closure and have a closure reject reason… |
| Merge closure decisions into register | `AccountId, NewStatus, Reason` | Merge closure decisions from the #ClosureDecisions temporary table into the PRO.ClosureRegister. |
| Insert unresolved dispute escalations | `AccountId, EscalationDate, Reason` | Insert records into PRO.CollectionsQueue for accounts with unresolved disputes that are pending closure and have a closure reject reason ot… |
| Insert audit log entries | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into PRO.AccountStatusAuditLog for accounts that have transitioned status. |
| Merge closure decisions | `AccountId, NewStatus, Reason, LastDecisionDate` | Merge closure decisions into the PRO.ClosureRegister. |
| Insert closure decisions [2] | `AccountId, NewStatus, Reason` | Insert closure decisions into the #ClosureDecisions temporary table for accounts pending closure with a closure reject reason or without an… |
| Insert collections queue records | `AccountId, EscalationDate, Reason` | Insert records into the PRO.CollectionsQueue table for accounts with closure reasons other than 'CLOSED_ZERO_BALANCE'. |
| Insert account status audit log entries | `AccountId, TransitionDate, NewStatus, Reason` | Insert audit log entries into the PRO.AccountStatusAuditLog table for accounts that transitioned status. |
| Determine AccountStatus | `AccountStatus` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine ClosureDate | `ClosureDate` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Business Rules

### R1 — Insert escalation records

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Reason is not 'CLOSED_ZERO_BALANCE'

**Summary:**

- Insert records into the CollectionsQueue table for escalation.


### R2 — Insert audit log entries (AccountId)

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:**

- Closure date is the process date or closure reject reason is 'OUTSTANDING_BALANCE' or 'UNRESOLVED_DISPUTE'

**Summary:**

- Insert audit log entries into the AccountStatusAuditLog table.


### R3 — Insert closure decisions [1]

**Affected Field:** `AccountId, NewStatus, Reason`

**Applies to:**

- Account is pending closure
- Closure reject reason is not 'CLOSED_ZERO_BALANCE'

**Summary:**

- Insert closure decisions into the #ClosureDecisions temporary table for accounts that are pending closure and have a closure reject reason other than 'CLOSED_ZERO_BALANCE'.


### R4 — Merge closure decisions into register

**Affected Field:** `AccountId, NewStatus, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Merge closure decisions from the #ClosureDecisions temporary table into the ClosureRegister.


### R5 — Insert unresolved dispute escalations

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Account is pending closure
- Closure reject reason is not 'CLOSED_ZERO_BALANCE'

**Summary:**

- Insert records into CollectionsQueue for accounts with unresolved disputes that are pending closure and have a closure reject reason other than 'CLOSED_ZERO_BALANCE'.


### R6 — Insert audit log entries

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:**

- Account closure date is the process date
- Closure reject reason is 'OUTSTANDING_BALANCE' or 'UNRESOLVED_DISPUTE'

**Summary:**

- Insert audit log entries into AccountStatusAuditLog for accounts that have transitioned status.


### R7 — Merge closure decisions

**Affected Field:** `AccountId, NewStatus, Reason, LastDecisionDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge closure decisions into the ClosureRegister.


### R8 — Insert closure decisions [2]

**Affected Field:** `AccountId, NewStatus, Reason`

**Applies to:**

- Account is pending closure
- Closure reject reason is set or account status is not active

**Summary:**

- Insert closure decisions into the #ClosureDecisions temporary table for accounts pending closure with a closure reject reason or without an active status.

### Decision Logic

| Condition | Result |
|---|---|
| AccountStatus = 'PENDING_CLOSURE' AND ClosureRejectReason IS NOT NULL | INSERT AccountId, NewStatus, Reason |
| AccountStatus = 'PENDING_CLOSURE' AND AccountStatus NOT IN ('ACTIVE') | INSERT AccountId, NewStatus, Reason |


### R9 — Insert collections queue records

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Closure reason is not 'CLOSED_ZERO_BALANCE'

**Summary:**

- Insert records into the CollectionsQueue table for accounts with closure reasons other than 'CLOSED_ZERO_BALANCE'.

### Decision Logic

| Condition | Result |
|---|---|
| Reason <> 'CLOSED_ZERO_BALANCE' | INSERT AccountId, EscalationDate, Reason |


### R10 — Insert account status audit log entries

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Insert audit log entries into the AccountStatusAuditLog table for accounts that transitioned status.


### R11 — Determine AccountStatus

**Affected Field:** `AccountStatus`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'PENDING_CLOSURE'

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A
- Expression: CASE WHEN COALESCE(A.OutstandingBalance, 0) = 0 THEN CASE WHEN A.DisputeFlag = 'N' OR A.DisputeFlag IS NULL THEN 'CLOSED' WHEN NOT A.DisputeRaisedDate IS NULL AND A.DisputeRaisedDate <= @DisputeGraceCutoff THEN 'CLOSED' ELSE 'PENDING_CLOSURE' END ELSE 'PENDING_CLOSURE' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (COALESCE(PRO.LoanAccountCal.OutstandingBalance, 0) = 0) AND (PRO.LoanAccountCal.DisputeFlag = 'N' OR PRO.LoanAccountCal.DisputeFlag IS NULL) | 'CLOSED' |
| (COALESCE(PRO.LoanAccountCal.OutstandingBalance, 0) = 0) AND (NOT PRO.LoanAccountCal.DisputeRaisedDate IS NULL AND PRO.LoanAccountCal.DisputeRaisedDate <= @DisputeGraceCutoff) | 'CLOSED' |
| COALESCE(PRO.LoanAccountCal.OutstandingBalance, 0) = 0 | 'PENDING_CLOSURE' |
| ELSE | 'PENDING_CLOSURE' |

### R12 — Determine ClosureDate

**Affected Field:** `ClosureDate`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'PENDING_CLOSURE'

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| ISNULL(PRO.LoanAccountCal.OutstandingBalance, 0) = 0<br>                     AND (PRO.LoanAccountCal.DisputeFlag = 'N' OR PRO.LoanAccountCal.DisputeFlag IS NULL<br>                          OR (PRO.LoanAccountCal.DisputeRaisedDate IS NOT NULL AND PRO.LoanAccountCal.DisputeRaisedDate <= @DisputeGraceCutoff)) | @ProcessDate |
| ELSE | PRO.LoanAccountCal.ClosureDate |

### R13 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- PRO.LoanAccountCal.ClosureDate = @ProcessDate OR PRO.LoanAccountCal.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE')

**Source context:**

- Target: #ClosureDecisions
- FROM PRO.LoanAccountCal AS A
- Expression: COALESCE(A.ClosureRejectReason, 'CLOSED_ZERO_BALANCE')

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.ClosureRejectReason IS NOT NULL | PRO.LoanAccountCal.ClosureRejectReason |
| ELSE | 'CLOSED_ZERO_BALANCE' |

## Calculations

### Calculation — Reason

**Expression:**

```sql
'CLOSURE_REJECTED_' + Reason
```

**Output:**
`PRO.CollectionsQueue.Reason`

**Used By:**
INSERT INTO PRO.CollectionsQueue

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: AccountStatus, ClosureDate, ClosureRejectReason |
| `PRO.ClosureRegister` | Read + Write | Provides: Target.AccountId, Target.NewStatus, Target.Reason, Target.LastDecisionDate, FirstDecisionDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ClosureDecisions` | Read + Write | Inserts data into: AccountId, NewStatus, Reason |

## Exception Handling

If an exception occurs during the account closure audit trail process, the procedure updates the status of the process to indicate it is not completed, records the current date as the error date, sets the error description, and increments the error count.

## Findings / Needs Review

- 7 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
