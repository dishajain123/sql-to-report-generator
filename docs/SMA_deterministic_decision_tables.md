# SMA marking — deterministic decision tables

Generated locally from the bundled SQL using the production decision recovery and renderer, with **no LLM-authored rules**. The snapshot contains 23 recognized decision tables: 12 CASE assignments/rankings, seven scalar fallbacks, two sequential UPDATE mappings, and two row-selection predicate tables. It is not a complete procedure report; see the [source-reviewed reference](SMA_MARKING_12122023_reference.md) for the whole process.

The first six tables populate `#TEMPTABLE`, which is never read by the active procedure. They do not gate account classification. The two `MAXSMA_CLASS` tables map per-row inputs to aggregation, first by customer entity and then by UCIF. Sequential UPDATE tables evaluate every statement in order; CASE/scalar tables use first-match selection. A WHERE predicate includes a row only when TRUE, not when FALSE or NULL. SQL type conversion and error behavior still apply.

## Business Rules

### R1 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_IntService`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0) | DPD_IntService |
| ELSE | 0 |

### R2 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_NoCredit`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0) | DPD_NoCredit |
| ELSE | 0 |

### R3 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_Overdrawn`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn ,0) | DPD_Overdrawn |
| ELSE | 0 |

### R4 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_Overdue`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue ,0) | DPD_Overdue |
| ELSE | 0 |

### R5 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_Renewal`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_Renewal,0)>=isnull(RefPeriodReview ,0) | DPD_Renewal |
| ELSE | 0 |

### R6 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `DPD_StockStmt`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- (COALESCE(DPD_IntService, 0) >= COALESCE(RefPeriodIntService, 0) OR COALESCE(DPD_NoCredit, 0) >= COALESCE(RefPeriodNoCredit, 0) OR COALESCE(DPD_Overdrawn, 0) >= COALESCE(RefPeriodOverDrawn, 0) OR COALESCE(DPD_Overdue, 0) >= COALESCE(RefPeriodOverdue, 0) OR COALESCE(DPD_Renewal, 0) >= COALESCE(RefPeriodReview, 0) OR COALESCE(DPD_StockStmt, 0) >= COALESCE(RefPeriodStkStatement, 0))

**Source context:**

- Target: #TEMPTABLE
- FROM #DPD AS A

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0) | DPD_StockStmt |
| ELSE | 0 |

### R7 — Determine DPD_Max

**Affected Field:** `DPD_Max`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- COALESCE(A.DPD_Overdrawn, 0) > 0 OR COALESCE(A.DPD_Overdue, 0) > 0

**Source context:**

