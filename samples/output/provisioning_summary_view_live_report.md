# VW Provision Summary — Business Logic Report

**Procedure:** `VW Provision Summary`  ·  **Dialect:** Oracle  ·  **Input:** None

## At a Glance

| | |
|---|---|
| Purpose | This view provides a summary of provisioning details for loan accounts, including the branch code, asset classification, account count, total outstanding amount, and total provision amount. It filters accounts based on non-null asset classification and the most recent provisioning date. |
| Business rules | 3 |
| Tables read | 2 |
| Tables written | 0 |
| Produces audit trail | No |

## What This Does

This view provides a summary of provisioning details for loan accounts, including the branch code, asset classification, account count, total outstanding amount, and total provision amount. It filters accounts based on non-null asset classification and the most recent provisioning date.

## Process Flow

1. Reads the branch code, asset classification, account count, total outstanding amount, and total provision amount from the LOAN_ACCOUNT and NPA_PROVISION tables.
2. Filters records where the asset classification is not null and the provisioning date is the most recent for each account.

## Business Rules

### R1 — Filter non-null asset classification

**Applies to:** `v_classification`
**Eligibility:** Asset classification is not null
**Meaning:** Ensures that only accounts with a non-null asset classification are included in the summary.


### R2 — Filter most recent provisioning date

**Applies to:** `account_id`
**Eligibility:** Provisioning date is the most recent for each account
**Meaning:** Ensures that only the most recent provisioning date for each account is included in the summary.


### R3 — Filter non-null asset classification

**Applies to:** `account_id`
**Eligibility:** latest calculated_date per account
**Meaning:** Filter non-null asset classification.

## Calculations

- **account_count:** COUNT(*)
- **total_outstanding:** SUM(la.outstanding_amount)
- **total_provision:** SUM(np.provision_amount)

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read | Ensures that only accounts with a non-null asset classification are included in the summary. |
| `NPA_PROVISION` | Read | Ensures that only accounts with a non-null asset classification are included in the summary. |

## Exception Handling

No specific exception handling is defined in the source SQL.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `VW_PROVISION_SUMMARY.View_verification.md`._
