# Update NPA TYPE — Business Logic Report

**Procedure:** `PRO.UPDATE_NPA_TYPE`  ·  **Dialect:** T-SQL  ·  **Input:** `@TIMEKEY` (INT, the processing day)

## At a Glance

| | |
|---|---|
| Procedure | `PRO.UPDATE_NPA_TYPE` |
| Dialect | T-SQL |
| Input | `@TIMEKEY` (INT) |
| Business rules | 3 |
| Tables read | 2 |
| Tables written | 0 |
| Produces audit trail | Not detected |

**Automated verification:** REVIEW REQUIRED (quality score 34/100) — 75.0% of SQL statements were not matched to a rule; 8 contradiction(s) were flagged between source and report. See the companion verification report before relying on this document.

## What This Does

This procedure updates the NPA type classification for accounts based on the days past due (DPD) and asset class short name.

## Process Flow

1. Reads data from the DimSourceDB, DimAssetClass, and ##AccountCal tables.
2. Updates the NpaType field in the ##AccountCal table based on the conditions defined in the procedure.

## Business Rule Summary

| Rule | Affected Field | Business Purpose |
|---|---|---|
| Set NpaType to REGULAR | `NpaType` | If the account's DPD_MAX is between 90 and 119, 120 and 149, 150 and 179, 180 and 209, or greater than or equal to 210, and the asset class… |
| Set NpaType to STICKY | `NpaType` | If the account's DPD_MAX is between 1 and 29, 30 and 59, or 60 and 89, and the asset class short name is SUB, DB1, DB2, or DB3, the NpaType… |
| Set NpaType to MULTIPLE | `NpaType` | If the account's DPD_MAX is 0, and the asset class short name is SUB, DB1, DB2, or DB3, the NpaType is set to MULTIPLE. |

## Business Rules

### R1 — Set NpaType to REGULAR

**Affected Field:** `NpaType`

**Applies to:**

- Account's DPD_MAX is between 90 and 119

**Summary:**

- If the account's DPD_MAX is between 90 and 119, 120 and 149, 150 and 179, 180 and 209, or greater than or equal to 210, and the asset class short name is SUB, DB1, DB2, or DB3, the NpaType is set to REGULAR.

### Decision Logic

| Condition | Result |
|---|---|
| CD=5 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 90 AND 119 | REGULAR |
| CD=5 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 90 AND 119 | REGULAR |
| CD=5 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 90 AND 119 | REGULAR |
| CD=5 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 90 AND 119 | REGULAR |
| CD=6 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 120 AND 149 | REGULAR |
| CD=6 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 120 AND 149 | REGULAR |
| CD=6 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 120 AND 149 | REGULAR |
| CD=6 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 120 AND 149 | REGULAR |
| CD=7 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 150 AND 179 | REGULAR |
| CD=7 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 150 AND 179 | REGULAR |
| CD=7 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 150 AND 179 | REGULAR |
| CD=7 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 150 AND 179 | REGULAR |
| CD=8 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 180 AND 209 | REGULAR |
| CD=8 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 180 AND 209 | REGULAR |
| CD=8 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 180 AND 209 | REGULAR |
| CD=8 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 180 AND 209 | REGULAR |
| CD=9 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX >=210 | REGULAR |
| CD=9 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX >=210 | REGULAR |
| CD=9 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX >=210 | REGULAR |
| CD=9 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX >=210 | REGULAR |


### R2 — Set NpaType to STICKY

**Affected Field:** `NpaType`

**Applies to:**

- Account's DPD_MAX is between 1 and 29

**Summary:**

- If the account's DPD_MAX is between 1 and 29, 30 and 59, or 60 and 89, and the asset class short name is SUB, DB1, DB2, or DB3, the NpaType is set to STICKY.

### Decision Logic

| Condition | Result |
|---|---|
| CD=2 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 1 AND 29 | STICKY |
| CD=2 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 1 AND 29 | STICKY |
| CD=2 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 1 AND 29 | STICKY |
| CD=2 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 1 AND 29 | STICKY |
| CD=3 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 30 AND 59 | STICKY |
| CD=3 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 30 AND 59 | STICKY |
| CD=3 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 30 AND 59 | STICKY |
| CD=3 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 30 AND 59 | STICKY |
| CD=4 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 60 AND 89 | STICKY |
| CD=4 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 60 AND 89 | STICKY |
| CD=4 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 60 AND 89 | STICKY |
| CD=4 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 60 AND 89 | STICKY |


### R3 — Set NpaType to MULTIPLE

**Affected Field:** `NpaType`

**Applies to:**

- Account's DPD_MAX is 0

**Summary:**

- If the account's DPD_MAX is 0, and the asset class short name is SUB, DB1, DB2, or DB3, the NpaType is set to MULTIPLE.

### Decision Logic

| Condition | Result |
|---|---|
| CD=0 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX = 0 | MULTIPLE |
| CD=0 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX = 0 | MULTIPLE |
| CD=0 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX = 0 | MULTIPLE |
| CD=0 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX = 0 | MULTIPLE |
| CD=1 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX = 0 | MULTIPLE |
| CD=1 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX = 0 | MULTIPLE |
| CD=1 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX = 0 | MULTIPLE |
| CD=1 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX = 0 | MULTIPLE |
| CD=2 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 1 AND 29 | MULTIPLE |
| CD=2 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 1 AND 29 | MULTIPLE |
| CD=2 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 1 AND 29 | MULTIPLE |
| CD=2 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 1 AND 29 | MULTIPLE |
| CD=3 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 30 AND 59 | MULTIPLE |
| CD=3 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 30 AND 59 | MULTIPLE |
| CD=3 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 30 AND 59 | MULTIPLE |
| CD=3 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 30 AND 59 | MULTIPLE |
| CD=4 AND ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 60 AND 89 | MULTIPLE |
| CD=4 AND ASSETCLASSSHORTNAME='DB1' AND DPD_MAX BETWEEN 60 AND 89 | MULTIPLE |
| CD=4 AND ASSETCLASSSHORTNAME='DB2' AND DPD_MAX BETWEEN 60 AND 89 | MULTIPLE |
| CD=4 AND ASSETCLASSSHORTNAME='DB3' AND DPD_MAX BETWEEN 60 AND 89 | MULTIPLE |

## Calculations

_None identified._

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `DimSourceDB` | Read | Provides: SourceName, AssetClassGroup, SourceAlt_Key, FinalAssetClassAlt_Key, AssetClassAlt_Key, DPD_MAX (+4 more) |
| `DimAssetClass` | Read | Provides: SourceName, AssetClassGroup, SourceAlt_Key, FinalAssetClassAlt_Key, AssetClassAlt_Key, DPD_MAX (+4 more) |

### Working Tables (temporary)

| Table | Read/Write | Purpose |
|---|---|---|
| `##AccountCal` | Read + Write | Updates: NpaType |

_1 table reference(s) could not be resolved to a table name and are omitted from this list - see the verification report for the full technical lineage._

## Exception Handling

No explicit failure-path behavior identified.

## Findings / Needs Review

- Possible unreviewed decision logic near source line 36-110 (ASSIGNMENT/CASE): no synthesized rule's evidence appears to reference "UPDATE A SET 	A.NpaType = ( CASE	  										WHEN CD=5 AND DA.ASSETCLASSSHORTNAME='SUB' AND DPD_MAX BETWEEN 90 AND  119  THEN  'REGULAR' 										WHEN CD=6 AND...". Needs human review to confirm whether this is business-relevant.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
