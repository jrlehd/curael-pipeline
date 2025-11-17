# modules/vip_diff_new.py

from __future__ import annotations
from pathlib import Path
from typing import Optional

import pandas as pd


def pick_first_existing(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def load_vip_file(path: str) -> pd.DataFrame:
    """
    VIP 스냅샷 파일에서
    - 환자명 컬럼 (환자명/이름/성명 등)
    - 등급 컬럼 (맴버십등급/환자 등급/등급 등)
    을 찾아서, ['환자명', '맴버십등급'] 형태의 DataFrame으로 반환.
    """
    p = Path(path)
    df = pd.read_csv(p, encoding="utf-8-sig")

    name_col = pick_first_existing(df, ["환자명", "이름", "성명"])
    grade_col = pick_first_existing(df, ["맴버십등급", "맴버십 등급", "환자 등급", "등급"])

    if name_col is None:
        raise KeyError(
            f"[vip_diff_new] '{p.name}'에서 환자명을 나타내는 컬럼을 찾을 수 없습니다. "
            "(환자명/이름/성명 등)"
        )

    if grade_col is None:
        raise KeyError(
            f"[vip_diff_new] '{p.name}'에서 등급 컬럼을 찾을 수 없습니다. "
            "(맴버십등급/환자 등급/등급 등)"
        )

    sub = df[[name_col, grade_col]].copy()
    sub = sub.rename(columns={name_col: "환자명", grade_col: "맴버십등급"})

    return sub


def is_vip(grade: str) -> bool:
    return str(grade) in ["VIP", "VVIP"]


def classify_change(row) -> str:
    prev_grade = str(row.get("맴버십등급_이전", "일반"))
    curr_grade = str(row.get("맴버십등급_현재", "일반"))

    prev_is_vip = is_vip(prev_grade)
    curr_is_vip = is_vip(curr_grade)

    if prev_is_vip and curr_is_vip:
        if prev_grade == curr_grade:
            return "유지"
        else:
            return "등급변경"
    elif prev_is_vip and not curr_is_vip:
        return "제외"
    elif (not prev_is_vip) and curr_is_vip:
        return "신규"
    else:
        return "기타"


def build_vip_diff_new(
    prev_file: str,
    curr_file: str,
) -> pd.DataFrame:
    """
    지난주 VIP 스냅샷(prev_file)과 이번주 VIP 스냅샷(curr_file)을 비교하여
    - 맴버십등급_이전
    - 맴버십등급_현재
    - 상태 (유지/신규/제외/등급변경/기타)
    를 계산한 DataFrame만 반환한다.
    (⚠ 여기서는 절대 파일 저장을 하지 않는다.)
    """
    prev = load_vip_file(prev_file)
    curr = load_vip_file(curr_file)

    # '환자명' 기준 outer merge
    merged = pd.merge(
        prev.rename(columns={"맴버십등급": "맴버십등급_이전"}),
        curr.rename(columns={"맴버십등급": "맴버십등급_현재"}),
        on="환자명",
        how="outer",
    )

    # 결측값은 기본 '일반'으로 처리
    merged["맴버십등급_이전"] = merged["맴버십등급_이전"].fillna("일반")
    merged["맴버십등급_현재"] = merged["맴버십등급_현재"].fillna("일반")

    # 상태 분류
    merged["상태"] = merged.apply(classify_change, axis=1)

    # 정렬: 상태별 / 이름순
    merged = merged.sort_values(["상태", "환자명"]).reset_index(drop=True)

    return merged
