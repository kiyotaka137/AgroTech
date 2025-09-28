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

        # === Общий горизонтальный сплиттер (3 колонки) ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== Сайдбар =====
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(5, 5, 5, 5)
        sidebar_layout.setSpacing(5)

        btn_empty = QPushButton("E")
        btn_empty.setFixedWidth(30)
        btn_empty.setFixedHeight(30)

        # Кнопки добавляются сверху
        sidebar_layout.addWidget(btn_empty)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)

        # ===== Средний бар (История) =====
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(5, 5, 5, 5)
        history_layout.setSpacing(5)

        history_widget = QWidget()

        # --- Заголовок "История" + кнопка "+"
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        lbl_history = QLabel("История")
        btn_add_history = QPushButton("+")
        btn_add_history.setFixedWidth(25)
        btn_add_history.setFixedHeight(25)

        header_layout.addWidget(lbl_history)
        header_layout.addStretch()
        header_layout.addWidget(btn_add_history)

        # --- Поле поиска + кнопка с иконкой
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(2)

        input_search = QLineEdit()
        input_search.setPlaceholderText("Поиск отчета по имени")

        btn_search = QPushButton()
        btn_search.setIcon(QIcon("../images/search.png"))
        btn_search.setFixedSize(30, 30)

        search_layout.addWidget(input_search)
        search_layout.addWidget(btn_search)

        # --- Список прошлых отчетов
        history_list = QListWidget()
        history_list.addItems(["Отчет 1", "Отчет 2", "Отчет 3"])

        # Компоновка "Истории"
        history_layout.addLayout(header_layout)
        history_layout.addLayout(search_layout)
        history_layout.addWidget(history_list)

        history_widget.setLayout(history_layout)

        # ===== Основное поле (Отчет) =====
        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(5, 5, 5, 5)
        report_layout.setSpacing(5)

        # Вкладки
        tabs = QTabWidget()
        tab_ration = QTextEdit("Здесь содержимое вкладки 'Рацион'")
        tab_report = QTextEdit("Здесь содержимое вкладки 'Отчет'")
        tabs.addTab(tab_ration, "Рацион")
        tabs.addTab(tab_report, "Отчет")

        report_layout.addWidget(tabs)
        report_widget = QWidget()
        report_widget.setLayout(report_layout)

        # Добавляем все три панели в сплиттер
        splitter.addWidget(sidebar_widget)   # сайдбар
        splitter.addWidget(history_widget)   # история 
        splitter.addWidget(report_widget)    # отчёт

        # Пропорции
        splitter.setSizes([60, 280, 1060])

        # === Финальный layout ===
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
