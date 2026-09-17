# Account Closure Audit Trail — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Account_Closure_Audit_Trail` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 7 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure updates the account closure status and reason in the closure register, inserts records into the collections queue for accounts with specific reasons, and logs the account status transition in the audit log. This procedure also writes to: AccountStatusAuditLog, ClosureDecisions, ClosureRegister, CollectionsQueue, LoanAccountCal.

## Process Flow

1. Read the date from the SysDayMatrix table where the TimeKey matches the provided @TimeKey parameter.
2. Calculate the dispute grace cutoff date by subtracting 30 days from the process date.
3. Update the account status and closure date for accounts with a pending closure status and an outstanding balance of zero.
4. Set the account status to 'CLOSED' if there is no dispute or the dispute was raised before the grace cutoff date.
5. Update the account status to 'ACTIVE' and set the closure reject reason to 'OUTSTANDING_BALANCE' for accounts pending closure with a positive outstanding balance.
6. Drop the temporary table '#ClosureDecisions' if it exists.
7. Create a temporary table '#ClosureDecisions' to store account closure decisions.
8. Insert into the temporary table '#ClosureDecisions' the account ID, new status, and closure reason for accounts that have been closed on the process date or have a closure reject reason of 'OUTSTANDING_BALANCE' or 'UNRESOLVED_DISPUTE'.
9. Merge the closure decisions into the closure register, updating existing records or inserting new ones.
10. Insert records into the collections queue for accounts with reasons other than 'CLOSED_ZERO_BALANCE'.
11. Insert records into the account status audit log for accounts that transitioned status.
12. Insert records into the PRO.LoanAccountCal.AccountStatusAuditLog table for accounts that have transitioned status, using data from the #ClosureDecisions temporary table.
13. Update the closure status and reason for loan accounts that are not active or have no closure reason.
14. Increment the count of completed processes in the audit trail.
15. On error, update the error status, date, and description in the audit trail and increment the error count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #ClosureDecisions | `AccountId, NewStatus, Reason` | Not specified |
| Upsert closureregister | `NewStatus, Reason, LastDecisionDate, AccountId, FirstDecisionDate` | Refresh existing rows and insert rows not already present. |
| Determine AccountStatus | `AccountStatus` | Not specified |
| Determine ClosureDate | `ClosureDate` | Not specified |
| Determine Reason | `Reason` | Not specified |
| Calculate dispute grace cutoff | `DisputeGraceCutoff` | Determine the dispute grace cutoff date by subtracting 30 days from the process date. |
| Insert into AccountStatusAuditLog | `PRO.AccountStatusAuditLog, AccountId, TransitionDate, NewStatus, Reason` | Insert records into the PRO.AccountStatusAuditLog table for accounts that have transitioned status. |

## Business Rules

### R1 — Insert into #ClosureDecisions

**Affected Field:** `AccountId, NewStatus, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.ClosureDate = @ProcessDate OR PRO.LoanAccountCal.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE') | AccountId := PRO.LoanAccountCal.AccountId; NewStatus := PRO.LoanAccountCal.AccountStatus; Reason := COALESCE(PRO.LoanAccountCal.ClosureRejectReason, 'CLOSED_ZERO_BALANCE') |


### R2 — Upsert closureregister

**Affected Field:** `NewStatus, Reason, LastDecisionDate, AccountId, FirstDecisionDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #ClosureDecisions.NewStatus; #ClosureDecisions.Reason; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #ClosureDecisions.AccountId; #ClosureDecisions.NewStatus; #ClosureDecisions.Reason; @ProcessDate |


### R3 — Determine AccountStatus

**Affected Field:** `AccountStatus`


**Applies to:**

- PRO.LoanAccountCal.AccountStatus = 'PENDING_CLOSURE'

**Source context:**

- Target: PRO.LoanAccountCal
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN COALESCE(PRO.LoanAccountCal.OutstandingBalance, 0) = 0 THEN CASE WHEN PRO.LoanAccountCal.DisputeFlag = 'N' OR PRO.LoanAccountCal.DisputeFlag IS NULL THEN 'CLOSED' WHEN NOT PRO.LoanAccountCal.DisputeRaisedDate IS NULL AND PRO.LoanAccountCal.DisputeRaisedDate <= @DisputeGraceCutoff THEN 'CLOSED' ELSE 'PENDING_CLOSURE' END ELSE 'PENDING_CLOSURE' END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (COALESCE(OutstandingBalance, 0) = 0) AND (DisputeFlag = 'N' OR DisputeFlag IS NULL) | 'CLOSED' |
| (COALESCE(OutstandingBalance, 0) = 0) AND (NOT DisputeRaisedDate IS NULL AND DisputeRaisedDate <= @DisputeGraceCutoff) | 'CLOSED' |
| COALESCE(OutstandingBalance, 0) = 0 | 'PENDING_CLOSURE' |
| ELSE | 'PENDING_CLOSURE' |

### R4 — Determine ClosureDate

**Affected Field:** `ClosureDate`


**Applies to:**

- PRO.LoanAccountCal.LoanAccountCal.AccountStatus = 'PENDING_CLOSURE'

**Source context:**

- Target: PRO.LoanAccountCal.LoanAccountCal
- FROM PRO.LoanAccountCal.LoanAccountCal

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| ISNULL(OutstandingBalance, 0) = 0<br>                     AND (DisputeFlag = 'N' OR DisputeFlag IS NULL<br>                          OR (DisputeRaisedDate IS NOT NULL AND DisputeRaisedDate <= @DisputeGraceCutoff)) | @ProcessDate |
| ELSE | LoanAccountCal.ClosureDate |

### R5 — Determine Reason

**Affected Field:** `Reason`


**Applies to:**

- PRO.LoanAccountCal.ClosureDate = @ProcessDate OR PRO.LoanAccountCal.ClosureRejectReason IN ('OUTSTANDING_BALANCE', 'UNRESOLVED_DISPUTE')

**Source context:**

- Target: #ClosureDecisions
- FROM PRO.LoanAccountCal
- Expression: COALESCE(PRO.LoanAccountCal.ClosureRejectReason, 'CLOSED_ZERO_BALANCE')

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| ClosureRejectReason IS NOT NULL | ClosureRejectReason |
| ELSE | 'CLOSED_ZERO_BALANCE' |

### R6 — Calculate dispute grace cutoff

**Affected Field:** `DisputeGraceCutoff`

**Applies to:**

- ProcessDate is set

**Summary:**

- Determine the dispute grace cutoff date by subtracting 30 days from the process date.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessDate is set | DisputeGraceCutoff |


### R7 — Insert into AccountStatusAuditLog

**Affected Field:** `PRO.AccountStatusAuditLog, AccountId, TransitionDate, NewStatus, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Insert records into the PRO.AccountStatusAuditLog table for accounts that have transitioned status.

### Decision Logic

| Condition | Result |
|---|---|
| Account has transitioned status | Insert record into PRO.AccountStatusAuditLog |

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

### Calculation — @DisputeGraceCutoff

**Expression:**

```sql
DATEADD(DAY, -30, @ProcessDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.AccountStatus, PRO.LoanAccountCal.ClosureDate, PRO.LoanAccountCal.ClosureRejectReason |
| `PRO.ClosureRegister` | Read + Write | Provides: #ClosureDecisions.NewStatus, #ClosureDecisions.Reason, #ClosureDecisions.LastDecisionDate, AccountId, FirstDecisionDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#ClosureDecisions` | Read + Write | Inserts data into: AccountId, NewStatus, Reason |

## Exception Handling

On error, the procedure updates the error status, date, and description in the audit trail and increments the error count.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
