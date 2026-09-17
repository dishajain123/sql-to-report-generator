# Overdue Account Late Fee Assessment — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Overdue_Account_Late_Fee_Assessment` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

This procedure calculates and records late fees for overdue accounts, determining the fee amount based on the number of notifications sent and the account's overdue days. This procedure also writes to: CollectionsQueue, FeeSchedule, LoanAccountCal, NotificationRegister.

## Process Flow

1. Initialize the temporary table #FeeSchedule to store account details and late fees.
2. Reset the NotifyCount for accounts that are overdue and have not been notified yet.
3. Insert account details and calculate the late fee into the #FeeSchedule temporary table based on the number of notifications sent and the account's overdue days.
4. Update the escalate flag in the fee schedule based on the number of overdue notifications.
5. Update the late fee amount, notification count, and last notification date in the loan account calendar based on the fee schedule.
6. Merge overdue account data from the temporary #FeeSchedule table into the PRO.NotificationRegister table, updating existing records or inserting new ones.
7. Insert records into the PRO.CollectionsQueue table for accounts that need escalation due to repeated overdue notifications.
8. Update the running process status for 'Overdue_Account_Late_Fee_Assessment' to mark it as completed, reset error details, and increment the count.
9. In case of an error, update the running process status to mark it as not completed, record the error date, set the error description, and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Set escalate flag | `EscalateFlag` | Determine the escalate flag based on the number of overdue notifications. |
| Insert into CollectionsQueue | `AccountId, EscalationDate, Reason` | Not specified |
| Determine LateFee | `LateFee` | Not specified |

## Business Rules

### R1 — Set escalate flag

**Affected Field:** `EscalateFlag`

**Summary:**

- Determine the escalate flag based on the number of overdue notifications.

**Source context:**

- Target: #FeeSchedule
- FROM #FeeSchedule

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| NotifyCount >= 3 | 'Y' |
| NotifyCount = 2 | 'PENDING' |
| ELSE | 'N' |

### R2 — Insert into CollectionsQueue

**Affected Field:** `AccountId, EscalationDate, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EscalateFlag = 'Y' | AccountId := AccountId; EscalationDate := @ProcessDate; Reason := 'REPEATED_OVERDUE_NOTIFICATION' |


### R3 — Determine LateFee

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
ISNULL(PRO.LoanAccountCal.LateFeeAmount, 0) + #FeeSchedule.LateFee
```

**Output:**
`PRO.LoanAccountCal.LateFeeAmount`

**Used By:**
READ PRO.LoanAccountCal

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
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.NotifyCount, PRO.LoanAccountCal.LateFeeAmount, PRO.LoanAccountCal.LastNotifyDate |
| `PRO.NotificationRegister` | Read + Write | Provides: #FeeSchedule.LateFee, #FeeSchedule.NotifyCount, #FeeSchedule.LastNotifyDate, AccountId, FirstNotifyDate |
| `PRO.CollectionsQueue` | Write | Inserts data into: AccountId, EscalationDate, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#FeeSchedule` | Read + Write | Inserts data into: AccountId, LateFee, NotifyCount, EscalateFlag |

## Exception Handling

If an error occurs during the process, the process status is updated to indicate failure, and error details are recorded.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
