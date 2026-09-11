# SMA marking — source-reviewed reference

Reference input: `samples/PRO.SMA_MARKING_12122023.StoredProcedure.sql` (718 lines).
This is a manually reviewed specification of executable SQL, not a regenerated model report. Line numbers refer to that bundled file. It describes implemented behavior, without asserting regulatory compliance or expanding identifiers whose definitions are absent from the SQL.

## Purpose and sequence

For the supplied `@TIMEKEY`, reset and classify eligible accounts using their overdue/overdrawn day counters, propagate account classifications to customers, record changes in classification, and maintain account/customer movement history. Later account updates also put asset-class status labels into `SMA_CLASS`, so its final contents are not limited to SMA labels.

1. Resolve processing dates and prepare the working DPD data.
2. Reset account SMA fields, then classify eligible accounts.
3. Reset customer SMA fields; propagate classifications first by customer entity and then by UCIF.
4. Rebuild the current-timekey SMA movement records and replace the previous-status snapshot.
5. Assign customer movement descriptions and fill account asset-class labels.
6. Conditionally maintain account and customer movement histories.
7. Record process success; on a caught error, attempt temporary-table cleanup and record failure.

## Dates and working DPD values

- `@ProcessDate` comes from `SYSDAYMATRIX.DATE` where `TIMEKEY=@TIMEKEY` (line 18).
- `@vEffectiveto` comes from `dbo.Automate_Advances.Timekey - 1` where `EXT_FLG='Y'` (line 19). It is not calculated from the input timekey.
- Include an account in `#DPD` only when `ISNULL(DPD_Overdrawn,0)>30 OR ISNULL(DPD_Overdue,0)>0` (lines 35–48).
- Copy `DPD_Overdrawn` and `DPD_Overdue` from the account. Initialize `DPD_IntService`, `DPD_NoCredit`, `DPD_Renewal`, `DPD_StockStmt` and `DPD_MAX` to zero. The date-difference calculations at lines 54–60 are comments and do not run.
- Set each of the six DPD counters to zero where its value is negative (lines 66–71). The predicate uses `ISNULL(value,0)<0`; this does not convert a NULL counter to zero in storage.
- Populate `#TEMPTABLE` with each DPD value when its null-normalized value is at least its corresponding null-normalized reference period; otherwise use zero. Include a row when any of those comparisons passes (lines 80–96). This is threshold gating, not the maximum of DPD and reference period. **No executable statement reads this table**, so it does not control the subsequent maximum or classification.
- Reset `#DPD.DPD_Max=0`, then compute the maximum of the six null-normalized DPD counters for rows with positive overdrawn or overdue days (lines 102–117). The maximum reads `#DPD`, not `#TEMPTABLE`.
- The ordered maximum CASE chooses interest-service, no-credit, overdrawn, renewal, overdue, then stock-statement as its fallback. Equal maxima produce the same numeric result. Under the active initialization, only overdrawn and overdue counters can contribute positive values.

## Account classification

Reset `SMA_CLASS`, `SMA_REASON`, `SMA_DT`, and `FLGSMA` to NULL on all rows of `PRO.ACCOUNTCAL` (lines 120–124).

The update at lines 128–162 then requires all of the following:

- Matching customer by `CustomerEntityID`.
- Matching `AdvAcBasicDetail` by `AccountEntityID`, effective inclusively at `@TIMEKEY`.
- Matching working DPD row by `AccountEntityID`.
- `ISNULL(customer.FLGPROCESSING,'N')='N'`.
- `ISNULL(FINALASSETCLASSALT_KEY,1)=1`.
- `ISNULL(account.BALANCE,0)>0`.
- `account.ASSET_NORM<>'ALWYS_STD'`. A NULL asset norm does not pass this SQL comparison.
- `ISNULL(dpd.DPD_Overdrawn,0)>=0 OR ISNULL(dpd.DPD_Overdue,0)>=0`.
- `ISNULL(dpd.DPD_MAX,0)>0`.

