from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class ReportListItem(QWidget):
    def __init__(self, name: str, modified: str):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 3, 4, 3)  
        layout.setSpacing(3) 

        lbl_name = QLabel(name)
        font_name = QFont()
        font_name.setPointSize(11)
        font_name.setBold(True)
        lbl_name.setFont(font_name)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        lbl_date = QLabel(modified)
        font_date = QFont()
        font_date.setPointSize(9)
        lbl_date.setFont(font_date)
        lbl_date.setStyleSheet("color: gray;")
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(lbl_name)
        layout.addWidget(lbl_date)
        self.setLayout(layout)
