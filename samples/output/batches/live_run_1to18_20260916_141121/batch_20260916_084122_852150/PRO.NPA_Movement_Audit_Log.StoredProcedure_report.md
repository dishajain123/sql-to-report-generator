# NPA Movement Audit Log — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.NPA_Movement_Audit_Log` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 2 |
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
6. Flag customers with multiple account movements in the CustomerCal table.
7. Update the run status in the RunStatus table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Update movement count | `MovementCount` | Increments the movement count in the run statistics table. |
| Flag multi-account movements | `MultiAccountMovementFlag` | Flags customers with more than one account moving in the current run for manual review. |

## Business Rules

### R1 — Update movement count

**Affected Field:** `MovementCount`

**Applies to:**

- StatisticName is DAILY_ASSET_MOVEMENTS

**Summary:**

- Increments the movement count in the run statistics table.


### R2 — Flag multi-account movements

**Affected Field:** `MultiAccountMovementFlag`

**Applies to:**

- Customer has more than one account moving

**Summary:**

- Flags customers with more than one account moving in the current run for manual review.

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

No explicit exception handling is defined in the provided extraction. The procedure uses a TRY-CATCH block to handle any exceptions that may occur during execution. If an exception occurs during the execution of the NPA_Movement_Audit_Log process, the procedure updates the run status to reflect an incomplete process and records the error details.

## Findings / Needs Review

- 5 claims generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
