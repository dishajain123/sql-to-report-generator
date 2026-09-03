# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a loan account based on its overdue days and doubtful since days, and calculates the provisioning amount for non-performing assets (NPA). It updates the account's asset classification and last classified date, inserts the classification and provisioning amount into the NPA provision table, and logs changes in the NPA audit log. |
| Business rules | 7 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure classifies a loan account based on its overdue days and doubtful since days, and calculates the provisioning amount for non-performing assets (NPA). It updates the account's asset classification and last classified date, inserts the classification and provisioning amount into the NPA provision table, and logs changes in the NPA audit log.

## Process Flow

1. Reads overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on overdue days and doubtful since days into categories such as STANDARD, SUBSTANDARD, DOUBTFUL1, DOUBTFUL2, DOUBTFUL3, and LOSS.
3. Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provision percentage.
4. Updates the asset classification and last classified date in the LOAN_ACCOUNT table for the specified account.
5. Inserts the account's classification and provisioning amount into the NPA_PROVISION table.
6. Inserts a log entry into the NPA_AUDIT_LOG table for the specified account.
7. Handles exceptions by logging an account not found or an error message into the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as STANDARD

**Affected Field:** `asset_classification, provisioning_percentage`

**Condition:**

- v_overdue_days <= 90
- v_overdue_days BETWEEN 91 AND 365
- v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365
- v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since > 365
- v_overdue_days > 1095 AND v_doubtful_since > 1095
- v_overdue_days > 1095 AND v_doubtful_since <= 1095

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
| v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since > 365 | DOUBTFUL2 |
| v_overdue_days > 1095 AND v_doubtful_since > 1095 | LOSS |
| v_overdue_days > 1095 AND v_doubtful_since <= 1095 | DOUBTFUL3 |

### R2 — Calculate provisioning amount

**Affected Field:** `provisioning_amount`

**Condition:**

- Not specified

**Then:**

- Calculates the provisioning amount using the formula: (outstanding amount - unsecured amount) * (provisioning percentage / 100) + (unsecured amount * ((provisioning percentage + 10) / 100)).


### R3 — Handle NO_DATA_FOUND exception

**Affected Field:** Not specified

**Condition:**

- Not specified

**Then:**

- Inserts an audit log entry for 'ACCOUNT_NOT_FOUND' and raises the exception.


### R4 — Handle OTHERS exception

**Affected Field:** Not specified

**Condition:**

- Not specified

**Then:**

- Inserts an audit log entry for 'ERROR: ' || SQLERRM and raises the exception.

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

If the account does not exist, logs 'ACCOUNT_NOT_FOUND'. For any other exception, logs the error message and re-raises the exception.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
