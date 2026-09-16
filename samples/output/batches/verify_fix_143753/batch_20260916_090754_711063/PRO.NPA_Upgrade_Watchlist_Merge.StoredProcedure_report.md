# NPA Upgrade Watchlist Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Upgrade_Watchlist_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 14 |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the DaysSinceLastOverdue field for accounts that are not classified as 'STANDARD' and have no overdue days, but have a LastOverdueClearedDate that is not null and is less than or equal to the process date. It also stages eligible accounts for upgrade in a temporary table and merges them into the NPA Upgrade Watchlist.

## Process Flow

1. Read the SysDayMatrix table to get the date for the provided TimeKey.
2. Update the DaysSinceLastOverdue, AssetClass, and UpgradeDate fields in the LoanAccountCal table for accounts that are not standard, have no overdue days, and have a cleared overdue date before the process date.
3. Insert records into the WatchlistStaging table for accounts that are eligible for upgrade.
4. Update the EligibleForUpgrade field in the WatchlistStaging table for records that are eligible for upgrade.
5. Merge data from the WatchlistStaging table into the NpaUpgradeWatchlist table.
6. Delete records from the NpaUpgradeWatchlist table for accounts that have overdue days greater than zero.
7. Read records from the NpaUpgradeWatchlist table for accounts that are eligible for upgrade.
8. Insert records into the AccountStatusAuditLog table for account status transitions.
9. Update the COMPLETED, ERRORDATE, ERRORDESCRIPTION, and COUNT fields in the ACLRUNNINGPROCESSSTATUS table for the NPA_Upgrade_Watchlist_Merge process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine EligibleForUpgrade | `EligibleForUpgrade` | Not specified |
| Update DaysSinceLastOverdue (DaysSinceLastOverdue) | `DaysSinceLastOverdue` | Update the 'DaysSinceLastOverdue' field in the 'PRO.LoanAccountCal' table. |
| Insert into WatchlistStaging | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Insert records into the '#WatchlistStaging' table with initial values for 'AccountId', 'AssetClass', 'DaysSinceLastOverdue', and 'EligibleF… |
| Update AssetClass and UpgradeDate | `AssetClass, UpgradeDate` | Update the 'AssetClass' and 'UpgradeDate' fields in the 'PRO.LoanAccountCal' table. |
| Calculate DaysSinceLastOverdue [1] | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have no overdue days, and have… |
| Merge temporary table into NPA Upgrade Watchlist | `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass` | Merge data from the temporary table into the NPA Upgrade Watchlist. |
| Calculate DaysSinceLastOverdue [2] | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not standard and have no overdue days. |
| Stage eligible accounts for upgrade (EligibleForUpgrade) | `EligibleForUpgrade` | Stage accounts for upgrade eligibility based on asset class and days since last overdue. |
| Stage eligible accounts for upgrade (S.EligibleForUpgrade) | `EligibleForUpgrade` | Stage accounts for upgrade eligibility based on asset class and days since last overdue. |
| Merge NPA Upgrade Watchlist records | `Not specified` | Merge, insert, update, and delete records in the NPA Upgrade Watchlist based on account status and overdue days. |
| Update DaysSinceLastOverdue (A.DaysSinceLastOverdue) | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date was cleared for accounts that are not standard, have no overdue days, and have a c… |
| Delete Eligible Accounts from NPA Upgrade Watchlist | `Not specified` | Delete records from the NPA Upgrade Watchlist where the account is eligible for upgrade. |
| Merge into NpaUpgradeWatchlist | `Target.DaysSinceLastOverdue, Target.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate` | Merge data from the WatchlistStaging table into the NpaUpgradeWatchlist table. |
| Delete Overdue Accounts from NPA Upgrade Watchlist | `Not specified` | Delete records from the NPA Upgrade Watchlist where the account has overdue days. |

## Business Rules

### R1 — Determine EligibleForUpgrade

