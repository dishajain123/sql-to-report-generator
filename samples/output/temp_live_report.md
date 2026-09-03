# DPD Calculation — Business Logic Report

**Procedure:** `PRO.DPD_Calculation`  ·  **Dialect:** Oracle  ·  **Input:** `p_TIMEKEY` (NUMBER, the processing day)

## At a Glance

| | |
|---|---|
| Purpose | This procedure calculates and updates various overdue days (DPD) metrics for accounts based on the provided time key. It resets certain date fields, calculates DPD values for different scenarios, and updates maximum DPD values for restructuring calculations. |
| Business rules | 24 |
| Tables read | 4 |
| Tables written | 3 |
| Produces audit trail | No |

## What This Does

This procedure calculates and updates various overdue days (DPD) metrics for accounts based on the provided time key. It resets certain date fields, calculates DPD values for different scenarios, and updates maximum DPD values for restructuring calculations.

## Process Flow

1. Retrieve the process date from the SysDayMatrix table based on the provided time key.
2. Update specific date fields in the AccountCal_Stg table to NULL if they match a default date.
3. Initialize all DPD fields in the AccountCal_Stg table to zero.
4. Calculate and update DPD values based on the provided time key and various conditions.
5. Ensure all DPD values are non-negative by setting them to zero if they are negative.
6. Update maximum DPD values for restructuring calculations in the AdvAcRestructureCal table.
7. Update specific fields in the AccountCal_Stg table for accounts under the Aqua Scheme.
8. Mark the DPD calculation process as completed in the ACLRUNNINGPROCESSSTATUS table.
9. Handle any exceptions by marking the process as failed and updating the error details in the ACLRUNNINGPROCESSSTATUS table.

## Business Rules

### R1 — Retrieve process date

**Applies to:** `v_ProcessDate`
**Eligibility:** ROWNUM equals 1
**Meaning:** Fetch the process date from the SysDayMatrix table based on the provided time key.


### R2 — Update IntNotServicedDt to NULL

