# Classify Npa And Provision — Business Logic Report

**Procedure:** `Classify Npa And Provision`  ·  **Dialect:** Oracle  ·  **Input:** `p_account_id` (NUMBER)

## At a Glance

| | |
|---|---|
| Purpose | This procedure classifies a loan account based on its overdue days and updates the asset classification and provisioning amount accordingly. It also logs the classification changes and handles exceptions. |
| Business rules | 9 |
| Tables read | 1 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure classifies a loan account based on its overdue days and updates the asset classification and provisioning amount accordingly. It also logs the classification changes and handles exceptions.

## Process Flow

1. Reads overdue days, outstanding amount, unsecured amount, and doubtful since days from the LOAN_ACCOUNT table for the specified account.
2. Classifies the account based on the overdue days and updates the asset classification and provision percentage.
3. Calculates the provision amount based on the outstanding amount, unsecured amount, and provision percentage.
4. Updates the asset classification and last classified date in the LOAN_ACCOUNT table.
5. Inserts the classification and provision amount into the NPA_PROVISION table.
6. Inserts the account ID, old classification, new classification, and change date into the NPA_AUDIT_LOG table.
7. Handles exceptions by inserting error details into the NPA_AUDIT_LOG table and raising the exception.

## Business Rules

### R1 — Classify account as Standard

**Affected Field:** `asset_classification, provisioning_percentage`

**Explanation:**

- Classifies the account as Standard if overdue days are less than or equal to 90.
- Classifies the account as Substandard if overdue days are between 91 and 365.
- Classifies the account as Doubtful1 if overdue days are between 366 and 1095 and doubtful since days are less than or equal to 365.

### Decision Logic

| Condition | Result |
|---|---|
| v_overdue_days <= 90 | Sets the account's asset classification to Standard and the provisioning percentage to 0.40. |
| v_overdue_days BETWEEN 91 AND 365 | Sets the account's asset classification to Substandard and the provisioning percentage to 15. |
| v_overdue_days BETWEEN 366 AND 1095 AND v_doubtful_since <= 365 | Sets the account's asset classification to Doubtful1 and the provisioning percentage to 25. |
| v_overdue_days BETWEEN 366 AND 1095 AND NOT (v_doubtful_since <= 365) | Sets the account's asset classification to Doubtful2 and the provisioning percentage to 40. |

### R2 — Classify account as

**Affected Field:** `asset_classification, provisioning_percentage`

**Explanation:**

- Classifies the account as Loss if doubtful since days are greater than 1095.
- Classifies the account as Doubtful3 if doubtful since days are not greater than 1095.

### Decision Logic

| Condition | Result |
|---|---|
| v_doubtful_since > 1095 | Sets the account's asset classification to Loss and the provisioning percentage to 100. |
| NOT (v_doubtful_since > 1095) | Sets the account's asset classification to Doubtful3 and the provisioning percentage to 100. |

### R3 — Calculate provisioning amount

**Affected Field:** `provisioning_amount`

**Condition:**

- v_provision_amt := (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100) + (v_unsecured_amt * ((v_provision_pct + 10) / 100))

**Then:**

- Calculates the provisioning amount.


### R4 — Handle NO_DATA_FOUND exception

**Affected Field:** Not specified

**Condition:**

- NO_DATA_FOUND

**Then:**

- Inserts an error record into the NPA_AUDIT_LOG table and raises the exception.


### R5 — Handle OTHERS exception

**Affected Field:** Not specified

**Condition:**

- OTHERS

**Then:**

- Inserts an error record into the NPA_AUDIT_LOG table and raises the exception.

## Calculations

### Calculation — provision_amount

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

If no data is found for the account, it logs 'ACCOUNT_NOT_FOUND'. For any other exception, it logs the error message and raises the exception.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
