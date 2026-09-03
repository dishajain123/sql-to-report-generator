# Anonymous Block — Business Logic Report

**Procedure:** `Anonymous Block`  ·  **Dialect:** Oracle  ·  **Input:** None

## At a Glance

| | |
|---|---|
| Purpose | This procedure updates the asset classification and provisioning percentage for accounts that are overdue by more than 90 days and currently classified as 'STANDARD'. It also logs changes and handles exceptions. |
| Business rules | 5 |
| Tables read | 3 |
| Tables written | 3 |
| Produces audit trail | Yes — records audit events |

## What This Does

This procedure updates the asset classification and provisioning percentage for accounts that are overdue by more than 90 days and currently classified as 'STANDARD'. It also logs changes and handles exceptions.

## Process Flow

1. Reads overdue accounts with more than 90 days overdue and classified as 'STANDARD'.
2. Classifies accounts based on the number of overdue days and updates the asset classification and provisioning percentage.
3. Calculates the provisioning amount based on the outstanding amount and the provisioning percentage.
4. Updates the provisioning record with the new provisioning amount and classification date.
5. Inserts an audit log entry for each account with the new classification and change date.
6. Handles exceptions by logging the error and rolling back the transaction.

## Business Rules

### R1 — Classify overdue accounts

**Affected Field:** `asset_classification, provision_pct`

**Explanation:**

- Classifies accounts based on the number of overdue days.

### Decision Logic

| Condition | Result |
|---|---|
| rec.overdue_days BETWEEN 91 AND 365 | Sets the account's asset classification to 'SUBSTANDARD' and provisioning percentage to 15%. |
| rec.overdue_days BETWEEN 366 AND 1095 | Sets the account's asset classification to 'SUBSTANDARD' and provisioning percentage to 15%. |
| rec.overdue_days < 91 OR rec.overdue_days > 1095 | Sets the account's asset classification to 'SUBSTANDARD' and provisioning percentage to 15%. |

### R2 — Update provisioning amount

**Affected Field:** `provision_amount`

**Condition:**

- rec.overdue_days > 90 AND asset_classification = 'STANDARD'

**Then:**

- Updates the provisioning amount based on the outstanding amount and the provisioning percentage.


### R3 — Insert audit log entry

**Affected Field:** `NPA_AUDIT_LOG, account_id, new_classification, change_date`

**Condition:**

- rec.overdue_days > 90 AND asset_classification = 'STANDARD'

**Then:**

- Inserts a new entry into the NPA_AUDIT_LOG table with the account ID, new classification, and change date.


### R4 — Merge provisioning data

**Affected Field:** `provision_amount, classification_date`

**Condition:**

- rec.overdue_days > 90 AND asset_classification = 'STANDARD'

**Then:**

- Updates the provisioning amount and classification date in the NPA_PROVISION table.


### R5 — Handle exceptions

**Affected Field:** Not specified

**Condition:**

- WHEN OTHERS

**Then:**

- Inserts an error log entry and rolls back the transaction.

## Calculations

### Calculation — provision_amount

**Expression:**
rec.outstanding_amount * v_provision_pct / 100

**Output:**
Not specified

**Used By:**
Not specified


## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Updates: asset_classification |
| `NPA_PROVISION` | Read + Write | Provides: np.account_id, provision_amount, classification_date, rec.outstanding_amount, v_provision_pct |
| `NPA_AUDIT_LOG` | Write | Inserts data into: account_id, new_classification, change_date |
| `dual` | Read | Provides: rec.account_id AS account_id |

## Exception Handling

Logs the error message and rolls back the transaction in case of an exception.

## Findings / Needs Review

- Possible unreviewed decision logic near source line 11-25 (ASSIGNMENT/LOOP/UPDATE): no synthesized rule's evidence appears to reference "FOR rec IN overdue_cursor LOOP     IF rec.overdue_days BETWEEN 91 AND 365 THEN       v_new_classification := 'SUBSTANDARD';       v_provision_pct := 15;     ELS...". Needs human review to confirm whether this is business-relevant.
- Possible unreviewed decision logic near source line 30-37 (ASSIGNMENT/CALCULATION/INSERT/WHEN): no synthesized rule's evidence appears to reference "WHEN MATCHED THEN       UPDATE SET provision_amount = rec.outstanding_amount * v_provision_pct / 100,                  classification_date = SYSDATE     WHEN NO...". Needs human review to confirm whether this is business-relevant.

---

_Source traceability, rule IDs, reconciliation, and run metadata are emitted in the pipeline run log rather than in this report._
