CREATE OR REPLACE VIEW VW_PROVISION_SUMMARY AS
SELECT
    la.branch_code,
    la.asset_classification,
    COUNT(*) AS account_count,
    SUM(la.outstanding_amount) AS total_outstanding,
    SUM(np.provision_amount) AS total_provision
FROM LOAN_ACCOUNT la
JOIN NPA_PROVISION np
  ON np.account_id = la.account_id
WHERE la.asset_classification IS NOT NULL
  AND np.calculated_date = (
        SELECT MAX(np2.calculated_date)
        FROM NPA_PROVISION np2
        WHERE np2.account_id = la.account_id
      )
GROUP BY la.branch_code, la.asset_classification;
