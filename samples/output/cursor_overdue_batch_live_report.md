# Anonymous Block — Business Logic Report

**Procedure:** `Anonymous Block`  ·  **Dialect:** Oracle  ·  **Input:** None

## At a Glance

| | |
|---|---|
| Purpose | This PL/SQL block processes each account with overdue days greater than 90, updating the asset classification and provisioning percentage based on the number of overdue days. It also updates the provisioning amount and logs the changes. |
| Business rules | 4 |
| Tables read | 3 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This PL/SQL block processes each account with overdue days greater than 90, updating the asset classification and provisioning percentage based on the number of overdue days. It also updates the provisioning amount and logs the changes.

## Process Flow

1. Reads account details from the LOAN_ACCOUNT table for accounts with overdue days greater than 90 and asset classification as 'STANDARD'.
2. For each account, determines the new asset classification and provisioning percentage based on the number of overdue days.
3. Updates the asset classification in the LOAN_ACCOUNT table.
4. Updates or inserts the provisioning amount and classification date in the NPA_PROVISION table.
5. Inserts an audit log entry in the NPA_AUDIT_LOG table.
6. In case of an exception, logs the error in the NPA_AUDIT_LOG table and rolls back the transaction.

## Business Rules

### R1 — Classify account as Substandard

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- Account is overdue is between 91 and 365 days
- overdue_days is above 90
**Meaning:** Classify account as Substandard.

### Decision Logic
| Condition | Outcome |
|---|---|
| overdue_days is between 91 and 365 | SUBSTANDARD |


### R2 — Calculate provisioning amount

**Applies to:** `provision_amount`
**Meaning:** Calculates the provisioning amount based on the outstanding amount and provisioning percentage.


### R3 — Classify account as Substandard

**Applies to:** `v_classification`
**Eligibility (all must hold):**
- overdue_days is between 91 and 365
- overdue_days is between 366 and 1095
**Meaning:** Classify account as Substandard.


### R4 — Update asset_classification

**Applies to:** `v_classification`
**Eligibility:** account_id equals account_id
**Meaning:** The procedure sets asset_classification to the source-defined value when account_id = rec.account_id.

## Calculations

- **provision_amount:** rec.outstanding_amount * v_provision_pct / 100

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Set STANDARD classification and 15 provision pct The procedure sets asset_classification to the source-defined value when account_id = rec.account_id. |
| `NPA_PROVISION` | Read + Write | Calculates the provisioning amount based on the outstanding amount and provisioning percentage. Set STANDARD classification and 0.40 provision pct |
| `NPA_AUDIT_LOG` | Write | The procedure sets asset_classification to the source-defined value when account_id = rec.account_id. |
| `dual` | Read | Provides: rec.account_id AS account_id |

## Exception Handling

Logs the error message in the NPA_AUDIT_LOG table and rolls back the transaction.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `cursor_overdue_batch_verification.md`._
