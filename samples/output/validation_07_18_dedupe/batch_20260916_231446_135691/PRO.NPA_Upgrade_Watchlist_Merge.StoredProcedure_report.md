# NPA Upgrade Watchlist Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Upgrade_Watchlist_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 8 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the NPA Upgrade Watchlist with the latest data from a staging table, ensuring that the records reflect the most current information regarding overdue accounts and their eligibility for upgrade. This procedure also writes to: AccountStatusAuditLog, LoanAccountCal, NpaUpgradeWatchlist, WatchlistStaging.

## Process Flow

1. Calculate the days since the last overdue date for non-standard asset classes.
2. Insert the calculated days since the last overdue date, account ID, asset class, and upgrade eligibility into a staging table.
3. Update the 'EligibleForUpgrade' field in the #WatchlistStaging table based on the days since last overdue and asset class.
4. If the process date is the first day of the month, update the 'EligibleForUpgrade' field to 'PENDING_APPROVAL' for accounts that are currently eligible for upgrade.
5. Merge the latest data from the #WatchlistStaging table into the PRO.NpaUpgradeWatchlist table, updating existing records and inserting new ones.
6. Delete records from the PRO.NpaUpgradeWatchlist table where the account ID is associated with overdue days greater than zero in the PRO.LoanAccountCal table.
7. Update the asset class and upgrade date for accounts on the NPA upgrade watchlist.
8. Insert a record into the account status audit log for accounts transitioning to a new status.
9. Delete records from the NPA upgrade watchlist that have been processed.
10. Update the process status to indicate completion and increment the count of processed records.
11. Handle any exceptions by updating the process status to indicate an error and logging the error details.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Insert into #WatchlistStaging | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Not specified |
| Determine UpgradeDate | `UpgradeDate` | Not specified |
| Insert into AccountStatusAuditLog | `AccountId, TransitionDate, NewStatus, Reason` | Not specified |
| Upsert npaupgradewatchlist | `DaysSinceLastOverdue, EligibleForUpgrade, LastCheckedDate, AccountId, AssetClass, FirstWatchedDate` | Refresh existing rows and insert rows not already present. |
| Determine EligibleForUpgrade | `EligibleForUpgrade` | Not specified |
| Calculate days since last overdue | `PRO.LoanAccountCal.DaysSinceLastOverdue` | Determine the number of days since the last overdue date for non-standard asset classes. |
| Determine EligibleForUpgrade (#WatchlistStaging) | `EligibleForUpgrade` | Set the 'EligibleForUpgrade' field based on the days since last overdue and asset class. |
| Delete overdue records | `Not specified` | Remove records from the NPA Upgrade Watchlist where the account ID is associated with overdue days greater than zero in the LoanAccountCal… |

## Business Rules

### R1 — Insert into #WatchlistStaging

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.AssetClass <> 'STANDARD' AND PRO.LoanAccountCal.OverdueDays = 0 | AccountId := PRO.LoanAccountCal.AccountId; AssetClass := PRO.LoanAccountCal.AssetClass; DaysSinceLastOverdue := PRO.LoanAccountCal.DaysSinceLastOverdue; EligibleForUpgrade := 'N' |


### R2 — Determine UpgradeDate

**Affected Field:** `UpgradeDate`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.NpaUpgradeWatchlist.EligibleForUpgrade = 'Y' | @ProcessDate |


### R3 — Insert into AccountStatusAuditLog

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.NpaUpgradeWatchlist.EligibleForUpgrade = 'Y' AND PRO.LoanAccountCal.AssetClass = 'STANDARD' AND PRO.LoanAccountCal.UpgradeDate = @ProcessDate | AccountId := PRO.LoanAccountCal.AccountId; TransitionDate := @ProcessDate; NewStatus := 'STANDARD'; Reason := 'NPA_WATCH_PERIOD_COMPLETE' |


### R4 — Upsert npaupgradewatchlist

**Affected Field:** `DaysSinceLastOverdue, EligibleForUpgrade, LastCheckedDate, AccountId, AssetClass, FirstWatchedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Refresh existing rows and insert rows not already present.

### Decision Logic

| Condition | Result |
|---|---|
| WHEN MATCHED | #WatchlistStaging.DaysSinceLastOverdue; #WatchlistStaging.EligibleForUpgrade; @ProcessDate |
| WHEN NOT MATCHED BY TARGET | #WatchlistStaging.AccountId; #WatchlistStaging.AssetClass; #WatchlistStaging.DaysSinceLastOverdue; #WatchlistStaging.EligibleForUpgrade; @ProcessDate |


### R5 — Determine EligibleForUpgrade

**Affected Field:** `EligibleForUpgrade`

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| DAY(@ProcessDate) = 1 — row filter: #WatchlistStaging.EligibleForUpgrade = 'Y' | 'PENDING_APPROVAL' |
| ELSE — applies to all rows (no additional filter) | #WatchlistStaging.EligibleForUpgrade |

### R6 — Calculate days since last overdue

**Affected Field:** `PRO.LoanAccountCal.DaysSinceLastOverdue`

**Applies to:**

- PRO.LoanAccountCal.AssetClass is not 'STANDARD'
- PRO.LoanAccountCal.OverdueDays is 0
- PRO.LoanAccountCal.LastOverdueClearedDate is not NULL
- PRO.LoanAccountCal.LastOverdueClearedDate is less than or equal to @ProcessDate

**Summary:**

- Determine the number of days since the last overdue date for non-standard asset classes.

### Decision Logic

| Condition | Result |
|---|---|
| PRO.LoanAccountCal.AssetClass <> 'STANDARD' AND PRO.LoanAccountCal.OverdueDays = 0 AND PRO.LoanAccountCal.LastOverdueClearedDate IS NOT NULL AND PRO.LoanAccountCal.LastOverdueClearedDate <= @ProcessDate | DATEDIFF(DAY, CAST(PRO.LoanAccountCal.LastOverdueClearedDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2)) |


### R7 — Determine EligibleForUpgrade (#WatchlistStaging)

**Affected Field:** `EligibleForUpgrade`

**Summary:**

- Set the 'EligibleForUpgrade' field based on the days since last overdue and asset class.

**Source context:**

- Target: #WatchlistStaging
- FROM #WatchlistStaging

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DaysSinceLastOverdue IS NULL | 'N' |
| AssetClass = 'SUBSTANDARD' AND DaysSinceLastOverdue >= @StandardWatchPeriodDays | 'Y' |
| AssetClass IN ('DOUBTFUL', 'LOSS') AND DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays | 'Y' |
| ELSE | 'N' |

### R8 — Delete overdue records

**Affected Field:** Not specified

**Applies to:**

- Account has overdue days greater than zero

**Summary:**

- Remove records from the NPA Upgrade Watchlist where the account ID is associated with overdue days greater than zero in the LoanAccountCal table.

## Calculations

### Calculation — DaysSinceLastOverdue

**Expression:**

```sql
DATEDIFF(DAY, CAST(PRO.LoanAccountCal.LastOverdueClearedDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastOverdue`

**Used By:**
READ PRO.LoanAccountCal; UPDATE PRO.LoanAccountCal

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — DaysSinceLastOverdue

**Expression:**

```sql
DATEDIFF(DAY, PRO.LoanAccountCal.LastOverdueClearedDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastOverdue`

**Used By:**
UPDATE PRO.LoanAccountCal


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: PRO.LoanAccountCal.DaysSinceLastOverdue, PRO.LoanAccountCal.AssetClass, PRO.LoanAccountCal.UpgradeDate |
| `PRO.NpaUpgradeWatchlist` | Read + Write | Deletes rows identified by: #WatchlistStaging.DaysSinceLastOverdue, #WatchlistStaging.EligibleForUpgrade, #WatchlistStaging.LastCheckedDate, AccountId, AssetClass, FirstWatchedDate |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#WatchlistStaging` | Read + Write | Inserts data into: AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade |

## Exception Handling

If an exception occurs during the process, the process status is updated to indicate an error, the error date and description are recorded, and the count of processed records is incremented.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
