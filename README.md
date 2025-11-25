CURAEL 환자 데이터 자동화 파이프라인 (GUI + EXE)

CURAEL 내부 환자 데이터 업무 전체 자동화
암종 → 마스터 → VIP → CRM → KPI까지
GUI 기반으로 클릭 한 번에 실행할 수 있는 파이프라인

🔍 개요

본 프로젝트는 CURAEL에서 매주 반복되던 환자 데이터 처리 과정을
100% 자동화 + GUI(EXE) 실행 앱으로 통합한 시스템입니다.

자동화된 주요 기능:

암종(태그) 병합

마스터 최신화

VIP 스냅샷 및 변화 분석

CRM 점수화 및 약사님별 대상 고객 자동 추출

KPI 생성

PyInstaller 기반 EXE로 배포 (Python 설치 불필요)

📁 폴더 구조
curael-pipeline/
│
├─ gui_app.py
├─ run_modules.py
├─ requirements.txt
├─ README.md
│
├─ modules/
│    ├─ tag_merged.py
│    ├─ merge_and_summary.py
│    ├─ vip_snapshot.py
│    ├─ vip_diff.py
│    ├─ crm_scoring.py
│    └─ kpi_builder.py
│
├─ data/
│    ├─ patient_data_merged.csv
│    ├─ merged_with_tag.csv
│    ├─ *_업데이트.csv
│    └─ ...
│
└─ dist/
     └─ CURAEL_Pipeline.exe

⚙️ 기능 요약
1) 암종(태그) 병합 — tag_merged.py

RAW 태그 데이터 정제

기존 마스터와 병합 → merged_with_tag.csv 생성

2) 마스터 최신화 및 요약 생성 — merge_and_summary.py

주간 RAW 파일 자동 탐지

마스터 업데이트

최신 요약 생성 → YYYYMMDD_업데이트.csv

3) VIP 스냅샷 — vip_snapshot.py

VIP 조건 자동 적용

YYYYMMDD_VIP_최신화.csv 생성

4) VIP 변화 분석 — vip_diff.py

이전/현재 VIP 비교

신규 진입 / 이탈 고객 분석

5) CRM 점수화 — crm_scoring.py

정제 총 매출 / 구매 횟수 / 평균 구매금 기반 자동 가중치

Robust Scaling(10~90%)

그룹별 점수화(A1/A2/C1 등)

약사님별 타깃 고객 3종 자동 Excel 생성

6) KPI 생성 — kpi_builder.py

요약 파일 기반 KPI 자동 집계

🎨 GUI(App) — gui_app.py

PySide6 기반 GUI:

좌측 기능 버튼 메뉴

우측 실시간 로그창

모든 작업을 클릭 한 번으로 실행

Python 미설치 PC에서도 EXE로 단독 실행

실행 파일 구성 예:

CURAEL_Pipeline.exe
data/

🚀 개발 실행 방법

Python 환경에서 실행:

python gui_app.py

📦 EXE 생성 방법

pip install -r requirements.txt
pip install PySide6 pyinstaller
pyinstaller --onefile --noconsole gui_app.py

EXE 결과물:

dist/gui_app.exe

배포 구성:

CURAEL_Pipeline/
├─ CURAEL_Pipeline.exe
└─ data/

🛠 기술 스택

Python 3.10+

PySide6 (Qt6 GUI)

Pandas / NumPy

Openpyxl

PyInstaller

pathlib
