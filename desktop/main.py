import sys
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from report_loader import ReportLoader

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Шаблон интерфейса")
        self.setGeometry(100, 100, 1400, 800)
        self.report_loader = ReportLoader()

        # ===== Сайдбар =====
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 5, 0, 0)
        sidebar_layout.setSpacing(5)

        self.btn_load_reports = QPushButton("И")
        self.btn_load_reports.setFixedSize(30, 30)
        sidebar_layout.addWidget(self.btn_load_reports)
        sidebar_layout.addStretch()
        self.btn_load_reports.clicked.connect(self.load_reports_to_list)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(30)
        sidebar_widget.setObjectName("sidebar")  # для QSS

        # ===== Средний бар (История) =====
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(0,0,0,0)
        history_layout.setSpacing(0)

        # Заголовок
        header_layout = QHBoxLayout()
        lbl_history = QLabel("История")
        lbl_history.setObjectName("headerLabel")

        # Кнопка "Добавить" с иконкой
        btn_add_history = QPushButton()
        btn_add_history.setIcon(QIcon("icons/add_report.png"))
        btn_add_history.setIconSize(QtCore.QSize(20, 20))  # размер иконки
        btn_add_history.setFixedSize(25, 25)

        # Кнопка "Закрыть/назад" с иконкой
        btn_close_history = QPushButton()
        btn_close_history.setIcon(QIcon("icons/close_history.png"))
        btn_close_history.setIconSize(QtCore.QSize(20, 20))
        btn_close_history.setFixedSize(25, 25)
        btn_close_history.clicked.connect(self.toggle_history)

        header_layout.addWidget(lbl_history)
        header_layout.addStretch()
        header_layout.addWidget(btn_add_history)
        header_layout.addWidget(btn_close_history)  # вставляем рядом
        header_layout.setContentsMargins(2,8,2,0)
        header_layout.setSpacing(0)

        # Поиск
        search_layout = QHBoxLayout()
        input_search = QLineEdit()
        input_search.setPlaceholderText("Поиск отчета по имени")
        input_search.setObjectName("searchInput")

        btn_search = QPushButton()
        btn_search.setIcon(QIcon("icons/search.png"))
        btn_search.setFixedSize(30, 30)

        search_layout.addWidget(input_search)
        search_layout.addWidget(btn_search)
        search_layout.setContentsMargins(0,0,2,0)
        search_layout.setSpacing(0)

        # Список
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        #history_list.addItems(["Отчет 1", "Отчет 2", "Отчет 3"])
        

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
        self.history_list.itemClicked.connect(self.display_report)

        # ===== Основное поле (Отчет) =====
        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        tab_ration = QTextEdit("Здесь содержимое вкладки 'Рацион'")
        tab_ration.setContentsMargins(0, 0, 0, 0)
        tab_ration.setViewportMargins(0, 0, 0, 0)

        tab_report = QTextEdit("Здесь содержимое вкладки 'Отчет'")
        tab_report.setContentsMargins(0, 0, 0, 0)
        tab_report.setViewportMargins(0, 0, 0, 0)

        tabs.addTab(tab_ration, "Рацион")
        tabs.addTab(tab_report, "Отчет")

        self.tab_ration = tab_ration
        self.tab_report = tab_report

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
        """Сворачивает истроию отчетов"""
        if self.history_widget.isVisible():
            self.history_widget.hide()
        else:
            self.history_widget.show()

    def load_reports_to_list(self):
        """Считывает все JSON файлы и выводит их в history_list"""
        self.history_list.clear()
        report_files = self.report_loader.list_reports()
        for report_file in report_files:
            self.history_list.addItem(report_file.stem)
        self.toggle_history()

    def display_report(self, item):
        """
        Загружает выбранный отчет и отображает его в вкладках
        """
        report_name = item.text()  # имя файла без .json
        filename = f"{report_name}.json"  # формируем имя файла
        try:
            report_data = self.report_loader.load_report(filename)
        except FileNotFoundError:
            print(f"Файл {filename} не найден")
            return

        # ===== Вкладка "Рацион" =====
        ration_array = report_data.get("ration", [])
        ration_text = ""
        for row in ration_array:
            ration_text += "\t".join(map(str, row)) + "\n"
        self.tab_ration.setPlainText(ration_text)

        # ===== Вкладка "Отчет" =====
        report_text = report_data.get("report_text", "")
        self.tab_report.setPlainText(report_text)




if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Подключаем QSS
    with open("desktop/styles.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
