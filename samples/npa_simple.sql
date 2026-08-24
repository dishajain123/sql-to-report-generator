CREATE OR REPLACE PROCEDURE classify_npa_and_provision(p_account_id IN NUMBER) AS
  v_overdue_days   NUMBER;
  v_outstanding    NUMBER;
  v_classification VARCHAR2(20);
  v_provision_pct  NUMBER;
BEGIN
  SELECT overdue_days, outstanding_amount
  INTO v_overdue_days, v_outstanding
  FROM LOAN_ACCOUNT
  WHERE account_id = p_account_id;

  IF v_overdue_days <= 90 THEN
    v_classification := 'STANDARD';
    v_provision_pct := 0.40;
  ELSIF v_overdue_days BETWEEN 91 AND 365 THEN
    v_classification := 'SUBSTANDARD';
    v_provision_pct := 15;
  ELSIF v_overdue_days BETWEEN 366 AND 1095 THEN
    v_classification := 'DOUBTFUL1';
    v_provision_pct := 25;
  ELSE
    v_classification := 'LOSS';
    v_provision_pct := 100;
  END IF;

  UPDATE LOAN_ACCOUNT
  SET asset_classification = v_classification
  WHERE account_id = p_account_id;

  INSERT INTO NPA_PROVISION (account_id, provision_amount, classification_date)
  VALUES (p_account_id, v_outstanding * v_provision_pct / 100, SYSDATE);

  INSERT INTO NPA_AUDIT_LOG (account_id, new_classification, change_date)
  VALUES (p_account_id, v_classification, SYSDATE);

EXCEPTION
  WHEN OTHERS THEN
    INSERT INTO NPA_AUDIT_LOG (account_id, new_classification, change_date)
    VALUES (p_account_id, 'ERROR: ' || SQLERRM, SYSDATE);
END;
/
