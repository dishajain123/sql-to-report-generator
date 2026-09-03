# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies non-performing assets (NPA) based on the number of overdue days and provisions an amount for the account. It updates the asset classification and inserts records into the NPA provision and audit log tables. |
| Business rules | 3 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## Review Required

The reconciliation stage detected source/report inconsistencies. Business Rules, Calculations, and Data Touched are provisional and must not be treated as confirmed until the discrepancies are resolved.

## What This Does

This procedure classifies non-performing assets (NPA) based on the number of overdue days and provisions an amount for the account. It updates the asset classification and inserts records into the NPA provision and audit log tables.

## Process Flow

1. Reads the overdue days and outstanding amount for the specified account.
2. Classifies the account based on the number of overdue days.
3. Calculates the provisioning amount based on the classification.
4. Updates the asset classification for the account.
5. Inserts a record into the NPA provision table with the provisioning amount and classification date.
6. Inserts a record into the NPA audit log table with the new classification and change date.
7. In case of an exception, logs the error in the NPA audit log table.

## Business Rules

### R1 — Classify account as Doubtful1

**Applies to:** `v_classification`
**Meaning:** Classifies the account as Doubtful1 if overdue days are between 366 and 1095.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 | DOUBTFUL1 |
| ELSE | LOSS |


### R2 — Classify account as DOUBTFUL1

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- v_overdue_days is at most 90
- v_overdue_days is between 366 and 1095
**Meaning:** Classifies the account as DOUBTFUL1 when v_overdue_days BETWEEN 366 AND 1095.


### R3 — Assign V_PROVISION_PCT by source-defined conditions

**Applies to:** `V_PROVISION_PCT`
**Meaning:** Assigns V_PROVISION_PCT according to the ordered conditions in the source.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | 0.40 |
| v_overdue_days is between 91 and 365 | 15 |
| v_overdue_days is between 366 and 1095 | 25 |
| ELSE | 100 |

## Calculations

- **provision_amount:** v_outstanding * v_provision_pct / 100

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Updates: asset_classification |
| `NPA_PROVISION` | Write | Inserts data into: account_id, provision_amount, classification_date |
| `NPA_AUDIT_LOG` | Write | Inserts data into: account_id, new_classification, change_date |

## Exception Handling

Logs the error message in the NPA audit log table if an exception occurs.

## Findings / Needs Review

- Calculation needs review: v_provision_pct is assigned a value below 1 and then divided by 100, which may reduce the intended rate by an additional factor of 100.
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
