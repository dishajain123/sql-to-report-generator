# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a loan account as Standard, Substandard, Doubtful, or Loss based on the number of overdue days and the duration since the account became doubtful. It also calculates the provisioning amount and updates the account's asset classification and last classification date. Additionally, it logs the classification changes and handles exceptions. |
| Business rules | 9 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure classifies a loan account as Standard, Substandard, Doubtful, or Loss based on the number of overdue days and the duration since the account became doubtful. It also calculates the provisioning amount and updates the account's asset classification and last classification date. Additionally, it logs the classification changes and handles exceptions.

## Process Flow

1. Reads overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the number of overdue days and the duration since the account became doubtful.
3. Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provision percentage.
4. Updates the asset classification and last classification date in the LOAN_ACCOUNT table.
5. Inserts the classification and provisioning amount into the NPA_PROVISION table.
6. Inserts the classification change into the NPA_AUDIT_LOG table.
7. Handles exceptions by logging the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as Standard

**Affected Field:** `asset_classification, provisioning_percentage`

**Condition:**

- v_overdue_days <= 90
- v_overdue_days BETWEEN 91 AND 365
- v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365
- v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365)
- v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since > 1095
- v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since > 1095)

**Then:**

- STANDARD
- SUBSTANDARD
- DOUBTFUL1
- DOUBTFUL2
- LOSS
- DOUBTFUL3

### Decision Logic

| Condition | Result |
|---|---|
| v_overdue_days <= 90 | STANDARD |
| v_overdue_days BETWEEN 91 AND 365 | SUBSTANDARD |
| v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 | DOUBTFUL1 |
| v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365) | DOUBTFUL2 |
| v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since > 1095 | LOSS |
| v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since > 1095) | DOUBTFUL3 |

### R2 — Calculate provisioning amount

**Affected Field:** `provisioning_amount`

**Condition:**

- Not specified

**Then:**

- Calculates the provisioning amount using the formula: (outstanding amount - unsecured amount) * (provisioning percentage / 100) + (unsecured amount * ((provisioning percentage + 10) / 100)).


### R3 — Handle no data found exception

**Affected Field:** `NPA_AUDIT_LOG`

**Condition:**

- NO_DATA_FOUND

**Then:**

- Inserts a record into the NPA_AUDIT_LOG table with the account ID, null for old classification, 'ACCOUNT_NOT_FOUND' for new classification, and the current date and time.


### R4 — Handle other exceptions

**Affected Field:** `NPA_AUDIT_LOG`

**Condition:**

- OTHERS

**Then:**

- Inserts a record into the NPA_AUDIT_LOG table with the account ID, null for old classification, 'ERROR: ' || SQLERRM for new classification, and the current date and time.

## Calculations

### Calculation — provisioning_amount

**Expression:**
(v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100))

**Output:**
NPA_PROVISION.provision_amount

**Used By:**
INSERT INTO NPA_PROVISION


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Updates: asset_classification, last_classified_date |
| `NPA_PROVISION` | Write | Inserts data into: account_id, classification, provision_amount, calculated_date |
| `NPA_AUDIT_LOG` | Write | Inserts data into: account_id, old_classification, new_classification, changed_on |

## Exception Handling

If the account does not exist, logs 'ACCOUNT_NOT_FOUND' in the NPA_AUDIT_LOG table. For any other exception, logs the error message in the NPA_AUDIT_LOG table and raises the exception.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
