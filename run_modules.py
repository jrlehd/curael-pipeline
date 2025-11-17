# run_modules.py
"""
환자 데이터 운영·분석 모듈 실행기 (자동 파일 탐지 + data 폴더 고정 버전)

디렉토리 구조 가정:

project_root/
│
├── run_modules.py
├── modules/
│   ├── tag_merged.py
│   ├── merge_and_summary.py
│   ├── vip_snapshot.py
│   ├── vip_diff.py
│   ├── crm_scoring.py
│   └── kpi_builder.py
│
└── data/
    ├── patient_data_merged.csv
    ├── 환자정보_2025-11-17T09_07_01.128.csv
    ├── 2025-11-10_2025-11-17_29ae7....csv
    └── 기타 생성 파일...

"""

from pathlib import Path
from datetime import datetime

from modules.tag_merged import merge_cancer_tag
from modules.merge_and_summary import update_master_and_build_summary
from modules.vip_snapshot import build_vip_snapshot
from modules.vip_diff import build_vip_diff_new
from modules.crm_scoring import run_crm_scoring
from modules.kpi_builder import build_kpi_prev3

# 📂 데이터 폴더: 반드시 project_root/data 에 있어야 함
DATA_DIR = Path("data")


def find_latest(pattern: str) -> Path | None:
    """DATA_DIR에서 glob 패턴에 맞는 파일 중 가장 마지막 파일 반환."""
    files = sorted(DATA_DIR.glob(pattern))
    return files[-1] if files else None


def find_latest_weekly_data() -> Path | None:
    """
    신규 주간 데이터 자동 탐색:
    파일명 패턴: YYYY-MM-DD_YYYY-MM-DD_*.csv
    """
    candidates: list[tuple[datetime, Path]] = []

    for f in DATA_DIR.glob("*.csv"):
        name = f.name
        parts = name.split("_")
        if len(parts) < 3:
            continue

        start_str = parts[0]
        end_str = parts[1]
        try:
            start_date = datetime.fromisoformat(start_str)
            end_date = datetime.fromisoformat(end_str)
        except ValueError:
            continue

        if end_date >= start_date:
            candidates.append((end_date, f))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]


def run_tag_merge():
    """
    [1] 암종(환자태그) 병합
    - 마스터: data/patient_data_merged.csv
    - 태그:   data/환자정보*.csv 중 가장 최근
    - 출력:   data/merged_with_tag.csv
    """
    print("\n[1] 암종(환자태그) 병합 실행")

    merged_file = DATA_DIR / "patient_data_merged.csv"
    if not merged_file.exists():
        print(f"  ❌ 마스터 파일이 없습니다: {merged_file}")
        print("     → data 폴더 안에 patient_data_merged.csv 가 있는지 확인하세요.")
        return

    tag_file = find_latest("환자정보*.csv")
    if tag_file is None:
        print("  ❌ '환자정보*.csv' 패턴에 맞는 태그 파일을 찾지 못했습니다.")
        print("     → data 폴더 안에 환자정보_YYYY-.. 형태 파일이 있는지 확인하세요.")
        return

    output_file = DATA_DIR / "merged_with_tag.csv"

    print(f"  ▶ 마스터 파일: {merged_file}")
    print(f"  ▶ 태그 파일  : {tag_file}")
    print(f"  ▶ 출력 파일  : {output_file}")

    merge_cancer_tag(
        merged_file_path=str(merged_file),
        tag_file_path=str(tag_file),
        output_file_path=str(output_file),
    )


def run_merge_and_summary():
    """
    [2] 마스터 병합 + 환자 요약
    - 신규 데이터: data/에서 YYYY-MM-DD_YYYY-MM-DD_*.csv 중 end_date 최신
    - 마스터:      data/patient_data_merged.csv (없으면 신규 기준으로 생성)
    - 태그 병합본: data/merged_with_tag.csv
    - 출력:        data/오늘날짜_업데이트.csv
    """
    print("\n[2] 마스터 병합 + 환자 요약 실행")

    new_file = find_latest_weekly_data()
    if new_file is None:
        print("  ❌ YYYY-MM-DD_YYYY-MM-DD_*.csv 패턴에 맞는 신규 주간 데이터 파일을 찾지 못했습니다.")
        print("     → 예: 2025-11-10_2025-11-17_랜덤.csv 이런 형식의 파일이 data 폴더에 있어야 합니다.")
        return

    merged_file = DATA_DIR / "patient_data_merged.csv"
    tag_file = DATA_DIR / "merged_with_tag.csv"

    today_str = datetime.today().strftime("%Y%m%d")
    output_file = DATA_DIR / f"{today_str}_업데이트.csv"

    print(f"  ▶ 신규 데이터 : {new_file}")
    print(f"  ▶ 마스터 파일 : {merged_file} (없으면 신규 기준으로 새로 생성 가능)")
    print(f"  ▶ 태그 병합본 : {tag_file} (없으면 환자태그 없이 요약될 수 있음)")
    print(f"  ▶ 출력 파일   : {output_file}")

    update_master_and_build_summary(
        new_file=str(new_file),
        merged_file=str(merged_file),
        tag_file=str(tag_file),
        output_summary_file=str(output_file),
    )


