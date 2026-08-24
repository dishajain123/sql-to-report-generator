CREATE OR REPLACE PROCEDURE classify_npa_and_provision (
    p_account_id IN NUMBER
) IS
    v_overdue_days      NUMBER;
    v_outstanding_amt   NUMBER;
    v_unsecured_amt     NUMBER;
    v_classification    VARCHAR2(20);
    v_provision_pct     NUMBER;
    v_provision_amt     NUMBER;
    v_doubtful_since    NUMBER;
BEGIN
    SELECT overdue_days, outstanding_amount, unsecured_amount, doubtful_since_days
      INTO v_overdue_days, v_outstanding_amt, v_unsecured_amt, v_doubtful_since
      FROM LOAN_ACCOUNT
     WHERE account_id = p_account_id;

    IF v_overdue_days <= 90 THEN
        v_classification := 'STANDARD';
        v_provision_pct := 0.40;
    ELSIF v_overdue_days BETWEEN 91 AND 365 THEN
        v_classification := 'SUBSTANDARD';
        v_provision_pct := 15;
    ELSIF v_overdue_days BETWEEN 366 AND 1095 THEN
        IF v_doubtful_since <= 365 THEN
            v_classification := 'DOUBTFUL1';
            v_provision_pct := 25;
        ELSE
            v_classification := 'DOUBTFUL2';
            v_provision_pct := 40;
        END IF;
    ELSE
        IF v_doubtful_since > 1095 THEN
            v_classification := 'LOSS';
            v_provision_pct := 100;
        ELSE
            v_classification := 'DOUBTFUL3';
            v_provision_pct := 100;
        END IF;
    END IF;

    v_provision_amt := (v_outstanding_amt - v_unsecured_amt) * (v_provision_pct / 100)
                        + (v_unsecured_amt * ((v_provision_pct + 10) / 100));

    UPDATE LOAN_ACCOUNT
       SET asset_classification = v_classification,
           last_classified_date = SYSDATE
     WHERE account_id = p_account_id;

    INSERT INTO NPA_PROVISION (account_id, classification, provision_amount, calculated_date)
    VALUES (p_account_id, v_classification, v_provision_amt, SYSDATE);

    INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on)
    VALUES (p_account_id, NULL, v_classification, SYSDATE);

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on)
        VALUES (p_account_id, NULL, 'ACCOUNT_NOT_FOUND', SYSDATE);
    WHEN OTHERS THEN
        INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on)
        VALUES (p_account_id, NULL, 'ERROR: ' || SQLERRM, SYSDATE);
        RAISE;
END;
/
