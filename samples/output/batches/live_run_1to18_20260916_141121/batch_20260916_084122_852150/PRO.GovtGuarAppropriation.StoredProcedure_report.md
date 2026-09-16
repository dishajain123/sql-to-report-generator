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

The procedure updates the running process status for the 'GovtGuarAppropriation' process, marking it as incomplete and incrementing the error count if an exception occurs.

## Process Flow

1. Reset AppGovGur to zero for accounts where the customer is not currently being processed.
2. Create a temporary table to store the calculated government guarantee amounts for specific facility types.
3. Calculate and insert the government guarantee amounts into the temporary table for accounts with specific facility types and non-zero government guarantee amounts.
4. Update the AppGovGur field in the account records with the calculated government guarantee amounts from the temporary table for accounts with specific facility types.
5. Update the AppGovGur field in the account records with the government guarantee amount for accounts with facility types other than specified.
6. Update the running process status to mark the process as completed and increment the count for the 'GovtGuarAppropriation' process.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Reset AppGovGur to zero | `AppGovGur` | For accounts where the customer is not currently being processed, the AppGovGur field is reset to zero. |
| Determine GovGur | `GovGur` | First matching row wins; ELSE includes false or NULL predicates. |
| ⚠️ Update AppGovGur with calculated amount | `AppGovGur` | Update the AppGovGur field in the account records with the calculated government guarantee amount from the temporary table for accounts wit… |
| ⚠️ Update AppGovGur with government guarantee amount | `AppGovGur` | Update the AppGovGur field in the account records with the government guarantee amount for accounts with facility types other than specifie… |

## Business Rules

### R1 — Reset AppGovGur to zero

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Customer is not currently mid-processing

**Summary:**

- For accounts where the customer is not currently being processed, the AppGovGur field is reset to zero.

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

- Account has specific facility types

**Summary:**

- Update the AppGovGur field in the account records with the calculated government guarantee amount from the temporary table for accounts with specific facility types.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN('BP','BD') | GovGur |


### R4 — Update AppGovGur with government guarantee amount

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Account has facility types other than specified

**Summary:**

- Update the AppGovGur field in the account records with the government guarantee amount for accounts with facility types other than specified.

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

The procedure uses a TRY block to handle any potential errors during execution, but no specific exception handling steps are detailed in the extraction. The procedure handles exceptions by updating the running process status for the 'GovtGuarAppropriation' process to indicate an error.

## Findings / Needs Review

- Lines 30-30 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 51-53 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.
- Lines 63-65 (ASSIGNMENT/UPDATE) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
