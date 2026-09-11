USE [RBL_MISDB]
GO
/****** Object:  StoredProcedure [PRO].[SMA_MARKING]    Script Date: 5/19/2026 5:56:29 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [PRO].[SMA_MARKING]
@TIMEKEY INT
WITH RECOMPILE
AS
BEGIN
	SET NOCOUNT ON
	BEGIN TRY

DECLARE @ProcessDate DATE=(SELECT DATE FROM SYSDAYMATRIX WHERE TIMEKEY=@TIMEKEY)
Declare @vEffectiveto INT Set @vEffectiveto= (select Timekey-1  FROM [dbo].Automate_Advances WHERE EXT_FLG='Y')


--------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-----------------

IF OBJECT_ID('TEMPDB..#DPD_Aqua_SMA') IS NOT NULL
  DROP TABLE  #DPD_Aqua_SMA

SELECT				A.CustomerAcID, A.AccountEntityID, A.DPD_Overdrawn, ContiExcessDt, DPD_Renewal, ReviewDueDt
into					#DPD_Aqua_SMA
FROM					##ACCOUNTCAL A
INNER JOIN			DIMPRODUCT C
ON						A.ProductAlt_Key =C.ProductAlt_Key
WHERE					C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY
AND						(ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD'))
AND						ISNULL(A.REFPERIODOVERDRAWN,91)=91 AND ISNULL(A.FinalAssetClassAlt_Key,1)=1

Update					A
SET						A.ContiExcessDt=NULL, A.DPD_Overdrawn=0
FROM					##ACCOUNTCAL A
INNER JOIN			#DPD_Aqua_SMA B
ON						A.AccountEntityID=B.AccountEntityID
WHERE					ISNULL(A.DPD_Overdrawn,0)<=30
--INNER JOIN			DIMPRODUCT C
--ON						A.ProductAlt_Key =C.ProductAlt_Key
--WHERE					C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY
--AND						(ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD'))
--AND						ISNULL(A.DPD_Overdrawn,0)<=30 AND ISNULL(A.REFPERIODOVERDRAWN,91)=91 AND ISNULL(A.FinalAssetClassAlt_Key,1)=1

Update					A
SET						A.ReviewDueDt=NULL, A.DPD_Renewal=0
FROM					##ACCOUNTCAL A
INNER JOIN			#DPD_Aqua_SMA B
ON						A.AccountEntityID=B.AccountEntityID
--INNER JOIN			DIMPRODUCT C
--ON						A.ProductAlt_Key =C.ProductAlt_Key
--WHERE					C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY
--AND						(ISNULL(C.Aqua_Scheme,'N')='Y' AND ISNULL(C.SchemeType,'')='ODA' and isnull(c.FacilityType,'') in ('CC','OD'))
--AND						ISNULL(A.REFPERIODOVERDRAWN,91)=91 AND ISNULL(A.FinalAssetClassAlt_Key,1)=1

--------------END------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-----------------


--IF OBJECT_ID('TEMPDB..#DpdToday') IS NOT NULL
--      DROP TABLE #DpdToday

--select AccountEntityId,DPD_Overdrawn,DPD_Overdue,sum(DPD_Overdrawn+DPD_Overdue) as DPD_Max
--INTO #DpdToday
--FROM PRO.ACCOUNTCAL A
--where  ( isnull(DPD_Overdrawn,0)>0   OR isnull(DPD_Overdue,0)>0 )
--group by AccountEntityId,DPD_Overdrawn,DPD_Overdue


IF OBJECT_ID('TEMPDB..#DPD') IS NOT NULL
  DROP TABLE  #DPD

select AccountEntityID,UcifEntityID,CustomerEntityID,CustomerAcID,
RefCustomerID,SourceSystemCustomerID,UCIF_ID,IntNotServicedDt,LastCrDate,ContiExcessDt,OverDueSinceDt,ReviewDueDt,StockStDt,
RefPeriodIntService,RefPeriodNoCredit,RefPeriodOverDrawn,RefPeriodOverdue,RefPeriodReview,RefPeriodStkStatement,

0 AS DPD_IntService,
0 AS DPD_NoCredit,
DPD_Overdrawn,
DPD_Overdue,
0 AS DPD_Renewal,
0 AS DPD_StockStmt,
0 AS DPD_MAX
  INTO #DPD
  from  ##AccountCal  a
WHERE  isnull(A.DPD_Overdrawn,0)>30   OR  Isnull(A.DPD_Overdue,0)>0



------/*----------CALCULATED ALL DPD--------------------------------------------------------------------------------*/

--UPDATE A SET  A.DPD_IntService = (CASE WHEN  A.IntNotServicedDt IS NOT NULL  THEN DATEDIFF(DAY,A.IntNotServicedDt,'2020-12-31')  ELSE 0 END)
--                     ,A.DPD_NoCredit =  (CASE WHEN  A.LastCrDate IS NOT NULL         THEN DATEDIFF(DAY,A.LastCrDate,   '2020-12-31')        ELSE 0 END)
--       ,A.DPD_Overdrawn=  (CASE WHEN    A.ContiExcessDt IS NOT NULL       THEN DATEDIFF(DAY,A.ContiExcessDt,   '2020-12-31') + 1     ELSE 0 END)
--       ,A.DPD_Overdue =   (CASE WHEN  A.OverDueSinceDt IS NOT NULL     THEN   DATEDIFF(DAY,A.OverDueSinceDt,   '2020-12-31')   ELSE 0 END)
--       ,A.DPD_Renewal =   (CASE WHEN  A.ReviewDueDt IS NOT NULL           THEN DATEDIFF(DAY,A.ReviewDueDt, '2020-12-31')         ELSE 0 END)
--       ,A.DPD_StockStmt=  (CASE WHEN  A.StockStDt IS NOT NULL                 THEN   DATEDIFF(DAY,A.StockStDt,'2020-12-31')           ELSE 0 END)
--FROM #DPD A



