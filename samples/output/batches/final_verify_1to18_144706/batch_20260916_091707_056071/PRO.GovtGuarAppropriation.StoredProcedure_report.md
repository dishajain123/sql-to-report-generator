# GovtGuarAppropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.GovtGuarAppropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 0 confident, 3 needs review |
| Tables read | 1 |
| Tables written | 1 |
| Produces audit trail | Not detected |
| **Run status** | ⚠️ **Partial — see rules marked "Needs Review" below.** 3 rule(s) came from a chunk or section whose analysis was truncated or failed and had to be recovered; affected rules are marked inline rather than silently filled in. |

## What This Does

The procedure calculates and updates the government guarantee appropriation for accounts based on their facility type and net balance, and updates the running process status.

## Process Flow

1. Reset AppGovGur to zero for accounts where the customer is not currently being processed.
2. Create a temporary table to store the calculated government guarantee amounts for specific facility types and non-zero government guarantee amounts.
3. Update AppGovGur for accounts with specific facility types using the calculated values from the temporary table.
4. Update AppGovGur for accounts with other facility types using their government guarantee amount directly.
5. Update the running process status to mark the process as completed and increment the count.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| ⚠️ Calculate government guarantee | `GovGur` | Calculate the government guarantee amount for accounts with specific facility types and non-zero government guarantee amounts. |
| ⚠️ Update AppGovGur with calculated values | `AppGovGur` | Update AppGovGur for accounts with specific facility types using the calculated values from the temporary table. |
| ⚠️ Update AppGovGur for other facility types | `AppGovGur` | Update AppGovGur for accounts with other facility types using their government guarantee amount directly. |

## Business Rules

### R1 — Calculate government guarantee

**Affected Field:** `GovGur`

**Summary:**

- Calculate the government guarantee amount for accounts with specific facility types and non-zero government guarantee amounts.

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

### R2 — Update AppGovGur with calculated values

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Facility type is 'BP' or 'BD'

**Summary:**

- Update AppGovGur for accounts with specific facility types using the calculated values from the temporary table.


### R3 — Update AppGovGur for other facility types

> ⚠️ **Needs Review — possibly incomplete.** This rule came from a chunk or section whose analysis was truncated or failed and had to be recovered; verify its content against the source before relying on it.

**Affected Field:** `AppGovGur`

**Applies to:**

- Facility type is not 'BP' or 'BD'

**Summary:**

- Update AppGovGur for accounts with other facility types using their government guarantee amount directly.

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

The procedure uses a TRY-CATCH block to handle exceptions, but no specific failure path is documented in the extraction. If an exception occurs during the execution of the 'GovtGuarAppropriation' process, the procedure updates the running process status to indicate it is not completed and increments the error count.

## Findings / Needs Review

- Lines 30-30 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.
- 1 claim generated from this source could not be confirmed against the SQL and were left out of the Business Rules section above rather than shown as fact.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
