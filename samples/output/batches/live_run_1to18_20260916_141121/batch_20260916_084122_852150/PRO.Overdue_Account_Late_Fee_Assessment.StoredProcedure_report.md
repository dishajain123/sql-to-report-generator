# Overdue Account Late Fee Assessment — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Overdue_Account_Late_Fee_Assessment` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 3 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

This procedure assesses overdue accounts to determine late fees and notify account holders of repeated overdue notifications.

## Process Flow

1. Initialize the process date and grace window end date.
2. Reset the notification count for accounts with overdue days and no last notification date.
3. Insert overdue accounts into a temporary fee schedule table with calculated late fees and incremented notification counts.
4. Update the escalate flag in the temporary fee schedule table based on the notification count.
5. Update the late fee amount, notification count, and last notification date in the loan account calendar table using the temporary fee schedule table.
6. Merge the temporary fee schedule table into the notification register table, updating existing records or inserting new ones.
7. Insert accounts with escalated notifications into the collections queue table.
8. Update the running process status table to mark the process as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Reset notification count | `NotifyCount` | Reset the notification count to zero for accounts with overdue days and no last notification date. |
| ⚠️ Update late fee amount | `LateFeeAmount, NotifyCount, LastNotifyDate` | Update the late fee amount, notification count, and last notification date in the loan account calendar table using the temporary fee sched… |
| ⚠️ Insert into collections queue | `AccountId, EscalationDate, Reason` | Insert accounts with escalated notifications into the collections queue table. |
| Determine LateFee | `LateFee` | First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates. |

## Business Rules

### R1 — Reset notification count

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `NotifyCount`

**Applies to:**

- Account has overdue days
- Last notification date is null
- Notification count is not null

**Summary:**

- Reset the notification count to zero for accounts with overdue days and no last notification date.

### Decision Logic

| Condition | Result |
|---|---|
| OverdueDays > 0 AND LastNotifyDate IS NULL AND NotifyCount IS NOT NULL | 0 |


### R2 — Update late fee amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `LateFeeAmount, NotifyCount, LastNotifyDate`

**Applies to:**

- Account ID in temporary fee schedule matches account ID in loan account calendar

**Summary:**

- Update the late fee amount, notification count, and last notification date in the loan account calendar table using the temporary fee schedule table.


### R3 — Insert into collections queue

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:**

- Escalate flag is 'Y'

**Summary:**

- Insert accounts with escalated notifications into the collections queue table.


### R4 — Determine LateFee

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

### Calculation — LateFee

**Expression:**

```sql
CASE
    WHEN ISNULL(NotifyCount, 0) = 0 THEN 250.00
    WHEN ISNULL(NotifyCount, 0) = 1 THEN 500.00
    ELSE 1000.00
END
```

**Output:**
`#FeeSchedule.LateFee`

**Used By:**
INSERT INTO #FeeSchedule

### Calculation — EscalateFlag

**Expression:**

```sql
CASE
    WHEN NotifyCount >= 3 THEN 'Y'
    WHEN NotifyCount = 2 THEN 'PENDING'
    ELSE 'N'
END
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

The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If the process fails, the running process status is updated to indicate an error.

## Findings / Needs Review

- Lines 26-26 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 109-111 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 116-118 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