----/*------------------IF ANY DPD IS NEGATIVE THEN ZERO---------------------------------------------------------*/

  UPDATE #DPD SET DPD_IntService=0 WHERE isnull(DPD_IntService,0)<0
  UPDATE #DPD SET DPD_NoCredit=0 WHERE isnull(DPD_NoCredit,0)<0
  UPDATE #DPD SET DPD_Overdrawn=0 WHERE isnull(DPD_Overdrawn,0)<0
  UPDATE #DPD SET DPD_Overdue=0 WHERE isnull(DPD_Overdue,0)<0
  UPDATE #DPD SET DPD_Renewal=0 WHERE isnull(DPD_Renewal,0)<0
  UPDATE #DPD SET DPD_StockStmt=0 WHERE isnull(DPD_StockStmt,0)<0



----/* CALCULATE MAX DPD */

    IF OBJECT_ID('TEMPDB..#TEMPTABLE') IS NOT NULL
          DROP TABLE #TEMPTABLE

    SELECT A.CustomerAcID
      ,CASE WHEN  isnull(A.DPD_IntService,0)>=isnull(A.RefPeriodIntService,0)    THEN A.DPD_IntService    ELSE 0      END DPD_IntService,
        CASE WHEN  isnull(A.DPD_NoCredit,0)>=isnull(A.RefPeriodNoCredit,0)      THEN A.DPD_NoCredit        ELSE 0      END DPD_NoCredit,
        CASE WHEN  isnull(A.DPD_Overdrawn,0)>=isnull(A.RefPeriodOverDrawn ,0)          THEN A.DPD_Overdrawn      ELSE 0      END DPD_Overdrawn,
        CASE WHEN  isnull(A.DPD_Overdue,0)>=isnull(A.RefPeriodOverdue ,0)            THEN A.DPD_Overdue          ELSE 0      END DPD_Overdue  ,
        CASE WHEN  isnull(A.DPD_Renewal,0)>=isnull(A.RefPeriodReview ,0)      THEN A.DPD_Renewal          ELSE 0      END  DPD_Renewal  ,
        CASE WHEN  isnull(A.DPD_StockStmt,0)>=isnull(A.RefPeriodStkStatement,0)              THEN A.DPD_StockStmt      ELSE 0      END DPD_StockStmt
        INTO #TEMPTABLE
    FROM #DPD A
        WHERE (
                          isnull(DPD_IntService,0)>=isnull(RefPeriodIntService,0)
                                      OR isnull(DPD_NoCredit,0)>=isnull(RefPeriodNoCredit,0)
              OR isnull(DPD_Overdrawn,0)>=isnull(RefPeriodOverDrawn,0)
              OR isnull(DPD_Overdue,0)>=isnull(RefPeriodOverdue,0)
              OR isnull(DPD_Renewal,0)>=isnull(RefPeriodReview,0)
                                      OR isnull(DPD_StockStmt,0)>=isnull(RefPeriodStkStatement,0)
                  )



----  /*----------------INTIAL MAX DPD 0 FOR RE PROCESSING DATA---------------------------------------------*/

    UPDATE A SET A.DPD_Max=0
      FROM #DPD A



----    /*--------------------------------FIND MAX DPD-------------------------------------------------------*/

    UPDATE     A SET A.DPD_Max=  (CASE        WHEN (isnull(A.DPD_IntService,0)>=isnull(A.DPD_NoCredit,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdrawn,0) AND        isnull(A.DPD_IntService,0)>=isnull(A.DPD_Overdue,0) AND    isnull(A.DPD_IntService,0)>=isnull(A.DPD_Renewal,0) AND isnull(A.DPD_IntService,0)>=isnull(A.DPD_StockStmt,0)) THEN isnull(A.DPD_IntService,0)
                        WHEN (isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_IntService,0) AND isnull(A.DPD_NoCredit,0)>=    isnull(A.DPD_Overdrawn,0) AND        isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_Overdue,0) AND        isnull(A.DPD_NoCredit,0)>=    isnull(A.DPD_Renewal,0) AND isnull(A.DPD_NoCredit,0)>=isnull(A.DPD_StockStmt,0)) THEN    isnull(A.DPD_NoCredit ,0)
                        WHEN (isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_NoCredit,0)  AND isnull(A.DPD_Overdrawn,0)>=  isnull(A.DPD_IntService,0)  AND    isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_Overdue,0) AND      isnull(A.DPD_Overdrawn,0)>=  isnull(A.DPD_Renewal,0) AND isnull(A.DPD_Overdrawn,0)>=isnull(A.DPD_StockStmt,0)) THEN  isnull(A.DPD_Overdrawn,0)
                        WHEN (isnull(A.DPD_Renewal,0)>=isnull(A.DPD_NoCredit,0)        AND isnull(A.DPD_Renewal,0)>=      isnull(A.DPD_IntService,0)  AND    isnull(A.DPD_Renewal,0)>=isnull(A.DPD_Overdrawn,0)  AND    isnull(A.DPD_Renewal,0)>=      isnull(A.DPD_Overdue,0)  AND isnull(A.DPD_Renewal,0)  >= isnull(A.DPD_StockStmt  ,0)) THEN isnull(A.DPD_Renewal,0)
                        WHEN (isnull(A.DPD_Overdue,0)>=isnull(A.DPD_NoCredit,0)        AND isnull(A.DPD_Overdue,0)>=      isnull(A.DPD_IntService,0)  AND    isnull(A.DPD_Overdue,0)>=isnull(A.DPD_Overdrawn,0)  AND    isnull(A.DPD_Overdue,0)>=      isnull(A.DPD_Renewal,0)  AND isnull(A.DPD_Overdue  ,0)>=isnull(A.DPD_StockStmt  ,0))  THEN    isnull(A.DPD_Overdue,0)
                        ELSE isnull(A.DPD_StockStmt,0) END)

    FROM  #DPD a
    WHERE  isnull(A.DPD_Overdrawn,0)>0   OR  Isnull(A.DPD_Overdue,0)>0


  UPDATE A SET A.SMA_CLASS=NULL
                        ,A.SMA_REASON=NULL
            ,A.SMA_DT=NULL
            ,A.FLGSMA=NULL
  FROM ##AccountCal A



