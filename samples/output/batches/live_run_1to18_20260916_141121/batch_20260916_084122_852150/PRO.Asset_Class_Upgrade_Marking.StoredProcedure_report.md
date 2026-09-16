# Asset Class Upgrade Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Asset_Class_Upgrade_Marking` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 9 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

This procedure determines the eligibility of accounts for asset class upgrades, reclassifies eligible accounts, and updates relevant account and process status fields.

## Process Flow

1. Check if there are any accounts with a non-standard asset class.
2. If non-standard accounts exist, update their eligibility for upgrade based on overdue days and days since last overdue.
3. Calculate the provision release amount for eligible accounts.
4. Reclassify eligible accounts back to the standard asset class with base provisioning.
5. Update the provision percentage and amount for eligible accounts.
6. Set the upgrade date for eligible accounts.
7. Mark the process as completed and increment the run count in the process status table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate provision release amount | `ProvisionReleaseAmount` | The provision release amount is calculated for eligible accounts based on their outstanding balance and standard provision percentage. |
| Reclassify eligible accounts | `AssetClass, ProvisionPct, ProvisionAmount` | Eligible accounts are reclassified to the standard asset class with base provisioning. |
| Set upgrade date | `UpgradeDate` | The upgrade date is set for eligible accounts. |
| Update process status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | The process status is marked as completed, and the run count is incremented. |
| Determine UpgradeEligible | `UpgradeEligible` | Not specified |
| Mark process as incomplete on error | `COMPLETED` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run status is marked as incomplete. |
| Record error date on exception | `ErrorDate` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the current date and time are recorded as the error date. |
| Record error description on exception | `ErrorDescription` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the error message is recorded as the error description. |
| Increment run count on exception | `RunCount` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run count is incremented by one. |

## Business Rules

### R1 — Calculate provision release amount

**Affected Field:** `ProvisionReleaseAmount`

**Applies to:**

- Eligible accounts

**Summary:**

- The provision release amount is calculated for eligible accounts based on their outstanding balance and standard provision percentage.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | ProvisionAmount - ((OutstandingBalance * StandardProvisionPct) / 100) |


### R2 — Reclassify eligible accounts

**Affected Field:** `AssetClass, ProvisionPct, ProvisionAmount`

**Applies to:**

- Eligible accounts

**Summary:**

- Eligible accounts are reclassified to the standard asset class with base provisioning.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | 'STANDARD', StandardProvisionPct, (OutstandingBalance * StandardProvisionPct) / 100 |


### R3 — Set upgrade date

**Affected Field:** `UpgradeDate`

**Applies to:**

- Eligible accounts

**Summary:**

- The upgrade date is set for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | @ProcessDate |


### R4 — Update process status

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- Process with name 'Asset_Class_Upgrade_Marking'

**Summary:**

- The process status is marked as completed, and the run count is incremented.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'Asset_Class_Upgrade_Marking' | COMPLETED = 'Y', ErrorDate = NULL, ErrorDescription = NULL, RunCount = ISNULL(RunCount, 0) + 1 |


### R5 — Determine UpgradeEligible

**Affected Field:** `UpgradeEligible`

**Applies to:** eligibility not documented.

**Summary:**

- Not explicitly determined from source SQL.

### Decision Logic

| Condition | Result |
|---|---|
| EXISTS (SELECT 1 FROM AccountCal WHERE AssetClass <> 'STANDARD') — row filter: AssetClass <> 'STANDARD' AND OverdueDays = 0 AND DaysSinceLastOverdue >= @ReviewPeriodDays | 'Y' |
| ELSE — applies to all rows (no additional filter) | 'N' |


### R6 — Mark process as incomplete on error

**Affected Field:** `COMPLETED`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run status is marked as incomplete.


### R7 — Record error date on exception

**Affected Field:** `ErrorDate`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the current date and time are recorded as the error date.


### R8 — Record error description on exception

**Affected Field:** `ErrorDescription`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the error message is recorded as the error description.


### R9 — Increment run count on exception

**Affected Field:** `RunCount`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run count is incremented by one.

## Calculations

### Calculation — ProvisionReleaseAmount

**Expression:**

```sql
ProvisionAmount - ((OutstandingBalance * StandardProvisionPct) / 100)
```

**Output:**
`PRO.AccountCal.ProvisionReleaseAmount`

**Used By:**
UPDATE PRO.AccountCal; READ PRO.AccountCal

### Calculation — ProvisionAmount

**Expression:**

```sql
(OutstandingBalance * StandardProvisionPct) / 100
```

**Output:**
`PRO.AccountCal.ProvisionAmount`

**Used By:**
UPDATE PRO.AccountCal; READ PRO.AccountCal

### Calculation — RunCount

**Expression:**

```sql
COALESCE(RunCount, 0) + 1
```

**Output:**
`RunCount`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: UpgradeEligible, ProvisionReleaseAmount, AssetClass, ProvisionPct, ProvisionAmount, UpgradeDate |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

## Exception Handling

The procedure uses a TRY-CATCH block to handle exceptions, but the specific handling steps are not detailed in the extraction. If an exception occurs during the execution of the 'Asset_Class_Upgrade_Marking' process, the run status is updated to reflect the error, including marking the process as incomplete, recording the error date, error description, and incrementing the run count.

## Findings / Needs Review

- The extraction does not provide specific details on the asset class upgrade or marking process, such as the conditions, actions, or fields affected.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
