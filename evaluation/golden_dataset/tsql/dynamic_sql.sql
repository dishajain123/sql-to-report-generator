CREATE OR ALTER PROCEDURE dbo.ApplyDynamicTableUpdate
  @TableName SYSNAME,
  @AccountId INT
AS
BEGIN
  DECLARE @sql NVARCHAR(MAX);
  SET @sql = N'UPDATE ' + QUOTENAME(@TableName) + N' SET flagged = 1 WHERE account_id = @id';
  EXEC sp_executesql @sql, N'@id INT', @id = @AccountId;
END;

