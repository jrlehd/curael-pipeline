# modules/merge_and_summary.py
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List


EXCLUDED_NAMES: List[str] = [
    "김훈하", "무명", "유해인", "김동은", "김종훈", "김예은",
    "강은진", "백인보", "전정미", "백형철", "강지석", "정기동",
]


def _clean_patient_number(df: pd.DataFrame, col: str = "환자 번호") -> pd.DataFrame:
    if col not in df.columns:
        return df
    df[col] = (
        df[col]
        .astype(str)
        .str.replace('="', "", regex=False)
        .str.replace('"', "", regex=False)
        .str.extract(r"(\d+)", expand=False)
    )
    return df


def _to_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def update_master_and_build_summary(
    new_file: str,
    merged_file: str = "patient_data_merged.csv",
    tag_file: str = "merged_with_tag.csv",
    output_summary_file: str | None = None,
) -> None:
    """
    1) 기존 마스터 + 신규 데이터를 병합하여 마스터를 최신화하고
    2) 암종 태그를 병합한 뒤 환자별 요약(매출, 횟수, 최초/최근, VIP 등)을 계산하여
       YYYYMMDD_업데이트.csv 형태로 저장한다.
    """
    today = datetime.today()
    today_str = today.strftime("%Y%m%d")
    if output_summary_file is None:
        output_summary_file = f"{today_str}_업데이트.csv"

    # --- 파일 로딩 ---
    merged_path = Path(merged_file)
    if merged_path.exists():
        df_existing = pd.read_csv(merged_path)
    else:
        print(f"[merge_and_summary] 기존 마스터가 없어 신규 파일로 시작합니다: {merged_path}")
        df_existing = pd.DataFrame()

    df_new = pd.read_csv(new_file)
    df_tags = pd.read_csv(tag_file)

    # --- 환자 번호 & 날짜 전처리 ---
    for df in [df_existing, df_new]:
        if not df.empty:
            _clean_patient_number(df, "환자 번호")
            _to_datetime(df, "진료일")

    _clean_patient_number(df_tags, "환자 번호")
    _to_datetime(df_tags, "진료일")

    # --- 마스터 병합 및 저장 ---
    combined_df = pd.concat([df_existing, df_new], ignore_index=True)
    combined_df = combined_df.drop_duplicates()
    combined_df.to_csv(merged_file, index=False, encoding="utf-8-sig")
    print(f"[merge_and_summary] 마스터 최신화 완료: {merged_file}")

    # --- 환자 태그 병합 ---
    tag_small = (
        df_tags[["환자 번호", "환자태그"]]
        .dropna(subset=["환자 번호"])
        .drop_duplicates(subset=["환자 번호"])
    )
    combined_df = combined_df.merge(tag_small, on="환자 번호", how="left")

    # --- 필터링: 내부/테스트 계정, 상담예약-only 등 제거 ---
    if "환자명" in combined_df.columns:
        mask_names = combined_df["환자명"].astype(str).apply(
            lambda x: any(name in x for name in EXCLUDED_NAMES)
        )
    else:
        mask_names = pd.Series(False, index=combined_df.index)

    if {"담당의", "방문 목적"}.issubset(combined_df.columns):
        mask_consult = (
            combined_df["담당의"].isin(["유해인", "강은진"])
            & (combined_df["방문 목적"] == "상담예약")
        )
    else:
        mask_consult = pd.Series(False, index=combined_df.index)

    filtered_df = combined_df[~(mask_names | mask_consult)].copy()

    # 진료일 중복 제거 (환자 번호 + 진료일 단위)
    if {"환자 번호", "진료일"}.issubset(filtered_df.columns):
        filtered_df = filtered_df.drop_duplicates(subset=["환자 번호", "진료일"])

    # --- 숫자형 컬럼 처리 ---
    for col in ["총 매출", "할인금", "환불금", "미수금"]:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce").fillna(0)
        else:
            filtered_df[col] = 0

    # --- 정제 총 매출 ---
    filtered_df["정제 총 매출"] = (
        filtered_df["총 매출"]
        - filtered_df["할인금"]
        + filtered_df["환불금"]
        - filtered_df["미수금"]
    )

    # --- 최근 진료일 ---
    if "진료일" not in filtered_df.columns:
        raise ValueError("필수 컬럼 '진료일'이 없습니다.")

    recent_date = (
        filtered_df.groupby("환자 번호")["진료일"]
        .max()
        .reset_index()
        .rename(columns={"진료일": "최근 진료일"})
    )

    # --- 최초 구매 금액 & 최초 구매일 ---
    # 금액 리스트를 먼저 구한 뒤 예약비(10만, 35만) 예외 처리
    tmp = (
        filtered_df.sort_values(by="진료일")
        .groupby("환자 번호")["총 매출"]
        .apply(list)
        .reset_index()
        .rename(columns={"총 매출": "금액리스트"})
    )

    def get_improved_first_amount(amounts: list[float]) -> float:
        valid = [amt for amt in amounts if amt > 0]
        if not valid:
            return 0.0
        if valid[0] in [100000, 350000] and len(valid) > 1:
            return float(valid[1])
        return float(valid[0])

    tmp["최초 구매 금액"] = tmp["금액리스트"].apply(get_improved_first_amount)
    first_amount = tmp[["환자 번호", "최초 구매 금액"]]

    # 최초 구매일: 총 매출 > 0인 가장 빠른 진료일
    first_purchase_date = (
        filtered_df[filtered_df["총 매출"] > 0]
        .sort_values(by="진료일")
        .groupby("환자 번호")["진료일"]
        .first()
        .reset_index()
        .rename(columns={"진료일": "최초 구매일"})
    )

    # --- 환자별 집계: 정제 총 매출 합계, 구매 횟수, 평균 구매금 ---
    summary = (
        filtered_df.groupby("환자 번호")
        .agg(
            정제_총_매출합=("정제 총 매출", "sum"),
            구매_횟수=("진료일", "count"),
        )
        .reset_index()
    )
    summary["평균 구매금"] = summary["정제_총_매출합"] / summary["구매_횟수"]

    # 합치기
    patient_summary = (
        summary.merge(recent_date, on="환자 번호", how="left")
        .merge(first_amount, on="환자 번호", how="left")
        .merge(first_purchase_date, on="환자 번호", how="left")
    )
    patient_summary = patient_summary.rename(columns={"정제_총_매출합": "정제 총 매출"})

    # --- 환자 등급 (VVIP/VIP/일반) ---
    def grade_from_sales(x: float) -> str:
        if x >= 10_000_000:
            return "VVIP"
        if x >= 5_000_000:
            return "VIP"
        return "일반"

    patient_summary["환자 등급"] = patient_summary["정제 총 매출"].apply(grade_from_sales)

    # --- 구매 기준 분류 (완전/부분/종료) ---
    now = pd.to_datetime("today")

    def purchase_status(row) -> str:
        recent = row["최근 진료일"]
        first_amt = row["최초 구매 금액"]
        avg_amt = row["평균 구매금"]

        if pd.isna(recent):
            return "종료 고객"
        if (now - recent).days > 120:
            return "종료 고객"

        try:
            if avg_amt < first_amt * 0.66:
                return "부분 구매 고객"
            else:
                return "완전 구매 고객"
        except Exception:
            return "부분 구매 고객"

    patient_summary["구매 기준"] = patient_summary.apply(purchase_status, axis=1)

    # --- 최신 환자명/태그 가져오기 ---
    latest_info = (
        filtered_df.sort_values("진료일", ascending=False)[
            ["환자 번호", "환자명", "환자태그"]
        ]
        .drop_duplicates(subset=["환자 번호"])
    )
    final_df = patient_summary.merge(latest_info, on="환자 번호", how="left")

    # --- 연락처 병합 (기존 마스터에서 가져오기) ---
    if "연락처" in df_existing.columns:
        contacts = (
            df_existing[["환자 번호", "연락처"]]
            .dropna(subset=["연락처"])
            .drop_duplicates(subset=["환자 번호"], keep="last")
        )
    else:
        contacts = (
            combined_df[["환자 번호", "연락처"]]
            .dropna(subset=["연락처"])
            .drop_duplicates(subset=["환자 번호"], keep="last")
        )

    final_df = final_df.merge(contacts, on="환자 번호", how="left")

    # --- 컬럼 순서 정리 ---
    cols = list(final_df.columns)
    # 환자명, 환자태그, 연락처를 앞으로
    ordered = []
    for c in ["환자명", "환자태그", "연락처"]:
        if c in cols:
            ordered.append(c)
    for c in ["환자 번호", "정제 총 매출", "구매_횟수", "평균 구매금", "최초 구매 금액", "최초 구매일", "최근 진료일", "환자 등급", "구매 기준"]:
        if c in cols and c not in ordered:
            ordered.append(c)
    # 나머지
    for c in cols:
        if c not in ordered:
            ordered.append(c)

    final_df = final_df[ordered]

    final_df.to_csv(output_summary_file, index=False, encoding="utf-8-sig")
    print(f"[merge_and_summary] 환자 요약 저장 완료: {output_summary_file}")


if __name__ == "__main__":
    # 예시 실행
    update_master_and_build_summary(
        new_file="2025-11-10_2025-11-17_신규데이터.csv",
        merged_file="patient_data_merged.csv",
        tag_file="merged_with_tag.csv",
    )
