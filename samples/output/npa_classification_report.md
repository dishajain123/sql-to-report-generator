## Object Overview

- **Object Name:** `classify_npa_and_provision`
- **Object Type:** Procedure
- **Parameters:**

| Parameter | Direction | Datatype |
|---|---|---|
| `p_account_id` | IN | NUMBER |

## Purpose Summary

The classify_npa_and_provision procedure classifies a loan account as Non-Performing Asset (NPA) based on its overdue days and doubtful since days, and calculates the provision amount accordingly. The procedure updates the loan account's asset classification and inserts records into NPA provision and audit log tables. The classification and provisioning are done in accordance with RBI IRAC guidelines.

## Tables Read

| Table Name | Business Context | Filter Conditions |
|---|---|---|
| `LOAN_ACCOUNT` | Columns referenced: overdue_days, outstanding_amount, unsecured_amount, doubtful_since_days | account_id = p_account_id |

## Tables Written

| Table Name | Operation Type | Columns Affected | Business Trigger |
|---|---|---|---|
| `LOAN_ACCOUNT` | UPDATE | asset_classification, last_classified_date | account_id = p_account_id |
| `NPA_PROVISION` | INSERT | account_id, classification, provision_amount, calculated_date | Always, on each execution |
| `NPA_AUDIT_LOG` | INSERT | account_id, old_classification, new_classification, changed_on | Always, on each execution |

## Step-by-Step Logic Flow

1. The system retrieves the loan account details, including overdue days, outstanding amount, unsecured amount, and doubtful since days, for the given account ID.
2. The system classifies the loan account as NPA based on its overdue days and doubtful since days.
3. The system calculates the provision amount based on the outstanding amount, unsecured amount, and provision percentage.
4. The system updates the loan account's asset classification and inserts records into NPA provision and audit log tables.

## Business Rules / Validations

| Condition | Resulting Action | Fields Affected |
|---|---|---|
| The loan account's overdue days are less than or equal to 90 days | The system sets the account's asset classification to STANDARD and the provision percentage to 40% | asset_classification, provision_percentage |
| The loan account's overdue days are between 91 and 365 days | The system sets the account's asset classification to SUBSTANDARD and the provision percentage to 15% | asset_classification, provision_percentage |
| The loan account's overdue days are between 366 and 1095 days | The system checks the doubtful since days to determine the asset classification and provision percentage | None (no data written) |
| The loan account's doubtful since days are less than or equal to 365 days | The system sets the account's asset classification to DOUBTFUL1 and the provision percentage to 25% | asset_classification, provision_percentage |
| The loan account's doubtful since days are greater than 365 days but less than or equal to 1095 days | The system sets the account's asset classification to DOUBTFUL2 and the provision percentage to 40% | asset_classification, provision_percentage |
| The loan account's doubtful since days are greater than 1095 days | The system sets the account's asset classification to LOSS and the provision percentage to 100% | asset_classification, provision_percentage |

## Calculations / Formulas

- **Provision amount:** The provision amount is calculated as the sum of the provision amount for the secured amount and the provision amount for the unsecured amount. The provision amount for the secured amount is calculated as the outstanding amount minus the unsecured amount, multiplied by the provision percentage divided by 100. The provision amount for the unsecured amount is calculated as the unsecured amount multiplied by the provision percentage plus 10, divided by 100.

## Exception Handling Behavior

The system handles exceptions by inserting records into the NPA audit log table and raising an error. If no data is found, the system inserts a record into the NPA audit log table.

## Ambiguities / Needs Review

None.
