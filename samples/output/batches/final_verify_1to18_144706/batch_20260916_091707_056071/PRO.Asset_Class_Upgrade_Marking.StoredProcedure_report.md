# Asset Class Upgrade Marking — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.Asset_Class_Upgrade_Marking` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 12 |
| Tables read | 3 |
| Tables written | 2 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the run status of the 'Asset_Class_Upgrade_Marking' process, marking it as incomplete and recording the error details if an exception occurs.

## Process Flow

1. Check if any accounts are not in the 'STANDARD' asset class.
2. If accounts exist that are not in the 'STANDARD' asset class, mark them as upgrade eligible if they meet certain criteria.
3. If no accounts are found that are not in the 'STANDARD' asset class, mark all accounts as not upgrade eligible.
4. Calculate the provision release amount for eligible accounts.
5. Calculate the provision amount for eligible accounts.
6. Update the run status to reflect the completion of the process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Calculate Provision Release Amount [1] | `ProvisionReleaseAmount` | The provision release amount is calculated for eligible accounts. |
| Reclassify to Standard with Base Provisioning | `AssetClass, ProvisionPct, ProvisionAmount` | Eligible accounts are reclassified back to standard with base provisioning. |
| Stamp Upgrade Date | `UpgradeDate` | The upgrade date is stamped for eligible accounts. |
| Update Run Status [1] | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | The run status is updated to mark the process as completed and increment the run count. |
| Determine UpgradeEligible | `UpgradeEligible` | Not specified |
| Calculate Provision Release Amount [2] | `ProvisionReleaseAmount` | Calculate the provision release amount for eligible accounts. |
| Calculate provision amount | `ProvisionAmount` | Calculate the provision amount for eligible accounts. |
| Update Run Status [2] | `RunCount, COMPLETED, ErrorDate, ErrorDescription` | Update the run status to reflect the completion of the process. |
| Mark process as incomplete on error | `COMPLETED` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run status is marked as incomplete. |
| Record error date on exception | `ErrorDate` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the current date and time are recorded as the error date. |
| Record error description on exception | `ErrorDescription` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the error message is recorded as the error description. |
| Increment run count on exception | `RunCount` | If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run count is incremented by one. |

## Business Rules

### R1 — Calculate Provision Release Amount [1]

**Affected Field:** `ProvisionReleaseAmount`

**Applies to:**

- UpgradeEligible = 'Y'

**Summary:**

- The provision release amount is calculated for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | ProvisionAmount - ((OutstandingBalance * StandardProvisionPct) / 100) |


### R2 — Reclassify to Standard with Base Provisioning

**Affected Field:** `AssetClass, ProvisionPct, ProvisionAmount`

**Applies to:**

- UpgradeEligible = 'Y'

**Summary:**

- Eligible accounts are reclassified back to standard with base provisioning.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | 'STANDARD' |


### R3 — Stamp Upgrade Date

**Affected Field:** `UpgradeDate`

**Applies to:**

- UpgradeEligible = 'Y'

**Summary:**

- The upgrade date is stamped for eligible accounts.

### Decision Logic

| Condition | Result |
|---|---|
| UpgradeEligible = 'Y' | @ProcessDate |


### R4 — Update Run Status [1]

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- ProcessName = 'Asset_Class_Upgrade_Marking'

**Summary:**

- The run status is updated to mark the process as completed and increment the run count.

### Decision Logic

| Condition | Result |
|---|---|
| ProcessName = 'Asset_Class_Upgrade_Marking' | ISNULL(RunCount, 0) + 1 |


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


### R6 — Calculate Provision Release Amount [2]

**Affected Field:** `ProvisionReleaseAmount`

**Applies to:**

- Accounts are upgrade eligible

**Summary:**

- Calculate the provision release amount for eligible accounts.


### R7 — Calculate provision amount

**Affected Field:** `ProvisionAmount`

**Applies to:**

- Accounts are upgrade eligible

**Summary:**

- Calculate the provision amount for eligible accounts.


### R8 — Update Run Status [2]

**Affected Field:** `RunCount, COMPLETED, ErrorDate, ErrorDescription`

**Applies to:**

- The process name is 'Asset_Class_Upgrade_Marking'

**Summary:**

- Update the run status to reflect the completion of the process.


### R9 — Mark process as incomplete on error

**Affected Field:** `COMPLETED`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run status is marked as incomplete.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | 'N' |


### R10 — Record error date on exception

**Affected Field:** `ErrorDate`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the current date and time are recorded as the error date.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | GETDATE() |


### R11 — Record error description on exception

**Affected Field:** `ErrorDescription`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the error message is recorded as the error description.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | ERROR_MESSAGE() |


### R12 — Increment run count on exception

**Affected Field:** `RunCount`

**Applies to:**

- ProcessName is 'Asset_Class_Upgrade_Marking'

**Summary:**

- If an exception occurs during the 'Asset_Class_Upgrade_Marking' process, the run count is incremented by one.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | ISNULL(RunCount, 0) + 1 |

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
`PRO.RunStatus.RunCount`

**Used By:**
UPDATE PRO.RunStatus; READ PRO.RunStatus


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal` | Read + Write | Updates: UpgradeEligible, ProvisionReleaseAmount, AssetClass, ProvisionPct, ProvisionAmount, UpgradeDate |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `SysDayMatrix` | Read | Provides: [Date] |

## Exception Handling

The procedure uses a TRY-CATCH block to handle exceptions, but the specific handling steps are not detailed in the provided extraction. The procedure does not explicitly handle exceptions. If an exception occurs during the execution of the 'Asset_Class_Upgrade_Marking' process, the run status is marked as incomplete, the error date and time are recorded, the error message is recorded, and the run count is incremented.

## Findings / Needs Review

- The extraction does not provide specific details on the asset class upgrade or marking process, such as the conditions or outcomes involved.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
