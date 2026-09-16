# Overdue Account Late Fee Assessment — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Overdue_Account_Late_Fee_Assessment` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 6 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure assesses overdue accounts to determine and apply late fees, update notification counts, and escalate overdue notifications based on the number of overdue days and the number of notifications sent.

## Process Flow

1. Initialize the process date and grace window end date.
2. Reset the notification count for accounts with overdue days and no last notification date.
3. Insert overdue accounts into the fee schedule with calculated late fees and notification counts.
4. Update the late fee amount, notification count, and last notification date in the loan account calendar.
5. Update the escalate flag in the fee schedule based on certain conditions.
6. Merge the fee schedule into the notification register.
7. Insert accounts into the collections queue for escalation.
8. Update the running process status to mark the process as completed and increment the count.
9. Read overdue accounts from the loan account calendar to determine late fees and notification counts.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Increment notification count [1] | `NotifyCount` | Increment the notification count for each overdue account. |
| Update late fee amount (A.LateFeeAmount) | `LateFeeAmount, NotifyCount, LastNotifyDate` | Update the late fee amount, notification count, and last notification date in the loan account calendar. |
| Merge into notification register | `AccountId, LateFee, NotifyCount, LastNotifyDate` | Merge the fee schedule into the notification register. |
| Read overdue accounts | `AccountId, LateFee, NotifyCount, LastNotifyDate` | Read overdue accounts from the loan account calendar to determine late fees and notification counts. |
| Calculate LateFeeAmount | `LateFeeAmount` | Calculate the late fee amount for each overdue account. |
| Determine LateFee | `LateFee` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Business Rules

### R1 — Increment notification count [1]

**Affected Field:** `NotifyCount`

**Applies to:**

- Account is overdue

**Summary:**

- Increment the notification count for each overdue account.

### Decision Logic

| Condition | Result |
|---|---|
| Account is overdue | NotifyCount + 1 |


### R2 — Update late fee amount (A.LateFeeAmount)

**Affected Field:** `LateFeeAmount, NotifyCount, LastNotifyDate`

**Applies to:**

- Account has overdue days
- Last notification date is null
- Notification count is not null

**Summary:**

- Update the late fee amount, notification count, and last notification date in the loan account calendar.


### R3 — Merge into notification register

**Affected Field:** `AccountId, LateFee, NotifyCount, LastNotifyDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge the fee schedule into the notification register.


### R4 — Read overdue accounts

**Affected Field:** `AccountId, LateFee, NotifyCount, LastNotifyDate`

**Applies to:**

- Account has overdue days
- Process date is not within grace window and overdue days are greater than 5

**Summary:**

- Read overdue accounts from the loan account calendar to determine late fees and notification counts.


### R5 — Calculate LateFeeAmount

**Affected Field:** `LateFeeAmount`

**Applies to:**

- Account is overdue
- No previous notification for this period
- Notification count is not null

**Summary:**

- Calculate the late fee amount for each overdue account.


### R6 — Determine LateFee

**Affected Field:** `LateFee`


**Applies to:**

- OverdueDays > 0 AND NOT (@ProcessDate <= @GraceWindowEnd AND OverdueDays <= 5)

**Source context:**

- Target: #FeeSchedule
- FROM PRO.LoanAccountCal
- Expression: CASE WHEN COALESCE(NotifyCount, 0) = 0 THEN 250.00 WHEN COALESCE(NotifyCount, 0) = 1 THEN 500.00 ELSE 1000.00 END

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| COALESCE(NotifyCount, 0) = 0 | 250.00 |
| COALESCE(NotifyCount, 0) = 1 | 500.00 |
| ELSE | 1000.00 |

## Calculations

### Calculation — NotifyCount

**Expression:**

```sql
COALESCE(NotifyCount, 0) + 1
```

**Output:**
`#FeeSchedule.NotifyCount`

**Used By:**
INSERT INTO #FeeSchedule

### Calculation — LateFeeAmount

**Expression:**

```sql
COALESCE(LateFeeAmount, 0) + LateFee
```

**Output:**
`PRO.LoanAccountCal.LateFeeAmount`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — @MonthStartDate

**Expression:**

```sql
DATEADD(DAY, -DAY(@ProcessDate) + 1, @ProcessDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — @GraceWindowEnd

**Expression:**

```sql
DATEADD(DAY, 6, @MonthStartDate)
```

**Output:**
`Not specified`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: NotifyCount, LateFeeAmount, LastNotifyDate |
| `PRO.NotificationRegister` | Read + Write | Provides: Target.AccountId, Target.LateFee, Target.NotifyCount, Target.LastNotifyDate, FirstNotifyDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#FeeSchedule` | Read + Write | Inserts data into: AccountId, LateFee, NotifyCount, EscalateFlag |

## Exception Handling

The procedure uses a TRY block to handle exceptions, but the specific handling steps are not detailed in the extraction. If the process fails, the running process status is updated to indicate the failure.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- The specific condition for an account being overdue is not detailed in the extraction.
- The escalation flag update rule assumes a default value of 0 for EscalateFlag when NotifyCount is not greater than 1, but this is not explicitly stated in the extraction.
- 11 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
