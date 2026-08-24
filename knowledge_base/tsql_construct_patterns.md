# T-SQL (SQL Server) Construct Semantics

Reference patterns for interpreting Microsoft SQL Server T-SQL objects
(stored procedures, functions, views, triggers) during technical
extraction. Mirrors the Oracle PL/SQL pattern reference so the same
extraction quality applies regardless of dialect.

## Batches and the GO separator

`GO` is a batch separator recognized by client tools (sqlcmd, SSMS), not
a T-SQL keyword itself. A single `.sql` file may contain multiple
batches (e.g. a `USE` statement, then `GO`, then the object definition).
Each batch executes independently; variables and temp tables do not
persist across a `GO` boundary. When reverse-engineering, treat the
batch containing the `CREATE`/`ALTER PROCEDURE|FUNCTION|VIEW|TRIGGER`
statement as the primary object; other batches (e.g. `USE`, permission
grants) provide supporting context but are not part of the object's own
logic.

## Procedures and functions

`CREATE PROCEDURE` / `CREATE OR ALTER PROCEDURE` define stored
procedures; `ALTER PROCEDURE` modifies an existing one. Parameters are
declared with a leading `@`, e.g. `@AccountId INT`, and may be marked
`OUTPUT` to return a value to the caller. Scalar functions
(`CREATE FUNCTION ... RETURNS INT`) and table-valued functions
(`RETURNS TABLE` / `RETURNS @ReturnTable TABLE (...)`) both exist;
table-valued functions effectively behave like parameterized views.

## Exception handling: TRY/CATCH

T-SQL uses `BEGIN TRY ... END TRY BEGIN CATCH ... END CATCH` instead of
Oracle's `EXCEPTION WHEN ...` block. Inside a `CATCH` block,
`ERROR_MESSAGE()`, `ERROR_NUMBER()`, and `ERROR_SEVERITY()` retrieve
details of the error that was caught; `THROW` (or, in older code,
`RAISERROR`) re-raises or raises a custom error. `ROLLBACK TRANSACTION`
inside a `CATCH` block undoes any writes made earlier in the batch -
functionally equivalent to Oracle's `ROLLBACK` in a `WHEN OTHERS`
handler.

## Variables, control flow, and system functions

Local variables are declared with `DECLARE @name TYPE` and assigned with
`SET @name = ...` or `SELECT @name = column FROM ...`. Control flow uses
`IF ... ELSE`, `WHILE`, and cursors (`DECLARE CURSOR FOR ... OPEN ...
FETCH NEXT ... CLOSE ... DEALLOCATE`) similarly to PL/SQL's cursor
pattern. `@@ROWCOUNT` returns the number of rows affected by the most
recent statement (commonly used to detect "no rows matched" conditions
after an `UPDATE`/`DELETE`); `@@ERROR` and `@@IDENTITY` are similar
system variables for error state and the last identity value inserted.

## Data-modification patterns

`MERGE` behaves the same conceptually as Oracle `MERGE` (`WHEN MATCHED`
/ `WHEN NOT MATCHED`). The `OUTPUT` clause on `INSERT`/`UPDATE`/`DELETE`
returns the affected rows' before/after values directly from the DML
statement, often used to capture what changed without a separate
`SELECT`. Table variables (`DECLARE @t TABLE (...)`) and temp tables
(`#LocalTemp` / `##GlobalTemp`) are both used as intermediate staging
areas within a batch - functionally similar to Oracle collections/global
temporary tables, but scoped differently (a temp table persists for the
connection/session, a table variable typically for the batch/procedure).

## Dynamic SQL

Dynamic SQL is built as a string and executed via `EXEC(@sql)` or the
more parameterized `sp_executesql @sql, @params, ...`. As with Oracle's
`EXECUTE IMMEDIATE`, the true executed statement text is often only
known at runtime (string concatenation of table/column names, filter
values, etc.) and cannot be statically resolved with certainty - this
should always be flagged as an ambiguity rather than guessed at.

## Common banking-domain patterns in T-SQL objects

- NPA/overdue classification logic commonly reads `DATEDIFF(DAY,
  DueDate, GETDATE())` (or similar date-arithmetic expressions) to
  compute an overdue-days figure, then branches on RBI IRAC-style
  thresholds (e.g. 90 days) to set an asset-classification column.
- Provisioning calculations commonly multiply an outstanding-balance
  column by a percentage determined by the asset classification,
  frequently implemented via a `CASE WHEN` expression or a lookup join
  against a rates/thresholds reference table.
- Batch/end-of-day procedures commonly cursor or set-based `UPDATE`
  across all active accounts, applying the same classification logic
  per row (or per set), and log failures via `INSERT` into an
  exceptions/audit table inside the `CATCH` block rather than letting
  the whole batch fail silently.