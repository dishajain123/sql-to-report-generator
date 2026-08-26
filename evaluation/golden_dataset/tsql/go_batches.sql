USE BankingDb;
GO

UPDATE dbo.Account
SET Status = 'OVERDUE'
WHERE DpdDays > 90;
GO

INSERT INTO dbo.AccountAudit (AccountId, NewStatus)
SELECT AccountId, 'OVERDUE'
FROM dbo.Account
WHERE DpdDays > 90;
GO

