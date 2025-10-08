# main.py
import sys
from pathlib import Path

from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QLabel, QListWidget,
    QTabWidget, QTextEdit, QSplitter, QListWidgetItem,
    QStackedWidget, QDialog, QMessageBox
)
from PyQt6.QtGui import QIcon, QMovie
from PyQt6.QtCore import (
    Qt, QFileSystemWatcher, QPropertyAnimation, 
    QEasingCurve, QThread, pyqtSignal, QObject, QTimer
)

from .report import create_md_webview, write_report_files,create_md_webview_for_Admin
import json
from .report_loader import ReportLoader
from .report_list_item import ReportListItem
from .new_report_window import AdminNewReport
from .api_client import APIClient
from .window_manager import window_manager
class AdminMainWindow(QWidget):

    return_to_main_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.client = APIClient("http://localhost:8000")
        self.setWindowTitle("Шаблон интерфейса")
        self.setGeometry(100, 100, 1400, 800)
        self.report_loader = ReportLoader()
        self.all_reports = []  # для фильтрации

        # Папка с отчетами (меняем в соответствии с твоим текущим расположением)
        #todo: get_all
        self.reports_dir = Path("desktop/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)


        # ===== Сайдбар =====
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(5, 40, 0, 0)
        sidebar_layout.setSpacing(10)

        # self.btn_add_sidebar = QPushButton()
        # self.btn_add_sidebar.setIcon(QIcon("desktop/icons/add_report.png"))
        # self.btn_add_sidebar.setIconSize(QtCore.QSize(26, 26))
        # self.btn_add_sidebar.setFixedSize(32, 32)
        # self.btn_add_sidebar.clicked.connect(self.create_new_report)

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

        self.btn_admin_esc = QPushButton()
        self.btn_admin_esc.setIcon(QIcon("desktop/icons/icons-esc.png"))
        self.btn_admin_esc.setIconSize(QtCore.QSize(26, 26))
        self.btn_admin_esc.setFixedSize(32, 32)
        self.btn_admin_esc.clicked.connect(self.popa)   #сюда вставить выход из админа

        #sidebar_layout.addWidget(self.btn_add_sidebar)
        sidebar_layout.addWidget(self.btn_load_reports)
        sidebar_layout.addWidget(self.btn_admin_keys)
        sidebar_layout.addWidget(self.btn_admin_esc)
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
        
        
        btn_close_history = QPushButton()
        btn_close_history.setIcon(QIcon("desktop/icons/close_history.png"))
        btn_close_history.setIconSize(QtCore.QSize(22, 22))
        btn_close_history.setFixedSize(28, 28)
        btn_close_history.clicked.connect(self.toggle_history)

        header_layout.addWidget(lbl_history)
        header_layout.addStretch()
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
        self.tab_ration_widget = AdminNewReport()
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

        # # ===== Вкладка анализа =====
        # self.tab_analysis = QWidget()
        # analysis_layout = QVBoxLayout(self.tab_analysis)
        # analysis_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # # GIF
        # self.gif_label = QLabel()
        # self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.movie = QMovie("desktop/icons/loading_trans.gif")
        # self.gif_label.setMovie(self.movie)

        # # Надписи
        # self.phrase_label = QLabel("Анализ таблицы моделью...")
        # self.phrase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # analysis_layout.addWidget(self.gif_label)
        # analysis_layout.addWidget(self.phrase_label)

        # # Добавляем вкладку в QTabWidget, но изначально выключаем
        # self.tabs.addTab(self.tab_analysis, "Анализ")
        # self.analysis_index = self.tabs.indexOf(self.tab_analysis)
        # self.tabs.setTabEnabled(self.analysis_index, False)

        # ===== Сплиттер =====
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.history_widget)
        splitter.addWidget(report_widget)
        splitter.setHandleWidth(0)
        splitter.setChildrenCollapsible(False)
        #splitter.setSizes([280, 1060])

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
        end_width = 0 if self.history_widget.isVisible() else 230

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
                self.history_widget.setMaximumWidth(230)  # вернуть ограничение

        self.anim.finished.connect(on_finished)
        self.anim.start()

    def load_reports_to_list(self):
        """Обновляет список отчетов и показывает историю"""
        self.refresh_reports_list()

        self.toggle_history()

    def refresh_reports_list(self):
        """Обновляет содержимое history_list по текущему состоянию папки reports (без смены видимости)."""
        self.history_list.clear()
        names = self.client.get_all_names()
        
        for name in  names:
            self._add_report_to_list(name)

    def _add_report_to_list(self, display_name):
        """
        Добавляет один элемент в QListWidget с заданным отображаемым именем.
        """
        # Создаём виджет и item
        widget = ReportListItem(display_name, "")  # дата оставлена пустой
        item = QListWidgetItem()
        item.setSizeHint(widget.sizeHint())

        # Сохраняем отображаемое имя в UserRole (если нужно для логики приложения)
        item.setData(Qt.ItemDataRole.UserRole, display_name)

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
        dialog = AdminNewReport(self)

        dialog.analysis_started.connect(self.show_analysis_tab)
        dialog.analysis_finished.connect(self.finish_analysis)

        dialog.exec()
        self.refresh_reports_list()

    def display_report(self, item):
        if item is None:
            return
    
        # Получаем имя записи из UserRole
        record_name = item.data(Qt.ItemDataRole.UserRole)
        
        if not record_name:
            return
        
        # Загружаем данные из базы через клиент
        report_data = self.client.get_record_by_name(record_name)
        record = self.client.get_record_by_name(record_name)
        if record and 'data' in record:
            report_data = record['data']  # Берем только содержимое поля data
        else:
            report_data = None

        # Извлекаем массивы данных
        ration_array = report_data.get("ration_rows", None)
        nutrient_array = report_data.get("nutrients_rows", None)
        report_text = report_data.get("report", "")

        # Загружаем данные в виджеты
        self.tab_ration_widget.load_from_json(ration_array, "left")
        self.tab_ration_widget.load_from_json(nutrient_array, "right")
       
        # Показываем виджет-рацион
        self.ration_stack.setCurrentIndex(0)

        # Отображаем текстовый отчет
        create_md_webview_for_Admin(self.tab_report,report_text)
        '''
        """
        Загружает и отображает отчёт. Берём реальный путь файла из UserRole.
        item — QListWidgetItem (передаётся сигналом itemClicked).
        """
        if item is None:
            return
        
        report_file = item.data(Qt.ItemDataRole.UserRole)

        #print(report_file )# путь находится правильно
        #снизу в комменте какой то бред
        
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
        
        # Попытка загрузить сначала по полному пути, затем по basename(зачем это надо)
        report_data = self.report_loader.load_report(report_file)
        #print(report_data)

        ration_array = report_data.get("ration_rows", None)
        nutrient_array = report_data.get("nutrients_rows", None)

        #print("массив с рационом",ration_array) #работает
        self.tab_ration_widget.get_json_path(report_file)
        self.tab_ration_widget.load_from_json(ration_array,"left")
        self.tab_ration_widget.load_from_json(nutrient_array,"right")

        self.ration_stack.setCurrentIndex(0)  # показываем виджет-рацион

        shown = False

        # Попробуем загрузить через специализированный метод рациона
        try:
            if ration_array is not None and hasattr(self.tab_ration_widget, "load_from_json"):
                
                shown = True
        except Exception as e:
            print(f"Ошибка при загрузке рациона через load_from_json: {e}")
            shown = False
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
        report_text = report_data.get("report", "")
        self.tab_report.setPlainText(report_text or "")
    '''
    '''
    def on_reports_dir_changed(self, path):
        """
        Вызывается QFileSystemWatcher при изменении папки reports.
        Обновляем список с небольшим debounce.
        """
        QtCore.QTimer.singleShot(100, self.refresh_reports_list)
    '''

    def show_access_key_dialog(self):
        """Минимальное уведомление о режиме администратора"""
        QMessageBox.information(self, " ", "Вы уже в  режиме администратора")

    # def show_analysis_tab(self):
    #     # Скрываем старые вкладки
    #     self.tabs.setTabEnabled(self.tabs.indexOf(self.ration_stack), False)
    #     self.tabs.setTabEnabled(self.tabs.indexOf(self.tab_report), False)

    #     # Включаем вкладку Анализ и переключаемся на неё
    #     self.tabs.setTabEnabled(self.analysis_index, True)
    #     self.tabs.setCurrentIndex(self.analysis_index)

    #     # Запускаем GIF
    #     self.movie.start()
    '''
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

        # Гифка
        gif_label = QLabel()
        movie = QMovie("desktop/icons/loading_trans.gif")  # путь к гифке
        gif_label.setMovie(movie)
        movie.start()
        layout.addWidget(gif_label)

        # Надпись
        self.loading_text = QLabel("Нейросети думают 🧠")
        self.loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.phrase_timer.start(2000)

        # Добавляем вкладку
        self.tabs.addTab(self.analysis_tab, "Анализ")
        self.tabs.setCurrentWidget(self.analysis_tab)
    '''
    '''
    def _change_phrase(self):
        """Меняет текст под гифкой"""
        if not hasattr(self, "loading_phrases") or not self.loading_phrases:
            return
        self._phrase_index = (self._phrase_index + 1) % len(self.loading_phrases)
        self.loading_text.setText(self.loading_phrases[self._phrase_index])
    '''
    
    '''
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
    '''
    def popa(self):
        window_manager.show_main_window()
def send_new_reports(client: 'APIClient'):
    """
    Читает все JSON файлы из ./records, объединяет их и отправляет на сервер
    одним запросом через client.add_records().
    """
    records_path = Path("../desktop/reports")

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

    window = AdminMainWindow()
    window.show()
    sys.exit(app.exec())