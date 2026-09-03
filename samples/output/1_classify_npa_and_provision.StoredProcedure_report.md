# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a loan account's Non-Performing Asset (NPA) status and calculates the provisioning amount based on the number of overdue days. It updates the account's asset classification and inserts records into the NPA provision and audit log tables. |
| Business rules | 2 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure classifies a loan account's Non-Performing Asset (NPA) status and calculates the provisioning amount based on the number of overdue days. It updates the account's asset classification and inserts records into the NPA provision and audit log tables.

## Process Flow

1. Reads the overdue days and outstanding amount from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the number of overdue days into one of four categories: STANDARD, SUBSTANDARD, DOUBTFUL1, or LOSS.
3. Calculates the provisioning amount based on the outstanding amount and the classification.
4. Updates the asset classification in the LOAN_ACCOUNT table for the specified account.
5. Inserts a record into the NPA_PROVISION table with the account ID, provisioning amount, and classification date.
6. Inserts a record into the NPA_AUDIT_LOG table with the account ID, new classification, and change date.
7. In case of an exception, logs the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as STANDARD

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- The account's overdue days are 90 or less
- The account's overdue days are more than 1095
- account_id equals p_account_id
**Meaning:** Classify account as STANDARD.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 | DOUBTFUL1 |
| ELSE | LOSS |


### R2 — Classify account as LOSS

**Applies to:** `v_classification`
**Eligibility:** v_overdue_days is between 366 and 1095
**Meaning:** Classify account as LOSS.

## Calculations

- **provision_amount:** v_outstanding * v_provision_pct / 100

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_PROVISION` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |

## Exception Handling

In case of an exception, the error message is logged in the NPA_AUDIT_LOG table.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
