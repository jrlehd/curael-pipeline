# CURAEL 환자 데이터 자동 최신화 파이프라인

이 프로젝트는 주간 환자 데이터를 기반으로 암종/태그 병합, 마스터 데이터 업데이트, VIP 스냅샷 생성, VIP 변동 분석, CRM 점수화, KPI 생성까지의 전체 과정을 자동화한 Python 파이프라인입니다. CURAEL 내부에서 실제로 주 1회 사용하는 워크플로우를 기반으로 구성되었습니다.

---

## 🚀 기능 개요

각 기능은 독립적으로 실행 가능하며, `run_modules.py`에서 번호 선택으로 원하는 기능만 실행할 수 있습니다.

### 1. 암종/태그 병합 (tag_merged.py)
- 환자 기본정보 파일과 암종/태그 정보 파일을 병합하여 마스터 태그 테이블 생성
- 이름 또는 연락처 기준으로 중복 및 누락 태그 처리

### 2. 마스터 병합 + 환자 요약 (merge_and_summary.py)
- 주간 신규 데이터를 기존 마스터와 병합
- 환자별 사용액, 방문/진료 횟수, 최근 방문일 등 요약 정보 생성
- 주간 업데이트 파일 저장

### 3. VIP 최신 스냅샷 생성 (vip_snapshot.py)
- 업데이트 파일을 기반으로 VIP/VVIP 자동 분류
- 최근 방문일 기준으로 기간 필터링 적용
- VIP 스냅샷 파일 생성

### 4. VIP 변화 분석 (vip_diff_new.py)
- 최근 두 개의 VIP 스냅샷을 비교하여 변화 탐지
- 신규 / 제외 / 유지 / 등급 변경 상태 분석

### 5. CRM 점수화 (crm_scoring.py)
- 실질 매출, 방문 횟수, 평균 구매 금액, 최근 구매일 등을 기반으로 CRM 점수 계산
- 점수에 따라 고객군 자동 분류

### 6. KPI 지표 생성 (kpi_builder.py)
- 월별 핵심 지표 생성
- 방문 수, 고유 환자 수, 실질 매출, ARPU, 신규/기존 환자 분포 분석

---

## 📁 폴더 구조

project_root/
│
├─ run_modules.py
├─ README.md
├─ .gitignore
│
├─ modules/
│    ├─ tag_merged.py
│    ├─ merge_and_summary.py
│    ├─ vip_snapshot.py
│    ├─ vip_diff_new.py
│    ├─ crm_scoring.py
│    └─ kpi_builder.py
│
└─ data/        (입력/출력 용도. CSV 파일은 GitHub에 업로드하지 않음)

---

## ⚙️ 실행 방법

### 1) 프로젝트 루트로 이동
cd [프로젝트 경로]

예시:
cd C:\Users\yulba\curael_pipeline

### 2) 실행
python run_modules.py

### 3) 메뉴 화면
1) 암종(환자태그) 병합  
2) 마스터 병합 + 환자 요약  
3) VIP 최신 스냅샷  
4) VIP 변화 분석  
5) CRM 점수화  
6) KPI 생성  

번호를 입력해 원하는 기능을 실행합니다.

---

## 📦 데이터 파일 안내

모든 데이터 파일은 `data/` 폴더 내부에서만 처리됩니다.

### 포함되는 파일 예:
- patient_data_merged.csv
- 환자정보_YYYYMMDD_*.csv
- YYYYMMDD_업데이트.csv
- YYYYMMDD_VIP_최신화.csv
- YYYYMMDD_VIP_변경내역.csv

### GitHub에는 업로드되지 않음
환자 데이터는 개인정보이기 때문에 `.gitignore`로 자동 제외되어 있습니다.

---

## 🛠️ 의존성 (requirements.txt)

pandas>=2.0.0  
python-dateutil>=2.8.2

설치:
pip install -r requirements.txt

---

## 📌 참고 사항

- VIP 변화 분석 기능(4번)은 VIP 스냅샷 파일이 최소 2개 이상 존재해야 실행됩니다.
- 모든 출력 파일은 날짜 기반 파일명으로 자동 생성됩니다. (예: 20251117_업데이트.csv)
- 주간 신규 데이터 파일명은 일정한 규칙(YYYY-MM-DD_YYYY-MM-DD_*)을 따라야 자동 탐색됩니다.
- data 폴더 안에는 CSV 파일만 존재하며, GitHub에는 업로드되지 않습니다.

