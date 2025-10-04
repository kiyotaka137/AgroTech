import sys
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter, QListWidgetItem
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from report_loader import ReportLoader
from new_report_window import NewReport
from report_list_item import ReportListItem  # отдельный виджет для элемента списка
from ration_table_widget import RationTableWidget


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Шаблон интерфейса")
        self.setGeometry(100, 100, 1400, 800)
        self.report_loader = ReportLoader()
        self.all_reports = []  # для фильтрации

        # ===== Сайдбар =====
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 5, 0, 0)
        sidebar_layout.setSpacing(5)

        self.btn_load_reports = QPushButton()
        self.btn_load_reports.setIcon(QIcon("desktop/icons/history.png"))
        self.btn_load_reports.setIconSize(QtCore.QSize(26, 26))
        self.btn_load_reports.setFixedSize(32, 32)
        self.btn_load_reports.clicked.connect(self.load_reports_to_list)

        sidebar_layout.addWidget(self.btn_load_reports)
        sidebar_layout.addStretch()

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(32)
        sidebar_widget.setObjectName("sidebar")

        # ===== Средний бар (История) =====
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(0)

        # Заголовок
        header_layout = QHBoxLayout()
        lbl_history = QLabel("История")
        lbl_history.setObjectName("headerLabel")

        btn_add_history = QPushButton()
        btn_add_history.setIcon(QIcon("desktop/icons/add_report.png"))
        btn_add_history.setIconSize(QtCore.QSize(22, 22))
        btn_add_history.setFixedSize(26, 26)
        btn_add_history.clicked.connect(self.create_new_report)

        btn_close_history = QPushButton()
        btn_close_history.setIcon(QIcon("desktop/icons/close_history.png"))
        btn_close_history.setIconSize(QtCore.QSize(22, 22))
        btn_close_history.setFixedSize(28, 28)
        btn_close_history.clicked.connect(self.toggle_history)

        header_layout.addWidget(lbl_history)
        header_layout.addStretch()
        header_layout.addWidget(btn_add_history)
        header_layout.addWidget(btn_close_history)
        header_layout.setContentsMargins(2, 8, 2, 0)
        header_layout.setSpacing(0)

        # Поиск
        search_layout = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Поиск отчета по имени")
        self.input_search.setObjectName("searchInput")
        self.input_search.setFixedHeight(32)
        self.input_search.textChanged.connect(self.filter_reports)  # фильтрация при вводе

        search_layout.addWidget(self.input_search)
        search_layout.setContentsMargins(0, 6, 0, 0)
        search_layout.setSpacing(0)

        # Список
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.itemClicked.connect(self.display_report)

        # Компоновка
        history_layout.addLayout(header_layout)
        history_layout.addLayout(search_layout)
        history_layout.addWidget(self.history_list)

        history_widget = QWidget()
        history_widget.setLayout(history_layout)
        history_widget.setObjectName("historyWidget")
        history_widget.setMinimumWidth(230)
        history_widget.setMaximumWidth(400)

        self.history_widget = history_widget
        self.history_widget.hide()

        # ===== Основное поле (Отчет) =====
        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # --- Вкладка Рацион ---
        self.tab_ration = RationTableWidget()
        tabs.addTab(self.tab_ration, "Рацион")

        # --- Вкладка Отчет ---
        self.tab_report = QTextEdit("Здесь содержимое вкладки 'Отчет'")
        tabs.addTab(self.tab_report, "Отчет")

        report_layout.addWidget(tabs)
        report_widget = QWidget()
        report_widget.setLayout(report_layout)

        # ===== Сплиттер =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(history_widget)
        splitter.addWidget(report_widget)
        splitter.setHandleWidth(0)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([280, 1060])

        # ===== Главный layout =====
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def toggle_history(self):
        """Сворачивает историю отчетов"""
        if self.history_widget.isVisible():
            self.history_widget.hide()
        else:
            self.history_widget.show()

    def load_reports_to_list(self):
        """Считывает все JSON файлы и выводит их в history_list"""
        self.history_list.clear()
        report_files = self.report_loader.list_reports()
        self.all_reports = report_files  # сохраняем полный список для фильтрации

        for report_file in report_files:
            self._add_report_to_list(report_file)

        self.toggle_history()

    def _add_report_to_list(self, report_file):
        """Добавляет один отчет в QListWidget"""
        info = self.report_loader.get_report_info(report_file)
        modified_str = info["modified"].strftime("%Y-%m-%d %H:%M:%S")

        widget = ReportListItem(info["name"], modified_str)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())
        self.history_list.addItem(item)
        self.history_list.setItemWidget(item, widget)

    def filter_reports(self, text):
        """Фильтрует историю по подстроке поиска"""
        self.history_list.clear()
        for report_file in self.all_reports:
            info = self.report_loader.get_report_info(report_file)
            if text.lower() in info["name"].lower():
                self._add_report_to_list(report_file)

    def create_new_report(self):
        dialog = NewReport()
        dialog.exec()

    def display_report(self, item):
        widget = self.history_list.itemWidget(item)
        if widget is None:
            return

        lbl_name = widget.layout().itemAt(0).widget()
        report_name = lbl_name.text()

        filename = f"{report_name}.json"
        try:
            report_data = self.report_loader.load_report(filename)
        except FileNotFoundError:
            print(f"Файл {filename} не найден")
            return

        # === Рацион ===
        ration_array = report_data.get("ration", [])
        self.tab_ration.load_from_json(ration_array)

        # === Текстовый отчет ===
        report_text = report_data.get("report_text", "")
        self.tab_report.setPlainText(report_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Подключаем QSS
    with open("desktop/styles/styles_light.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
