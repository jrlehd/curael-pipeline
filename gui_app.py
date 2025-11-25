# gui_app.py
from __future__ import annotations

import sys
import io
import contextlib
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

# 🔹 기존 콘솔용 모듈 재사용
from run_modules import (
    run_tag_merge,
    run_merge_and_summary,
    run_vip_snapshot,
    run_vip_diff,
    run_crm,
    run_kpi,
    DATA_DIR,
)


def run_with_log(func):
    """
    기존 콘솔 출력(print)을 모두 캡처해서 문자열로 돌려주는 헬퍼.
    GUI에서 버튼 클릭 시 이걸 통해 로그를 가져와서 QTextEdit에 넣어줌.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            func()
        except Exception as e:
            print("\n[오류 감지]")
            print(repr(e))
    return buf.getvalue()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CURAEL 환자 데이터 파이프라인")
        self.setMinimumSize(900, 600)
        self.setup_ui()
        self.apply_style()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ===== 좌측: 메뉴 영역 =====
        left = QVBoxLayout()
        left.setSpacing(15)

        title = QLabel("CURAEL Pipeline")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel("주간 환자 데이터 자동 최신화 · VIP · CRM · KPI")
        subtitle.setStyleSheet("color: #666; font-size: 12px;")

        left.addWidget(title)
        left.addWidget(subtitle)

        # 구분선
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        left.addWidget(sep)

        # 버튼들
        btn_tag = QPushButton("① 암종(태그) 병합")
        btn_merge = QPushButton("② 마스터 병합 + 환자 요약")
        btn_vip_snap = QPushButton("③ VIP 최신 스냅샷")
        btn_vip_diff = QPushButton("④ VIP 변화 분석")
        btn_crm = QPushButton("⑤ CRM 점수화 / 분류")
        btn_kpi = QPushButton("⑥ KPI 생성")

        for b in [btn_tag, btn_merge, btn_vip_snap, btn_vip_diff, btn_crm, btn_kpi]:
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumHeight(40)
            left.addWidget(b)

        left.addStretch(1)

        # data 폴더 안내
        data_label = QLabel(f"데이터 폴더: {DATA_DIR}")
        data_label.setStyleSheet("color: #999; font-size: 11px;")
        left.addWidget(data_label)

        main_layout.addLayout(left, 3)  # 좌측 영역 비율

        # ===== 우측: 로그 영역 =====
        right = QVBoxLayout()
        right.setSpacing(10)

        log_title = QLabel("실행 로그")
        log_title.setStyleSheet("font-size: 16px; font-weight: 600;")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(
            """
            QTextEdit {
                background-color: #111212;
                color: #e4e4e4;
                font-family: Consolas, 'Fira Code', monospace;
                font-size: 12px;
                border-radius: 10px;
                padding: 10px;
            }
            """
        )

        right.addWidget(log_title)
        right.addWidget(self.log, 1)

        main_layout.addLayout(right, 5)  # 우측 영역 비율

        # ===== 버튼 시그널 연결 =====
        btn_tag.clicked.connect(self.handle_tag_merge)
        btn_merge.clicked.connect(self.handle_merge_and_summary)
        btn_vip_snap.clicked.connect(self.handle_vip_snapshot)
        btn_vip_diff.clicked.connect(self.handle_vip_diff)
        btn_crm.clicked.connect(self.handle_crm)
        btn_kpi.clicked.connect(self.handle_kpi)

    def apply_style(self):
        # 전체 윈도우 스타일 (라이트톤 + 둥근 버튼)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #f5f7fb;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dde2ec;
                border-radius: 10px;
                padding: 8px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e6f0ff;
                border-color: #b4c8ff;
            }
            QPushButton:pressed {
                background-color: #d2e0ff;
            }
            """
        )

    # ===== 로그 출력 헬퍼 =====
    def append_log(self, text: str):
        """
        로그창에 텍스트 추가 + 스크롤을 항상 맨 아래로 이동.
        여기서 QTextCursor.End를 제대로 사용하도록 수정.
        """
        if not text:
            return
        self.log.append(text)
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    def run_step(self, label: str, func):
        self.append_log(f"\n▶ {label} 실행 시작...")
        QApplication.processEvents()  # UI 갱신

        # 실제 처리 로직 실행 + 콘솔 로그 캡처
        log_text = run_with_log(func)
        if log_text.strip():
            self.append_log(log_text)

        self.append_log(f"▶ {label} 실행 완료\n" + ("─" * 40))

    # ===== 각 버튼 핸들러 =====
    def handle_tag_merge(self):
        self.run_step("① 암종(태그) 병합", run_tag_merge)

    def handle_merge_and_summary(self):
        self.run_step("② 마스터 병합 + 환자 요약", run_merge_and_summary)

    def handle_vip_snapshot(self):
        self.run_step("③ VIP 최신 스냅샷", run_vip_snapshot)

    def handle_vip_diff(self):
        self.run_step("④ VIP 변화 분석", run_vip_diff)

    def handle_crm(self):
        self.run_step("⑤ CRM 점수화 / 분류", run_crm)

    def handle_kpi(self):
        self.run_step("⑥ KPI 생성", run_kpi)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
