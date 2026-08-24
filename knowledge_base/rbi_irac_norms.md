# RBI IRAC Asset Classification & Provisioning Norms (Reference)

This document summarizes commonly implemented Income Recognition, Asset
Classification and Provisioning (IRAC) norms used in Indian core-banking
systems for classifying loan accounts and calculating regulatory
provisioning. It is used as retrieval context so the extraction pipeline
correctly interprets overdue-day thresholds and provisioning logic found
in banking stored procedures.

## Asset Classification Buckets (by overdue days)

- **Standard**: Overdue for 90 days or less (interest and/or principal not
  past due, or past due for a period not exceeding 90 days). Attracts a
  minimal standard provisioning charge (commonly around 0.40% of the
  outstanding, varying by loan segment).
- **Sub-Standard (NPA)**: An account that has remained an NPA for a period
  less than or equal to 12 months (i.e., overdue between 91 and roughly
  365 days). Typically attracts around 15% provisioning on the total
  outstanding, with a higher rate (commonly 25%) applied to the unsecured
  portion of the exposure.
- **Doubtful 1**: Remained in the doubtful category for up to 1 year after
  being classified sub-standard (roughly 366-730 days overdue). Provisioning
  increases, often to around 25% on the secured portion.
- **Doubtful 2**: Remained doubtful for 1-3 years (roughly 731-1095 days
  overdue). Provisioning increases further, often to around 40% on the
  secured portion.
- **Doubtful 3**: Remained doubtful for more than 3 years. Provisioning on
  the secured portion rises toward 100%.
- **Loss**: An account identified as a loss asset, where the entire
  outstanding is generally considered unrecoverable. Provisioning is 100%
  of the outstanding.
- **Unsecured portion**: Regardless of bucket, the unsecured portion of an
  NPA's exposure generally attracts a higher provisioning percentage than
  the secured portion, since there is no collateral to recover against.

## Why this matters for logic extraction

When a stored procedure branches on a variable representing "days overdue"
or "days past due" and assigns a classification code (e.g.
'STANDARD', 'SUBSTANDARD', 'DOUBTFUL1', 'DOUBTFUL2', 'DOUBTFUL3', 'LOSS'),
this is implementing IRAC asset classification. When it subsequently
computes an amount using a percentage tied to that classification, this is
implementing the corresponding provisioning calculation. The business
intent is regulatory compliance and financial risk provisioning, not
generic status tracking.

## Interest Recognition

Once an account is classified as an NPA, banks are generally required to
stop recognizing interest income on an accrual basis for that account, and
instead recognize it only when actually received. Logic that halts
interest accrual, reverses previously accrued but uncollected interest, or
moves an account to a memorandum/suspense interest account upon NPA
classification is implementing this income-recognition rule.

## Audit / Traceability Expectations

Regulatory examinations require that every asset classification change and
every provisioning change be traceable. Logic that writes classification
or provisioning changes into an audit/history/log table is implementing a
regulatory traceability control, not just generic logging.
