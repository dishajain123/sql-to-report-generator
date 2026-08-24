## Object Overview

- **Object Name:** `PRO.DPD_Calculation`
- **Object Type:** Procedure
- **Parameters:**

| Parameter | Direction | Datatype |
|---|---|---|
| `p_TIMEKEY` | IN | NUMBER |

## Purpose Summary

The DPD_Calculation procedure calculates Days Past Due (DPD) for various loan and account attributes, such as interest servicing, credit, overdraft, and overdue payments. The procedure updates the AccountCal_Stg table with the calculated DPD values. The calculations are based on the time key and other relevant dates, such as the last credit date, interest not serviced date, and overdraft since date. The procedure also handles exceptions and updates the process status accordingly.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `PRO.AccountCal_Stg` | Columns referenced: N/A | No filter / full read |
| `SysDayMatrix` | Columns referenced: Date | TimeKey = p_TIMEKEY AND ROWNUM = 1 |
| `PRO.AccountCal_Stg` | Columns referenced: IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, DebitSinceDt, SourceAlt_Key | null |
| `DIMPRODUCT` | Columns referenced: EffectiveFromTimeKey, EffectiveToTimeKey, Aqua_Scheme, SchemeType | null |
| `PRO.AdvAcRestructureCal` | Columns referenced: DPD_MaxFin, DPD_MaxNonFin | null |
| `PRO.ACLRUNNINGPROCESSSTATUS` | Columns referenced: COMPLETED, ERRORDATE, ERRORDESCRIPTION, COUNT | RUNNINGPROCESSNAME = 'DPD_Calculation' |

## Tables Written

| Table Name | Operation Type | Business Trigger |
|---|---|---|
| `PRO.AccountCal_Stg` | UPDATE | null |
| `PRO.AccountCal_Stg` | UPDATE | IntNotServicedDt = DATE '1900-01-01' OR IntNotServicedDt = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AccountCal_Stg` | UPDATE | LastCrDate = DATE '1900-01-01' OR LastCrDate = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AccountCal_Stg` | UPDATE | ContiExcessDt = DATE '1900-01-01' OR ContiExcessDt = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AccountCal_Stg` | UPDATE | OverDueSinceDt = DATE '1900-01-01' OR OverDueSinceDt = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AccountCal_Stg` | UPDATE | ReviewDueDt = DATE '1900-01-01' OR ReviewDueDt = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AccountCal_Stg` | UPDATE | StockStDt = DATE '1900-01-01' OR StockStDt = TO_DATE('01/01/1900','DD/MM/YYYY') |
| `PRO.AdvAcRestructureCal` | MERGE | null |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | RUNNINGPROCESSNAME = 'DPD_Calculation' |
| `BANDAUDITSTATUS` | UPDATE | always (as part of the main procedure body) |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | WHEN OTHERS (exception handling) |

## Step-by-Step Logic Flow

1. The system first verifies the time key to determine the correct calculation method for DPD values.
2. The system then calculates the DPD values for interest servicing, credit, overdraft, and overdue payments based on the relevant dates.
3. The system updates the AccountCal_Stg table with the calculated DPD values.
4. The system handles exceptions, such as no data found or other errors, and updates the process status accordingly.

## Business Rules / Validations

| Condition | Resulting Action |
|---|---|
| The account has an interest not serviced date | Calculate the DPD for interest servicing based on the date difference between the process date and the interest not serviced date |
| The account has a last credit date | Calculate the DPD for credit based on the date difference between the process date and the last credit date |
| The account has an overdraft since date | Calculate the DPD for overdraft based on the date difference between the process date and the overdraft since date |
| The account has an overdue since date | Calculate the DPD for overdue payments based on the date difference between the process date and the overdue since date |
| The account has a review due date | Calculate the DPD for renewal based on the date difference between the process date and the review due date |
| The account has a stock statement date | Calculate the DPD for stock statement based on the date difference between the process date and the stock statement date |

## Calculations / Formulas

- **DPD for interest servicing:** The date difference between the process date and the interest not serviced date, plus 1 or 2 days depending on the time key
- **DPD for credit:** The date difference between the process date and the last credit date, plus 1 day
- **DPD for overdraft:** The date difference between the process date and the overdraft since date, plus 1 day
- **DPD for overdue payments:** The date difference between the process date and the overdue since date, plus 1 day or 0 days depending on the source alternative key
- **DPD for renewal:** The date difference between the process date and the review due date, plus 1 day
- **DPD for stock statement:** The date difference between the process date and the stock statement date, plus 1 day

## Exception Handling Behavior

The procedure handles exceptions, such as no data found or other errors, by updating the process status and logging the error. The procedure does not re-raise the exception.

## Ambiguities / Needs Review

- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE IN DPD_Overdrawn AS DISCUSSED WITH SHARMA SIR AND TRILOKI SIR ON 31082021 */
        /*   amar --commented as per...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE A SET DPD_NoCredit=0
        --FROM PRO.AccountCal A INNER JOIN PRO.CustomerCal B ON A.RefCustomerID=B.RefCustome...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE FOR Aqua Scheme---Prashant under guidence of Akshay Sir----03122025---------------
        MERGE INTO PRO.Account...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): UPDATE FOR Aqua Scheme---Prashant under guidence of Akshay Sir----03122025---------------

        UPDATE PRO.ACLRUNNING...
- Could not fully structurally parse embedded SQL statement (non-fatal, passed through as raw text): Update BANDAUDITSTATUS set CompletedCount=CompletedCount+1 where BandName='ASSET CLASSIFICATION'

    EXCEPTION...
- The dynamic logic and specific operations within the procedure are not fully defined in the provided technical extraction.
