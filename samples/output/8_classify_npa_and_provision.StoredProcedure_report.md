# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies the asset classification and provisioning percentage for a loan account based on the number of overdue days and updates the relevant tables accordingly. |
| Business rules | 4 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure classifies the asset classification and provisioning percentage for a loan account based on the number of overdue days and updates the relevant tables accordingly.

## Process Flow

1. Reads the overdue days and outstanding amount for the specified account from the LOAN_ACCOUNT table.
2. Classifies the account based on the number of overdue days into one of four categories: STANDARD, SUBSTANDARD, DOUBTFUL1, or LOSS.
3. Calculates the provisioning amount based on the outstanding amount and the classification.
4. Updates the asset classification in the LOAN_ACCOUNT table for the specified account.
5. Inserts a record into the NPA_PROVISION table with the account ID, provisioning amount, and classification date.
6. Inserts a record into the NPA_AUDIT_LOG table with the account ID, new classification, and change date.
7. If an exception occurs, logs the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Assign v_classification as STANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90.


### R2 — Assign v_classification as SUBSTANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365.


### R3 — Assign v_classification as DOUBTFUL1

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095.


### R4 — Assign v_classification as LOSS

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value LOSS when the source condition is NOT (v_overdue_days <= 90) AND NOT (v_overdue_days BETWEEN 91 AND 365) AND NOT (v_overdue_days BETWEEN 366 AND 1095).

## Calculations

- **provision_amount:** v_outstanding * v_provision_pct / 100

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Updates: asset_classification |
| `NPA_PROVISION` | Write | Inserts data into: account_id, provision_amount, classification_date |
| `NPA_AUDIT_LOG` | Write | Inserts data into: account_id, new_classification, change_date |

## Exception Handling

If an exception occurs, the error message is logged in the NPA_AUDIT_LOG table.

## Findings / Needs Review

- Calculation needs review: v_provision_pct is assigned a value below 1 and then divided by 100, which may reduce the intended rate by an additional factor of 100.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- The calculation for provision_amount may reduce the intended rate by an additional factor of 100 due to the division by 100.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
