# Asset Class Upgrade Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Asset_Class_Upgrade_Marking` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 5 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the run status of the 'Asset_Class_Upgrade_Marking' process, marking it as incomplete and recording the error details if an exception occurs.

## Process Flow

1. Check if any accounts are not in the 'STANDARD' asset class.
2. If accounts exist with a non-standard asset class, mark them as upgrade eligible if they have been overdue for 90 days or more.
3. If no accounts are found with a non-standard asset class, mark all accounts as not upgrade eligible.
4. Calculate the provision release amount for eligible accounts.
5. Reclassify eligible accounts back to the 'STANDARD' asset class with base provisioning.
6. Record the date of the upgrade for eligible accounts.
7. Update the process status to indicate completion and increment the run count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate provision release amount | `ProvisionReleaseAmount` | Computes the provision release amount for eligible accounts. |
| Reclassify accounts to standard | `AssetClass, ProvisionPct, ProvisionAmount` | Reclassifies eligible accounts to the 'STANDARD' asset class with base provisioning. |
| Record upgrade date | `UpgradeDate` | Stamps the date the upgrade took effect for eligible accounts. |
| Update process status | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Marks the process as completed and increments the run count. |
| Determine UpgradeEligible | `UpgradeEligible` | Not specified |

## Business Rules

### R1 — Calculate provision release amount

**Affected Field:** `ProvisionReleaseAmount`

**Applies to:**

- Accounts are upgrade eligible

**Summary:**

- Computes the provision release amount for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | ProvisionAmount - ((OutstandingBalance * StandardProvisionPct) / 100) |


### R2 — Reclassify accounts to standard

**Affected Field:** `AssetClass, ProvisionPct, ProvisionAmount`

**Applies to:**

- Accounts are upgrade eligible

**Summary:**

- Reclassifies eligible accounts to the 'STANDARD' asset class with base provisioning.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | 'STANDARD', StandardProvisionPct, (OutstandingBalance * StandardProvisionPct) / 100 |


### R3 — Record upgrade date

**Affected Field:** `UpgradeDate`

**Applies to:**

- Accounts are upgrade eligible

**Summary:**

- Stamps the date the upgrade took effect for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | @ProcessDate |


### R4 — Update process status

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- Marks the process as completed and increments the run count.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'Asset_Class_Upgrade_Marking' | 'Y', NULL, NULL, ISNULL(RunCount, 0) + 1 |


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

The procedure uses a TRY block to handle exceptions, but the specific handling details are not provided in the extraction. If an exception occurs during the execution of the 'Asset_Class_Upgrade_Marking' process, the procedure updates the run status in the PRO.RunStatus table to reflect the error.

## Findings / Needs Review

- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
