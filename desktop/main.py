# main.py
import sys
import os
from pathlib import Path
import json
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter, QListWidgetItem,
    QStackedWidget, QDialog, QMessageBox
)
from PyQt6.QtGui import QIcon, QMovie, QFont
from PyQt6.QtCore import (
    Qt, QFileSystemWatcher, QPropertyAnimation, 
    QEasingCurve, QThread, pyqtSignal, QObject, QTimer, QSize
)
from .report_loader import ReportLoader
from .report_list_item import ReportListItem
from .new_report_window import NewReport, RefactorReport
from .report import create_md_webview, write_report_files
from .window_manager import window_manager
from .api_client import APIClient
#from .data_utils import init_llm_in_main_thread


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        #init_llm_in_main_thread(n_ctx=1024, n_batch=128)  # один раз, в GUI-потоке

        self.setWindowTitle("Молочный Анализатор")
        self.setWindowIcon(QIcon("desktop/icons/window_icon.png"))
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
        sidebar_layout.setContentsMargins(5, 40, 0, 0)
        sidebar_layout.setSpacing(10)

        self.btn_add_sidebar = QPushButton()
        self.btn_add_sidebar.setIcon(QIcon("desktop/icons/add_report.png"))
        self.btn_add_sidebar.setIconSize(QtCore.QSize(26, 26))
        self.btn_add_sidebar.setFixedSize(32, 32)
        self.btn_add_sidebar.clicked.connect(self.create_new_report)

        self.btn_load_reports = QPushButton()
        self.btn_load_reports.setIcon(QIcon("desktop/icons/history.png"))
        self.btn_load_reports.setIconSize(QtCore.QSize(26, 26))
        self.btn_load_reports.setFixedSize(32, 32)
        self.btn_load_reports.clicked.connect(self.load_reports_to_list)

        self.btn_admin_keys = QPushButton()
        self.btn_admin_keys.setIcon(QIcon("desktop/icons/admin_keys.png"))
        self.btn_admin_keys.setIconSize(QtCore.QSize(26, 26))
        self.btn_admin_keys.setFixedSize(32, 32)
        self.btn_admin_keys.clicked.connect(self.show_access_key_dialog)

        sidebar_layout.addWidget(self.btn_add_sidebar)
        sidebar_layout.addWidget(self.btn_load_reports)
        sidebar_layout.addWidget(self.btn_admin_keys)
        sidebar_layout.addStretch()

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setFixedWidth(40)
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
        self.history_list.itemClicked.connect(self.display_report)
        
        # Компоновка
        history_layout.addLayout(header_layout)
        history_layout.addLayout(search_layout)
        history_layout.addWidget(self.history_list)

        self.history_widget = QWidget()
        self.history_widget.setLayout(history_layout)
        self.history_widget.setObjectName("historyWidget")
        self.history_widget.setMinimumWidth(0)
        self.history_widget.setMaximumWidth(400)

        self.history_widget.hide()

        # ===== Основное поле (Отчет) =====
        report_layout = QVBoxLayout()
        report_layout.setContentsMargins(0, 0, 0, 0)
        report_layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        self.tabs = tabs  # сохранить ссылку на TabWidget
        tabs.tabBar().setDrawBase(False)  # ← убирает базовую линию под вкладками

        # --- Вкладка Рацион ---
        # Используем QStackedWidget: страница 0 = RationTableWidget, страница 1 = текстовый просмотрщик (fallback)
        self.tab_ration_widget = RefactorReport()

        self.tab_ration_widget.analysis_started.connect(self.show_analysis_tab)
        self.tab_ration_widget.analysis_finished.connect(self.finish_analysis)

        self.refresh_reports_list()

        self.tab_ration_debug = QTextEdit()
        self.tab_ration_debug.setReadOnly(True)

        self.ration_stack = QStackedWidget()
        self.ration_stack.addWidget(self.tab_ration_widget)  # 0
        self.ration_stack.addWidget(self.tab_ration_debug)   # 1

        tabs.addTab(self.ration_stack, "Рацион")

        # --- Вкладка Отчет ---
        self.tab_report = QWidget() # QTextEdit("Здесь содержимое вкладки 'Отчет'")
        tabs.addTab(self.tab_report, "Отчет")

        report_layout.addWidget(tabs)
        report_widget = QWidget()
        report_widget.setLayout(report_layout)

        # ===== Сплиттер =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.history_widget)
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
        """Плавное сворачивание/раскрытие панели истории"""
        # Если уже идёт анимация — прерываем
        if hasattr(self, "anim") and self.anim.state() == self.anim.State.Running:
            return

        start_width = self.history_widget.width()
        end_width = 0 if self.history_widget.isVisible() else 260

        # Если будем показывать — убедимся, что виджет отображается
        if not self.history_widget.isVisible():
            self.history_widget.show()

        # Создаём анимацию по свойству maximumWidth
        self.anim = QPropertyAnimation(self.history_widget, b"maximumWidth")
        self.anim.setDuration(350)  # длительность, мс
        self.anim.setStartValue(start_width)
        self.anim.setEndValue(end_width)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Когда анимация закончится — если свернули, скрываем
        def on_finished():
            if end_width == 0:
                self.history_widget.hide()
                self.history_widget.setMaximumWidth(260)  # вернуть ограничение

        self.anim.finished.connect(on_finished)
        self.anim.start()

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
        dialog = NewReport(self)

        dialog.analysis_started.connect(self.show_analysis_tab)
        dialog.analysis_finished.connect(self.finish_analysis)
        dialog.analysis_err.connect(self._show_error_message)

        dialog.exec()
        self.refresh_reports_list()

    def display_report(self, item):
        """
        Загружает и отображает отчёт. Берём реальный путь файла из UserRole.
        item — QListWidgetItem (передаётся сигналом itemClicked).
        """
        if item is None:
            return

        report_file = item.data(Qt.ItemDataRole.UserRole)

        # Попытка загрузить сначала по полному пути, затем по basename(зачем это надо)
        report_data = self.report_loader.load_report(report_file)
        #print(report_data)

        meta = report_data.get("meta", None)
        ration_array = report_data.get("ration_rows", None)
        nutrient_array = report_data.get("nutrients_rows", None)

        #print("массив с рационом",ration_array) # работает
        self.tab_ration_widget.get_json_path(report_file)
        self.tab_ration_widget.load_from_json(meta, "meta")
        self.tab_ration_widget.load_from_json(ration_array,"left")
        self.tab_ration_widget.load_from_json(nutrient_array,"right")

        self.ration_stack.setCurrentIndex(0)  # показываем виджет-рацион


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
        #report_text = report_data.get("report", "")
        #self.tab_report.setPlainText(report_text or "")
        try:
            jsonname = os.path.splitext(os.path.basename(report_file))[0]
            md_path = "desktop/final_reports/" + jsonname + ".md"
            if not os.path.exists(md_path):
                write_report_files(
                    input_json_path=report_file,
                    out_report_md=md_path,
                    update_json_with_report=True,
                )

            create_md_webview(self.tab_report, md_path)
        except Exception as e:
            print(e) # todo: всплывающую ошибку

    def on_reports_dir_changed(self, path):
        """
        Вызывается QFileSystemWatcher при изменении папки reports.
        Обновляем список с небольшим debounce.
        """
        QtCore.QTimer.singleShot(100, self.refresh_reports_list)
    

    def show_access_key_dialog(self):
        """Открывает окно для ввода ключа доступа и проверяет его"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Проверка доступа")
        dialog.setModal(True)
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("Введите ключ доступа:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        key_input = QLineEdit()
        key_input.setPlaceholderText("Ваш ключ...")
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        key_input.setFixedWidth(220)

        error_label = QLabel("")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        confirm_btn = QPushButton("Подтвердить")

        layout.addWidget(label)
        layout.addWidget(key_input)
        layout.addWidget(error_label)
        layout.addWidget(confirm_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        def check_key():
            entered = key_input.text().strip()
            correct_key = "1234"  # <-- здесь можешь заменить на свой ключ
            if entered == correct_key:
                dialog.accept()
                window_manager.show_admin_window()
                #функкция котора отправляет все новые reports
                send_new_reports()
            else:
                # Выделяем ошибку визуально
                key_input.setStyleSheet("""
                    QLineEdit {
                        border: 1px solid #d32f2f;
                        background-color: #ffeaea;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
                error_label.setText("Неверный ключ доступа")


        confirm_btn.clicked.connect(check_key)

        # Сбрасываем подсветку при новом вводе
        def reset_error():
            key_input.setStyleSheet("")
            error_label.setText("")

        key_input.textChanged.connect(reset_error)

        dialog.exec()

    def show_analysis_tab(self):
        """Добавляет временную вкладку 'Анализ' и показывает гифку"""
        # Прячем существующие вкладки
        self.saved_tabs = []
        for i in reversed(range(self.tabs.count())):
            text = self.tabs.tabText(i)
            widget = self.tabs.widget(i)
            self.saved_tabs.append((text, widget))
            self.tabs.removeTab(i)

        # Создаём вкладку 'Анализ'
        self.analysis_tab = QWidget()
        layout = QVBoxLayout(self.analysis_tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(25)

        # Гифка — уменьшим размер
        gif_label = QLabel()
        movie = QMovie("desktop/icons/loading_trans.gif")
        movie.setScaledSize(QSize(192, 96))  
        gif_label.setMovie(movie)
        movie.start()
        layout.addWidget(gif_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Надпись — крупный и мягкий шрифт
        self.loading_text = QLabel("Нейросети думают 🧠")
        self.loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("Segoe UI", 14, QFont.Weight.Medium)
        self.loading_text.setFont(font)
        self.loading_text.setStyleSheet("""
            color: #1F2937;      /* gray-800 */
            padding-top: 8px;
        """)
        layout.addWidget(self.loading_text)

        # Фразы
        self.loading_phrases = [
            "Нейросети думают 🧠",
            "Коровы жуют траву 🐄",
            "Сенсор анализа травы перегревается 🌿🔥",
            "Молоко почти готово 🥛",
            "Идёт расчёт удоев... 📊",
            "Думаем о будущем сельского хозяйства 🚜"
        ]
        self._phrase_index = 0

        # Таймер для смены фраз
        self.phrase_timer = QTimer(self)
        self.phrase_timer.timeout.connect(self._change_phrase)
        self.phrase_timer.start(2200)

        # Добавляем вкладку
        self.tabs.addTab(self.analysis_tab, "Анализ")
        self.tabs.setCurrentWidget(self.analysis_tab)


    def _change_phrase(self):
        """Меняет текст под гифкой"""
        if not hasattr(self, "loading_phrases") or not self.loading_phrases:
            return
        self._phrase_index = (self._phrase_index + 1) % len(self.loading_phrases)
        self.loading_text.setText(self.loading_phrases[self._phrase_index])

    
    def _show_error_message(self, msg: str):
        mb = QMessageBox()
        mb.setIcon(QMessageBox.Icon.Critical)
        mb.setWindowTitle("Ошибка")
        mb.setText(msg)
        mb.exec()
    

    def finish_analysis(self):
        # Удаляем вкладку анализа, если она есть
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Анализ":
                self.tabs.removeTab(i)
                break

        # Возвращаем остальные
        for text, widget in reversed(self.saved_tabs):
            self.tabs.addTab(widget, text)

        # Возвращаем фокус на вкладку Рацион
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Рацион":
                self.tabs.setCurrentIndex(i)
                break

def send_new_reports():
    """
    Читает все JSON файлы из ./records, объединяет их и отправляет на сервер
    одним запросом через client.add_records().
    """
    client = APIClient("http://localhost:8000")
    records_path = Path("desktop/reports")

    all_records = []


    for file_path in records_path.glob("*.json"):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        
        file_name = file_path.stem  
        if isinstance(data, dict):
            data["name"] = file_name
            all_records.append(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    item["name"] = file_name
                    all_records.append(item)
        

    if not all_records:
        print("Нет данных для отправки.")
        return

    resp = client.add_records(all_records)

    if resp is None:
        print("Ошибка при отправке данных на сервер.")
    else:
        print(f"Успешно отправлено {len(all_records)} записей.")
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Подключаем QSS
    with open("desktop/styles/styles_light.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())