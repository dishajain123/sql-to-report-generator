# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a loan account based on its overdue days and updates the asset classification and provisioning percentage accordingly. It also logs the classification changes and handles exceptions. |
| Business rules | 9 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure classifies a loan account based on its overdue days and updates the asset classification and provisioning percentage accordingly. It also logs the classification changes and handles exceptions.

## Process Flow

1. Reads the overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the overdue days and updates the asset classification and last classified date in the LOAN_ACCOUNT table.
3. Calculates the provisioning amount based on the outstanding amount, unsecured amount, and provisioning percentage.
4. Inserts the account classification and provisioning amount into the NPA_PROVISION table.
5. Inserts the account classification change into the NPA_AUDIT_LOG table.
6. Handles exceptions by logging the error in the NPA_AUDIT_LOG table.

## Business Rules

### R1 — Classify account as Standard

**Affected Field:** `asset_classification, provisioning_percentage`

**Explanation:**

- Classifies the account as Standard if the overdue days are 90 or less.
- Classifies the account as Substandard if the overdue days are between 91 and 365.
- Classifies the account as Doubtful1 if the overdue days are between 366 and 1095 and the account has been doubtful for 365 days or less.

### Decision Logic

| Condition | Result |
|---|---|
| v_overdue_days <= 90 | Sets the account's asset classification to Standard and provisioning percentage to 0.40. |
| v_overdue_days BETWEEN 91 AND 365 | Sets the account's asset classification to Substandard and provisioning percentage to 15. |
| v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 | Sets the account's asset classification to Doubtful1 and provisioning percentage to 25. |
| v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365) | Sets the account's asset classification to Doubtful2 and provisioning percentage to 40. |

### R2 — Classify account as

**Affected Field:** `asset_classification, provisioning_percentage`

**Explanation:**

- Classifies the account as Loss if the account has been doubtful for more than 1095 days.
- Classifies the account as Doubtful3 if the account has been doubtful for 1095 days or less.

### Decision Logic

| Condition | Result |
|---|---|
| v_doubtful_since > 1095 | Sets the account's asset classification to Loss and provisioning percentage to 100. |
| NOT (v_doubtful_since > 1095) | Sets the account's asset classification to Doubtful3 and provisioning percentage to 100. |

### R3 — Calculate provisioning amount

**Affected Field:** `provisioning_amount`

**Condition:**

- Not specified

**Then:**

- Calculates the provisioning amount.


### R4 — Handle NO_DATA_FOUND exception

**Affected Field:** Not specified

**Condition:**

- NO_DATA_FOUND

**Then:**

- Logs the error in the NPA_AUDIT_LOG table.


### R5 — Handle OTHERS exception

**Affected Field:** Not specified

**Condition:**

- OTHERS

**Then:**

- Logs the error in the NPA_AUDIT_LOG table and raises the exception.

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

If the account is not found, logs 'ACCOUNT_NOT_FOUND' in the NPA_AUDIT_LOG table. For any other exception, logs the error message in the NPA_AUDIT_LOG table and raises the exception.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
