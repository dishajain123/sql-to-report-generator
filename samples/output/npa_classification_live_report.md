# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies the asset classification and provisioning percentage for a loan account based on the number of overdue days and the number of days since the account became doubtful. |
| Business rules | 5 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure classifies the asset classification and provisioning percentage for a loan account based on the number of overdue days and the number of days since the account became doubtful.

## Process Flow

1. Reads the overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the number of overdue days and the number of days since the account became doubtful.
3. Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provisioning percentage.
4. Updates the asset classification and last classified date in the LOAN_ACCOUNT table for the specified account.
5. Inserts a record into the NPA_PROVISION table with the account ID, classification, provisioning amount, and calculated date.
6. Inserts a record into the NPA_AUDIT_LOG table with the account ID, old classification, new classification, and changed date.
7. Handles exceptions by logging the error and continuing or re-raising the exception.

## Business Rules

### R1 — Classify account as Standard

**Applies to:** `v_classification`
**Eligibility:** Account has overdue days less than or equal to 90
**Meaning:** Classifies the account as Standard if the overdue days are less than or equal to 90.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |


### R2 — Classify account as Doubtful3 or Loss

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- v_overdue_days is at most 90
- v_overdue_days is between 91 and 365
- v_overdue_days is between 366 and 1095
**Meaning:** Classify account as Doubtful3 or Loss.


### R3 — Classify account as Doubtful3 or Loss

**Eligibility:** latest calculated_date per account
**Meaning:** Classify account as Doubtful3 or Loss.


### R4 — Update asset_classification, last_classified_date

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id.


### R5 — Classify account as Doubtful3 or Loss

**Applies to:** `v_classification`
**Eligibility:** Account has overdue days greater than 1095
**Meaning:** Set LOSS or DOUBTFUL3 based on doubtful_since

### Decision Logic
| Condition | Outcome |
|---|---|
| v_doubtful_since is at most 1095 | DOUBTFUL3 |
| v_doubtful_since is above 1095 | LOSS |

## Calculations

- **provisioning_amount:** (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100))

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Classifies the account as Standard if the overdue days are less than or equal to 90. The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_acco… |
| `NPA_PROVISION` | Write | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |

## Exception Handling

Logs an error message and continues if no data is found for the account. Logs an error message and re-raises the exception for any other errors.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