- Target: #DPD
- FROM #DPD AS a

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| (isnull(DPD_IntService,0)>=isnull(DPD_NoCredit,0) AND isnull(DPD_IntService,0)>=isnull(DPD_Overdrawn,0) AND    isnull(DPD_IntService,0)>=isnull(DPD_Overdue,0) AND  isnull(DPD_IntService,0)>=isnull(DPD_Renewal,0) AND isnull(DPD_IntService,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_IntService,0) |
| (isnull(DPD_NoCredit,0)>=isnull(DPD_IntService,0) AND isnull(DPD_NoCredit,0)>=  isnull(DPD_Overdrawn,0) AND    isnull(DPD_NoCredit,0)>=isnull(DPD_Overdue,0) AND    isnull(DPD_NoCredit,0)>=  isnull(DPD_Renewal,0) AND isnull(DPD_NoCredit,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_NoCredit ,0) |
| (isnull(DPD_Overdrawn,0)>=isnull(DPD_NoCredit,0)  AND isnull(DPD_Overdrawn,0)>= isnull(DPD_IntService,0)  AND  isnull(DPD_Overdrawn,0)>=isnull(DPD_Overdue,0) AND   isnull(DPD_Overdrawn,0)>= isnull(DPD_Renewal,0) AND isnull(DPD_Overdrawn,0)>=isnull(DPD_StockStmt,0)) | isnull(DPD_Overdrawn,0) |
| (isnull(DPD_Renewal,0)>=isnull(DPD_NoCredit,0)    AND isnull(DPD_Renewal,0)>=   isnull(DPD_IntService,0)  AND  isnull(DPD_Renewal,0)>=isnull(DPD_Overdrawn,0)  AND  isnull(DPD_Renewal,0)>=   isnull(DPD_Overdue,0)  AND isnull(DPD_Renewal,0) >=isnull(DPD_StockStmt ,0)) | isnull(DPD_Renewal,0) |
| (isnull(DPD_Overdue,0)>=isnull(DPD_NoCredit,0)    AND isnull(DPD_Overdue,0)>=   isnull(DPD_IntService,0)  AND  isnull(DPD_Overdue,0)>=isnull(DPD_Overdrawn,0)  AND  isnull(DPD_Overdue,0)>=   isnull(DPD_Renewal,0)  AND isnull(DPD_Overdue ,0)>=isnull(DPD_StockStmt ,0)) | isnull(DPD_Overdue,0) |
| ELSE | isnull(DPD_StockStmt,0) |

### R8 — Determine SMA_CLASS

**Affected Field:** `SMA_CLASS`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0

**Source context:**

- Target: PRO.ACCOUNTCAL
- FROM PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID INNER JOIN AdvAcBasicDetail AS ABD ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY) INNER JOIN #DPD AS dpd ON dpd.AccountEntityId = a.AccountEntityId

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| DPD_Max  BETWEEN 1 AND 30 | 'SMA_0' |
| DPD_Max  BETWEEN 31 AND 60 | 'SMA_1' |
| DPD_Max  BETWEEN 61 AND 90 | 'SMA_2' |
| DPD_Max >90 | 'SMA_2' |
| ELSE | NULL |

### R9 — Determine SMA_REASON

**Affected Field:** `SMA_REASON`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Applies to:**

- COALESCE(B.FLGPROCESSING, 'N') = 'N' AND COALESCE(FINALASSETCLASSALT_KEY, 1) = 1 AND COALESCE(A.BALANCE, 0) > 0 AND A.ASSET_NORM <> 'ALWYS_STD' AND (COALESCE(dpd.DPD_Overdrawn, 0) >= 0 OR COALESCE(dpd.DPD_Overdue, 0) >= 0) AND COALESCE(DPD.DPD_MAX, 0) > 0

**Source context:**

- Target: PRO.ACCOUNTCAL
- FROM PRO.ACCOUNTCAL AS A INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID INNER JOIN AdvAcBasicDetail AS ABD ON A.AccountEntityID = ABD.AccountEntityId AND (ABD.EffectiveFromTimeKey <= @TIMEKEY AND ABD.EffectiveToTimeKey >= @TIMEKEY) INNER JOIN #DPD AS dpd ON dpd.AccountEntityId = a.AccountEntityId

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_INTSERVICE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY INT NOT SERVICED' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_NOCREDIT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY NO CREDIT' |
| FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD_OVERDUE,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY OVERDUE' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_OVERDRAWN,0)=ISNULL(DPD_MAX,0) and ISNULL(DPD_OVERDRAWN,0)>30 | 'DEGRADE BY CONTI EXCESS' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_STOCKSTMT,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY STOCK STATEMENT' |
| FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD_RENEWAL,0)=ISNULL(DPD_MAX,0) | 'DEGRADE BY REVIEW DUE DATE' |
| ELSE | 'OTHER' |

### R10 — Determine inputs to MAX for MAXSMA_CLASS

**Affected Field:** `MAXSMA_CLASS`

**Summary:**

- The decision rows show per-row inputs to MAX; MAXSMA_CLASS is the aggregate of those inputs over the SQL grouping.

**Source context:**

- Target: #TEMPTABLE_SMACLASS
- FROM PRO.ACCOUNTCAL AS A
- INNER JOIN PRO.CUSTOMERCAL AS B ON A.CustomerEntityID = B.CustomerEntityID AND B.FLGSMA = 'Y'
- GROUP BY A.CustomerEntityID

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |
| ELSE | 0 |

### R11 — Determine inputs to MAX for MAXSMA_CLASS

**Affected Field:** `MAXSMA_CLASS`

**Summary:**

- The decision rows show per-row inputs to MAX; MAXSMA_CLASS is the aggregate of those inputs over the SQL grouping.

**Source context:**

- Target: #TEMPTABLE_SMACLASSUcif
- FROM PRO.ACCOUNTCAL AS A
- INNER JOIN PRO.CUSTOMERCAL AS B ON A.UCIF_ID = B.UCIF_ID AND B.FLGSMA = 'Y'
- GROUP BY A.UCIF_ID

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |
| ELSE | 0 |

### R12 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `SMA_CLASS`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Applies to:**