UPDATE A SET A.SMA_CLASS=
      (CASE   WHEN dpd.DPD_Max   BETWEEN 1 AND 30   THEN 'SMA_0'
              WHEN dpd.DPD_Max   BETWEEN 31 AND 60   THEN 'SMA_1'
        WHEN dpd.DPD_Max   BETWEEN 61 AND 90   THEN 'SMA_2'
        WHEN dpd.DPD_Max > 90 THEN 'SMA_2'
        ELSE NULL
        END)
, A.SMA_REASON= (CASE
            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'
            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'
            WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'
            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30 THEN 'DEGRADE BY CONTI EXCESS'
            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'
            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'

            ELSE 'OTHER'
          END)
, A.SMA_DT=      DATEADD(DAY,  -dpd.DPD_MAX+1  ,@ProcessDate)
, A.FLGSMA='Y'
FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID
INNER JOIN AdvAcBasicDetail ABD
      ON A.AccountEntityID=ABD.AccountEntityId
      AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)
            --AND ABD.ReferencePeriod=91
  INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId
      --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY
      --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'
      --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')
      --and c.NPANorms='DPD91'
      --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)
WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1
  AND ISNULL(A.BALANCE,0)>0
  and A.ASSET_NORM<>'ALWYS_STD'
AND (  isnull(dpd.DPD_Overdrawn,0)>=0   OR isnull(dpd.DPD_Overdue,0)>=0 )
AND ISNULL(DPD.DPD_MAX,0)>0




------UPDATE A SET A.SMA_CLASS=
------      (CASE   WHEN dpd.DPD_Max   BETWEEN 31 AND 60   THEN 'SMA_0'
------              WHEN dpd.DPD_Max   BETWEEN 61 AND 90   THEN 'SMA_1'
------        WHEN dpd.DPD_Max   BETWEEN 91 AND 180   THEN 'SMA_2'
------        WHEN dpd.DPD_Max > 180 THEN 'SMA_2'
------        ELSE NULL
------        END)
------, A.SMA_REASON= (CASE
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'
------            WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(dpd.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(dpd.DPD_OVERDRAWN,0)=ISNULL(dpd.DPD_MAX,0) and ISNULL(dpd.DPD_OVERDRAWN,0)>30  THEN 'DEGRADE BY CONTI EXCESS'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(dpd.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'

------            ELSE 'OTHER'
------          END)
------, A.SMA_DT=      DATEADD(DAY,  -dpd.DPD_MAX+1  ,@ProcessDate)
------, A.FLGSMA='Y'
------FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID
------INNER JOIN AdvAcBasicDetail ABD
------      ON A.AccountEntityID=ABD.AccountEntityId
------      AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)
------            AND ABD.ReferencePeriod=181
------  INNER JOIN #DPD dpd on dpd.AccountEntityId=a.AccountEntityId
------      --LEFT JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY
------      --AND ISNULL(C.PRODUCTGROUP,'N')<>'KCC'
------      --AND isnull(C.ProductSubGroup,'N') NOT in('KCC')
------      --and c.NPANorms='DPD91'
------      --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)
------WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1
------  AND ISNULL(A.BALANCE,0)>0
------  and A.ASSET_NORM<>'ALWYS_STD'
------AND (  isnull(dpd.DPD_Overdrawn,0)>=0   OR isnull(dpd.DPD_Overdue,0)>=0 )
--------AND ISNULL(DPD.DPD_MAX,0)>0
------AND ISNULL(DPD.DPD_MAX,0)>30




