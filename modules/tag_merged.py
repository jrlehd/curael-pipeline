# modules/tag_merge.py
import pandas as pd
from pathlib import Path


def merge_cancer_tag(
    merged_file_path: str = "patient_data_merged.csv",
    tag_file_path: str = "환자정보_2025-11-17T09_07_01.128.csv",
    output_file_path: str = "merged_with_tag.csv",
) -> None:
    """
    마스터 환자 데이터와 암종(환자태그) 데이터를 병합해서 저장하는 함수.

    Parameters
    ----------
    merged_file_path : str
        진료·매출이 누적된 마스터 파일 경로 (예: patient_data_merged.csv)
    tag_file_path : str
        환자번호 + 환자태그(암종)가 들어 있는 파일 경로
    output_file_path : str
        병합 결과를 저장할 파일 경로 (예: merged_with_tag.csv)
    """
    merged_path = Path(merged_file_path)
    tag_path = Path(tag_file_path)

    if not merged_path.exists():
        raise FileNotFoundError(f"마스터 파일을 찾을 수 없습니다: {merged_path}")
    if not tag_path.exists():
        raise FileNotFoundError(f"태그 파일을 찾을 수 없습니다: {tag_path}")

    merged_df = pd.read_csv(merged_path)
    tag_df = pd.read_csv(tag_path)

    # --- 환자번호 정규화 ---
    # tag_df: '환자번호' → 숫자만 추출 후 int 변환
    if "환자번호" not in tag_df.columns:
        raise ValueError("태그 파일에 '환자번호' 컬럼이 없습니다.")

    tag_df["환자번호"] = (
        tag_df["환자번호"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
        .astype("Int64")
    )

    # merged_df: '환자 번호'를 int로 맞춰줌
    if "환자 번호" not in merged_df.columns:
        raise ValueError("마스터 파일에 '환자 번호' 컬럼이 없습니다.")

    merged_df["환자 번호"] = (
        merged_df["환자 번호"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
        .astype("Int64")
    )

    # --- 병합: left join ---
    cols_to_use = ["환자번호", "환자태그"] if "환자태그" in tag_df.columns else ["환자번호"]
    tag_small = tag_df[cols_to_use].drop_duplicates(subset=["환자번호"])

    result_df = pd.merge(
        merged_df,
        tag_small,
        left_on="환자 번호",
        right_on="환자번호",
        how="left",
    )

    # 병합 후 오른쪽 key 컬럼 제거
    if "환자번호" in result_df.columns:
        result_df = result_df.drop(columns=["환자번호"])

    result_df.to_csv(output_file_path, index=False, encoding="utf-8-sig")
    print(f"[tag_merge] 병합된 파일이 저장되었습니다: {output_file_path}")


if __name__ == "__main__":
    merge_cancer_tag()
