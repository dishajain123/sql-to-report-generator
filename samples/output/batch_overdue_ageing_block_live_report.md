# Anonymous Block — Business Logic Report

**Procedure:** `Anonymous Block`  ·  **Dialect:** Oracle  ·  **Input:** None

## At a Glance

| | |
|---|---|
| Purpose | This PL/SQL block processes overdue loan accounts, classifies them into ageing buckets based on the number of overdue days, and updates the ageing summary table with the new classification. It also logs any failures during the process. |
| Business rules | 5 |
| Tables read | 3 |
| Tables written | 3 |
| Produces audit trail | Yes — account and customer movement history |

## What This Does

This PL/SQL block processes overdue loan accounts, classifies them into ageing buckets based on the number of overdue days, and updates the ageing summary table with the new classification. It also logs any failures during the process.

## Process Flow

1. Locks active loan accounts with overdue days greater than zero.
2. Iterates over each locked overdue account.
3. Classifies the account into an ageing bucket based on the number of overdue days.
4. Updates the ageing summary table with the new ageing bucket classification.
5. Increments the count of processed accounts.
6. Logs any exceptions that occur during the process.

## Business Rules

### R1 — Lock active overdue accounts

**Applies to:** `status`
**Eligibility (all must hold):**
- Account status is active
- Account has overdue days greater than zero
**Meaning:** Ensures that active loan accounts with overdue days greater than zero are locked for processing.


### R2 — Update ageing summary table

**Applies to:** `ageing_bucket`
**Eligibility:** Account record matches in the ageing summary table
**Meaning:** The ageing summary table is updated.


### R3 — Increment processed account count

**Applies to:** `v_processed_count`
**Eligibility:** v_processed_count : equals v_processed_count + 1
**Meaning:** Increments the count of processed accounts.


### R4 — Update ageing summary table

**Applies to:** `status`
**Eligibility:** status equals 'ACTIVE' and overdue_days is above 0
**Meaning:** The ageing summary table is updated.


### R5 — Update ageing summary table

**Applies to:** `v_ageing_bucket`
**Eligibility (all must hold):**
- overdue_days is at most 30
- overdue_days is at most 60
- overdue_days is at most 90
**Meaning:** The ageing summary table is updated.

## Calculations

_None identified._

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read + Write | Ensures that active loan accounts with overdue days greater than zero are locked for processing. Assign BUCKET_0_30 |
| `OVERDUE_AGEING_SUMMARY` | Read + Write | Set STANDARD classification and 25 provision pct Assign BUCKET_0_30 |
| `NPA_AUDIT_LOG` | Write | Updates: account_id, old_classification, new_classification, changed_on |
| `dual` | Read | Provides: rec.account_id AS account_id |

## Exception Handling

If an exception occurs during the processing of an account, it is logged in the NPA audit log, and the transaction is rolled back. The exception is then re-raised.

## Findings / Needs Review

- The condition for the IF statement is missing.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `batch_overdue_ageing_block_verification.md`._
