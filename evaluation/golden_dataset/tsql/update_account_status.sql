CREATE OR ALTER PROCEDURE dbo.UpdateAccountStatus
  @AccountId INT,
  @NewStatus VARCHAR(20)
AS
BEGIN TRY
  UPDATE dbo.Account
    SET Status = @NewStatus,
        UpdatedAt = GETDATE()
    WHERE AccountId = @AccountId;

  INSERT INTO dbo.AccountAudit (AccountId, OldStatus, NewStatus, ChangedAt)
  SELECT a.AccountId, a.Status, @NewStatus, GETDATE()
  FROM dbo.Account AS a
  WHERE a.AccountId = @AccountId;
END TRY
BEGIN CATCH
  INSERT INTO dbo.ErrorLog (ErrorMessage, CreatedAt)
  VALUES (ERROR_MESSAGE(), GETDATE());
END CATCH;

