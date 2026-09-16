# NPA Movement Audit Log — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Movement_Audit_Log` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 4 |
| Tables read | 7 |
| Tables written | 6 |
| Produces audit trail | Yes — records audit events |

## What This Does

The procedure updates the run status of the NPA_Movement_Audit_Log process, marking it as incomplete and recording an error if an exception occurs during execution.

## Process Flow

1. Insert asset class movements into PRO.AssetClassMovementHistory.
2. Insert customer class movements into PRO.CustomerClassMovementHistory.
3. Truncate PRO.PreviousAssetClass.
4. Update PRO.PreviousAssetClass with current account asset classes.
5. Update movement count in PRO.RunStatistics.
6. Flag customers with multiple account movements in PRO.CustomerCal.
7. Update run status in PRO.RunStatus.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Truncate previous asset class | `Not specified` | Clears previous asset class data in PRO.PreviousAssetClass. |
| Update movement count | `MovementCount` | Increments the movement count in PRO.RunStatistics. |
| Flag multi-account movements | `MultiAccountMovementFlag` | Flags customers with more than one account movement in PRO.CustomerCal. |
| Update run status on error | `COMPLETED, ErrorDate, ErrorDescription, RunCount` | If an exception occurs during the NPA_Movement_Audit_Log process, the run status is updated to indicate the process did not complete succes… |

## Business Rules

### R1 — Truncate previous asset class

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Clears previous asset class data in PreviousAssetClass.


### R2 — Update movement count

**Affected Field:** `MovementCount`

**Applies to:**

- Statistic name is 'DAILY_ASSET_MOVEMENTS'

**Summary:**

- Increments the movement count in RunStatistics.


### R3 — Flag multi-account movements

**Affected Field:** `MultiAccountMovementFlag`

**Applies to:**

- Customer has more than one account movement

**Summary:**

- Flags customers with more than one account movement in CustomerCal.


### R4 — Update run status on error

**Affected Field:** `COMPLETED, ErrorDate, ErrorDescription, RunCount`

**Applies to:**

- ProcessName is 'NPA_Movement_Audit_Log'

**Summary:**

- If an exception occurs during the NPA_Movement_Audit_Log process, the run status is updated to indicate the process did not complete successfully.

### Decision Logic

| Condition | Result |
|---|---|
| Exception occurs | N |

## Calculations

### Calculation — WorstClass

**Expression:**

```sql
MIN(AssetClass)
```

**Output:**
`PRO.CustomerClassMovementHistory.WorstClass`

**Used By:**
INSERT INTO PRO.CustomerClassMovementHistory

### Calculation — MovementCount

**Expression:**

```sql
MovementCount + (SELECT COUNT(*) FROM AssetClassMovementHistory WHERE TimeKey = @TimeKey)
```

**Output:**
`PRO.RunStatistics.MovementCount`

**Used By:**
UPDATE PRO.RunStatistics; READ PRO.RunStatistics

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
| `PRO.AssetClassMovementHistory` | Read + Write | Inserts data into: TimeKey, AccountId, PreviousClass, CurrentClass, MovementDate |
| `PRO.CustomerClassMovementHistory` | Read + Write | Inserts data into: TimeKey, CustomerId, WorstClass, MovementDate |
| `PRO.PreviousAssetClass` | Read + Write | Inserts data into: AccountId, AssetClass |
| `PRO.RunStatistics` | Read + Write | Updates: MovementCount |
| `PRO.CustomerCal` | Read + Write | Updates: MultiAccountMovementFlag |
| `PRO.RunStatus` | Read + Write | Updates: COMPLETED, ErrorDate, ErrorDescription, RunCount |
| `PRO.AccountCal` | Read | Provides: @TimeKey, CustomerId, MIN(B.AssetClass), GETDATE(), AccountId, AssetClass |

## Exception Handling

The procedure uses a TRY block to handle any potential errors during execution. If an exception occurs during the execution of the NPA_Movement_Audit_Log process, the procedure updates the run status to indicate the process did not complete successfully.

## Findings / Needs Review

- 3 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
