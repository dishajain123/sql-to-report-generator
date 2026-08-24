## Object Overview

- **Object Name:** `PRO.DPD_Calculation`
- **Object Type:** Procedure
- **Parameters:**

| Parameter | Direction | Datatype |
|---|---|---|
| `p_TIMEKEY` | IN | NUMBER |

## Purpose Summary

The DPD_Calculation procedure calculates Days Past Due (DPD) for various account attributes, such as interest service, no credit, overdraft, overdue, renewal, and stock statement. The procedure updates the PRO.AccountCal_Stg table with the calculated DPD values. The calculations are based on the account's historical data and the current process date. The procedure also updates the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the completion status of the process.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `PRO.AccountCal_Stg` | Columns referenced: N/A | No filter / full read |
| `SysDayMatrix` | Columns referenced: Date | TimeKey = p_TIMEKEY AND ROWNUM = 1 |
| `PRO.AccountCal_Stg` | Columns referenced: IntNotServicedDt, LastCrDate, ContiExcessDt, OverDueSinceDt, ReviewDueDt, StockStDt, DebitSinceDt, SourceAlt_Key | null |
| `DIMPRODUCT` | Columns referenced: Aqua_Scheme, SchemeType | C.EffectiveFromTimeKey <= p_TIMEKEY AND C.EffectiveToTimeKey >= p_TIMEKEY AND (NVL(C.Aqua_Scheme,'N') = 'Y' AND NVL(C.SchemeType,'') = 'ODA') |
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
| `PRO.AdvAcRestructureCal` | MERGE | T.AccountEntityId = A.AccountEntityID |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | RUNNINGPROCESSNAME = 'DPD_Calculation' |
| `PRO.ACLRUNNINGPROCESSSTATUS` | UPDATE | WHEN OTHERS |
| `BANDAUDITSTATUS` | UPDATE | null |

## Step-by-Step Logic Flow

1. The system first determines the process date based on the input parameter p_TIMEKEY.
2. The system then calculates the DPD values for each account attribute, such as interest service, no credit, overdraft, overdue, renewal, and stock statement.
3. The system updates the PRO.AccountCal_Stg table with the calculated DPD values.
4. The system also updates the PRO.ACLRUNNINGPROCESSSTATUS table to reflect the completion status of the process.

## Business Rules / Validations

| Condition | Resulting Action |
|---|---|
| The account's interest not serviced date is not null. | Sets the DPD interest service to the difference between the process date and the interest not serviced date plus 1 or 2. |
| The account's last credit date is not null and the debit since date is null or the difference between the process date and the debit since date is greater than or equal to 90 days. | Sets the DPD no credit to the difference between the process date and the last credit date plus 1. |
| The account's continuous excess date is not null. | Sets the DPD overdraft to the difference between the process date and the continuous excess date plus 1. |
| The account's overdue since date is not null. | Sets the DPD overdue to the difference between the process date and the overdue since date plus 1 or the difference between the process date and the overdue since date plus a value determined by the SourceAlt_Key. |
| The account's review due date is not null. | Sets the DPD renewal to the difference between the process date and the review due date plus 1. |
| The account's stock statement date is not null. | Sets the DPD stock statement to the difference between the process date and the stock statement date plus 1. |
| The calculated DPD value is less than 0. | Sets the DPD value to 0. |

## Calculations / Formulas

- **DPD interest service:** The difference between the process date and the interest not serviced date plus 1 or 2.
- **DPD no credit:** The difference between the process date and the last credit date plus 1.
- **DPD overdraft:** The difference between the process date and the continuous excess date plus 1.
- **DPD overdue:** The difference between the process date and the overdue since date plus 1 or the difference between the process date and the overdue since date plus a value determined by the SourceAlt_Key.
- **DPD renewal:** The difference between the process date and the review due date plus 1.
- **DPD stock statement:** The difference between the process date and the stock statement date plus 1.

## Exception Handling Behavior

The procedure handles exceptions by logging and updating the status in the PRO.ACLRUNNINGPROCESSSTATUS table. If an error occurs, the procedure will update the error date and description in the status table.

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
- The usage of SourceAlt_Key in the DPD overdue calculation is not clearly defined.
- The usage of DebitSinceDt in the DPD no credit calculation is not clearly defined.
- The calculation of DPD_MaxFin and DPD_MaxNonFin is not clearly defined.
