# modules/kpi_builder.py

from __future__ import annotations
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np


def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def build_kpi_prev3(
    csv_path: str,
    start_month: str,
    end_month: str,
    include_arpu: bool = True,
    purpose_as_percent: bool = True,
    output_path: str | None = None,
):
    """
    마스터 CSV를 기반으로 기간별 KPI를 계산.

    Parameters
    ----------
    csv_path : str
        마스터 CSV 경로 (예: data/patient_data_merged.csv)
    start_month : str
        시작 연월 (YYYY-MM)
    end_month : str
        종료 연월 (YYYY-MM)
    include_arpu : bool
        ARPU(고객당 매출) 계산 포함 여부
    purpose_as_percent : bool
        방문 목적을 비율(%)로 볼지 여부 (False면 건수 컬럼 생성)

    Returns
    -------
    (pd.DataFrame, str)
        (KPI DataFrame, 저장 경로 문자열)
    """
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # ---- 컬럼 매핑 ----------------------------------------------------
    COL_DATE = pick_first_existing(df, ["진료일", "방문일", "구매일", "내원일"])
    COL_PATIENT = pick_first_existing(df, ["환자 번호", "환자번호", "고객번호", "환자명", "이름"])
    COL_SALES = pick_first_existing(df, ["실질매출", "정제 총 매출", "총 매출"])
    COL_DISC = pick_first_existing(df, ["할인금", "할인액"])
    COL_REFUND = pick_first_existing(df, ["환불금", "환불액"])
    COL_RECEIVABLE = pick_first_existing(df, ["미수금"])
    COL_PURPOSE = pick_first_existing(df, ["방문 목적", "내원 목적", "구매 목적"])

    if COL_DATE is None:
        raise KeyError("[kpi_builder] 날짜 컬럼(진료일/방문일/구매일 등)이 필요합니다.")
    if COL_PATIENT is None:
        raise KeyError("[kpi_builder] 환자/고객을 식별할 컬럼이 필요합니다. (환자 번호/환자명 등)")

    # 날짜 변환
    df["_date"] = pd.to_datetime(df[COL_DATE], errors="coerce")
    df = df.dropna(subset=["_date"])

    # 연월(YYYY-MM) 컬럼
    df["_ym"] = df["_date"].dt.to_period("M").astype(str)

    # 기간 필터
    ym_start = pd.Period(start_month, freq="M")
    ym_end = pd.Period(end_month, freq="M")
    df_period = df[
        (pd.PeriodIndex(df["_ym"], freq="M") >= ym_start)
        & (pd.PeriodIndex(df["_ym"], freq="M") <= ym_end)
    ].copy()

    if df_period.empty:
        print("[kpi_builder] 경고: 지정한 기간에 해당하는 데이터가 없습니다.")
        kpi = pd.DataFrame()
        if output_path is None:
            out_path = csv_path.parent / f"KPI_{start_month}_{end_month}.csv"
        else:
            out_path = Path(output_path)
        kpi.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"[kpi_builder] 빈 KPI 파일이 저장되었습니다: {out_path}")
        return kpi, str(out_path)

    # ---- 매출 관련 숫자 처리 -----------------------------------------
    if COL_SALES:
        df_period["_sales"] = safe_to_numeric(df_period[COL_SALES])
    else:
        # 실질매출 직접 계산
        base = safe_to_numeric(df_period.pick_first_existing(["총 매출"]))
        disc = safe_to_numeric(df_period[COL_DISC]) if COL_DISC else 0
        refund = safe_to_numeric(df_period[COL_REFUND]) if COL_REFUND else 0
        recv = safe_to_numeric(df_period[COL_RECEIVABLE]) if COL_RECEIVABLE else 0
        df_period["_sales"] = base - disc + refund - recv

    # ---- 환자 첫 방문월 / 신규/기존 구분 ------------------------------
    # 전체 데이터 기준 첫 방문월 계산 (원하면 df_period 기준으로 바꾸어도 됨)
    all_dates = df.copy()
    all_dates["_date"] = pd.to_datetime(all_dates[COL_DATE], errors="coerce")
    all_dates["_ym"] = all_dates["_date"].dt.to_period("M").astype(str)

    first_visit = (
        all_dates
        .groupby(COL_PATIENT)["_date"]
        .min()
        .dt.to_period("M")
        .astype(str)
        .rename("first_ym")
    )

    df_period = df_period.merge(first_visit, left_on=COL_PATIENT, right_index=True, how="left")

    df_period["_is_new"] = df_period["_ym"] == df_period["first_ym"]
    df_period["_is_old"] = df_period["_ym"] != df_period["first_ym"]

    # ---- 월별 그룹 집계 ----------------------------------------------
    group = df_period.groupby("_ym")

    kpi = pd.DataFrame()
    kpi["방문 수"] = group.size()
    kpi["고유 환자 수"] = group[COL_PATIENT].nunique()
    kpi["신규 환자 수"] = group["_is_new"].sum()
    kpi["기존 환자 수"] = group["_is_old"].sum()
    kpi["실질 매출"] = group["_sales"].sum().round(0)

    if include_arpu:
        # ARPU = 실질매출 / 고유 환자 수
        kpi["ARPU"] = (kpi["실질 매출"] / kpi["고유 환자 수"].replace(0, np.nan)).round(0)

    # ---- 방문 목적 분포 ----------------------------------------------
    if COL_PURPOSE:
        purpose_ct = (
            df_period
            .groupby(["_ym", COL_PURPOSE])
            .size()
            .unstack(fill_value=0)
        )
        if purpose_as_percent:
            purpose_pct = (purpose_ct.T / purpose_ct.sum(axis=1)).T * 100
            purpose_pct = purpose_pct.round(1)
            # 컬럼 이름에 '(%)' 붙이기
            purpose_pct = purpose_pct.add_suffix(" (%)")
            kpi = kpi.join(purpose_pct, how="left")
        else:
            # 건수 그대로 붙이기
            kpi = kpi.join(purpose_ct, how="left")

    # 인덱스(연월)를 컬럼으로
    kpi = kpi.reset_index().rename(columns={"_ym": "연월"})

    # ---- 파일 저장 ----------------------------------------------------
    if output_path is None:
        out_path = csv_path.parent / f"KPI_{start_month}_{end_month}.csv"
    else:
        out_path = Path(output_path)

    kpi.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[kpi_builder] KPI 파일 저장: {out_path}")

    return kpi, str(out_path)