- B.FLGSMA = 'Y' AND COALESCE(A.BALANCE, 0) > 0 AND COALESCE(B.SYSASSETCLASSALT_KEY, 1) = 1

**Source context:**

- Target: #SMACLASS
- FROM PRO.ACCOUNTCAL AS A
- INNER JOIN PRO.CUSTOMERCAL AS B ON A.REFCUSTOMERID = B.REFCUSTOMERID AND A.CUSTOMERENTITYID = B.CUSTOMERENTITYID AND A.FLGSMA = 'Y'
- Expression: COALESCE(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY, 'SMA_0', 'SMA_1', 'SMA_2'))

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS IS NOT NULL | SMA_CLASS |
| CONVERT(INT, SMA_CLASS_KEY) = 1 | 'SMA_0' |
| CONVERT(INT, SMA_CLASS_KEY) = 2 | 'SMA_1' |
| CONVERT(INT, SMA_CLASS_KEY) = 3 | 'SMA_2' |
| ELSE | NULL |

### R13 — First matching row wins; ELSE includes false or NULL predicates.

**Affected Field:** `SMA_CLASS`

**Summary:**

- First matching row wins; ELSE includes false or NULL predicates.

**Source context:**

- Target: #SMACLASS

**Evaluation order:**

- First matching row wins; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| SMA_CLASS='SMA_0' | 1 |
| SMA_CLASS='SMA_1' | 2 |
| SMA_CLASS='SMA_2' | 3 |
| ELSE | SMA_CLASS |

### R14 — Determine CustMoveDescription

**Affected Field:** `CustMoveDescription`

**Summary:**

- Each row is a separate UPDATE executed in source order. Conditions use current values; later matching updates can overwrite earlier values. No matching update leaves the existing value unchanged.

**Source context:**

- Target: PRO.CUSTOMERCAL

**Evaluation order:**

- Each row is a separate UPDATE executed in source order. Conditions use current values; later matching updates can overwrite earlier values. No matching update leaves the existing value unchanged.

### Decision Logic

| Condition | Result |
|---|---|
| SYSASSETCLASSALT_KEY = 1 | 'STD' |
| SYSASSETCLASSALT_KEY = 2 | 'SUB' |
| SYSASSETCLASSALT_KEY = 3 | 'DB1' |
| SYSASSETCLASSALT_KEY = 4 | 'DB2' |
| SYSASSETCLASSALT_KEY = 5 | 'DB3' |
| SYSASSETCLASSALT_KEY = 6 | 'LOS' |
| SMA_CLASS_KEY = 1 | 'SMA_0' |
| SMA_CLASS_KEY = 2 | 'SMA_1' |
| SMA_CLASS_KEY = 3 | 'SMA_2' |

### R15 — Determine SMA_CLASS

**Affected Field:** `SMA_CLASS`

**Summary:**

- Each row is a separate UPDATE executed in source order. Conditions use current values; later matching updates can overwrite earlier values. No matching update leaves the existing value unchanged.

**Source context:**

- Target: PRO.AccountCal

**Evaluation order:**

- Each row is a separate UPDATE executed in source order. Conditions use current values; later matching updates can overwrite earlier values. No matching update leaves the existing value unchanged.

### Decision Logic

| Condition | Result |
|---|---|
| FinalAssetClassAlt_Key = 1 AND SMA_CLASS IS NULL | 'STD' |
| FinalAssetClassAlt_Key = 2 AND SMA_CLASS IS NULL | 'SUB' |
| FinalAssetClassAlt_Key = 3 AND SMA_CLASS IS NULL | 'DB1' |
| FinalAssetClassAlt_Key = 4 AND SMA_CLASS IS NULL | 'DB2' |
| FinalAssetClassAlt_Key = 5 AND SMA_CLASS IS NULL | 'DB3' |
| FinalAssetClassAlt_Key = 6 AND SMA_CLASS IS NULL | 'LOS' |

### R16 — Determine TotOsAcc

**Affected Field:** `TotOsAcc`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: #ACCOUNT_MOVEMENT_HISTORY
- FROM PRO.ACCOUNTCAL
- Expression: COALESCE(Balance, 0)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| Balance IS NOT NULL | Balance |
| ELSE | 0 |

### R17 — Determine Row selection predicate

**Decision output:** `Row selection predicate`

**Summary:**