--------UPDATE A SET A.SMA_CLASS=(
--------                                                            CASE WHEN A.FACILITYTYPE IN('CC','OD') THEN (  CASE WHEN    REFPERIODOVERDRAWN-60>=DPD_MAX
--------                                                                                                            THEN 'SMA_0'
--------                                                                                                  WHEN REFPERIODOVERDRAWN-30>=DPD_MAX    THEN 'SMA_1'
--------                                              ELSE 'SMA_2'  END)
--------                                                            ELSE (  CASE WHEN    REFPERIODOVERDUE-60>=DPD_MAX
--------                                                                                                            THEN 'SMA_0'
--------                                                                                                  WHEN REFPERIODOVERDUE-30>=DPD_MAX    THEN 'SMA_1'
--------                                              ELSE 'SMA_2'  END)
--------                  END)

------UPDATE A SET A.SMA_CLASS=
------      (CASE   WHEN dpd.DPD_MAX   BETWEEN 276 AND 305   THEN 'SMA_0'
------              WHEN dpd.DPD_MAX   BETWEEN 306 AND 335   THEN 'SMA_1'
------        WHEN dpd.DPD_MAX   BETWEEN 336 AND 365   THEN 'SMA_2'
------        WHEN dpd.DPD_MAX >=366 THEN 'SMA_2'
------        ELSE NULL
------        END)

------      , A.SMA_REASON= (CASE
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_INTSERVICE,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY INT NOT SERVICED'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_NOCREDIT,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY NO CREDIT'
------            WHEN A.FACILITYTYPE IN ('TL','DL','BP','BD','PC') AND ISNULL(DPD.DPD_OVERDUE,0)=ISNULL(dpd.DPD_MAX,0) THEN  'DEGRADE BY OVERDUE'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_OVERDRAWN,0)=ISNULL(DPD.DPD_MAX,0) AND ISNULL(DPD.DPD_OVERDRAWN,0)>275 THEN 'DEGRADE BY CONTI EXCESS'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_STOCKSTMT,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY STOCK STATEMENT'
------            WHEN A.FACILITYTYPE IN ('CC','OD') AND ISNULL(DPD.DPD_RENEWAL,0)=ISNULL(DPD.DPD_MAX,0) THEN 'DEGRADE BY REVIEW DUE DATE'
------            ELSE 'OTHER'
------          END)
------      , A.SMA_DT=      DATEADD(DAY,  -dpd.DPD_MAX+1  ,@PROCESSDATE)
------      , A.FLGSMA='Y'
------FROM PRO.ACCOUNTCAL A INNER JOIN PRO.CUSTOMERCAL B ON A.CustomerEntityID=B.CustomerEntityID
------INNER JOIN AdvAcBasicDetail ABD
------      ON A.AccountEntityID=ABD.AccountEntityId
------      AND (ABD.EffectiveFromTimeKey<=@TIMEKEY AND ABD.EffectiveToTimeKey>=@TIMEKEY)
------      AND ABD.ReferencePeriod=366
------      INNER JOIN #DPD DPD on dpd.AccountEntityId=a.AccountEntityId
------  --INNER JOIN DIMPRODUCT C ON C.PRODUCTALT_KEY=A.PRODUCTALT_KEY
------  --  --AND ISNULL(C.PRODUCTGROUP,'N')='KCC'
------  --  --AND isnull(C.ProductSubGroup,'N')  in('KCC')
------  --    and C.NPANorms='DPD366'
------  --AND (C.EffectiveFromTimeKey<=@TIMEKEY AND C.EffectiveToTimeKey>=@TIMEKEY)
------WHERE ISNULL(B.FLGPROCESSING,'N')='N' AND ISNULL(FINALASSETCLASSALT_KEY,1)=1
------    AND ISNULL(A.BALANCE,0)>0  and A.ASSET_NORM<>'ALWYS_STD'
------AND (  isnull(DPD.DPD_Overdrawn,0)>=0   OR isnull(DPD.DPD_Overdue,0)>=0 )
--------AND ISNULL(DPD.DPD_MAX,0)>0
------AND ISNULL(DPD.DPD_MAX,0)>275



/*--------Account not to be reported in  SMA 0 for Continuous Excess Date Criteria up to  30 days--------------------  */
----UPDATE A SET A.SMA_Class=NULL
----                      ,A.SMA_Reason=NULL
----          ,A.SMA_Dt=NULL
----          ,A.FlgSMA=NULL
----            FROM PRO.AccountCal a
----WHERE ISNULL(DPD_Max,0)>0
----  --AND  FacilityType in('CC','OD')
----    AND  DPD_Overdrawn=DPD_Max
----    AND DPD_Max<=30 and FlgSMA='Y'



/*------SMA MARKING FOR CUSTOMER LEVEL-------------------------------------*/


  UPDATE A SET A.FLGSMA=NULL
                        ,A.SMA_CLASS_KEY=NULL
            ,A.SMA_DT=NULL
        FROM ##CUSTOMERCAL A

UPDATE A SET A.FLGSMA='Y'
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.CustomerEntityID =B.CustomerEntityID
WHERE B.FLGSMA='Y'


IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASS') IS NOT NULL
      DROP TABLE #TEMPTABLE_SMACLASS

SELECT A.CustomerEntityID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1
                                                          WHEN SMA_CLASS='SMA_1' THEN  2
                WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS
                , MIN(A.SMA_Dt) AS SMA_Dt

INTO #TEMPTABLE_SMACLASS
  FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B
ON A.CustomerEntityID=B.CustomerEntityID AND  B.FLGSMA='Y'
GROUP BY A.CustomerEntityID

UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS, A.SMA_DT=B.SMA_Dt
FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASS B ON A.CustomerEntityID=B.CustomerEntityID
WHERE A.FLGSMA='Y'



UPDATE A SET A.FLGSMA='Y'
FROM ##CUSTOMERCAL A INNER JOIN ##AccountCal B ON A.UCIF_ID =B.UCIF_ID
WHERE B.FLGSMA='Y'


IF OBJECT_ID('TEMPDB..#TEMPTABLE_SMACLASSUcif') IS NOT NULL
      DROP TABLE #TEMPTABLE_SMACLASSUcif

SELECT A.UCIF_ID, MAX(CASE WHEN SMA_CLASS='SMA_0' THEN  1
                                                    WHEN SMA_CLASS='SMA_1' THEN  2
                                                    WHEN SMA_CLASS='SMA_2' THEN  3 ELSE 0 END ) MAXSMA_CLASS
                                    , MIN(A.SMA_Dt) AS SMA_Dt

INTO #TEMPTABLE_SMACLASSUcif
  FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B
ON A.UCIF_ID=B.UCIF_ID AND  B.FLGSMA='Y'
GROUP BY A.UCIF_ID

UPDATE A SET A.SMA_CLASS_KEY=B.MAXSMA_CLASS, A.SMA_DT=B.SMA_Dt
FROM ##CUSTOMERCAL A  INNER JOIN  #TEMPTABLE_SMACLASSUcif B ON A.UCIF_ID=B.UCIF_ID
WHERE A.FLGSMA='Y'



  IF EXISTS(SELECT 1 FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY)
  BEGIN
    DELETE FROM PRO.SMA_MOVEMENT_HISTORY WHERE TIMEKEY=@TIMEKEY
  END


  IF OBJECT_ID('TEMPDB..#SMACLASS') IS NOT NULL
      DROP TABLE #SMACLASS

SELECT A.CustomerAcID, ISNULL(A.SMA_CLASS, CHOOSE(B.SMA_CLASS_KEY,'SMA_0','SMA_1','SMA_2'))  SMA_CLASS INTO #SMACLASS
FROM ##AccountCal A INNER JOIN ##CUSTOMERCAL B ON A.REFCUSTOMERID=B.REFCUSTOMERID
  AND A.CUSTOMERENTITYID=B.CUSTOMERENTITYID AND A.FLGSMA='Y'
WHERE B.FLGSMA='Y' AND  ISNULL(A.BALANCE,0)>0 AND ISNULL(B.SYSASSETCLASSALT_KEY,1)=1

UPDATE #SMACLASS SET SMA_CLASS=(CASE WHEN SMA_CLASS='SMA_0' THEN 1
          WHEN SMA_CLASS='SMA_1' THEN 2
          WHEN SMA_CLASS='SMA_2' THEN 3 ELSE SMA_CLASS END)

INSERT INTO PRO.SMA_MOVEMENT_HISTORY (TIMEKEY,CustomerAcID,PREVSTATUS,CURRENTSTATUS)
SELECT @TIMEKEY, B.CustomerAcID, A.SMA_CLASS, B.SMA_CLASS
FROM PRO.PREVSMASTATUS A  RIGHT OUTER JOIN  #SMACLASS B
ON A.CustomerAcID=B.CustomerAcID
WHERE B.SMA_CLASS IS NOT NULL AND ISNULL(A.SMA_CLASS,'')<>ISNULL(B.SMA_CLASS,'')

TRUNCATE TABLE PRO.PREVSMASTATUS

INSERT INTO PRO.PREVSMASTATUS
SELECT @TIMEKEY, CustomerAcID, SMA_CLASS
FROM #SMACLASS

--INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY)
--SELECT A.CustomerAcID, A.FinalAssetClassAlt_Key, A.FinalNpaDt, @TIMEKEY, 49999
--FROM PRO.AccountCal A  LEFT OUTER JOIN  Pro.ACCOUNT_MOVEMENT_HISTORY B
--ON A.CustomerAcID=B.CustomerAcID
--WHERE  ISNULL(A.FinalAssetClassAlt_Key,'')<>ISNULL(B.FinalAssetClassAlt_Key,'') AND B.EffectiveToTimeKeY=49999

      UPDATE ##CUSTOMERCAL SET CustMoveDescription='STD' WHERE SYSASSETCLASSALT_KEY=1
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='SUB' WHERE SYSASSETCLASSALT_KEY=2
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB1' WHERE SYSASSETCLASSALT_KEY=3
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB2' WHERE SYSASSETCLASSALT_KEY=4
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='DB3' WHERE SYSASSETCLASSALT_KEY=5
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='LOS' WHERE SYSASSETCLASSALT_KEY=6
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_0' WHERE SMA_CLASS_KEY=1
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_1' WHERE SMA_CLASS_KEY=2
      UPDATE ##CUSTOMERCAL SET CustMoveDescription='SMA_2' WHERE SMA_CLASS_KEY=3

      UPDATE  ##AccountCal SET SMA_CLASS='STD' WHERE FinalAssetClassAlt_Key=1 AND  SMA_CLASS is NULL
      UPDATE  ##AccountCal SET SMA_CLASS='SUB' WHERE FinalAssetClassAlt_Key=2 AND  SMA_CLASS is NULL
      UPDATE  ##AccountCal SET SMA_CLASS='DB1' WHERE FinalAssetClassAlt_Key=3  AND  SMA_CLASS is NULL
      UPDATE  ##AccountCal SET SMA_CLASS='DB2' WHERE FinalAssetClassAlt_Key=4  AND  SMA_CLASS is NULL
      UPDATE  ##AccountCal SET SMA_CLASS='DB3' WHERE FinalAssetClassAlt_Key=5  AND  SMA_CLASS is NULL
      UPDATE  ##AccountCal SET SMA_CLASS='LOS' WHERE FinalAssetClassAlt_Key=6 AND  SMA_CLASS is NULL


  --IF OBJECT_ID('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL
  --    DROP TABLE #ACCOUNT_MOVEMENT_HISTORY

  --    SELECT CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY    INTO #ACCOUNT_MOVEMENT_HISTORY
  --    FROM  PRO.AccountCal

  --    ALTER TABLE #ACCOUNT_MOVEMENT_HISTORY ADD MATCH CHAR(1)
  --    UPDATE #ACCOUNT_MOVEMENT_HISTORY SET MATCH='N'

  --  UPDATE A SET MATCH='Y'
  --    FROM  #ACCOUNT_MOVEMENT_HISTORY A
  --    INNER JOIN PRO.ACCOUNT_MOVEMENT_HISTORY B   ON A.CustomerAcID=B.CustomerAcID
  --    AND A.FinalAssetClassAlt_Key=B.FinalAssetClassAlt_Key
  --    WHERE B.EffectiveToTimeKey=49999

  --    UPDATE A SET MATCH='D'
  --      FROM  #ACCOUNT_MOVEMENT_HISTORY A
  --      INNER JOIN PRO.ACCOUNT_MOVEMENT_HISTORY B     ON A.CustomerAcID=B.CustomerAcID
  --      AND A.FinalAssetClassAlt_Key<>B.FinalAssetClassAlt_Key
  --    WHERE B.EffectiveToTimeKey=49999

  --    UPDATE B  SET EffectiveToTimeKey=@TIMEKEY-1
  --    FROM #ACCOUNT_MOVEMENT_HISTORY A   INNER JOIN PRO.ACCOUNT_MOVEMENT_HISTORY B
  --    ON A.CustomerAcID=B.CustomerAcID
  --    WHERE A.MATCH='D' AND B.EffectiveToTimeKey=49999

  --INSERT INTO PRO.ACCOUNT_MOVEMENT_HISTORY (CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,EffectiveFromTimeKey,EffectiveToTimeKeY)
  --select CustomerAcID,FinalAssetClassAlt_Key,FinalNpaDt,@TIMEKEY,49999
  --from #ACCOUNT_MOVEMENT_HISTORY where MATCH  in ('N','D')


    if EXISTS  ( select  1  from PRO.ACCOUNT_MOVEMENT_HISTORY where  [EffectiveFromTimeKey]= @Timekey)
      begin
      print 'NO NEDD TO INSERT DATA'
      end
else
begin
  IF OBJECT_ID ('TEMPDB..#ACCOUNT_MOVEMENT_HISTORY') IS NOT NULL
  DROP TABLE #ACCOUNT_MOVEMENT_HISTORY


CREATE TABLE #ACCOUNT_MOVEMENT_HISTORY (
  [UCIF_ID] [varchar](50) NULL,
  [RefCustomerID] [varchar](50) NULL,
  [SourceSystemCustomerID] [varchar](50) NULL,
  [CustomerAcID] [varchar](225) NULL,
  [FinalAssetClassAlt_Key] [int] NULL,
  [FinalNpaDt] [date] NULL,
  [EffectiveFromTimeKey] [int] NULL,
  [EffectiveToTimeKey] [int] NULL,
  [MovementFromStatus] [varchar](10) NULL,
  [MovementToStatus]   [varchar](10) NULL,
  [TotOsAcc] DECIMAL(18,2),
  MovementFromDate date,   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
  MovementToDate  date  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

  )

  INSERT INTO #ACCOUNT_MOVEMENT_HISTORY
      (
          UCIF_ID,
          RefCustomerID,
          SourceSystemCustomerID,
          CustomerAcID,
          FinalAssetClassAlt_Key,
          FinalNpaDt,
          EffectiveFromTimeKey,
          EffectiveToTimeKey,
          MovementFromStatus,
          MovementToStatus,
          TotOsAcc,
          MovementFromDate ,   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
            )
    SELECT
          UCIF_ID,
          RefCustomerID,
          SourceSystemCustomerID,
          CustomerAcID,
          FinalAssetClassAlt_Key,
          FinalNpaDt,
          EffectiveFromTimeKey,
          49999 AS  EffectiveToTimeKey
          , SMA_CLASS AS MovementFromStatus
          , SMA_CLASS AS MovementToStatus
          , ISNULL(Balance,0) as TotOsAcc,
        @ProcessDate MovementFromDate ,   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
      '2086-11-21' MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

          FROM  ##AccountCal


    INSERT  INTO  PRO.ACCOUNT_MOVEMENT_HISTORY

    (
          UCIF_ID,
          RefCustomerID,
          SourceSystemCustomerID,
          CustomerAcID,
          FinalAssetClassAlt_Key,
          FinalNpaDt,
          EffectiveFromTimeKey,
          EffectiveToTimeKey,
          MovementFromStatus,
          MovementToStatus
          , TotOsAcc
            , MovementFromDate    -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          , MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

    )
    SELECT
                                  A.UCIF_ID,
          A.RefCustomerID,
          A.SourceSystemCustomerID,
          A.CustomerAcID,
          A.FinalAssetClassAlt_Key,
          A.FinalNpaDt,
          A.EffectiveFromTimeKey,
          A.EffectiveToTimeKey,
          ISNULL(B.MovementTOStatus, A.MovementFromStatus),
          A.MovementToStatus,
          ISNULL(A.TotOsAcc,0) AS TotOsAcc
            , A.MovementFromDate   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          , A.MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

      FROM #ACCOUNT_MOVEMENT_HISTORY A
        LEFT JOIN PRO.ACCOUNT_MOVEMENT_HISTORY B ON A.CustomerAcID=B.CustomerAcID
          AND B.EFFECTIVETOTimekey=49999

      WHERE
                  (CASE WHEN  B.CustomerAcID IS NULL THEN 1
            WHEN B.CustomerAcID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1  END ) = 1

  UPDATE AA
      SET
        EffectiveToTimeKey  =  @vEffectiveto
        , MovementToDate=DATEADD(DD,-1,@ProcessDate)  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
  FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA
    LEFT JOIN #ACCOUNT_MOVEMENT_HISTORY B ON  AA.CustomerAcID=B.CustomerAcID AND B.EffectiveToTimeKey =49999
    WHERE AA.EffectiveToTimeKey = 49999
    and B.CustomerAcID is null


    UPDATE AA
  SET
      EffectiveToTimeKey  =  @vEffectiveto
        , MovementToDate=DATEADD(DD,-1,@ProcessDate)  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
  FROM PRO.ACCOUNT_MOVEMENT_HISTORY AA
  WHERE AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY
  AND  EXISTS (SELECT 1 FROM #ACCOUNT_MOVEMENT_HISTORY BB
      WHERE AA.CustomerAcID=BB.CustomerAcID
      AND BB.EffectiveToTimeKey =49999
      --AND AA.MOVEMENTFROMSTATUS<>BB.MOVEMENTTOSTATUS
      AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS
    )

    ----  --COMMENTED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

  --------UPDATE A SET MovementFromDate=B.DATE
  --------    FROM PRO.ACCOUNT_MOVEMENT_HISTORY  A
  --------  inner join sysdaymatrix B on A.EffectiveFromTimeKey=B.TimeKey

  --------  UPDATE A SET MovementToDate=B.DATE
  --------    FROM PRO.ACCOUNT_MOVEMENT_HISTORY  A
  --------  inner join sysdaymatrix B on A.EffectiveToTimeKey=B.TimeKey

    END

    if EXISTS  ( select  1  from PRO.CUSTOMER_MOVEMENT_HISTORY where  [EffectiveFromTimeKey]= @Timekey)
      begin
      print 'NO NEDD TO INSERT DATA'
      end
