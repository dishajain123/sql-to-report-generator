CREATE OR ALTER PROCEDURE dbo.SyncProvisioning
AS
BEGIN
  MERGE dbo.NPA_Provision AS tgt
  USING (
    SELECT account_id, provision_amount
    FROM dbo.Staging_Provisioning
  ) AS src
  ON tgt.account_id = src.account_id
  WHEN MATCHED THEN
    UPDATE SET provision_amount = src.provision_amount,
               updated_at = GETDATE()
  WHEN NOT MATCHED THEN
    INSERT (account_id, provision_amount, created_at)
    VALUES (src.account_id, src.provision_amount, GETDATE());
END;

