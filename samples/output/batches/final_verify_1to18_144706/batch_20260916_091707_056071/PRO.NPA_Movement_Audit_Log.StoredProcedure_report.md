# NPA Movement Audit Log — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Movement_Audit_Log` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 3 |
| Tables read | 7 |
| Tables written | 6 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates the run status of the NPA_Movement_Audit_Log process, marking it as incomplete and recording an error if an exception occurs during execution.

## Process Flow

1. Insert asset class movements into the AssetClassMovementHistory table.
2. Insert customer class movements into the CustomerClassMovementHistory table.
3. Truncate the PreviousAssetClass table.
4. Insert current asset classes into the PreviousAssetClass table.
5. Update the MovementCount in the RunStatistics table.
6. Set the MultiAccountMovementFlag for customers with multiple account movements.
7. Update the run status to mark the process as completed.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Truncate previous asset class | `Not specified` | Clears the previous asset class records to prepare for new data insertion. |
| Update movement count | `MovementCount` | Increments the movement count in the RunStatistics table based on the number of asset class movements recorded. |
| Flag multi-account movements | `MultiAccountMovementFlag` | Sets the MultiAccountMovementFlag to 'Y' for customers with more than one account movement in the current run. |

## Business Rules

### R1 — Truncate previous asset class

**Affected Field:** Not specified

**Applies to:** eligibility not documented.

**Summary:**

- Clears the previous asset class records to prepare for new data insertion.


### R2 — Update movement count

**Affected Field:** `MovementCount`

**Applies to:**

- StatisticName is 'DAILY_ASSET_MOVEMENTS'

**Summary:**

- Increments the movement count in the RunStatistics table based on the number of asset class movements recorded.

### Decision Logic

| Condition | Result |
|---|---|
| StatisticName = 'DAILY_ASSET_MOVEMENTS' | MovementCount = MovementCount + (SELECT COUNT(*) FROM AssetClassMovementHistory WHERE TimeKey = @TimeKey) |


### R3 — Flag multi-account movements

**Affected Field:** `MultiAccountMovementFlag`

**Applies to:**

- Customer has more than one account movement

**Summary:**

- Sets the MultiAccountMovementFlag to 'Y' for customers with more than one account movement in the current run.

### Decision Logic

| Condition | Result |
|---|---|
| CustomerId IN (SELECT CustomerId FROM CustomerClassMovementHistory WHERE TimeKey = @TimeKey GROUP BY CustomerId HAVING COUNT(*) > 1) | Set MultiAccountMovementFlag to 'Y' |

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

The procedure uses a TRY block to ensure that all operations are attempted, and any failures are caught and handled outside the scope of this extraction. If an exception occurs during the execution of the NPA_Movement_Audit_Log process, the run status is updated to reflect the error.

## Findings / Needs Review

- 4 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
