# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies non-performing assets (NPA) based on the number of overdue days and the duration since the account became doubtful. It also calculates the provisioning amount and updates the account's asset classification and provisioning records. |
| Business rules | 10 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure classifies non-performing assets (NPA) based on the number of overdue days and the duration since the account became doubtful. It also calculates the provisioning amount and updates the account's asset classification and provisioning records.

## Process Flow

1. Reads overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the number of overdue days and duration since the account became doubtful.
3. Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provision percentage.
4. Updates the asset classification and last classified date in the LOAN_ACCOUNT table for the specified account.
5. Inserts a new record into the NPA_PROVISION table with the account's classification and calculated provisioning amount.
6. Inserts a new record into the NPA_AUDIT_LOG table with the account's classification change details.
7. Handles exceptions by logging the error in the NPA_AUDIT_LOG table and re-raising the exception.

## Business Rules

### R1 — Classify account as Standard

**Applies to:** `v_classification`
**Meaning:** Sets the account's asset classification to Standard if overdue days are 90 or less.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 and v_doubtful_since is at most 365 | DOUBTFUL1 |
| v_overdue_days is between 366 and 1095 and ELSE | DOUBTFUL2 |
| ELSE and v_doubtful_since is above 1095 | LOSS |
| ELSE and ELSE | DOUBTFUL3 |


### R2 — Classify account as Standard

**Eligibility:** latest calculated_date per account
**Meaning:** Classify account as Standard.


### R3 — Update asset_classification, last_classified_date

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id.


### R4 — Assign v_classification as STANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value STANDARD when the source condition is v_overdue_days <= 90.


### R5 — Assign v_classification as SUBSTANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365.


### R6 — Assign v_classification as DOUBTFUL1

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value DOUBTFUL1 when the source condition is v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365.


### R7 — Assign v_classification as DOUBTFUL2

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value DOUBTFUL2 when the source condition is v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365).


### R8 — Assign v_classification as LOSS

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value LOSS when the source condition is ELSE AND v_doubtful_since > 1095.


### R9 — Assign v_classification as DOUBTFUL3

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value DOUBTFUL3 when the source condition is ELSE AND NOT (v_doubtful_since > 1095).


### R10 — Classify account as Loss

**Applies to:** `v_classification`
**Meaning:** Set LOSS or DOUBTFUL3 based on doubtful_since

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is above 1095 and v_doubtful_since is above 1095 | LOSS |

## Calculations

- **provisioning_amount:** (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100))

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Updates: asset_classification, last_classified_date |
| `NPA_PROVISION` | Write | Inserts data into: account_id, classification, provision_amount, calculated_date |
| `NPA_AUDIT_LOG` | Write | Inserts data into: account_id, old_classification, new_classification, changed_on |

## Exception Handling

If no data is found, logs 'ACCOUNT_NOT_FOUND' in the NPA_AUDIT_LOG table. For any other exception, logs the error message in the NPA_AUDIT_LOG table and re-raises the exception.

## Findings / Needs Review

- Calculation needs review: v_provision_pct is assigned a value below 1 and then divided by 100, which may reduce the intended rate by an additional factor of 100.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is unresolved and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized rule affects different fields than the deterministic evidence.
- Reconciliation detected a source/report discrepancy: Synthesized outcome/assignment conflicts with deterministic evidence.
- The calculation for provisioning amount may need review as v_provision_pct is assigned a value below 1 and then divided by 100, which may reduce the intended rate by an additional factor of 100.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
