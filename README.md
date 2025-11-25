# CURAEL 환자 데이터 자동화 파이프라인 (GUI + EXE)

> CURAEL 내부 환자 데이터 처리 전체 과정을 자동화한 시스템  
> 암종(태그) → 마스터 최신화 → VIP → CRM 점수화 → KPI 생성까지  
> 모든 단계를 GUI 방식으로 클릭 한 번에 실행 가능

---

## 🔍 개요

본 프로젝트는 CURAEL에서 매주 반복되던 환자 데이터 처리 업무를  
**100% 자동화 + GUI 실행 프로그램(EXE)** 형태로 통합한 시스템입니다.

자동화된 주요 기능:

- 암종(태그) 병합  
- 주간 RAW → 마스터 업데이트  
- VIP 스냅샷 및 변화 분석  
- CRM 점수화 및 약사님별 타깃 리스트 생성  
- KPI 집계 자동화  
- PyInstaller 기반 EXE로 배포 (Python 미설치 PC에서도 실행 가능)

---

## 📁 폴더 구조

```text
curael-pipeline/
│
├─ gui_app.py            # GUI 프로그램 메인 파일 (PySide6)
├─ run_modules.py        # 콘솔 기반 실행 관리자
├─ requirements.txt
├─ README.md
│
├─ modules/              # 모든 데이터 처리 모듈
│    ├─ tag_merged.py
│    ├─ merge_and_summary.py
│    ├─ vip_snapshot.py
│    ├─ vip_diff.py
│    ├─ crm_scoring.py
│    └─ kpi_builder.py
│
├─ data/                 # (업로드 금지) 입력/출력 CSV/XLSX
│    ├─ patient_data_merged.csv
│    ├─ merged_with_tag.csv
│    ├─ *_업데이트.csv
│    └─ ...
│
└─ dist/                 # PyInstaller 빌드 결과 (GitHub 업로드 제외)
     └─ CURAEL_Pipeline.exe
.venv/, data/, dist/, build/ 등은 .gitignore 처리됨.
```


⚙️ 기능 설명
1️⃣ 암종(태그) 병합 – tag_merged.py
환자 태그 RAW 데이터를 정제하고

기존 마스터와 자동 병합

결과 → merged_with_tag.csv

2️⃣ 마스터 최신화 + 요약 – merge_and_summary.py
주간 RAW 파일 자동 탐지

기존 마스터 업데이트

VIP 여부·매출·방문기록·암종 정보 자동 반영

결과 → YYYYMMDD_업데이트.csv

3️⃣ VIP 스냅샷 – vip_snapshot.py
최종 업데이트 파일 기준으로 VIP 자동 추출

결과 → YYYYMMDD_VIP_최신화.csv

4️⃣ VIP 변화 분석 – vip_diff.py
이전/현재 VIP 비교

신규 진입 & 이탈 고객 자동 분석

Excel 보고서 생성

5️⃣ CRM 점수화 – crm_scoring.py
정제 총 매출 / 구매 횟수 / 평균 구매금 기반

자동 가중치 산출 (상관관계 기반)

Robust 10–90% Scaling

A/C/D/E 그룹 점수화 → A1/A2/C1 등급 자동 분류

약사님별 타깃 목적지 3종 자동 생성

Excel 서식 자동 적용

생성 파일 예:

YYMMDD_환자분류_절대65점컷.xlsx

YYMMDD_김훈하_약사님.xlsx

YYMMDD_전정미_약사님.xlsx

YYMMDD_백인보_약사님.xlsx

6️⃣ KPI 생성 – kpi_builder.py
요약 파일 기반 KPI 자동 집계

병원/약국 분석용 KPI 생성

🎨 GUI(App) 기능 – gui_app.py
PySide6 기반의 현대적 GUI 적용:

좌측 기능 버튼 메뉴(①~⑥ 단계)

우측 실행 로그 실시간 출력

클릭 한 번으로 전체 파이프라인 실행

콘솔 없이 GUI만으로 운영 가능

실행 파일 구성:
CURAEL_Pipeline.exe
data/

🚀 개발 모드 실행
python gui_app.py

📦 EXE 생성 방법 (PyInstaller)
가상환경 활성화 후:
pip install -r requirements.txt
pip install PySide6 pyinstaller

EXE 빌드:
pyinstaller --onefile --noconsole gui_app.py

생성 결과:
dist/gui_app.exe

배포 구조 예:
CURAEL_Pipeline/
│
├─ CURAEL_Pipeline.exe
└─ data/
→ Python 미설치 PC에서도 바로 실행 가능

🛠 기술 스택
Python 3.10+

PySide6 (Qt6 GUI)

Pandas / NumPy

Openpyxl

PyInstaller

pathlib 기반 경로 자동 처리

