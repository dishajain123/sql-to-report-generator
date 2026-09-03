# Vw Active Npa Provisions — Business Logic Report

**Procedure:** `Vw Active Npa Provisions`  ·  **Dialect:** Oracle  ·  **Input:** None

## At a Glance

| | |
|---|---|
| Purpose | This view provides a list of active non-performing asset (NPA) provisions for accounts that are not classified as Standard. It includes details such as account ID, customer ID, overdue days, outstanding amount, asset classification, provision amount, and the date of the most recent classification. |
| Business rules | 2 |
| Tables read | 2 |
| Tables written | 0 |
| Produces audit trail | No |

## What This Does

This view provides a list of active non-performing asset (NPA) provisions for accounts that are not classified as Standard. It includes details such as account ID, customer ID, overdue days, outstanding amount, asset classification, provision amount, and the date of the most recent classification.

## Process Flow

1. Reads account details from the LOAN_ACCOUNT table where the asset classification is not Standard.
2. Reads the most recent provision amount and classification date from the NPA_PROVISION table for each account.
3. Filters the records to include only those where the classification date is the most recent one for the account.

## Business Rules

### R1 — Select active NPA provisions

**Applies to:** `v_classification`
**Eligibility:** Account asset classification is not Standard
**Meaning:** Retrieves active non-performing asset provisions for accounts not classified as Standard.


### R2 — Select active NPA provisions

**Applies to:** `classification_date, account_id`
**Eligibility:** latest classification_date per account
**Meaning:** Select active NPA provisions.

## Calculations

_None identified._

## Data Touched

| Table | Read/Write | Purpose |
|---|---|---|
| `LOAN_ACCOUNT` | Read | Retrieves active non-performing asset provisions for accounts not classified as Standard. Keep only most recent provision row |
| `NPA_PROVISION` | Read | Retrieves active non-performing asset provisions for accounts not classified as Standard. Keep only most recent provision row |

## Exception Handling

No exception handling logic is explicitly defined in the source.

## Findings / Needs Review

None identified.

---

_Source traceability, rule IDs, reconciliation, and run metadata for this report are maintained separately in `vw_active_npa_provisions.View_verification.md`._