| Ordered condition | Assigned `SMA_CLASS` |
|---|---|
| DPD_Max between 1 and 30 inclusive | `SMA_0` |
| DPD_Max between 31 and 60 inclusive | `SMA_1` |
| DPD_Max between 61 and 90 inclusive | `SMA_2` |
| DPD_Max greater than 90 | `SMA_2` |
| Otherwise | NULL (unreachable for positive integral DPD values satisfying the update) |

Reason is chosen by the **first matching** row below. Every equality uses `ISNULL(counter,0)=ISNULL(DPD_MAX,0)`.

| Priority | Facility | Additional condition | Assigned `SMA_REASON` |
|---|---|---|---|
| 1 | CC, OD | Interest-service DPD equals maximum | `DEGRADE BY INT NOT SERVICED` |
| 2 | CC, OD | No-credit DPD equals maximum | `DEGRADE BY NO CREDIT` |
| 3 | TL, DL, BP, BD, PC | Overdue DPD equals maximum | `DEGRADE BY OVERDUE` |
| 4 | CC, OD | Overdrawn DPD equals maximum and is greater than 30 | `DEGRADE BY CONTI EXCESS` |
| 5 | CC, OD | Stock-statement DPD equals maximum | `DEGRADE BY STOCK STATEMENT` |
| 6 | CC, OD | Renewal DPD equals maximum | `DEGRADE BY REVIEW DUE DATE` |
| Fallback | Any | No prior row matches | `OTHER` |

The source contains all six reason branches, although the four counters initialized to zero cannot equal a positive DPD maximum in this procedure's active path.

Set `SMA_DT=DATEADD(DAY,-dpd.DPD_MAX+1,@ProcessDate)` and `FLGSMA='Y'`. For example, DPD 1 yields the process date; DPD 31 yields the process date minus 30 days. Account rows excluded from this update retain the reset NULL values at this stage.

The alternate threshold ladders and continuous-excess reset at lines 166–264 are disabled comments. They must not appear as active business rules.

## Customer propagation

Reset customer `FLGSMA`, `SMA_CLASS_KEY`, and `SMA_DT` to NULL (lines 271–274).

First, set a customer's flag to Y when a matching account by `CustomerEntityID` has `FLGSMA='Y'`. For flagged customers, group joined account rows by customer entity, compute `MAX(CASE SMA_CLASS: SMA_0→1, SMA_1→2, SMA_2→3, otherwise→0)` and `MIN(account.SMA_DT)`, and write the results to the customer (lines 276–296).

Repeat the flag propagation and aggregation by `UCIF_ID`, updating `SMA_CLASS_KEY` and `SMA_DT` again (lines 300–320). This later update can overwrite the entity-level result. The aggregate joins restrict the customer flag; they do not independently filter account rows to `account.FLGSMA='Y'`. The minimum date is over the joined group, not only the accounts holding the maximum rank.

## SMA movement and previous snapshot

Delete existing `PRO.SMA_MOVEMENT_HISTORY` rows for `@TIMEKEY` if any exist (lines 324–327).

Build `#SMACLASS` from accounts joined to customers on both `REFCUSTOMERID` and `CUSTOMERENTITYID`, requiring both SMA flags to be Y, positive account balance, and `ISNULL(customer.SYSASSETCLASSALT_KEY,1)=1`. Use the account SMA label when non-NULL, otherwise `CHOOSE(customer.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2')`. Map those labels to 1, 2, 3, preserving other values (lines 333–340).

Right-join previous status to the current working set by `CustomerAcID`. Insert `@TIMEKEY`, account ID, previous status and current status when the current status is non-NULL and the null-normalized old and new statuses differ (lines 342–346). Because this is driven by the current working set, accounts that disappear from it are not recorded here as an exit movement.

Truncate `PRO.PREVSMASTATUS` and replace it with the current `@TIMEKEY`, account ID and status from `#SMACLASS` (lines 348–352). This is a whole-table replacement, not an append.