else
begin
  IF OBJECT_ID ('TEMPDB..#Customer_MOVEMENT_HISTORY') IS NOT NULL
  DROP TABLE #Customer_MOVEMENT_HISTORY


CREATE TABLE #Customer_MOVEMENT_HISTORY (
  [UCIF_ID] [varchar](50) NULL,
  [RefCustomerID] [varchar](50) NULL,
  [SourceSystemCustomerID] [varchar](50) NULL,
  [CustomerName] [varchar](225) NULL,
  [SysAssetClassAlt_Key] [int] NULL,
  [SysNPA_Dt] [date] NULL,
  [EffectiveFromTimeKey] [int] NULL,
  [EffectiveToTimeKey] [int] NULL,
  [MovementFromStatus] [varchar](10) NULL,
  [MovementToStatus]   [varchar](10) NULL,
  [TotOsCust] decimal(18,2)
    , MovementFromDate   DATE  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
  , MovementToDate  DATE -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

  )


  INSERT INTO #Customer_MOVEMENT_HISTORY
      (
          UCIF_ID,
          RefCustomerID,
          SourceSystemCustomerID,
          CustomerName,
          SysAssetClassAlt_Key,
          SysNPA_Dt,
          EffectiveFromTimeKey,
          EffectiveToTimeKey,
          MovementFromStatus,
          MovementToStatus,
          totOsCust
            , MovementFromDate ,   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
            )
      SELECT
            UCIF_ID,
            RefCustomerID,
            SourceSystemCustomerID,
            CustomerName,
            SysAssetClassAlt_Key,
            SysNPA_Dt,
            EffectiveFromTimeKey,
            49999 AS  EffectiveToTimeKey
            , CustMoveDescription AS MovementFromStatus
            , CustMoveDescription AS MovementToStatus
            , ISNULL(TotOsCust,0) AS TotOsCust
          , @ProcessDate MovementFromDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
        , '2086-11-21' MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE


          FROM  ##CUSTOMERCAL


    INSERT  INTO  PRO.CUSTOMER_MOVEMENT_HISTORY

    (
          UCIF_ID,
          RefCustomerID,
          SourceSystemCustomerID,
          CustomerName,
          SysAssetClassAlt_Key,
          SysNPA_Dt,
          EffectiveFromTimeKey,
          EffectiveToTimeKey,
          MovementFromStatus,
          MovementToStatus,
          TotOsCust
            , MovementFromDate    -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          , MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

    )
    SELECT

                                  A.UCIF_ID,
          A.RefCustomerID,
          A.SourceSystemCustomerID,
          A.CustomerName,
          A.SysAssetClassAlt_Key,
          A.SysNPA_Dt,
          A.EffectiveFromTimeKey,
          A.EffectiveToTimeKey,
          ISNULL(B.MovementTOStatus, A.MovementFromStatus),
          A.MovementToStatus,
          ISNULL(A.TotOsCust,0) AS TotOsCust
            , A.MovementFromDate   -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
          , A.MovementToDate  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE


          FROM #Customer_MOVEMENT_HISTORY A
          LEFT JOIN PRO.CUSTOMER_MOVEMENT_HISTORY B ON A.SourceSystemCustomerID=B.SourceSystemCustomerID
            AND B.EFFECTIVETOTimekey=49999

