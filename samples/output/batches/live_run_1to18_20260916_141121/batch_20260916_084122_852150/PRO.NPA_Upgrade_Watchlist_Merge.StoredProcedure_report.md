# NPA Upgrade Watchlist Merge — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Upgrade_Watchlist_Merge` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 7 needs review |
| Tables read | 4 |
| Tables written | 4 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 7 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure updates the 'DaysSinceLastOverdue' and 'AssetClass' fields in the 'PRO.LoanAccountCal' table and inserts/updates records in the '#WatchlistStaging' table based on the input time key.

## Process Flow

1. Calculate the number of days since the last overdue date for accounts.
2. Stage eligible accounts for upgrade in a temporary table.
3. Determine if accounts are eligible for upgrade based on their days since last overdue and asset class.
4. Update the eligibility status of accounts in the staging table based on the process date.
5. Merge the staging table data into the NPA Upgrade Watchlist.
6. Delete records from the NPA Upgrade Watchlist for accounts with overdue days greater than zero.
7. Update the asset class and upgrade date for eligible accounts.
8. Log the account status transition in the account status audit log.
9. Delete records from the NPA Upgrade Watchlist where the accounts are eligible for upgrade.
10. Update the running process status in the ACL Running Process Status table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate Days Since Last Overdue | `DaysSinceLastOverdue` | Compute the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have zero overdue days, and a no… |
| ⚠️ Stage Eligible Accounts for Upgrade | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade` | Insert accounts into a staging table that are not classified as 'STANDARD' and have zero overdue days. |
| ⚠️ Update Eligibility Status on First Day of Month | `EligibleForUpgrade` | Set the eligibility status for upgrade in the staging table to 'PENDING_APPROVAL' if the process date is the first day of the month. |
| ⚠️ Merge Staging Data into Watchlist | `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate` | Merge data from the staging table into the NPA Upgrade Watchlist, updating existing records and inserting new ones. |
| ⚠️ Delete Overdue Accounts from Watchlist | `AccountId, OverdueDays, EligibleForUpgrade` | Remove records from the NPA Upgrade Watchlist for accounts with overdue days greater than zero. |
| ⚠️ Log Account Status Transition | `AccountId, TransitionDate, NewStatus, Reason` | Insert a record into the account status audit log for accounts that have been upgraded to 'STANDARD'. |
| ⚠️ Delete Eligible Accounts from Watchlist | `AccountId, OverdueDays, EligibleForUpgrade` | Remove records from the NPA Upgrade Watchlist for accounts that are eligible for upgrade. |

## Business Rules

### R1 — Calculate Days Since Last Overdue

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `DaysSinceLastOverdue`

**Applies to:**

- Account is not classified as 'STANDARD'
- Account has zero overdue days
- Last overdue cleared date is not null
- Last overdue cleared date is on or before the process date

**Summary:**

- Compute the number of days since the last overdue date for accounts that are not classified as 'STANDARD', have zero overdue days, and a non-null last overdue cleared date.


### R2 — Stage Eligible Accounts for Upgrade

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade`

**Applies to:**

- Account is not classified as 'STANDARD'
- Account has zero overdue days

**Summary:**

- Insert accounts into a staging table that are not classified as 'STANDARD' and have zero overdue days.


### R3 — Update Eligibility Status on First Day of Month

**Affected Field:** `EligibleForUpgrade`

**Summary:**

- Set the eligibility status for upgrade in the staging table to 'PENDING_APPROVAL' if the process date is the first day of the month.

### Decision Logic

| Condition | Result |
|---|---|
| DAY(@ProcessDate) = 1 | Set EligibleForUpgrade to 'PENDING_APPROVAL' if EligibleForUpgrade = 'Y' |
| ELSE |  |

### R4 — Merge Staging Data into Watchlist

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, AssetClass, DaysSinceLastOverdue, EligibleForUpgrade, FirstWatchedDate, LastCheckedDate`

**Applies to:** eligibility not documented.

**Summary:**

- Merge data from the staging table into the NPA Upgrade Watchlist, updating existing records and inserting new ones.


### R5 — Delete Overdue Accounts from Watchlist

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, OverdueDays, EligibleForUpgrade`

**Applies to:**

- Account has overdue days greater than zero

**Summary:**

- Remove records from the NPA Upgrade Watchlist for accounts with overdue days greater than zero.


### R6 — Log Account Status Transition

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, TransitionDate, NewStatus, Reason`

**Applies to:**

- Account is eligible for upgrade
- Account asset class is 'STANDARD'
- Account upgrade date is the process date

**Summary:**

- Insert a record into the account status audit log for accounts that have been upgraded to 'STANDARD'.


### R7 — Delete Eligible Accounts from Watchlist

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AccountId, OverdueDays, EligibleForUpgrade`

**Applies to:**

- Account is eligible for upgrade

**Summary:**

- Remove records from the NPA Upgrade Watchlist for accounts that are eligible for upgrade.

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
DATEDIFF(DAY, CAST(LastOverdueClearedDate AS DATETIME2), CAST(@ProcessDate AS DATETIME2))
```

**Output:**
`DaysSinceLastOverdue`

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

The procedure uses a TRY block to handle exceptions, but the specific handling steps are not detailed in the extraction. If an error occurs during the execution of the procedure, the status of the 'NPA_Upgrade_Watchlist_Merge' process is updated to indicate it is not completed, the error date is recorded, the error message is captured, and the error count is incremented.

## Findings / Needs Review

- Lines 27-27 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 133-135 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 140-142 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