## Status labels before movement history

For customer `CustMoveDescription`, map `SYSASSETCLASSALT_KEY` 1–6 to `STD`, `SUB`, `DB1`, `DB2`, `DB3`, `LOS`. Then overwrite with `SMA_0`, `SMA_1`, `SMA_2` where customer `SMA_CLASS_KEY` is 1, 2, 3 respectively (lines 360–368). Values outside these conditions retain their existing description; the procedure does not first clear that column.

For account `SMA_CLASS`, map `FinalAssetClassAlt_Key` 1–6 to the same six asset-class labels, **only where `SMA_CLASS IS NULL`** (lines 370–375). Existing SMA labels survive. Other fields such as `FLGSMA` are not changed by these label updates.

## Account and customer movement histories

Account processing (lines 407–545) is skipped in its entirety when any account-history row already has `EffectiveFromTimeKey=@TIMEKEY`; customer processing has an independent equivalent guard (lines 547–689). These are table-wide existence checks, not per-account/per-customer checks.

Otherwise, each path:

1. Stages all current account/customer calendar rows, including their source `EffectiveFromTimeKey` (not a replacement with `@TIMEKEY`), their identifiers and asset-class/date values. Sets `EffectiveToTimeKey=49999`, movement start date to `@ProcessDate`, movement end date to literal `2086-11-21`, and both initial movement statuses to the current label. Null balances/outstandings become zero.
2. Left-joins staged rows to open history (`EffectiveToTimeKey=49999`), using `CustomerAcID` for accounts and `SourceSystemCustomerID` for customers. Inserts a row when there is no matching prior identifier, or when the staged status differs from the existing movement-to status. The inserted movement-from status uses the prior movement-to status if non-NULL; otherwise the staged status. SQL NULL comparison semantics still apply.
3. Closes open history rows absent from the staged set. Sets `EffectiveToTimeKey=@vEffectiveto` and `MovementToDate=DATEADD(DD,-1,@ProcessDate)`.
4. Closes open history rows with `EffectiveFromTimeKey<@TIMEKEY` when a matching staged row has a different movement-to status, using the same closing timekey and date.

The missing-row customer closure tests the **joined staged identifier** `B.SourceSystemCustomerID IS NULL`, not whether the stored history identifier itself is NULL. The changed-row comparison compares old movement-to with new movement-to, not movement-from with movement-to on a single record.

## Completion and error handling

On the normal path, update `PRO.ACLRUNNINGPROCESSSTATUS` for `RUNNINGPROCESSNAME='SMA_MARKING'`: set `COMPLETED='Y'`, clear error date/description, and increment `COUNT` with `ISNULL(COUNT,0)+1` (lines 693–695).

A `BEGIN TRY / BEGIN CATCH` handler exists. The catch first drops four temporary tables, without existence guards, then attempts to set `COMPLETED='N'`, `ERRORDATE=GETDATE()`, `ERRORDESCRIPTION=ERROR_MESSAGE()`, and increment the count for the same process (lines 702–714). A drop can itself fail if the table was never created, preventing the later failure-status update. The source contains no explicit transaction, rollback, or rethrow. Ordinary history-existence checks are not exception handling.

## Review observations about the SQL itself

- The reference-period staging table has no downstream reader. Do not describe its thresholds as effective classification gates.
- Several reason branches are present but cannot be selected with the counters this active procedure initializes to zero.
- The procedure retains `SMA_2` above DPD 90; it does not itself perform an NPA conversion in that CASE.
- UCIF aggregation overrides earlier entity aggregation.
- SMA movement rebuilding and account/customer movement handling use different rerun strategies.
- Movement history uses calendar-row effective-from keys; the SQL does not replace them with the input key, despite using the input key in its rerun guards.
- Unprotected catch cleanup can interrupt failure recording. No transaction in this source makes the complete sequence atomic.
