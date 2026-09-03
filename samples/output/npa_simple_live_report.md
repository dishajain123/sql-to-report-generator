# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a non-performing asset (NPA) based on the number of overdue days and calculates the provisioning amount. It updates the asset classification and inserts records into the NPA provisioning and audit log tables. |
| Business rules | 3 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure classifies a non-performing asset (NPA) based on the number of overdue days and calculates the provisioning amount. It updates the asset classification and inserts records into the NPA provisioning and audit log tables.

## Process Flow

1. Reads the overdue days and outstanding amount for the specified account from the LOAN_ACCOUNT table.
2. Classifies the account based on the number of overdue days and calculates the provisioning percentage.
3. Updates the asset classification in the LOAN_ACCOUNT table.
4. Inserts a record into the NPA_PROVISION table with the calculated provisioning amount and classification date.
5. Inserts a record into the NPA_AUDIT_LOG table with the new classification and change date.
6. In case of an exception, logs the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as Doubtful1

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- Account has overdue days is between 366 and 1095
- Account has overdue days more than 1095
**Meaning:** Classifies the account as Doubtful1 if the overdue days are between 366 and 1095.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is between 366 and 1095 | DOUBTFUL1 |
| ELSE | LOSS |


### R2 — Classify account as Loss

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- v_overdue_days is at most 90
- v_overdue_days is between 91 and 365
**Meaning:** Classify account as Loss.


### R3 — Update asset_classification

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification to the source-defined value when account_id = p_account_id.

## Calculations

- **provision_amount:** v_outstanding * v_provision_pct / 100

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Classifies the account as Doubtful1 if the overdue days are between 366 and 1095. The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_PROVISION` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |

## Exception Handling

In case of an exception, the error message is logged in the NPA_AUDIT_LOG table.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