**Affected Field:** `EligibleForUpgrade`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| DAY(@ProcessDate) = 1 — row filter: EligibleForUpgrade = 'Y' | 'PENDING_APPROVAL' |
| ELSE — applies to all rows (no additional filter) | EligibleForUpgrade |


### R2 — Update DaysSinceLastOverdue (DaysSinceLastOverdue)

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- The 'LoanAccountCal' table is being updated.

**Summary:**

- Update the 'DaysSinceLastOverdue' field in the 'LoanAccountCal' table.


### R3 — Insert into WatchlistStaging

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade`

**Applies to:**

- The '#WatchlistStaging' table is being inserted into.

**Summary:**

- Insert records into the '#WatchlistStaging' table with initial values for 'AccountId', 'AssetClass', 'DaysSinceLastOverdue', and 'EligibleForUpgrade'.


### R4 — Update AssetClass and UpgradeDate

**Affected Field:** `AssetClass, UpgradeDate`

**Applies to:**

- The 'LoanAccountCal' table is being updated.

**Summary:**

- Update the 'AssetClass' and 'UpgradeDate' fields in the 'LoanAccountCal' table.


### R5 — Calculate DaysSinceLastOverdue [1]

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not classified as 'STANDARD'
- Account has no overdue days
- Account has a LastOverdueClearedDate that is not null
- Account's LastOverdueClearedDate is less than or equal to the process date

**Summary:**

- Calculate the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have no overdue days, and have a LastOverdueClearedDate that is not null and is less than or equal to the process date.


### R6 — Merge temporary table into NPA Upgrade Watchlist

**Affected Field:** `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass`

**Applies to:** eligibility not documented.

**Summary:**

- Merge data from the temporary table into the NPA Upgrade Watchlist.


### R7 — Calculate DaysSinceLastOverdue [2]

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not standard
- Account has no overdue days
- Last overdue cleared date is not null
- Last overdue cleared date is on or before the process date

**Summary:**

- Calculate the number of days since the last overdue date for accounts that are not standard and have no overdue days.


### R8 — Stage eligible accounts for upgrade (EligibleForUpgrade)

**Affected Field:** `EligibleForUpgrade`

**Summary:**

- Stage accounts for upgrade eligibility based on asset class and days since last overdue.

**Source context:**

- Target: #WatchlistStaging
- FROM #WatchlistStaging AS S

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| #WatchlistStaging.DaysSinceLastOverdue IS NULL | 'N' |
| #WatchlistStaging.AssetClass = 'SUBSTANDARD' AND #WatchlistStaging.DaysSinceLastOverdue >= @StandardWatchPeriodDays | 'Y' |
| #WatchlistStaging.AssetClass IN ('DOUBTFUL', 'LOSS') AND #WatchlistStaging.DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays | 'Y' |
| ELSE | 'N' |

### R9 — Stage eligible accounts for upgrade (S.EligibleForUpgrade)

**Affected Field:** `EligibleForUpgrade`

**Summary:**

- Stage accounts for upgrade eligibility based on asset class and days since last overdue.

### Decision Logic

| Condition | Result |
|---|---|
| DaysSinceLastOverdue IS NULL | 'N' |
| AssetClass = 'SUBSTANDARD' AND DaysSinceLastOverdue >= @StandardWatchPeriodDays | 'Y' |
| AssetClass IN ('DOUBTFUL', 'LOSS') AND DaysSinceLastOverdue >= @DoubtfulWatchPeriodDays | 'Y' |
| ELSE | 'N' |

### R10 — Merge NPA Upgrade Watchlist records

**Affected Field:** Not specified

**Applies to:**

- Account has overdue days

**Summary:**

- Merge, insert, update, and delete records in the NPA Upgrade Watchlist based on account status and overdue days.


### R11 — Update DaysSinceLastOverdue (A.DaysSinceLastOverdue)

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not standard
- Account has no overdue days
- Account has a cleared overdue date before the process date

**Summary:**

- Calculate the number of days since the last overdue date was cleared for accounts that are not standard, have no overdue days, and have a cleared overdue date before the process date.

### Decision Logic

| Condition | Result |
|---|---|
| AssetClass <> 'STANDARD' AND OverdueDays = 0 AND LastOverdueClearedDate IS NOT NULL AND LastOverdueClearedDate <= @ProcessDate | DATEDIFF(DAY, CAST(LastOverdueClearedDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2)) |


### R12 — Delete Eligible Accounts from NPA Upgrade Watchlist

_Note: Also extracted with additional fields attached in another pass (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) - kept the narrower, consistent version of this rule._

**Affected Field:** Not specified

**Applies to:**

- Account is eligible for upgrade

**Summary:**

- Delete records from the NPA Upgrade Watchlist where the account is eligible for upgrade.

### Decision Logic

| Condition | Result |
|---|---|
| EligibleForUpgrade = 'Y' | DELETE FROM NpaUpgradeWatchlist WHERE EligibleForUpgrade = 'Y' |


### R13 — Merge into NpaUpgradeWatchlist

**Affected Field:** `Target.DaysSinceLastOverdue, Target.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate`

**Applies to:**

- Account ID in WatchlistStaging matches Account ID in NpaUpgradeWatchlist

**Summary:**

- Merge data from the WatchlistStaging table into the NpaUpgradeWatchlist table.

### Decision Logic

| Condition | Result |
|---|---|
| Target.AccountId = Source.AccountId | UPDATE SET Target.DaysSinceLastOverdue = Source.DaysSinceLastOverdue, Target.EligibleForUpgrade = Source.EligibleForUpgrade, Target.LastCheckedDate = @ProcessDate |
| Target.AccountId!= Source.AccountId | INSERT (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate) VALUES (Source.AccountId, Source.AssetClass, Source.DaysSinceLastOverdue, Source.EligibleForUpgrade, @ProcessDate, @ProcessDate) |


### R14 — Delete Overdue Accounts from NPA Upgrade Watchlist

_Note: Also extracted with additional fields attached in another pass (AccountId, EligibleForUpgrade, OverdueDays) - kept the narrower, consistent version of this rule._

**Affected Field:** Not specified

**Applies to:**

- Account has overdue days

**Summary:**

- Delete records from the NPA Upgrade Watchlist where the account has overdue days.

### Decision Logic

| Condition | Result |
|---|---|
| AccountId IN (SELECT AccountId FROM LoanAccountCal WHERE OverdueDays > 0) | DELETE FROM NpaUpgradeWatchlist WHERE AccountId IN (SELECT AccountId FROM LoanAccountCal WHERE OverdueDays > 0) |

## Calculations

### Calculation — DaysSinceLastOverdue

**Expression:**

```sql
DATEDIFF(DAY, LastOverdueClearedDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastOverdue`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — DaysSinceLastOverdue

**Expression:**

```sql
DATEDIFF(DAY, CAST(LastOverdueClearedDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastOverdue`

**Used By:**
UPDATE PRO.LoanAccountCal; READ PRO.LoanAccountCal

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`COUNT`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.LoanAccountCal` | Read + Write | Updates: DaysSinceLastOverdue, AssetClass, UpgradeDate |
| `PRO.NpaUpgradeWatchlist` | Read + Write | Deletes rows identified by: Target.AccountId, Target.DaysSinceLastOverdue, Target.EligibleForUpgrade, Target.LastCheckedDate, AssetClass, FirstWatchedDate |
| `PRO.AccountStatusAuditLog` | Write | Inserts data into: AccountId, TransitionDate, NewStatus, Reason |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |
| `SysDayMatrix` | Read | Provides: [Date] |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `#WatchlistStaging` | Read + Write | Inserts data into: AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade |

## Exception Handling

If an error occurs during the execution of the 'NPA_Upgrade_Watchlist_Merge' process, the procedure updates the status to indicate it is not completed, records the error date, captures the error message, and increments the error count.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 133-135 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 140-142 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
