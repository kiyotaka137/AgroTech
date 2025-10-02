import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Шаблон интерфейса")
        self.setGeometry(100, 100, 1400, 800)

        # ===== Сайдбар =====
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 5, 0, 0)
        sidebar_layout.setSpacing(5)

        btn_empty = QPushButton("E")
        btn_empty.setFixedSize(30, 30)

        sidebar_layout.addWidget(btn_empty)
        sidebar_layout.addStretch()

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(30)   # фиксированная ширина
        sidebar_widget.setStyleSheet("background-color: #1e1e1e;")  # фон для сайдбара

        # ===== Средний бар (История) =====
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(8,8,8,0)
        history_layout.setSpacing(0)

        # Заголовок
        header_layout = QHBoxLayout()
        lbl_history = QLabel("История")
        lbl_history.setStyleSheet("color: white; font-weight: bold;")

        btn_add_history = QPushButton("+")
        btn_add_history.setFixedSize(25, 25)
        btn_add_history.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #333333;
            }
        """)

        header_layout.addWidget(lbl_history)
        header_layout.addStretch()
        header_layout.addWidget(btn_add_history)

        # Поиск
        search_layout = QHBoxLayout()
        input_search = QLineEdit()
        input_search.setPlaceholderText("Поиск отчета по имени")
        input_search.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                padding: 4px;
            }
        """)

        btn_search = QPushButton()
        btn_search.setIcon(QIcon("icons/search.png"))
        btn_search.setFixedSize(30, 30)
        btn_search.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: #333333;
            }
        """)

        search_layout.addWidget(input_search)
        search_layout.addWidget(btn_search)

        # Список
        history_list = QListWidget()
        history_list.addItems(["Отчет 1", "Отчет 2", "Отчет 3"])
        history_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px
            }
            QListWidget::item {
                height: 40px;            
                padding-left: 5px;       
            }
            QListWidget::item:selected {
                background: #333333;
            }
            """)

        # Компоновка
        history_layout.addLayout(header_layout)
        history_layout.addLayout(search_layout)
        history_layout.addWidget(history_list)

        history_widget = QWidget()
        history_widget.setLayout(history_layout)
        history_widget.setStyleSheet("background-color: rgb(21, 21, 21);")

        # ===== Основное поле (Отчет) =====
        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tab_ration = QTextEdit("Здесь содержимое вкладки 'Рацион'")
        tab_report = QTextEdit("Здесь содержимое вкладки 'Отчет'")
        tabs.addTab(tab_ration, "Рацион")
        tabs.addTab(tab_report, "Отчет")

        report_layout.addWidget(tabs)
        report_widget = QWidget()
        report_widget.setLayout(report_layout)

        # ===== Сплиттер для истории и отчета =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(history_widget)
        splitter.addWidget(report_widget)
        splitter.setSizes([280, 1060])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        # === Финальный layout ===
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # сайдбар фиксированный
        main_layout.addWidget(sidebar_widget)

        # сплиттер (история + отчет)
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
