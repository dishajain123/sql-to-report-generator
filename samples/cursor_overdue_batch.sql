DECLARE
  CURSOR overdue_cursor IS
    SELECT account_id, overdue_days, outstanding_amount
    FROM LOAN_ACCOUNT
    WHERE overdue_days > 90
      AND asset_classification = 'STANDARD';

  v_new_classification VARCHAR2(20);
  v_provision_pct       NUMBER;
BEGIN
  FOR rec IN overdue_cursor LOOP
    IF rec.overdue_days BETWEEN 91 AND 365 THEN
      v_new_classification := 'SUBSTANDARD';
      v_provision_pct := 15;
    ELSIF rec.overdue_days BETWEEN 366 AND 1095 THEN
      v_new_classification := 'DOUBTFUL1';
      v_provision_pct := 25;
    ELSE
      v_new_classification := 'LOSS';
      v_provision_pct := 100;
    END IF;

    UPDATE LOAN_ACCOUNT
    SET asset_classification = v_new_classification
    WHERE account_id = rec.account_id;

    MERGE INTO NPA_PROVISION np
    USING (SELECT rec.account_id AS account_id FROM dual) src
    ON (np.account_id = src.account_id)
    WHEN MATCHED THEN
      UPDATE SET provision_amount = rec.outstanding_amount * v_provision_pct / 100,
                 classification_date = SYSDATE
    WHEN NOT MATCHED THEN
      INSERT (account_id, provision_amount, classification_date)
      VALUES (rec.account_id, rec.outstanding_amount * v_provision_pct / 100, SYSDATE);

    INSERT INTO NPA_AUDIT_LOG (account_id, new_classification, change_date)
    VALUES (rec.account_id, v_new_classification, SYSDATE);
  END LOOP;

EXCEPTION
  WHEN OTHERS THEN
    INSERT INTO NPA_AUDIT_LOG (account_id, new_classification, change_date)
    VALUES (NULL, 'BATCH ERROR: ' || SQLERRM, SYSDATE);
    ROLLBACK;
END;
/
