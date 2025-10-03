from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont

class ReportListItem(QWidget):
    def __init__(self, name: str, modified: str):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(0)

        lbl_name = QLabel(name)
        font_name = QFont()
        font_name.setPointSize(11)
        font_name.setBold(True)
        lbl_name.setFont(font_name)

        lbl_date = QLabel(modified)
        font_date = QFont()
        font_date.setPointSize(9)
        lbl_date.setFont(font_date)
        lbl_date.setStyleSheet("color: gray;")

        layout.addWidget(lbl_name)
        layout.addWidget(lbl_date)
        self.setLayout(layout)
