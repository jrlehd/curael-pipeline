# modules/crm_scoring.py

from __future__ import annotations
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np
from datetime import datetime


def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """df.columns 안에서 후보 리스트 중 처음으로 발견되는 컬럼 이름을 반환."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def safe_to_numeric(series: pd.Series) -> pd.Series:
    """문자/콤마 섞인 숫자 시리즈를 안전하게 float로 변환."""
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def safe_to_date(series: pd.Series) -> pd.Series:
    """문자열 시리즈를 날짜로 변환 (에러는 NaT)."""
    return pd.to_datetime(series, errors="coerce").dt.date


def over_90_days(d: datetime.date, today: datetime.date) -> bool:
    return (today - d).days >= 90


def run_crm_scoring(base_name: str, input_dir: str = ".") -> pd.DataFrame:
    """
    CRM 점수화/분류 메인 함수

    Parameters
    ----------
    base_name : str
        확장자를 제외한 파일 이름 (예: '20251117_업데이트')
    input_dir : str
        CSV/XLSX 가 들어있는 폴더 경로 (기본 '.')

    Returns
    -------
    pd.DataFrame
        점수/등급이 포함된 최종 DataFrame
    """
    input_path_csv = Path(input_dir) / f"{base_name}.csv"
    input_path_xlsx = Path(input_dir) / f"{base_name}.xlsx"

    if input_path_csv.exists():
        path = input_path_csv
        df = pd.read_csv(path, encoding="utf-8-sig")
    elif input_path_xlsx.exists():
        path = input_path_xlsx
        df = pd.read_excel(path)
    else:
        raise FileNotFoundError(f"[crm_scoring] 입력 파일을 찾을 수 없습니다: {input_path_csv} 또는 {input_path_xlsx}")

    print(f"[crm_scoring] 입력 파일: {path}")

    # --- 컬럼 매핑 (유연하게) -------------------------------------
    COL_SALES = pick_first_existing(df, ["정제 총 매출", "실질매출", "총 매출"])
    COL_COUNT = pick_first_existing(df, ["구매 횟수", "방문 횟수", "내원 횟수"])
    COL_AVG = pick_first_existing(df, ["평균 구매금", "평균 구매액", "평균 객단가"])
    COL_RECENT = pick_first_existing(df, ["최근 구매일", "최근 진료일", "최근 방문일"])
    COL_FIRST = pick_first_existing(df, ["최초 구매일", "첫 구매일", "첫 진료일", "첫 방문일"])

    if COL_SALES is None:
        raise KeyError("[crm_scoring] '정제 총 매출'(또는 동등한 컬럼)이 존재하지 않습니다. 최소 하나는 필요합니다.")

    if COL_COUNT is None:
        print("[crm_scoring] 경고: 구매/방문 횟수 컬럼이 없습니다. 일부 기능이 제한될 수 있습니다.")
    if COL_AVG is None:
        print("[crm_scoring] 경고: 평균 구매금/객단가 컬럼이 없습니다. 일부 기능이 제한될 수 있습니다.")
    if COL_RECENT is None:
        print("[crm_scoring] 경고: 최근 구매일/진료일 컬럼이 없습니다. 90일 경과 기준 강제 3군 기능이 비활성화됩니다.")
    if COL_FIRST is None:
        print("[crm_scoring] 경고: 최초 구매일/진료일 컬럼이 없습니다. 최초 대비 부분구매 로직 일부가 제한될 수 있습니다.")

    # --- 숫자/날짜 변환 -------------------------------------------
    df["_sales"] = safe_to_numeric(df[COL_SALES])

    if COL_COUNT:
        df["_count"] = safe_to_numeric(df[COL_COUNT]).fillna(1)
    else:
        df["_count"] = 1  # 없으면 모두 1회로 가정

    if COL_AVG:
        df["_avg"] = safe_to_numeric(df[COL_AVG])
    else:
        # 없으면 _sales / _count 로 대체
        df["_avg"] = df["_sales"] / df["_count"].replace(0, np.nan)

    today = datetime.today().date()

    if COL_RECENT:
        df["_recent_date"] = safe_to_date(df[COL_RECENT])
    else:
        df["_recent_date"] = pd.NaT

    if COL_FIRST:
        df["_first_date"] = safe_to_date(df[COL_FIRST])
    else:
        df["_first_date"] = pd.NaT

    # --- 강제 3군 조건 (최근일자 없는 경우는 이 로직 생략) ---------
    if COL_RECENT:
        df["_over90"] = df["_recent_date"].apply(
            lambda d: over_90_days(d, today) if pd.notna(d) else True
        )
    else:
        df["_over90"] = False  # 날짜 없으면 90일 경과 기준은 사용하지 않음

    df["_sales_zero"] = df["_sales"].fillna(0) <= 0

    # 하나라도 True면 강제 3군
    df["_forced3"] = df["_over90"] | df["_sales_zero"]

    # --- 상관관계 기반 가중치 계산 (강제3군 아닌 데이터만) ----------
    corr_df = df.loc[~df["_forced3"], ["_sales", "_count", "_avg"]].dropna()
    if len(corr_df) < 5:
        print("[crm_scoring] 경고: 상관관계 계산을 위한 데이터가 부족합니다. 기본 가중치(동일 가중) 사용.")
        weights = np.array([1.0, 1.0, 1.0])
    else:
        corr = corr_df.corr(method="pearson")
        # 매출과의 절댓값 상관계수 기준으로 중요도 추정
        rel = np.abs(corr.loc["_sales", ["_sales", "_count", "_avg"]].values)
        rel[0] = max(rel[0], 1.0)  # 자기자신은 최소 1
        if rel.sum() == 0:
            weights = np.array([1.0, 1.0, 1.0])
        else:
            weights = rel / rel.sum() * 10  # 합이 10이 되도록 스케일
    w_sales, w_count, w_avg = weights
    print(f"[crm_scoring] 가중치 (매출, 횟수, 평균): {w_sales:.2f}, {w_count:.2f}, {w_avg:.2f}")

    # --- 간단 정규화 (0~1) ---------------------------------------
    def norm_col(s: pd.Series) -> pd.Series:
        q = s.quantile(0.9)
        if q <= 0 or np.isnan(q):
            return s * 0
        return (s / q).clip(0, 1)

    nsales = norm_col(df["_sales"].fillna(0))
    ncnt = norm_col(df["_count"].fillna(0))
    navg = norm_col(df["_avg"].fillna(0))

    df["_score_raw"] = nsales * w_sales + ncnt * w_count + navg * w_avg

    max_score = df["_score_raw"].max()
    if max_score <= 0 or np.isnan(max_score):
        df["_score100"] = 0
    else:
        df["_score100"] = (df["_score_raw"] / max_score * 100).round(1)

    # --- 등급 부여 -----------------------------------------------
    # 강제 3군
    df["_grade"] = "3군"
    df.loc[~df["_forced3"], "_grade"] = "2군"  # 일단 2군으로 기본 설정

    # 점수 기반으로 상위/중위/하위 구간 나누기 (forced3 아닌 애들만)
    mask = ~df["_forced3"]
    scores = df.loc[mask, "_score100"]

    if len(scores) >= 5:
        q1 = scores.quantile(1 / 3)
        q2 = scores.quantile(2 / 3)

        df.loc[mask & (df["_score100"] >= q2), "_grade"] = "1군"
        df.loc[mask & (df["_score100"] < q1), "_grade"] = "3군"
        # 나머지는 2군 유지
    else:
        print("[crm_scoring] 경고: 등급을 세분화하기에 데이터가 적어, 기본 2~3군만 사용합니다.")

    # --- 결과 정리 -----------------------------------------------
    # 출력에 포함할 주요 컬럼들 (실제 파일 컬럼 이름 + 점수/등급)
    output_cols = []

    for col in ["환자명", "이름", "성명"]:
        if col in df.columns:
            output_cols.append(col)
            break

    for col in ["연락처", "전화번호", "휴대전화"]:
        if col in df.columns:
            output_cols.append(col)
            break

    # 원래 매출/횟수/평균/날짜 컬럼들
    for col in [COL_SALES, COL_COUNT, COL_AVG, COL_FIRST, COL_RECENT]:
        if col and col in df.columns and col not in output_cols:
            output_cols.append(col)

    # 점수/등급 추가
    output_cols += ["_score100", "_grade"]

    result = df[output_cols].copy()
    result = result.rename(columns={"_score100": "CRM 점수(0-100)", "_grade": "CRM 등급"})

    # 파일 저장
    output_path = Path(input_dir) / f"{base_name}_환자분류_결과.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[crm_scoring] 결과 파일이 저장되었습니다: {output_path}")

    return result
