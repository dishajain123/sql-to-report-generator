CREATE OR ALTER PROCEDURE dbo.RecalculateRiskBand
  @AccountId INT
AS
BEGIN TRY
  UPDATE dbo.AccountRisk
    SET RiskBand = CASE
      WHEN DpdDays <= 30 THEN 'LOW'
      WHEN DpdDays <= 90 THEN 'MEDIUM'
      ELSE 'HIGH'
    END
  WHERE AccountId = @AccountId;
END TRY
BEGIN CATCH
  INSERT INTO dbo.RiskErrors (AccountId, ErrorMessage)
  VALUES (@AccountId, ERROR_MESSAGE());
END CATCH;

