# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a non-performing asset (NPA) based on the number of overdue days and provisions an amount for the asset. It updates the asset classification and inserts records into the NPA provision and audit log tables. |
| Business rules | 7 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure classifies a non-performing asset (NPA) based on the number of overdue days and provisions an amount for the asset. It updates the asset classification and inserts records into the NPA provision and audit log tables.

## Process Flow

1. Reads the overdue days and outstanding amount from the LOAN_ACCOUNT table for the specified account ID.
2. Classifies the account based on the number of overdue days and calculates the provisioning percentage.
3. Updates the asset classification in the LOAN_ACCOUNT table.
4. Inserts a record into the NPA_PROVISION table with the calculated provisioning amount and classification date.
5. Inserts a record into the NPA_AUDIT_LOG table with the new classification and change date.
6. In case of an exception, logs the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as Doubtful1

**Applies to:** `v_classification`
**Meaning:** Classifies the account as Doubtful1 if the overdue days are between 366 and 1095.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 | DOUBTFUL1 |
| ELSE | LOSS |


### R2 — Classify account as Loss

**Applies to:** `v_classification`
**Meaning:** Classifies the account as Loss if the overdue days are more than 1095.

### Decision Logic
| Condition | Outcome |
|---|---|
| ELSE | LOSS |


### R3 — Update asset_classification

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification to the source-defined value when account_id = p_account_id.


### R4 — Assign v_classification as STANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90.


### R5 — Assign v_classification as SUBSTANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365.


### R6 — Assign v_classification as DOUBTFUL1

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095.


### R7 — Assign v_classification as LOSS

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

Logs the error message in the NPA_AUDIT_LOG table and the source does not explicitly state whether processing continues.

## Findings / Needs Review

- Calculation needs review: v_provision_pct is assigned a value below 1 and then divided by 100, which may reduce the intended rate by an additional factor of 100.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized rule affects different fields than the deterministic evidence.
- Reconciliation detected a source/report discrepancy: Synthesized outcome/assignment conflicts with deterministic evidence.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
