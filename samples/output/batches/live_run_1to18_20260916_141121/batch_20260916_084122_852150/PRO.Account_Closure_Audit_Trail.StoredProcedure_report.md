# Account Closure Audit Trail — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Account_Closure_Audit_Trail` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 4 |
| Tables read | 4 |
| Tables written | 5 |
| Produces audit trail | Not detected |

## What This Does

This procedure updates account statuses and records decisions for pending account closures based on outstanding balances and dispute flags, ensuring compliance with regulatory requirements.

## Process Flow

1. Set the process date based on the time key.
2. Calculate the dispute grace cutoff date.
3. Update account statuses for accounts pending closure based on outstanding balance and dispute status.
4. Update account statuses to 'ACTIVE' and set rejection reasons for accounts with pending closure and outstanding balance or unresolved dispute.
5. Drop the temporary table if it exists.
6. Create a temporary table to store closure decisions.
7. Insert closure decisions into the temporary table for accounts with a closure date matching the process date or with specific rejection reasons.
8. Merge closure decisions into the closure register.
9. Insert records into the collections queue for closure rejections that are not due to zero balance.
10. Insert audit log entries for account status transitions.
11. Clear closure rejection reasons for accounts not in active status or with null rejection reasons.
12. Update the running process status for the account closure audit trail.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine AccountStatus | `AccountStatus` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Determine ClosureDate | `ClosureDate` | First matching row wins; ELSE includes false or NULL predicates. |
| Determine Reason | `Reason` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |
| Merge closure decisions | `NewStatus, Reason, LastDecisionDate, AccountId, FirstDecisionDate` | Merge closure decisions into the closure register, updating existing records or inserting new ones. |

## Business Rules

### R1 — Determine AccountStatus

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

### R2 — Determine ClosureDate

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

### R3 — Determine Reason

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

### R4 — Merge closure decisions

**Affected Field:** `NewStatus, Reason, LastDecisionDate, AccountId, FirstDecisionDate`

**Applies to:**

- Closure decisions match an account in the closure register

**Summary:**

- Merge closure decisions into the closure register, updating existing records or inserting new ones.

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

The procedure uses a TRY-CATCH block to handle exceptions, but the specific handling steps are not detailed in the extraction. The procedure captures and logs any errors encountered during the account closure audit trail process by updating the process status with the error details.

## Findings / Needs Review

- Lines 126-128 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 133-135 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 5 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
