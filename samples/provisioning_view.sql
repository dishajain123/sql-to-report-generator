CREATE OR REPLACE VIEW vw_active_npa_provisions AS
SELECT
  la.account_id,
  la.customer_id,
  la.overdue_days,
  la.outstanding_amount,
  la.asset_classification,
  np.provision_amount,
  np.classification_date
FROM LOAN_ACCOUNT la
JOIN NPA_PROVISION np
  ON la.account_id = np.account_id
WHERE la.asset_classification != 'STANDARD'
  AND np.classification_date = (
    SELECT MAX(classification_date)
    FROM NPA_PROVISION
    WHERE account_id = la.account_id
  );
