# GovtGuarAppropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.GovtGuarAppropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 1 confident, 3 needs review |
| Tables read | 1 |
| Tables written | 1 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure updates the running process status for the 'GovtGuarAppropriation' process, marking it as not completed and incrementing the error count if an exception occurs.

## Process Flow

1. Initialize the AppGovGur field to zero for accounts not currently being processed.
2. Calculate the government guarantee amount for eligible accounts and store it in a temporary table.
3. Update the AppGovGur field for accounts with calculated government guarantee amounts.
4. Update the AppGovGur field for accounts without calculated government guarantee amounts.
5. Mark the process as completed and increment the process count in the running process status table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Reset AppGovGur to zero | `AppGovGur` | Set the AppGovGur field to zero for accounts not currently being processed. |
| Determine GovGur | `GovGur` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Update AppGovGur with calculated amount | `AppGovGur` | Update the AppGovGur field for accounts with calculated government guarantee amounts. |
| ⚠️ Update AppGovGur for non-eligible accounts | `AppGovGur` | Update the AppGovGur field for accounts without calculated government guarantee amounts. |

## Business Rules

### R1 — Reset AppGovGur to zero

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Customer is not currently mid-processing

**Summary:**

- Set the AppGovGur field to zero for accounts not currently being processed.

### Decision Logic

| Condition | Result |
|---|---|
| FlgProcessing = 'N' | 0 |


### R2 — Determine GovGur

**Affected Field:** `GovGur`


**Applies to:**

- ##ACCOUNTCAL.FacilityType IN ('BP', 'BD') AND COALESCE(##ACCOUNTCAL.GovtGtyAmt, 0) > 0

**Source context:**

- Target: #TEMPTABLEAppGovGur
- FROM ##ACCOUNTCAL AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SUM(##ACCOUNTCAL.NetBalance) OVER (PARTITION BY ##ACCOUNTCAL.CustomerEntityId) > 0 | (##ACCOUNTCAL.GovtGtyAmt * (##ACCOUNTCAL.NetBalance / SUM(##ACCOUNTCAL.NetBalance) OVER (PARTITION BY ##ACCOUNTCAL.CustomerEntityId))) |
| ELSE | NULL |

### R3 — Update AppGovGur with calculated amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Account facility type is BP or BD

**Summary:**

- Update the AppGovGur field for accounts with calculated government guarantee amounts.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN('BP','BD') | GovGur |


### R4 — Update AppGovGur for non-eligible accounts

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Account facility type is not BP or BD

**Summary:**

- Update the AppGovGur field for accounts without calculated government guarantee amounts.

### Decision Logic

| Condition | Result |
|---|---|
| NOT (FacilityType IN('BP','BD')) | GovtGtyAmt |

## Calculations

### Calculation — GovGur

**Expression:**

```sql
    (CASE
    WHEN SUM(NetBalance) OVER (PARTITION BY CustomerEntityId) > 0 THEN (GovtGtyAmt * (NetBalance / SUM(NetBalance) OVER (PARTITION BY CustomerEntityId)))
END)
```

**Output:**
`#TEMPTABLEAppGovGur.GovGur`

**Used By:**
INSERT INTO #TEMPTABLEAppGovGur

### Calculation — GovGur

**Expression:**

```sql
(GovtGtyAmt * (NetBalance / SUM(NetBalance) OVER (PARTITION BY CustomerEntityId)))
```

**Output:**
`Not specified`

**Used By:**
Not specified

### Calculation — COUNT

**Expression:**

```sql
COALESCE(COUNT, 0) + 1
```

**Output:**
`COUNT`

**Used By:**
Not specified

### Calculation — COUNT

**Expression:**

```sql
ISNULL(COUNT,0)+1
```

**Output:**
`COUNT`

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | Updates: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `##ACCOUNTCAL` | Read + Write | Updates: AppGovGur |
| `#TEMPTABLEAppGovGur` | Read + Write | Inserts data into: AccountEntityID, (CASE WHEN SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId) > 0 THEN (A.GovtGtyAmt * (A.NetBalance / SUM(A.NetBalance) OVER (PARTITION BY A.CustomerEntityId))) END) AS GovGur |
| `##CustomerCal` | Read | Provides: FlgProcessing, CustomerEntityID |

## Exception Handling

The procedure uses a TRY-CATCH block to handle any potential errors during execution. If an exception occurs during the execution of the 'GovtGuarAppropriation' process, the procedure updates the running process status to indicate the error and increments the error count.

## Findings / Needs Review

- Lines 30-30 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 51-53 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 63-65 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
