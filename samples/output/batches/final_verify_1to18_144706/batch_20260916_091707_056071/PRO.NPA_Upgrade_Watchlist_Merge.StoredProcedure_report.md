# NPA Upgrade Watchlist Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Upgrade_Watchlist_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 15 |
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
| Update DaysSinceLastOverdue (DaysSinceLastOverdue) | `DaysSinceLastOverdue` | Update the 'DaysSinceLastOverdue' field in the 'PRO.LoanAccountCal' table. |
| Calculate DaysSinceLastOverdue [1] | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not standard and have no overdue days. |
| Merge NPA Upgrade Watchlist | `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass` | Merge records into the NPA Upgrade Watchlist based on account status and overdue days. |
| Calculate days since last overdue | `DaysSinceLastOverdue` | Determine the number of days since the last overdue date for accounts that are not 'STANDARD' and have zero overdue days. |
| Insert into Watchlist Staging | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Insert eligible accounts into the Watchlist Staging table. |
| Merge into NPA Upgrade Watchlist | `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass` | Merge data from the Loan Account Calculation table into the NPA Upgrade Watchlist. |
| Delete from NPA Upgrade Watchlist | `AccountId, OverdueDays, EligibleForUpgrade` | Delete records from the NPA Upgrade Watchlist where the account has overdue days. |
| Insert into Account Status Audit Log | `AccountId, TransitionDate, NewStatus, Reason` | Insert a record into the Account Status Audit Log for accounts that have been marked as 'STANDARD' and have an upgrade date matching the pr… |
| Delete from NPA Upgrade Watchlist by EligibleForUpgrade | `AccountId, OverdueDays, EligibleForUpgrade` | Delete records from the NPA Upgrade Watchlist where the account is eligible for upgrade. |
| Determine EligibleForUpgrade | `EligibleForUpgrade` | Not specified |
| Calculate DaysSinceLastOverdue [2] | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have no overdue days, and have… |
| Merge temporary table into NPA Upgrade Watchlist | `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass` | Merge data from the temporary table into the NPA Upgrade Watchlist. |
| Update DaysSinceLastOverdue (A.DaysSinceLastOverdue) | `DaysSinceLastOverdue` | Calculate the number of days since the last overdue date was cleared for accounts that are not standard, have no overdue days, and have a c… |
| Insert into WatchlistStaging [2] | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Stage eligible accounts in the WatchlistStaging table. |
| Merge into NpaUpgradeWatchlist | `Target.DaysSinceLastOverdue, Target.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate` | Merge data from the WatchlistStaging table into the NpaUpgradeWatchlist table. |

## Business Rules

### R1 — Update DaysSinceLastOverdue (DaysSinceLastOverdue)

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- The 'LoanAccountCal' table is being updated

**Summary:**

- Update the 'DaysSinceLastOverdue' field in the 'LoanAccountCal' table.


### R2 — Calculate DaysSinceLastOverdue [1]

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not standard
- Account has no overdue days
- Last overdue cleared date is not null
- Last overdue cleared date is on or before the process date

**Summary:**

- Calculate the number of days since the last overdue date for accounts that are not standard and have no overdue days.


### R3 — Merge NPA Upgrade Watchlist

**Affected Field:** `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass`

**Applies to:**

- Account ID is in the list of accounts with overdue days greater than 0

**Summary:**

- Merge records into the NPA Upgrade Watchlist based on account status and overdue days.


### R4 — Calculate days since last overdue

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not 'STANDARD'
- Account has zero overdue days
- Last overdue cleared date is not null
- Last overdue cleared date is on or before the process date

**Summary:**

- Determine the number of days since the last overdue date for accounts that are not 'STANDARD' and have zero overdue days.


### R5 — Insert into Watchlist Staging

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade`

**Applies to:**

- Account is not 'STANDARD'
- Account has zero overdue days
- Last overdue cleared date is not null
- Last overdue cleared date is on or before the process date

**Summary:**

- Insert eligible accounts into the Watchlist Staging table.


### R6 — Merge into NPA Upgrade Watchlist

**Affected Field:** `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass`

**Applies to:**

- EligibleForUpgrade status is 'Y'

**Summary:**

- Merge data from the Loan Account Calculation table into the NPA Upgrade Watchlist.


### R7 — Delete from NPA Upgrade Watchlist

**Affected Field:** `AccountId, OverdueDays, EligibleForUpgrade`

**Applies to:**

- Account Id is in the list of accounts with overdue days

**Summary:**

- Delete records from the NPA Upgrade Watchlist where the account has overdue days.


### R8 — Insert into Account Status Audit Log

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:**

- EligibleForUpgrade status is 'Y'
- Asset class is 'STANDARD'
- Upgrade date matches the process date

**Summary:**

- Insert a record into the Account Status Audit Log for accounts that have been marked as 'STANDARD' and have an upgrade date matching the process date.


### R9 — Delete from NPA Upgrade Watchlist by EligibleForUpgrade

**Affected Field:** `AccountId, OverdueDays, EligibleForUpgrade`

**Applies to:**

- EligibleForUpgrade status is 'Y'

**Summary:**

- Delete records from the NPA Upgrade Watchlist where the account is eligible for upgrade.


### R10 — Determine EligibleForUpgrade

**Affected Field:** `EligibleForUpgrade`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| DAY(@ProcessDate) = 1 — row filter: EligibleForUpgrade = 'Y' | 'PENDING_APPROVAL' |
| ELSE — applies to all rows (no additional filter) | EligibleForUpgrade |


### R11 — Calculate DaysSinceLastOverdue [2]

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not classified as 'STANDARD'
- Account has no overdue days
- Account has a LastOverdueClearedDate that is not null
- Account's LastOverdueClearedDate is less than or equal to the process date

**Summary:**

- Calculate the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have no overdue days, and have a LastOverdueClearedDate that is not null and is less than or equal to the process date.


### R12 — Merge temporary table into NPA Upgrade Watchlist

**Affected Field:** `Target.AccountId, Source.AccountId, Target.DaysSinceLastOverdue, Source.DaysSinceLastOverdue, Target.EligibleForUpgrade, Source.EligibleForUpgrade, Target.LastCheckedDate, AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate, Source.AssetClass`

**Applies to:** eligibility not documented.

**Summary:**

- Merge data from the temporary table into the NPA Upgrade Watchlist.


### R13 — Update DaysSinceLastOverdue (A.DaysSinceLastOverdue)

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


### R14 — Insert into WatchlistStaging [2]

_Note: Also extracted with additional fields attached in another pass (A.AccountId, W.AccountId, W.AssetClass, W.EligibleForUpgrade) - kept the narrower, consistent version of this rule._

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade`

**Applies to:**

- Account is eligible for upgrade

**Summary:**

- Stage eligible accounts in the WatchlistStaging table.

### Decision Logic

| Condition | Result |
|---|---|
| EligibleForUpgrade = 'Y' | INSERT INTO #WatchlistStaging (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) VALUES (AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade) |


### R15 — Merge into NpaUpgradeWatchlist

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

## Calculations

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
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

### Calculation — DaysSinceLastOverdue

**Expression:**

```sql
DATEDIFF(DAY, LastOverdueClearedDate, @ProcessDate)
```

**Output:**
`PRO.LoanAccountCal.DaysSinceLastOverdue`

**Used By:**
UPDATE PRO.LoanAccountCal


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

If an error occurs during the execution of the 'NPA_Upgrade_Watchlist_Merge' process, the procedure updates the status, records the error date, captures the error description, and increments the error count.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- 8 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