- First matching row selects this CASE value in the WHERE predicate. The resulting predicate includes the row only when TRUE; FALSE or NULL excludes it. Other predicate terms still apply.

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.ACCOUNT_MOVEMENT_HISTORY
- FROM #ACCOUNT_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY AS B ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999

**Evaluation order:**

- First matching row selects this CASE value in the WHERE predicate. The resulting predicate includes the row only when TRUE; FALSE or NULL excludes it. Other predicate terms still apply.

### Decision Logic

| Condition | Result |
|---|---|
| CustomerAcID IS NULL | (1) = 1 |
| NOT CustomerAcID IS NULL AND MOVEMENTFROMSTATUS <> MOVEMENTTOSTATUS | (1) = 1 |
| ELSE | (NULL) = 1 |

### R18 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `MovementFromStatus`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Applies to:**

- (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.ACCOUNT_MOVEMENT_HISTORY
- FROM #ACCOUNT_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY AS B ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999
- Expression: COALESCE(B.MovementTOStatus, A.MovementFromStatus)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| MovementTOStatus IS NOT NULL | MovementTOStatus |
| ELSE | MovementFromStatus |

### R19 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `TotOsAcc`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Applies to:**

- (CASE WHEN B.CustomerAcID IS NULL THEN 1 WHEN NOT B.CustomerAcID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.ACCOUNT_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.ACCOUNT_MOVEMENT_HISTORY
- FROM #ACCOUNT_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY AS B ON A.CustomerAcID = B.CustomerAcID AND B.EFFECTIVETOTimekey = 49999
- Expression: COALESCE(A.TotOsAcc, 0)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| TotOsAcc IS NOT NULL | TotOsAcc |
| ELSE | 0 |

### R20 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `totOsCust`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: #Customer_MOVEMENT_HISTORY
- FROM PRO.CustomerCal
- Expression: COALESCE(TotOsCust, 0)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| TotOsCust IS NOT NULL | TotOsCust |
| ELSE | 0 |

### R21 — Determine Row selection predicate

**Decision output:** `Row selection predicate`

**Summary:**

- First matching row selects this CASE value in the WHERE predicate. The resulting predicate includes the row only when TRUE; FALSE or NULL excludes it. Other predicate terms still apply.

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.CUSTOMER_MOVEMENT_HISTORY
- FROM #Customer_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY AS B ON A.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey = 49999

**Evaluation order:**

- First matching row selects this CASE value in the WHERE predicate. The resulting predicate includes the row only when TRUE; FALSE or NULL excludes it. Other predicate terms still apply.

### Decision Logic

| Condition | Result |
|---|---|
| SourceSystemCustomerID IS NULL | (1) = 1 |
| NOT SourceSystemCustomerID IS NULL AND MOVEMENTFROMSTATUS <> MOVEMENTTOSTATUS | (1) = 1 |
| ELSE | (NULL) = 1 |

### R22 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `MovementFromStatus`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Applies to:**

- (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.CUSTOMER_MOVEMENT_HISTORY
- FROM #Customer_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY AS B ON A.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey = 49999
- Expression: COALESCE(B.MovementTOStatus, A.MovementFromStatus)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| MovementTOStatus IS NOT NULL | MovementTOStatus |
| ELSE | MovementFromStatus |

### R23 — First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Affected Field:** `TotOsCust`

**Summary:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

**Applies to:**

- (CASE WHEN B.SourceSystemCustomerID IS NULL THEN 1 WHEN NOT B.SourceSystemCustomerID IS NULL AND A.MOVEMENTFROMSTATUS <> B.MOVEMENTTOSTATUS THEN 1 END) = 1

**Source context:**

- ELSE of IF EXISTS ( select 1 from PRO.CUSTOMER_MOVEMENT_HISTORY where [EffectiveFromTimeKey]= @Timekey) (false or NULL)
- Target: PRO.CUSTOMER_MOVEMENT_HISTORY
- FROM #Customer_MOVEMENT_HISTORY AS A
- LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY AS B ON A.SourceSystemCustomerID = B.SourceSystemCustomerID AND B.EFFECTIVETOTimekey = 49999
- Expression: COALESCE(A.TotOsCust, 0)

**Evaluation order:**

- First matching row wins. SQL type conversion still applies; ELSE includes false or NULL predicates.

### Decision Logic

| Condition | Result |
|---|---|
| TotOsCust IS NOT NULL | TotOsCust |
| ELSE | 0 |