WHERE
                  (CASE WHEN  B.SourceSystemCustomerID IS NULL THEN 1
            WHEN B.SourceSystemCustomerID IS NOT NULL AND  A.MOVEMENTFROMSTATUS<>B.MOVEMENTTOSTATUS THEN 1  END ) = 1

  UPDATE AA
SET
    EffectiveToTimeKey  =  @vEffectiveto
        , MovementToDate=DATEADD(DD,-1,@ProcessDate)  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE
FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA
LEFT JOIN #Customer_MOVEMENT_HISTORY B ON  AA.SourceSystemCustomerID=B.SourceSystemCustomerID AND B.EffectiveToTimeKey =49999
WHERE AA.EffectiveToTimeKey = 49999
and B.SourceSystemCustomerID is null


    UPDATE AA
SET
  EffectiveToTimeKey  =  @vEffectiveto
, MovementToDate=DATEADD(DD,-1,@ProcessDate)  -- ADDED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

FROM PRO.CUSTOMER_MOVEMENT_HISTORY AA
WHERE AA.EffectiveToTimeKey = 49999 AND AA.EffectiveFROMTimeKey<@TIMEKEY
AND  EXISTS (SELECT 1 FROM #Customer_MOVEMENT_HISTORY BB

    WHERE AA.SourceSystemCustomerID=BB.SourceSystemCustomerID
    AND BB.EffectiveToTimeKey =49999
    --AND AA.MOVEMENTFROMSTATUS<>BB.MOVEMENTTOSTATUS
    AND AA.MOVEMENTTOSTATUS<>BB.MOVEMENTTOSTATUS
    )

    ----  --COMMENTED BY AMAR ON 13102021 FOR OPTIMISE - TABIKNG TME TO UPDATE

  ------UPDATE A SET MovementFromDate=B.DATE
  ------    FROM PRO.Customer_MOVEMENT_HISTORY  A
  ------  inner join sysdaymatrix B on A.EffectiveFromTimeKey=B.TimeKey

  ------  UPDATE A SET MovementToDate=B.DATE
  ------    FROM PRO.Customer_MOVEMENT_HISTORY  A
  ------  inner join sysdaymatrix B on A.EffectiveToTimeKey=B.TimeKey

    end
        --------------START------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-----------------

Update					A
SET						A.ContiExcessDt=B.ContiExcessDt, A.DPD_Overdrawn=B.DPD_Overdrawn, A.ReviewDueDt=B.ReviewDueDt, A.DPD_Renewal=B.DPD_Renewal
FROM					##ACCOUNTCAL A
inner join			#DPD_Aqua_SMA B
on						A.AccountEntityID=B.AccountEntityID
--WHERE					ISNULL(B.DPD_Overdrawn,0)<=30

--Update					A
--SET						A.ReviewDueDt=B.ReviewDueDt, A.DPD_Renewal=B.DPD_Renewal
--FROM					##ACCOUNTCAL A
--inner join			#DPD_Aqua_SMA B
--on						A.AccountEntityID=B.AccountEntityID


--------------END------------DPD UPDATE FOR SMA Aqua Scheme---Prashant under guidence of Akshay Sir----17012026-----------------




UPDATE PRO.ACLRUNNINGPROCESSSTATUS
SET COMPLETED='Y', ERRORDATE=NULL, ERRORDESCRIPTION=NULL, COUNT=ISNULL(COUNT,0)+1
WHERE RUNNINGPROCESSNAME='SMA_MARKING'


  --------------------------------Added for DashBoard 04-03-2021
--Update BANDAUDITSTATUS set CompletedCount=CompletedCount+1 where BandName='ASSET CLASSIFICATION'

END TRY
BEGIN   CATCH


        DROP TABLE #TEMPTABLE_SMACLASS
    DROP TABLE #SMACLASS
    DROP TABLE #ACCOUNT_MOVEMENT_HISTORY
    DROP TABLE #Customer_MOVEMENT_HISTORY

UPDATE PRO.ACLRUNNINGPROCESSSTATUS
SET COMPLETED='N', ERRORDATE=GETDATE(), ERRORDESCRIPTION=ERROR_MESSAGE(), COUNT=ISNULL(COUNT,0)+1
WHERE RUNNINGPROCESSNAME='SMA_MARKING'

END CATCH
SET NOCOUNT OFF
END

GO
