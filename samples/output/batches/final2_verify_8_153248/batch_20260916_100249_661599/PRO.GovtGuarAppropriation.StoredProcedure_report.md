# GovtGuarAppropriation — Business Logic Report

## At a Glance

| | |
|---|---|
| Procedure | `PRO.GovtGuarAppropriation` |
| Dialect | T-SQL |
| Input | `@TimeKey` (INT) |
| Business rules | 4 |
| Tables read | 1 |
| Tables written | 1 |
| Produces audit trail | Not detected |

## What This Does

The procedure updates the running process status for the 'GovtGuarAppropriation' process, marking it as not completed and incrementing the error count if an exception occurs.

## Process Flow

1. Reset the AppGovGur field to zero for accounts where the customer is not currently being processed.
2. Create a temporary table to store the calculated government guarantee amounts for accounts with a facility type of 'BP' or 'BD' and a non-zero government guarantee amount.
3. Calculate the government guarantee amount for accounts with a facility type of 'BP' or 'BD' and a non-zero government guarantee amount, and store the result in the temporary table.
4. Update the AppGovGur field for accounts with a facility type of 'BP' or 'BD' using the calculated values from the temporary table.
5. Update the AppGovGur field for accounts with a facility type other than 'BP' or 'BD' using the government guarantee amount directly.
6. Mark the process as completed and increment the count in the running process status table.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Determine GovGur | `GovGur` | First matching row wins; ELSE includes false or NULL predicates. |
| Reset AppGovGur to zero | `AppGovGur` | If the customer is not currently being processed, the AppGovGur field is reset to zero. |
| Update AppGovGur from temporary table | `AppGovGur` | For accounts with a facility type of 'BP' or 'BD', update the AppGovGur field using the calculated values from the temporary table. |
| Update AppGovGur for non-BP/BD accounts | `AppGovGur` | For accounts with a facility type other than 'BP' or 'BD', update the AppGovGur field using the government guarantee amount directly. |

## Business Rules

### R1 — Determine GovGur

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

### R2 — Reset AppGovGur to zero

**Affected Field:** `AppGovGur`

**Applies to:**

- Customer is not currently mid-processing

**Summary:**

- If the customer is not currently being processed, the AppGovGur field is reset to zero.

### Decision Logic

| Condition | Result |
|---|---|
| FlgProcessing = 'N' | 0 |


### R3 — Update AppGovGur from temporary table

**Affected Field:** `AppGovGur`

**Applies to:**

- Account has a facility type of 'BP' or 'BD'

**Summary:**

- For accounts with a facility type of 'BP' or 'BD', update the AppGovGur field using the calculated values from the temporary table.

### Decision Logic

| Condition | Result |
|---|---|
| FacilityType IN('BP','BD') | GovGur |


### R4 — Update AppGovGur for non-BP/BD accounts

**Affected Field:** `AppGovGur`

**Applies to:**

- Account has a facility type other than 'BP' or 'BD'

**Summary:**

- For accounts with a facility type other than 'BP' or 'BD', update the AppGovGur field using the government guarantee amount directly.

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

### Calculation — COUNT

**Expression:**

```sql
ISNULL(COUNT, 0) + 1
```

**Output:**
`PRO.ACLRUNNINGPROCESSSTATUS.COUNT`

**Used By:**
UPDATE PRO.ACLRUNNINGPROCESSSTATUS; READ PRO.ACLRUNNINGPROCESSSTATUS

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

The procedure uses a TRY block to handle any potential errors during execution. If an exception occurs during the execution of the procedure, the running process status for 'GovtGuarAppropriation' is updated to indicate it is not completed, and the error details are recorded.

## Findings / Needs Review

- Lines 30-30 (IF) not referenced by any synthesized rule - needs review to confirm business relevance.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
