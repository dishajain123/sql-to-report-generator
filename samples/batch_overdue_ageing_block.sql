DECLARE
    CURSOR c_overdue_accounts IS
        SELECT account_id, overdue_days, outstanding_amount
          FROM LOAN_ACCOUNT
         WHERE status = 'ACTIVE'
           AND overdue_days > 0
         FOR UPDATE;

    v_ageing_bucket VARCHAR2(20);
    v_processed_count NUMBER := 0;
BEGIN
    FOR rec IN c_overdue_accounts LOOP
        BEGIN
            IF rec.overdue_days <= 30 THEN
                v_ageing_bucket := 'BUCKET_0_30';
            ELSIF rec.overdue_days <= 60 THEN
                v_ageing_bucket := 'BUCKET_31_60';
            ELSIF rec.overdue_days <= 90 THEN
                v_ageing_bucket := 'BUCKET_61_90';
            ELSE
                v_ageing_bucket := 'BUCKET_90_PLUS';
            END IF;

            MERGE INTO OVERDUE_AGEING_SUMMARY tgt
            USING (SELECT rec.account_id AS account_id FROM dual) src
            ON (tgt.account_id = src.account_id)
            WHEN MATCHED THEN
                UPDATE SET tgt.ageing_bucket = v_ageing_bucket,
                           tgt.last_updated = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (account_id, ageing_bucket, last_updated)
                VALUES (rec.account_id, v_ageing_bucket, SYSDATE);

            v_processed_count := v_processed_count + 1;

        EXCEPTION
            WHEN OTHERS THEN
                INSERT INTO NPA_AUDIT_LOG (account_id, old_classification, new_classification, changed_on)
                VALUES (rec.account_id, NULL, 'AGEING_UPDATE_FAILED: ' || SQLERRM, SYSDATE);
        END;
    END LOOP;

    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE;
END;
/
