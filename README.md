# CURAEL 환자 데이터 자동화 파이프라인 (GUI + EXE)

> CURAEL 내부 업무용 환자 데이터 자동화 시스템  
> 암종(태그) 병합 → 마스터 최신화 → VIP → CRM → KPI까지  
> 모든 과정을 GUI 기반으로 클릭 한 번에 실행할 수 있는 형태로 개발

---

## 🔍 개요

본 프로젝트는 CURAEL에서 매주 반복되던 환자 데이터 처리 업무를  
**100% 자동화 + GUI 실행 프로그램(EXE)** 형태로 통합한 시스템입니다.

처리되는 주요 업무:

- 암종(태그) 자동 병합  
- 마스터 데이터 최신화  
- VIP 스냅샷 생성  
- VIP 변화 분석  
- CRM 점수화 및 약사님별 대상자 자동 추출  
- KPI 생성  

모든 기능은 **GUI 앱**으로 제공되며,  
**Python 미설치 PC에서도 단독(EXE) 실행**이 가능합니다.

---

## 📁 폴더 구조

curael-pipeline/
│
├─ gui_app.py # GUI 프로그램 메인 파일 (PySide6)
├─ run_modules.py # 콘솔 기반 실행 관리자
├─ requirements.txt
├─ README.md
│
├─ modules/ # 실제 데이터 처리 모듈
│ ├─ tag_merged.py
│ ├─ merge_and_summary.py
│ ├─ vip_snapshot.py
│ ├─ vip_diff.py
│ ├─ crm_scoring.py
│ └─ kpi_builder.py
│
├─ data/ # (업로드 금지) 입력/출력 CSV/XLSX
│ ├─ patient_data_merged.csv
│ ├─ merged_with_tag.csv
│ ├─ *_업데이트.csv
│ └─ ...
│
└─ dist/ # PyInstaller 빌드 결과 (업로드 금지)
└─ CURAEL_Pipeline.exe

yaml
코드 복사

> `.venv/`, `data/`, `dist/`, `build/` 등은 `.gitignore`로 제외됨.

---

## ⚙️ 기능 개요

### **1️⃣ 암종(태그) 병합 (tag_merged.py)**
- 환자 태그 RAW 데이터를 정제  
- 마스터 파일과 자동 병합 → `merged_with_tag.csv` 생성

### **2️⃣ 마스터 최신화 + 요약 생성 (merge_and_summary.py)**
- 최신 주간 RAW 파일 자동 검색  
- 기존 마스터 파일 업데이트  
- 환자 요약 파일 생성 → `YYYYMMDD_업데이트.csv`

### **3️⃣ VIP 스냅샷 생성 (vip_snapshot.py)**
- VIP 조건 자동 적용  
- `YYYYMMDD_VIP_최신화.csv` 생성

### **4️⃣ VIP 변화 분석 (vip_diff.py)**
- “이전 VIP vs 최신 VIP” 비교  
- 신규 진입 / 이탈 환자 분석 → Excel 출력

### **5️⃣ CRM 점수화 및 분류 (crm_scoring.py)**
- 구매 총액/횟수/객단가 기반 자동 가중치 산출  
- Robust Scaling (10~90%)  
- 군별 점수(A1/A2/C1 …) 부여  
- 약사님별 타깃 리스트 3종 자동 생성  
- Excel 서식 자동 적용

### **6️⃣ KPI 생성 (kpi_builder.py)**
- 주간/월간 KPI 자동 집계

---

## 🎨 GUI(App) 기능

GUI는 PySide6 기반으로 제작되었으며:

- 현대적인 화이트톤 UI
- 좌측 기능 버튼 6개
- 우측 실시간 로그창
- 클릭 한 번으로 전체 파이프라인 실행 가능
- 콘솔 없이 단독 GUI 앱으로 작동

GUI 메인 파일:

gui_app.py

yaml
코드 복사

---

## 🚀 개발 모드 실행

```bash
python gui_app.py
📦 EXE 생성 방법 (PyInstaller)
가상환경 활성화 후:

bash
코드 복사
pip install -r requirements.txt
pip install PySide6 pyinstaller
EXE 생성:

bash
코드 복사
pyinstaller --onefile --noconsole gui_app.py
생성된 EXE 위치:

bash
코드 복사
dist/gui_app.exe
배포 폴더 구성 예:

kotlin
코드 복사
CURAEL_Pipeline/
│
├─ CURAEL_Pipeline.exe
└─ data/
→ Python 미설치 PC에서도 즉시 실행 가능

🛠 기술 스택
Python 3.10+

PySide6 (Qt6 GUI)

Pandas / NumPy

Openpyxl

PyInstaller

Pathlib 기반 경로 자동 인식

📄 라이선스
본 프로젝트는 CURAEL 내부 사용을 목적으로 합니다.
무단 배포를 금합니다.
