# modules/vip_snapshot.py

from __future__ import annotations
from pathlib import Path
from datetime import datetime, date
from typing import Optional

import pandas as pd
import numpy as np


def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """df.columns 중에서 candidates 리스트에서 처음으로 존재하는 컬럼명을 반환."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


def safe_to_numeric(series: pd.Series) -> pd.Series:
    """콤마/문자 섞인 숫자 시리즈를 안전하게 float로 변환."""
    return pd.to_numeric(series.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def safe_to_date(series: pd.Series) -> pd.Series:
    """문자열 시리즈를 날짜로 변환 (에러는 NaT)."""
    return pd.to_datetime(series, errors="coerce").dt.date


def build_vip_snapshot(
    update_file: str,
    patient_file: str,          # 현재는 사용하지 않지만 인터페이스 유지용
    output_dir: str | None = None,
    days_window: int = 180,     # 최근 N일 이내
    vip_threshold: int = 5_000_000,
    vvip_threshold: int = 10_000_000,
) -> pd.DataFrame:
    """
    업데이트 요약 파일(YYYYMMDD_업데이트.csv)을 기반으로
    최근 N일 이내 + 매출 기준으로 VIP/VVIP 스냅샷을 생성.

    결과 CSV는 항상 output_dir(또는 update_file이 있는 폴더)에
    'YYYYMMDD_VIP_최신화.csv' 이름으로 저장된다.

    Parameters
    ----------
    update_file : str
        환자 요약 파일 경로 (예: data/20251117_업데이트.csv)
    patient_file : str
        마스터 파일 경로 (현재 버전에서는 주로 무시, 시그니처 유지용)
    output_dir : str | None
        결과를 저장할 폴더.
        None이면 update_file이 있는 폴더에 저장.
    days_window : int
        최근 며칠 이내 방문을 VIP 후보로 볼지 (기본 180일)
    vip_threshold : int
        VIP 매출 기준 (기본 500만)
    vvip_threshold : int
        VVIP 매출 기준 (기본 1,000만)

    Returns
    -------
    pd.DataFrame
        VIP/VVIP만 담긴 스냅샷 DataFrame
    """
    update_path = Path(update_file)
    patient_path = Path(patient_file)  # 현재는 사용 안 하지만, 필요하면 연동 가능

    # 🔥 출력 디렉토리 결정
    if output_dir is None:
        out_dir = update_path.parent      # 예: data/
    else:
        out_dir = Path(output_dir)

    # ---- 데이터 로드 --------------------------------------------------
    df = pd.read_csv(update_path, encoding="utf-8-sig")

    # ---- 컬럼 매핑 (유연하게) -----------------------------------------
    # 이름/연락처/매출/최근일/기존 등급 컬럼을 최대한 자동으로 찾음
    COL_NAME = pick_first_existing(df, ["환자명", "이름", "성명"])
    COL_PHONE = pick_first_existing(df, ["연락처", "전화번호", "휴대전화", "핸드폰"])
    COL_SALES = pick_first_existing(df, ["정제 총 매출", "실질매출", "총 매출", "매출"])
    COL_RECENT = pick_first_existing(df, ["최근 진료일", "최근 방문일", "최근 구매일"])
    COL_GRADE = pick_first_existing(df, ["맴버십등급", "맴버십 등급", "환자 등급", "등급"])

    if COL_NAME is None:
        raise KeyError(
            "[vip_snapshot] 환자명을 나타내는 컬럼이 필요합니다. "
            "(예: '환자명', '이름', '성명')"
        )

    if COL_SALES is None:
        raise KeyError(
            "[vip_snapshot] 매출 컬럼이 필요합니다. "
            "(예: '정제 총 매출', '실질매출', '총 매출', '매출')"
        )

    if COL_RECENT is None:
        print(
            "[vip_snapshot] 경고: 최근 진료/방문/구매일 컬럼이 없어, "
            f"'최근 {days_window}일' 기간 필터 없이 전체를 대상으로 VIP를 산출합니다."
        )

    # ---- 타입 변환 ----------------------------------------------------
    df["_sales"] = safe_to_numeric(df[COL_SALES])

    if COL_RECENT:
        df["_recent_date"] = safe_to_date(df[COL_RECENT])
    else:
        df["_recent_date"] = pd.NaT

    # ---- 최근 N일 필터 ------------------------------------------------
    today = datetime.today().date()

    if COL_RECENT:
        df["_within_window"] = df["_recent_date"].apply(
            lambda d: ((today - d).days <= days_window) if isinstance(d, date) else False
        )
    else:
        df["_within_window"] = True  # 날짜 정보가 없으면 기간 필터는 생략

    # ---- 매출 기준 VIP/VVIP 분류 --------------------------------------
    def classify_by_sales(sales: float) -> str:
        if sales >= vvip_threshold:
            return "VVIP"
        elif sales >= vip_threshold:
            return "VIP"
        else:
            return "일반"

    if COL_GRADE:
        # 기존에 등급 컬럼이 있으면 그대로 가져오고,
        # 매출 기준으로 업그레이드하고 싶으면 여기서 덮어쓸 수도 있음.
        df["_grade_raw"] = df[COL_GRADE].fillna("일반")
        # 아래 주석을 풀면 매출 기준 등급으로 강제 오버라이드 가능
        # mask_sales_vip = df["_sales"] >= vip_threshold
        # df.loc[mask_sales_vip, "_grade_raw"] = df.loc[mask_sales_vip, "_sales"].apply(classify_by_sales)
    else:
        df["_grade_raw"] = df["_sales"].apply(lambda x: classify_by_sales(x if pd.notna(x) else 0))

    # ---- VIP/VVIP + 기간 필터 적용 ------------------------------------
    is_vip = df["_grade_raw"].isin(["VIP", "VVIP"])
    mask = is_vip & df["_within_window"]

    vip_df = df.loc[mask].copy()

    if vip_df.empty:
        print("[vip_snapshot] 경고: 조건에 맞는 VIP/VVIP 고객이 없습니다.")
    else:
        print(f"[vip_snapshot] VIP/VVIP 대상자 수: {len(vip_df)}")

    # ---- 출력 컬럼 정리 -----------------------------------------------
    # vip_diff와 호환되도록 최종 컬럼 이름을 '환자명', '맴버십등급'으로 맞춘다.
    out = pd.DataFrame()
    out["환자명"] = vip_df[COL_NAME].astype(str)

    if COL_PHONE:
        out["연락처"] = vip_df[COL_PHONE].astype(str)

    out["총매출"] = vip_df["_sales"]

    if COL_RECENT:
        out["최근일자"] = vip_df["_recent_date"]

    out["맴버십등급"] = vip_df["_grade_raw"]

    # 이름 기준 중복이 있다면 1행만 남기기 (원하면 더 복잡한 로직으로 변경 가능)
    out = out.drop_duplicates(subset=["환자명"])

    # ---- 파일 저장 ----------------------------------------------------
    today_str = today.strftime("%Y%m%d")
    out_path = out_dir / f"{today_str}_VIP_최신화.csv"

    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[vip_snapshot] VIP 스냅샷 저장: {out_path}")

    return out