def run_vip_snapshot():
    """
    [3] VIP 최신 스냅샷
    - 업데이트 파일: data/ 에서 가장 최신 *_업데이트.csv
    - 마스터      : data/patient_data_merged.csv
    - 출력        : data/오늘날짜_VIP_최신화.csv
    """
    print("\n[3] VIP 최신 스냅샷 생성")

    update_file = find_latest("*_업데이트.csv")
    if update_file is None:
        print("  ❌ '*_업데이트.csv' 패턴에 맞는 파일을 찾지 못했습니다.")
        print("     → 먼저 [2] 마스터 병합 + 요약을 실행해 업데이트 파일을 만드세요.")
        return

    patient_file = DATA_DIR / "patient_data_merged.csv"
    if not patient_file.exists():
        print(f"  ❌ 마스터 파일이 없습니다: {patient_file}")
        return

    print(f"  ▶ 업데이트 파일: {update_file}")
    print(f"  ▶ 마스터 파일  : {patient_file}")

    build_vip_snapshot(
        update_file=str(update_file),
        patient_file=str(patient_file),
    )


def run_vip_diff():
    """
    [4] VIP 변화 분석
    - data/의 *_VIP_최신화.csv 중 가장 최신 2개로 비교
    - 결과는 항상 data/ 폴더에 YYYYMMDD_VIP_변경내역.csv 로 저장
    """
    print("\n[4] VIP 변화 분석 실행")

    vip_files = sorted(DATA_DIR.glob("*_VIP_최신화.csv"))
    if len(vip_files) < 2:
        print("  ❌ '_VIP_최신화.csv' 패턴에 맞는 파일이 2개 이상 있어야 합니다.")
        print("     → 최소 2주 이상 VIP 스냅샷이 쌓인 후 사용 가능합니다.")
        return

    prev_file, curr_file = vip_files[-2], vip_files[-1]

    print(f"  ▶ 이전 VIP 스냅샷: {prev_file}")
    print(f"  ▶ 현재 VIP 스냅샷: {curr_file}")

    # 1) 비교 결과 DataFrame만 받아옴
    diff_df = build_vip_diff_new(
        prev_file=str(prev_file),
        curr_file=str(curr_file),
    )

    # 2) 저장은 무조건 DATA_DIR 아래에만
    today_str = datetime.today().strftime("%Y%m%d")
    out_path = DATA_DIR / f"{today_str}_VIP_변경내역.csv"

    diff_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[vip_diff] VIP 변경내역 저장: {out_path}")


def run_crm():
    """
    [5] CRM 점수화/분류
    - 기준 파일: data/의 가장 최신 *_업데이트.csv
    - 출력: data/base_name_환자분류_결과.csv
    """
    print("\n[5] CRM 점수화/분류 실행")

    latest_update = find_latest("*_업데이트.csv")
    if latest_update is None:
        print("  ❌ '*_업데이트.csv' 패턴에 맞는 파일을 찾지 못했습니다.")
        print("     → 먼저 [2] 마스터 병합 + 요약을 실행해 업데이트 파일을 만드세요.")
        return

    base_name = latest_update.stem
    print(f"  ▶ 기준 파일(base_name): {base_name} (from {latest_update})")

    run_crm_scoring(
        base_name=base_name,
        input_dir=str(DATA_DIR),
    )


def run_kpi():
    """
    [6] KPI 생성
    - 마스터: data/patient_data_merged.csv
    - 기간  : 기본 2025-01 ~ 2025-12
    - 출력  : data/KPI_시작월_종료월.csv
    """
    print("\n[6] KPI 생성 실행")

    csv_path = DATA_DIR / "patient_data_merged.csv"
    if not csv_path.exists():
        print(f"  ❌ 마스터 파일이 없습니다: {csv_path}")
        print("     → 먼저 [2] 마스터 병합 + 요약을 실행해 마스터를 생성하세요.")
        return

    start_month = "2025-01"
    end_month = "2025-12"
    include_arpu = True
    purpose_as_percent = True

    print(f"  ▶ 마스터 파일 : {csv_path}")
    print(f"  ▶ 분석 기간   : {start_month} ~ {end_month}")
    print(f"  ▶ ARPU 포함   : {include_arpu}")
    print(f"  ▶ 목적 비율%  : {purpose_as_percent}")

    kpi, out_path = build_kpi_prev3(
        csv_path=str(csv_path),
        start_month=start_month,
        end_month=end_month,
        include_arpu=include_arpu,
        purpose_as_percent=purpose_as_percent,
        output_path=None,
    )

    print("\n[KPI 미리보기]")
    try:
        print(kpi.head())
    except Exception:
        pass
    print(f"\nKPI 파일 저장 경로: {out_path}")


def main_menu():
    if not DATA_DIR.exists():
        print(f"⚠ data 폴더가 없습니다. project_root에 'data' 폴더를 만들어 주세요.")
        return

    while True:
        print("\n==============================")
        print(" 환자 데이터 모듈 실행 메뉴")
        print("==============================")
        print(" 1) 암종(환자태그) 병합 (tag_merged.py)")
        print(" 2) 마스터 병합 + 환자 요약 (merge_and_summary.py)")
        print(" 3) VIP 최신 스냅샷 (vip_snapshot.py)")
        print(" 4) VIP 변화 분석 (vip_diff.py)")
        print(" 5) CRM 점수화/분류 (crm_scoring.py)")
        print(" 6) KPI 생성 (kpi_builder.py)")
        print(" 0) 종료")
        choice = input("번호를 선택하세요: ").strip()

        if choice == "1":
            run_tag_merge()
        elif choice == "2":
            run_merge_and_summary()
        elif choice == "3":
            run_vip_snapshot()
        elif choice == "4":
            run_vip_diff()
        elif choice == "5":
            run_crm()
        elif choice == "6":
            run_kpi()
        elif choice == "0":
            print("종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 선택해주세요.")


if __name__ == "__main__":
    main_menu()
