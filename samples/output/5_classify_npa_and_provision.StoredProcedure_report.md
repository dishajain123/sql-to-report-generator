# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies non-performing assets (NPA) and provisions for potential losses based on the account's overdue days and other factors. It updates the account's asset classification and calculates the provisioning amount, then logs the classification and provisioning details. |
| Business rules | 6 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure classifies non-performing assets (NPA) and provisions for potential losses based on the account's overdue days and other factors. It updates the account's asset classification and calculates the provisioning amount, then logs the classification and provisioning details.

## Process Flow

1. Reads overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on overdue days and doubtful since days into categories such as STANDARD, SUBSTANDARD, DOUBTFUL1, DOUBTFUL2, DOUBTFUL3, or LOSS.
3. Calculates the provisioning amount based on the classification and account details.
4. Updates the asset classification and last classified date in the LOAN_ACCOUNT table for the specified account.
5. Inserts the account's classification and provisioning amount into the NPA_PROVISION table.
6. Inserts the account's classification change details into the NPA_AUDIT_LOG table.
7. Handles exceptions by logging the error and re-raising the exception.

## Business Rules

### R1 — Classify account as STANDARD

**Applies to:** `v_classification`
**Meaning:** Sets the account's asset classification to STANDARD if overdue days are 90 or less.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 and v_doubtful_since is at most 365 | DOUBTFUL1 |
| v_overdue_days is between 366 and 1095 and ELSE | DOUBTFUL2 |
| ELSE and v_doubtful_since is above 1095 | LOSS |
| ELSE and ELSE | DOUBTFUL3 |


### R2 — Classify account as STANDARD

**Eligibility:** latest calculated_date per account
**Meaning:** Classify account as STANDARD.


### R3 — Update asset_classification, last_classified_date

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id.


### R4 — Assign v_classification as SUBSTANDARD

**Applies to:** `v_classification`
**Meaning:** Assigns v_classification the value SUBSTANDARD when the source condition is v_overdue_days BETWEEN 91 AND 365.


### R5 — Assign v_provision_pct as unchanged

**Applies to:** `v_provision_pct`
**Meaning:** Assigns v_provision_pct the value unchanged when the source condition is v_overdue_days BETWEEN 366 AND 1095.


### R6 — Classify account as DOUBTFUL3 or LOSS

**Applies to:** `v_classification`
**Meaning:** Set LOSS or DOUBTFUL3 based on doubtful_since

### Decision Logic
| Condition | Outcome |
|---|---|
| v_doubtful_since is above 1095 | LOSS |
| v_doubtful_since is at most 1095 | DOUBTFUL3 |

## Calculations

- **provisioning_amount:** (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100))

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Sets the account's asset classification to STANDARD if overdue days are 90 or less. The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_accou… |
| `NPA_PROVISION` | Write | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification, last_classified_date to the source-defined value when account_id = p_account_id. |

## Exception Handling

If no data is found for the account, it logs 'ACCOUNT_NOT_FOUND'. For any other exception, it logs the error message and re-raises the exception.

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
