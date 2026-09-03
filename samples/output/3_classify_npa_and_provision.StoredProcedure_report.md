# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a non-performing asset (NPA) based on the number of overdue days and provisions an amount for the asset. It updates the asset classification and inserts records into the NPA_PROVISION and NPA_AUDIT_LOG tables. |
| Business rules | 3 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This procedure classifies a non-performing asset (NPA) based on the number of overdue days and provisions an amount for the asset. It updates the asset classification and inserts records into the NPA_PROVISION and NPA_AUDIT_LOG tables.

## Process Flow

1. Reads the overdue days and outstanding amount for the specified account from the LOAN_ACCOUNT table.
2. Classifies the account based on the number of overdue days and calculates the provisioning percentage.
3. Updates the asset classification in the LOAN_ACCOUNT table.
4. Inserts a record into the NPA_PROVISION table with the calculated provisioning amount.
5. Inserts a record into the NPA_AUDIT_LOG table with the new classification and change date.
6. In case of an exception, logs the error in the NPA_AUDIT_LOG table and continues execution.

## Business Rules

### R1 — Determine v_classification from decision bands

**Applies to:** `v_classification`
**Meaning:** Determines the value assigned to v_classification based on the source-defined decision bands.

### Decision Logic
| Condition | Outcome |
|---|---|
| v_overdue_days is at most 90 | STANDARD |
| v_overdue_days is between 91 and 365 | SUBSTANDARD |
| v_overdue_days is between 366 and 1095 | DOUBTFUL1 |
| ELSE | LOSS |


### R2 — Update asset_classification

**Applies to:** `v_classification`
**Eligibility:** account_id equals p_account_id
**Meaning:** The procedure sets asset_classification to the source-defined value when account_id = p_account_id.


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
| `LOAN_ACCOUNT` | Read + Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_PROVISION` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification to the source-defined value when account_id = p_account_id. |

## Exception Handling

In case of an exception, the error message is logged in the NPA_AUDIT_LOG table, and the procedure continues execution.

## Findings / Needs Review

- Provisioning calculation needs review: a percentage below 1 is divided by 100 in the source, producing a rate below 1% (for example, 0.40 / 100).
- Reconciliation review required: rule evidence is llm_only and must not be treated as a confirmed business rule.
- Reconciliation review required: rule evidence is conflict and must not be treated as a confirmed business rule.
- Reconciliation review required: coverage evidence is deterministic_only and must not be treated as a confirmed business rule.
- Reconciliation detected a source/report discrepancy: Synthesized rule affects different fields than the deterministic evidence.
- Reconciliation detected a source/report discrepancy: Synthesized outcome/assignment conflicts with deterministic evidence.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `classify_npa_and_provision.StoredProcedure_verification.md`._