**Applies to:** `IntNotServicedDt`
**Eligibility (all must hold):**
- (IntNotServicedDt equals DATE '1900-01-01' or IntNotServicedDt equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (IntNotServicedDt equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or IntNotServicedDt equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets IntNotServicedDt to the source-defined value when (IntNotServicedDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR IntNotServicedDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R3 — Update LastCrDate to NULL

**Applies to:** `LastCrDate`
**Eligibility (all must hold):**
- (LastCrDate equals DATE '1900-01-01' or LastCrDate equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (LastCrDate equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or LastCrDate equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets LastCrDate to the source-defined value when (LastCrDate = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR LastCrDate = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R4 — Update ContiExcessDt to NULL

**Applies to:** `ContiExcessDt`
**Eligibility (all must hold):**
- (ContiExcessDt equals DATE '1900-01-01' or ContiExcessDt equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (ContiExcessDt equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or ContiExcessDt equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets ContiExcessDt to the source-defined value when (ContiExcessDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR ContiExcessDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R5 — Update OverDueSinceDt to NULL

**Applies to:** `OverDueSinceDt`
**Eligibility (all must hold):**
- (OverDueSinceDt equals DATE '1900-01-01' or OverDueSinceDt equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (OverDueSinceDt equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or OverDueSinceDt equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets OverDueSinceDt to the source-defined value when (OverDueSinceDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR OverDueSinceDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R6 — Update ReviewDueDt to NULL

**Applies to:** `ReviewDueDt`
**Eligibility (all must hold):**
- (ReviewDueDt equals DATE '1900-01-01' or ReviewDueDt equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (ReviewDueDt equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or ReviewDueDt equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets ReviewDueDt to the source-defined value when (ReviewDueDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR ReviewDueDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R7 — Update StockStDt to NULL

**Applies to:** `StockStDt`
**Eligibility (all must hold):**
- (StockStDt equals DATE '1900-01-01' or StockStDt equals TO_DATE('01/01/1900','DD/MM/YYYY'))
- (StockStDt equals TO_DATE('1900-01-01', 'YYYY-MM-DD') or StockStDt equals TO_DATE('01/01/1900', 'DD/MM/YYYY'))
**Meaning:** The procedure sets StockStDt to the source-defined value when (StockStDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR StockStDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')).


### R8 — Calculate DPD_IntService

**Applies to:** `DPD_IntService`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_IntService, 0) is below 0
**Meaning:** The procedure sets DPD_IntService to the source-defined value when NVL(DPD_IntService, 0) < 0.


### R9 — Update DPD_OtherOverdueSince

**Applies to:** `DPD_NoCredit`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_NoCredit, 0) is below 0
- NVL(DPD_OtherOverdueSince, 0) is below 0
**Meaning:** The procedure sets DPD_OtherOverdueSince to the source-defined value when NVL(DPD_OtherOverdueSince, 0) < 0.


### R10 — Calculate DPD_Overdrawn

**Applies to:** `DPD_Overdrawn`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_Overdrawn, 0) is below 0
**Meaning:** The procedure sets DPD_Overdrawn to the source-defined value when NVL(DPD_Overdrawn, 0) < 0.


### R11 — Calculate DPD_Overdue

**Applies to:** `DPD_Overdue`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_Overdue, 0) is below 0
**Meaning:** The procedure sets DPD_Overdue to the source-defined value when NVL(DPD_Overdue, 0) < 0.


### R12 — Calculate DPD_Renewal

**Applies to:** `DPD_Renewal`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_Renewal, 0) is below 0
**Meaning:** The procedure sets DPD_Renewal to the source-defined value when NVL(DPD_Renewal, 0) < 0.


### R13 — Calculate DPD_PrincOverdue

**Applies to:** `DPD_PrincOverdue`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_PrincOverdue, 0) is below 0
**Meaning:** The procedure sets DPD_PrincOverdue to the source-defined value when NVL(DPD_PrincOverdue, 0) < 0.


### R14 — Calculate DPD_IntOverdueSince

**Applies to:** `DPD_IntOverdueSince`
**Eligibility (all must hold):**
- p_TIMEKEY is above 26267
- NVL(DPD_IntOverdueSince, 0) is below 0
**Meaning:** The procedure sets DPD_IntOverdueSince to the source-defined value when NVL(DPD_IntOverdueSince, 0) < 0.


### R15 — Calculate DPD_OtherOverdueSince

**Applies to:** `DPD_OtherOverdueSince`
**Eligibility:** p_TIMEKEY is above 26267
**Meaning:** Calculate the DPD_OtherOverdueSince value based on the provided time key and conditions.


### R16 — Set negative DPD values to zero

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince`
**Eligibility:** NVL(DPD_IntService,0) is below 0 or NVL(DPD_NoCredit,0) is below 0 or NVL(DPD_Overdrawn,0) is below 0 or NVL(DPD_Overdue,0) is below 0 or NVL(DPD_Renewal,0) is below 0 or NVL(DPD_StockStmt,0) is below 0 or NVL(DPD_PrincOverdue,0) is below 0 or NVL(DPD_IntOverdueSince,0) is below 0 or NVL(DPD_OtherOverdueSince,0) is below 0
**Meaning:** Ensure all DPD values are non-negative by setting them to zero if they are negative.


### R17 — Update DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince`
**Meaning:** The procedure sets DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt, DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince to the source-defined value.


### R18 — Update DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt

**Applies to:** `DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt`
**Eligibility:** NVL(DPD_StockStmt, 0) is below 0
**Meaning:** The procedure sets DPD_IntService, DPD_NoCredit, DPD_Overdrawn, DPD_Overdue, DPD_Renewal, DPD_StockStmt to the source-defined value.


### R19 — Update DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince

**Applies to:** `DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince`
**Meaning:** The procedure sets DPD_PrincOverdue, DPD_IntOverdueSince, DPD_OtherOverdueSince to the source-defined value.


### R20 — Update DPD_MaxNonFin in AdvAcRestructureCal

**Applies to:** `DPD_MaxNonFin`
**Eligibility (all must hold):**
- DPD_MaxNonFin IS NULL
- AccountEntityID matches is between AccountCal_Stg and AdvAcRestructureCal
**Meaning:** Update the DPD_MaxNonFin value in the AdvAcRestructureCal table based on the maximum DPD values from AccountCal_Stg.


### R21 — Update DPD_MaxNonFin and DPD_MaxFin to zero if NULL

**Applies to:** `DPD_MaxFin`
**Eligibility (all must hold):**
- DPD_MaxNonFin IS NULL
- DPD_MaxNonFin IS NULL or DPD_MaxFin IS NULL
**Meaning:** Set DPD_MaxNonFin and DPD_MaxFin to zero if they are NULL in the AdvAcRestructureCal table.


### R22 — Update COMPLETED, ERRORDATE, ERRORDESCRIPTION, "COUNT"

**Applies to:** `COMPLETED, ERRORDATE, ERRORDESCRIPTION, "COUNT"`
**Eligibility:** RUNNINGPROCESSNAME equals 'DPD_Calculation'
**Meaning:** The procedure sets COMPLETED, ERRORDATE, ERRORDESCRIPTION, "COUNT" to the source-defined value when RUNNINGPROCESSNAME = 'DPD_Calculation'.


### R23 — Update specific fields for Aqua Scheme

**Applies to:** `DPD_StockStmt`
**Eligibility:** AccountEntityID matches and the product is under the Aqua Scheme and SchemeType is ODA
**Meaning:** Update specific fields in the AccountCal_Stg table for accounts under the Aqua Scheme.


### R24 — Update DPD_MaxFin in AdvAcRestructureCal

**Applies to:** `DPD_MaxFin`
**Eligibility:** AccountEntityID matches is between AccountCal_Stg and AdvAcRestructureCal
**Meaning:** Update the DPD_MaxFin value in the AdvAcRestructureCal table based on the maximum DPD values from AccountCal_Stg.

## Calculations

- **v_ProcessDate:** DATE
- **DPD_IntService:** CASE WHEN p_TIMEKEY > 26384 THEN (CASE WHEN A.IntNotServicedDt IS NOT NULL THEN (v_ProcessDate - A.IntNotServicedDt) + 2 ELSE 0 END) ELSE (CASE WHEN A.IntNotServicedDt IS NOT NULL THEN (v_ProcessDate - A.IntNotServicedDt) + 1 ELSE 0 END) END
- **DPD_NoCredit:** CASE WHEN (DebitSinceDt IS NULL OR (v_ProcessDate - DebitSinceDt) >= 90) THEN (CASE WHEN A.LastCrDate IS NOT NULL THEN (v_ProcessDate - A.LastCrDate) + 1 ELSE 0 END) ELSE 0 END
- **DPD_Overdrawn:** (CASE WHEN A.ContiExcessDt IS NOT NULL THEN (v_ProcessDate - A.ContiExcessDt) + 1 ELSE 0 END)
- **DPD_Overdue:** CASE WHEN p_TIMEKEY > 26372 THEN (CASE WHEN A.OverDueSinceDt IS NOT NULL THEN (v_ProcessDate - A.OverDueSinceDt) + 1 ELSE 0 END) ELSE (CASE WHEN A.OverDueSinceDt IS NOT NULL THEN (v_ProcessDate - A.OverDueSinceDt) + (CASE WHEN SourceAlt_Key = 6 THEN 0 ELSE 1 END) ELSE 0 END) END
- **DPD_Renewal:** (CASE WHEN A.ReviewDueDt IS NOT NULL THEN (v_ProcessDate - A.ReviewDueDt) + 1 ELSE 0 END)
- **DPD_StockStmt:** (CASE WHEN A.StockStDt IS NOT NULL THEN (v_ProcessDate - A.StockStDt) + 1 ELSE 0 END)
- **DPD_PrincOverdue:** (CASE WHEN A.PrincOverdueSinceDt IS NOT NULL THEN (v_ProcessDate - A.PrincOverdueSinceDt) + 1 ELSE 0 END)
- **DPD_IntOverdueSince:** (CASE WHEN A.IntOverdueSinceDt IS NOT NULL THEN (v_ProcessDate - A.IntOverdueSinceDt) + 1 ELSE 0 END)
- **DPD_OtherOverdueSince:** (CASE WHEN A.OtherOverdueSinceDt IS NOT NULL THEN (v_ProcessDate - A.OtherOverdueSinceDt) + 1 ELSE 0 END)

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `PRO.AccountCal_Stg` | Read + Write | The procedure sets IntNotServicedDt to the source-defined value when (IntNotServicedDt = TO_DATE('1900-01-01', 'YYYY-MM-DD') OR IntNotServicedDt = TO_DATE('01/01/1900', 'DD/MM/YYYY')). The procedure… |
| `PRO.AdvAcRestructureCal` | Read + Write | The procedure sets DPD_IntService to the source-defined value when NVL(DPD_IntService, 0) < 0. The procedure sets DPD_OtherOverdueSince to the source-defined value when NVL(DPD_OtherOverdueSince, 0)… |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Read + Write | The procedure sets COMPLETED, ERRORDATE, ERRORDESCRIPTION, "COUNT" to the source-defined value when RUNNINGPROCESSNAME = 'DPD_Calculation'. |
| `SysDayMatrix` | Read | Provides: "Date", "Date" INTO v_ProcessDate |

## Exception Handling

If an exception occurs, the process is marked as failed, and the error details are updated in the ACLRUNNINGPROCESSSTATUS table.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `PRO.DPD_Calculation.StoredProcedure_verification.md`._
