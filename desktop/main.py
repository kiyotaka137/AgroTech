# main.py
import sys
from pathlib import Path

from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter, QListWidgetItem,
    QStackedWidget
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QFileSystemWatcher

from report_loader import ReportLoader
from new_report_window import NewReport
from report_list_item import ReportListItem
from new_report_window import NewReport


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Шаблон интерфейса")
        self.setGeometry(100, 100, 1400, 800)
        self.report_loader = ReportLoader()
        self.all_reports = []  # для фильтрации

        # Папка с отчетами (меняем в соответствии с твоим текущим расположением)
        self.reports_dir = Path("desktop/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Файловый watcher для автоматического обновления списка
        self.fs_watcher = QFileSystemWatcher([str(self.reports_dir)])
        self.fs_watcher.directoryChanged.connect(self.on_reports_dir_changed)

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
        self.input_search.setPlaceholderText("Поиск отчета по имени/отделу/периоду")
        self.input_search.setObjectName("searchInput")
        self.input_search.setFixedHeight(32)
        self.input_search.textChanged.connect(self.filter_reports)

        search_layout.addWidget(self.input_search)
        search_layout.setContentsMargins(0, 6, 0, 0)
        search_layout.setSpacing(0)

        # Список
        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setStyleSheet("""
        QListWidget#historyList {
            background-color: #000;
            border: none;
        }
        QListWidget#historyList::item:selected {
            background-color: #2b2b2b;
        }
        """)
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
        self.tabs = tabs  # сохранить ссылку на TabWidget

        # --- Вкладка Рацион ---
        # Используем QStackedWidget: страница 0 = RationTableWidget, страница 1 = текстовый просмотрщик (fallback)
        self.tab_ration_widget = NewReport()
        self.tab_ration_debug = QTextEdit()
        self.tab_ration_debug.setReadOnly(True)

        self.ration_stack = QStackedWidget()
        self.ration_stack.addWidget(self.tab_ration_widget)  # 0
        self.ration_stack.addWidget(self.tab_ration_debug)   # 1

        tabs.addTab(self.ration_stack, "Рацион")

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

        # Первоначальная загрузка списка
        self.refresh_reports_list()

    def toggle_history(self):
        """Сворачивает/раскрывает панель истории"""
        if self.history_widget.isVisible():
            self.history_widget.hide()
        else:
            self.history_widget.show()

    def load_reports_to_list(self):
        """Обновляет список отчетов и показывает историю"""
        self.refresh_reports_list()
        self.toggle_history()

    def refresh_reports_list(self):
        """Обновляет содержимое history_list по текущему состоянию папки reports (без смены видимости)."""
        self.history_list.clear()
        # Получаем список файлов от loader
        report_files = self.report_loader.list_reports()
        # Сохраняем полный список (строки/пути), пригодится для фильтрации
        self.all_reports = list(report_files)

        # Сортируем по дате модификации (newest first), если есть такая информация
        try:
            def key_fn(p):
                info = self.report_loader.get_report_info(p)
                return info.get("modified", None) or Path(p).stat().st_mtime
            report_files_sorted = sorted(report_files, key=key_fn, reverse=True)
        except Exception:
            report_files_sorted = list(report_files)

        for report_file in report_files_sorted:
            self._add_report_to_list(report_file)

    def _add_report_to_list(self, report_file):
        """
        Добавляет один отчет в QListWidget.
        Отображаемое имя: имя_отдел_период (подчёркивания вместо пробелов).
        В UserRole сохраняется реальный путь/имя файла для надёжной загрузки.
        """
        # Попытаемся получить мета-инфо через loader
        info = {}
        try:
            info = self.report_loader.load_report(report_file) or {}
        except Exception:
            info = {}


        # Берём поля, если они есть
        meta_info = info.get("meta", {})
        name = meta_info.get("name") if isinstance(info, dict) else None # todo: чекнуть почему срабатывает if снизу и нет норм имени
        complex_ = meta_info.get("complex") if isinstance(info, dict) else None
        period = meta_info.get("period") if isinstance(info, dict) else None


        # Если полей нет — парсим имя файла (без расширения)
        if not (name or complex_ or period):
            stem = Path(report_file).stem
            parts = stem.split("_")
            if len(parts) >= 3:
                name, complex_, period = parts[0], parts[1], "_".join(parts[2:])
            elif len(parts) == 2:
                name, complex_ = parts[0], parts[1]
            else:
                name = stem

        def norm(s):
            if s is None:
                return None
            s = str(s).strip()
            if not s:
                return None
            return s.replace(" ", "_")

        parts = [p for p in (norm(name), norm(complex_), norm(period)) if p]
        display_name = "_".join(parts) if parts else Path(report_file).stem

        # форматируем дату
        #last_time_refactor = self.report_loader.get_report_info(report_file)["modified"]
        last_time_refactor = str(meta_info.get("created_at"))[:10] # todo: сделать чтоб время после модификации появлялось


        # Создаём виджет и item
        widget = ReportListItem(display_name, last_time_refactor)
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())

        # Сохраняем реальный путь/имя файла в UserRole
        item.setData(Qt.ItemDataRole.UserRole, str(report_file))

        self.history_list.addItem(item)
        self.history_list.setItemWidget(item, widget)

    def filter_reports(self, text):
        """Фильтрует историю по подстроке (ищем по name, complex, period)."""
        text = (text or "").strip().lower()
        self.history_list.clear()
        if not text:
            # пустой фильтр — показываем все
            for report_file in self.all_reports:
                self._add_report_to_list(report_file)
            return

        for report_file in self.all_reports:
            try:
                info = self.report_loader.get_report_info(report_file) or {}
            except Exception:
                info = {}

            name = str(info.get("name") or "")
            complex_ = str(info.get("complex") or "")
            period = str(info.get("period") or "")
            combined = " ".join([name, complex_, period]).lower()

            # если хотя бы одно совпадение — добавляем
            if text in combined or text in Path(report_file).stem.lower():
                self._add_report_to_list(report_file)

    def create_new_report(self):
        dialog = NewReport()
        dialog.exec()
        # После закрытия диалога — обновим список (на случай, если watcher пропустил момент)
        self.refresh_reports_list()

    def display_report(self, item):
        """
        Загружает и отображает отчёт. Берём реальный путь файла из UserRole.
        item — QListWidgetItem (передаётся сигналом itemClicked).
        """
        if item is None:
            return

        report_file = item.data(Qt.ItemDataRole.UserRole)
        print(report_file)#путь находится правильно
        #снизу в комменте какой то бред
        '''
        if not report_file:
            # fallback: пробуем получить текст из виджета
            widget = self.history_list.itemWidget(item)
            if widget is None:
                return
            try:
                lbl_name = widget.layout().itemAt(0).widget()
                report_name = lbl_name.text()
                report_file = str(self.reports_dir / f"{report_name}.json")
            except Exception:
                return
        '''
        # Попытка загрузить сначала по полному пути, затем по basename(зачем это надо)
        report_data = self.report_loader.load_report(report_file)
        print(report_data)
        # === Рацион ===
        ration_array = report_data.get("rows", None)
        print("массив с рационом",ration_array) #работает
        self.tab_ration_widget.load_from_json(ration_array,"left")
        self.ration_stack.setCurrentIndex(0)  # показываем виджет-рацион
        '''
        shown = False

        # Попробуем загрузить через специализированный метод рациона
        try:
            if ration_array is not None and hasattr(self.tab_ration_widget, "load_from_json"):
                
                shown = True
        except Exception as e:
            print(f"Ошибка при загрузке рациона через load_from_json: {e}")
            shown = False
        '''
        # fallback: показать сырой текст файла (или repr данных)
        raw = None
        try:
            # пытаемся открыть файл как текст
            with open(report_file, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            try:
                raw = str(report_data)
            except Exception:
                raw = "Не удалось прочитать содержимое файла."

            # отображаем в QTextEdit (страница 1)
            self.tab_ration_debug.setPlainText(raw)
            self.ration_stack.setCurrentIndex(1)

        # === Текстовый отчет ===
        report_text = report_data.get("report_text", "")
        self.tab_report.setPlainText(report_text or "")

    def on_reports_dir_changed(self, path):
        """
        Вызывается QFileSystemWatcher при изменении папки reports.
        Обновляем список с небольшим debounce.
        """
        QtCore.QTimer.singleShot(100, self.refresh_reports_list)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Подключаем QSS
    with open("desktop/styles/styles_light.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())