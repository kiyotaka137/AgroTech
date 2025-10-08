# new_report_window.py
import os
import json
import time
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QLabel, QAbstractItemView, QComboBox, QFileDialog,
    QHeaderView, QSizePolicy, QProgressBar,QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QMovie, QColor, QFontDatabase
from PyQt6.QtCore import (Qt, QTimer, QSize, pyqtSignal, QThread, pyqtSignal, QObject)

from desktop.data_utils import parse_excel_ration, parse_pdf_for_tables, predict_from_file

ROWSLEFT = ['K (%)', 'aNDFom фуража (%)', 'СЖ (%)', 'CHO B3 медленная фракция (%)', 'Растворимая клетчатка (%)', 'Крахмал (%)', 'peNDF (%)', 'aNDFom (%)', 'ЧЭЛ 3x NRC (МДжоуль/кг)', 'CHO B3 pdNDF (%)', 'Сахар (ВРУ) (%)', 'НСУ (%)', 'ОЖК (%)', 'НВУ (%)', 'CHO C uNDF (%)', 'СП (%)', 'RD Крахмал 3xУровень 1 (%)']
COLUMNSLEFT = ["Ингредиенты","%СВ"]
COLUMNSRIGHT=["Нутриент","СВ"]


class NewReport(QDialog):
    analysis_started = pyqtSignal()
    analysis_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Прогноз молока по рациону коров")
        self.resize(800, 600)
        try:
            with open("desktop/styles/new_report_window.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception:
            pass
        self.setModal(True)

        self.setStyleSheet(self.styleSheet() + """
        /* === общий фон окна и панелей слева/справа === */
        #newReportDlg, #container, #paneLeft, #paneRight {
            background: #F2F3F5; /* подбери HEX под твой базовый фон */
        }

        /* === фон внутри таблиц (viewport), чтобы пустота не была белой === */
        #newReportDlg QTableWidget, 
        #newReportDlg QTableView {
            background: transparent;   /* само «окно» таблицы прозрачное */
            border: none;
        }
        #newReportDlg QTableWidget::viewport, 
        #newReportDlg QTableView::viewport {
            background: #F2F3F5;       /* реальная заливка внутри таблиц */
        }

        /* === заголовки/угол/выделение (как было) === */
        #newReportDlg QHeaderView::section {
            border: 1px solid lightgray;
            padding: 4px;
            background-color: #f0f0f0;
        }
        #newReportDlg QTableCornerButton::section {
            background-color: #f0f0f0;
        }
        #newReportDlg QTableWidget::item:selected {
            background-color: #e0e0e0;
        }

        /* === убрать белую полосу у ручки сплиттера, если есть === */
        #newReportDlg QSplitter::handle {
            background: transparent;
        }

        /* === PRIMARY-кнопка «Анализировать» === */
        QPushButton[primary="true"] {
            background: #4DA3FF;
            color: #ffffff;
            border: 0px;
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }
        QPushButton[primary="true"]:enabled:hover {
            background: #5BB0FF;
        }
        QPushButton[primary="true"]:enabled:pressed {
            background: #3B8EF0;
        }
        QPushButton[primary="true"]:focus {
            outline: none;
            border: 2px solid rgba(61, 131, 255, 0.8);
        }
        QPushButton[primary="true"]:disabled {
            background: #BFD9FF;
            color: rgba(255,255,255,0.85);
        }
        #footer { background: transparent; }  /* ← ДОБАВЬ ЭТУ СТРОКУ */
        
        #analyzeBtn {
            background: #E5E7EB;          /* gray-200 */
            color: #111827;               /* gray-900 */
            border: 1px solid #D1D5DB;    /* gray-300 */
            border-radius: 12px;
            padding: 12px 28px;
            font-family: "Inter", "Segoe UI", system-ui, sans-serif;
            font-weight: 600;
        }
        #analyzeBtn:enabled:hover  { background: #D1D5DB; }  /* gray-300 */
        #analyzeBtn:enabled:pressed{ background: #9CA3AF; }  /* gray-400 */
        #analyzeBtn:disabled {
            background: #F3F4F6;          /* gray-100 */
            color: #6B7280;               /* gray-500 */
            border-color: #E5E7EB;
        }
                           
        /* Кнопки-пилюли (как #analyzeBtn), но компактнее */
        QPushButton[pill="true"] {
            background: #E5E7EB;          /* gray-200 */
            color: #111827;               /* gray-900 */
            border: 1px solid #D1D5DB;    /* gray-300 */
            border-radius: 12px;
            padding: 8px 20px;            /* компактнее, чем у analyze */
            font-weight: 600;
        }
        QPushButton[pill="true"]:enabled:hover  { background: #D1D5DB; } /* gray-300 */
        QPushButton[pill="true"]:enabled:pressed{ background: #9CA3AF; } /* gray-400 */
        QPushButton[pill="true"]:disabled {
            background: #F3F4F6;          /* gray-100 */
            color: #6B7280;               /* gray-500 */
            border-color: #E5E7EB;
        }
        
        /* Кнопки-пилюли */
        QPushButton[pill="true"] {
            background: #E5E7EB;
            color: #111827;
            border: 1px solid #D1D5DB;
            border-radius: 12px;
            padding: 8px 20px;
            font-weight: 600;
        }
        QPushButton[pill="true"]:enabled:hover  { background: #D1D5DB; }
        QPushButton[pill="true"]:enabled:pressed{ background: #9CA3AF; }
        QPushButton[pill="true"]:disabled {
            background: #F3F4F6;
            color: #6B7280;
            border-color: #E5E7EB;
        }
        
        
        /*/* Убрать нижнюю линию под вкладками */
        QTabBar {
            qproperty-drawBase: 0;   /* отключает рисование базовой линии */
        }
        
        QTabWidget::pane {
            border: none;            /* на всякий случай убираем рамку панели */
        }
        
        /* Если у табов были свои бордеры — тоже уберём */
        QTabBar::tab {
            border: none;
        }

        QTabWidget {
            border: none;
            background: transparent;
        }*/
        """)

        font = QFont("Segoe UI", 10)
        self.setFont(font)

        # ===== Надёжная загрузка Inter независимо от рабочей директории =====
        self._inter_family = None

        self.thread = QThread()
        self.worker = AnalysisWorker(self._finish_analysis)

        def _try_load_inter() -> str | None:
            """Вернёт имя гарнитуры Inter если шрифт удалось подключить, иначе None."""
            here = Path(__file__).resolve().parent  # .../desktop
            candidates = [
                here / "fonts" / "inter-variable.ttf",  # desktop/fonts/inter-variable.ttf
                here.parent / "desktop" / "fonts" / "inter-variable.ttf",  # на случай странных путей
                here / "fonts" / "Inter-VariableFont_slnt,wght.ttf",  # альтернативное имя файла
            ]
            for p in candidates:
                if p.is_file():
                    font_id = QFontDatabase.addApplicationFont(str(p))
                    fams = QFontDatabase.applicationFontFamilies(font_id)
                    if fams:
                        return fams[0]

            # запасной вариант: загрузка из байтов (если путь всё-таки есть, но Qt не любит относительный)
            for p in candidates:
                try:
                    data = p.read_bytes()
                    if data:
                        font_id = QFontDatabase.addApplicationFontFromData(data)
                        fams = QFontDatabase.applicationFontFamilies(font_id)
                        if fams:
                            return fams[0]
                except Exception:
                    pass
            return None

        self._inter_family = _try_load_inter()

        # Пути выбранных файлов
        self.excel_path = None

        # Поля для управления загрузочным диалогом/анимацией
        self._loading_dialog = None
        self._loading_movie = None

        self._build_main()
        self._build_statusbar()

        # стартовые 5 строк
        for _ in range(5):
            self.add_row_for_left_table()

        QTimer.singleShot(100, self.setup_columns_ratio)
        self.reports_dir = Path("desktop/reports")


    def resizeEvent(self, event):
        """При изменении размера окна пересчитываем столбцы"""
        super().resizeEvent(event)
        QTimer.singleShot(50, self.setup_columns_ratio)

    def _build_main(self):
        container = QWidget()
        container.setObjectName("container")
        main_layout = QVBoxLayout(container)
        self.setLayout(main_layout)

        # Поля ввода
        # Поля ввода
        fields_layout = QHBoxLayout()
        name_lbl = QLabel("Имя:")
        name_lbl.setFixedWidth(40)
        self.name_edit = QLineEdit(placeholderText="Введите имя")
        self.name_edit.setFixedWidth(220)

        complex_lbl = QLabel("Комплекс:")
        complex_lbl.setFixedWidth(80)
        self.complex_edit = QLineEdit(placeholderText="Введите комплекс")
        self.complex_edit.setFixedWidth(220)

        period_lbl = QLabel("Дата:")
        period_lbl.setFixedWidth(60)
        self.period_edit = QLineEdit(placeholderText="например: 2025-01")
        self.period_edit.setFixedWidth(160)

        fields_layout.addWidget(name_lbl); fields_layout.addWidget(self.name_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(complex_lbl); fields_layout.addWidget(self.complex_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(period_lbl); fields_layout.addWidget(self.period_edit)
        fields_layout.addStretch()

        # Поля ввода (одна строка)
        fields_layout = QHBoxLayout()
        name_lbl = QLabel("Имя:");
        name_lbl.setFixedWidth(40)
        self.name_edit = QLineEdit(placeholderText="Введите имя");
        self.name_edit.setFixedWidth(220)

        complex_lbl = QLabel("Комплекс:");
        complex_lbl.setFixedWidth(80)
        self.complex_edit = QLineEdit(placeholderText="Введите комплекс");
        self.complex_edit.setFixedWidth(220)

        period_lbl = QLabel("Дата:");
        period_lbl.setFixedWidth(60)
        self.period_edit = QLineEdit(placeholderText="например: 2025-01");
        self.period_edit.setFixedWidth(160)

        fields_layout.addWidget(name_lbl);
        fields_layout.addWidget(self.name_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(complex_lbl);
        fields_layout.addWidget(self.complex_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(period_lbl);
        fields_layout.addWidget(self.period_edit)

        # >>> новое: кнопки в той же строке, прижаты вправо
        fields_layout.addStretch()
        self.excel_btn = QPushButton("Excel");
        self.excel_btn.clicked.connect(self.choose_excel_file)
        self.pdf_btn = QPushButton("PDF");
        self.pdf_btn.clicked.connect(self.choose_pdf_file)

        # чтобы по высоте совпадало с инпутами
        btn_h = max(self.name_edit.sizeHint().height(), 28)
        self.excel_btn.setFixedHeight(btn_h)
        self.pdf_btn.setFixedHeight(btn_h)

        fields_layout.addSpacing(8)
        fields_layout.addWidget(self.excel_btn)
        fields_layout.addWidget(self.pdf_btn)

        # добавляем строку в разметку ТЕПЕРЬ, после кнопок
        main_layout.addLayout(fields_layout)

        #main_layout.addLayout(fields_layout)

        # Кнопки Excel
        ''' files_layout = QHBoxLayout()
        files_layout.addStretch()

        self.excel_btn = QPushButton("Excel"); self.excel_btn.clicked.connect(self.choose_excel_file)
        self.pdf_btn = QPushButton("PDF"); self.pdf_btn.clicked.connect(self.choose_pdf_file)

        files_layout.addWidget(self.excel_btn)
        files_layout.addWidget(self.pdf_btn)

        files_layout.addStretch()
        main_layout.addLayout(files_layout) '''

        #контейнеры чтобб разделять на левую и правую часть
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        #таблица сводный анализ(правая)
        self.right_table = QTableWidget(0,2)
        #self.right_table.setStyleSheet("QTableWidget { border-left: 1px solid #e6e6e6; }")
        self.right_table.setHorizontalHeaderLabels(COLUMNSRIGHT)
        self.right_table.setAlternatingRowColors(True)
        self.right_table.verticalHeader().setVisible(False)
        self.right_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.right_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Таблица ингридиенты( левая)
        self.left_table = QTableWidget(0, 2)
        #self.left_table.setStyleSheet("QTableWidget { border-left: 1px solid #e6e6e6; }")
        self.left_table.setHorizontalHeaderLabels(COLUMNSLEFT)
        self.left_table.setAlternatingRowColors(True)
        self.left_table.verticalHeader().setVisible(False)
        self.left_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # todo: исправить что таблица странно выглядит
        self.left_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Убираем все автоматические настройки размера

        # Fixed режим запрещает пользователю менять размеры, но позволяет программе
        for i in range(2):
            self.left_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self.right_table.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeMode.Fixed)

        #выделяется вся строчка при нажати и текст в ячейке выравнивается по центру
        self.left_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.right_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Стили для таблицы
        self.left_table.setShowGrid(True)
        self.left_table.setStyleSheet("""
    QTableWidget {
        gridline-color: lightgray;
        border: none; 
        outline: none;
    }
    QTableWidget::item {
        border-bottom: 1px solid lightgray;
    }
    QHeaderView::section {
        border: 1px solid lightgray;
        padding: 4px;
        background-color: #f0f0f0;
    }
    QTableWidget::item:selected {
        background-color: #e0e0e0; 
    }
""")
        self.right_table.setShowGrid(True)
        self.right_table.setStyleSheet("""
    QTableWidget {
        gridline-color: lightgray;
        border: none; 
        outline: none;
    }
    QTableWidget::item {
        border-bottom: 1px solid lightgray;
    }
    QHeaderView::section {
        border: 1px solid lightgray;
        padding: 4px;
        background-color: #f0f0f0;
    }
    QTableWidget::item:selected {
        background-color: #e0e0e0; 
    }
""")

        # заполняется начальными значениями правая таблица нутриенов
        for r, nutrient in enumerate(ROWSLEFT):
            self.add_row_for_right_table()
            item = QTableWidgetItem(nutrient)
            self.right_table.setItem(r, 0, item)

        for row in range(self.right_table.rowCount()):
            # Первый столбец — фиксированный (нельзя редактировать)
            item_fixed = self.right_table.item(row, 0)
            item_fixed.setFlags(item_fixed.flags() & ~Qt.ItemFlag.ItemIsEditable)


        # добавить/удалить  для левой таблицы
        left_buttons_layout = QHBoxLayout()
        left_buttons_layout.addWidget(self._make_button("Добавить строку", self.add_row_for_left_table))
        left_buttons_layout.addWidget(self._make_button("Удалить выделенные", self.remove_selected_for_left_table))
        left_buttons_layout.addStretch()


        #сплитер для разделения таблиц
        splitter=QSplitter(Qt.Orientation.Horizontal)
        left_layout.addWidget(self.left_table)
        right_layout.addWidget(self.right_table)
        left_layout.addLayout(left_buttons_layout)
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)

        # установка соотношения таблиц
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter,1)
        QTimer.singleShot(0, self.setup_columns_ratio)

        # Кнопка "Анализировать"
        analyze_layout = QHBoxLayout()
        analyze_layout.addStretch()
        self.analyze_btn = QPushButton("Анализировать")
        self.analyze_btn.setProperty("primary", True)
        self.analyze_btn.setFixedSize(400, 50)
        self.analyze_btn.clicked.connect(self.analyze_clicked)
        analyze_layout.addWidget(self.analyze_btn)
        analyze_layout.addStretch()
        main_layout.addLayout(analyze_layout)

        

    def _make_button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _build_statusbar(self):
        # У QDialog нет statusBar, поэтому добавляем QLabel снизу
        self.status_label = QLabel("Готово")
        self.layout().addWidget(self.status_label)

    def setup_columns_ratio(self):
        """Настройка соотношения столбцов 4:1:1:1:1"""
        if self.left_table.width() == 0:
            QTimer.singleShot(10, self.setup_columns_ratio)
            return

        total_width = self.left_table.width()

        col_width = int(total_width * 1 / 2)

        self.left_table.setColumnWidth(0, col_width)
        self.left_table.setColumnWidth(1,col_width)
        self.right_table.setColumnWidth(0,col_width)
        self.right_table.setColumnWidth(1,col_width)

    def add_row_for_left_table(self):
        table = self.left_table
        columns = COLUMNSLEFT
        
        row = table.rowCount()
        table.insertRow(row)

        # Убеждаемся, что соотношение столбцов правильное
        self.setup_columns_ratio()

        for c, col_name in enumerate(columns):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.left_table.setItem(row, c, item)


    def add_row_for_right_table(self):
        table = self.right_table
        columns=COLUMNSRIGHT
        row = table.rowCount()
        table.insertRow(row)

        # Убеждаемся, что соотношение столбцов правильное
        self.setup_columns_ratio()

        for c, col_name in enumerate(columns):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.left_table.setItem(row, c, item)


    def remove_selected_for_left_table(self):
        table = self.left_table
        selected = table.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            table.removeRow(row)


    def remove_selected_for_right_table(self):
        table=self.right_table
            
        selected = table.selectionModel().selectedRows()
        if not selected:
            return
        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            table.removeRow(row)


    def filling_left_table_from_file(self, rows):
        """
        таблица заполняется из строк спаршенных с пдф/эксель
        """
        self.left_table.setRowCount(len(rows))
        self.left_table.setColumnCount(len(COLUMNSLEFT))

        # лёгкое форматирование чисел
        def fmt(v) -> str:
            if isinstance(v, float):
                # 2 знака после запятой, запятая как десятичный
                return f"{v:.3f}".replace(".", ",")
            return "" if v is None else str(v)

        numeric_cols_idx = set(range(1, len(COLUMNSLEFT)))

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(fmt(value))

                if c in numeric_cols_idx:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                self.left_table.setItem(r, c, item)

    def filling_right_table_from_file(self, rows_dict):
        """
        Заполняет правую колонку значениями из словаря, используя значения левой колонки как ключи
        """
        # Проходим по всем строкам таблицы
        for row in range(self.right_table.rowCount()):
            # Получаем значение из левой колонки (ключ)
            key_item = self.right_table.item(row, 0)

            if key_item is not None:
                key_text = " ".join(key_item.text().split(" ")[:-1])

                # Ищем соответствующее значение в словаре
                value = rows_dict.get(key_text)  # Используем get чтобы избежать KeyError

                # Создаем или получаем элемент для правой колонки
                value_item = self.right_table.item(row, 1)
                if value_item is None:
                    value_item = QTableWidgetItem()
                    self.right_table.setItem(row, 1, value_item)

                # Форматируем и устанавливаем значение
                def fmt(v) -> str:
                    if isinstance(v, float):
                        return f"{v:.3f}".replace(".", ",")
                    return "" if v is None else str(v)

                value_item.setText(fmt(value))

                # Устанавливаем выравнивание и флаги
                # value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                # value_item.setFlags(value_item.flags() | Qt.ItemFlag.ItemIsEditable)


    def choose_excel_file(self):  # todo: после того как будет переделанна функция парсинга пофиксить для двух таблиц
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Excel/CSV", "", "Excel/CSV files (*.xlsx *.xls *.csv);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

            rows = parse_excel_ration(path)
            self.filling_left_table_from_file(rows)


    def choose_pdf_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать PDF файл", "", "PDF files (*.pdf);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

            rows_rationtable, rows_nutrient = parse_pdf_for_tables(path)
            print(rows_nutrient)
            self.filling_left_table_from_file(rows_rationtable)
            self.filling_right_table_from_file(rows_nutrient)


    def _collect_table_data(self, table):
        """Собираем данные из таблицы в список словарей"""
        if table == self.left_table:
            cols = COLUMNSLEFT
        else:
            cols = COLUMNSRIGHT

        rows = []
        for r in range(table.rowCount()):
            row_data = {}
            empty_row = True
            for c, col_name in enumerate(cols):
                item = table.item(r, c)
                text = item.text() if item is not None else ""
                if text.strip():
                    empty_row = False
                row_data[col_name] = text

            if not empty_row:
                rows.append(row_data)

        return rows


    # def analyze_clicked(self):
    #     """
    #     При нажатии: показываем модальное окно загрузки (имитация) 5 секунд,
    #     затем собираем таблицу в JSON и сохраняем файл в папке reports.
    #     """
    #     # Отключаем кнопку чтобы избежать повторных нажатий
    #     self.analyze_btn.setEnabled(False)

    #     # --- Создаём простое модальное окно загрузки с GIF ---
    #     loading = QDialog(self)
    #     loading.setWindowTitle("Анализ — загрузка")
    #     loading.setModal(True)
    #     loading.setWindowModality(Qt.WindowModality.ApplicationModal)
    #     loading.resize(360, 180)

    #     layout = QVBoxLayout(loading)
    #     layout.setContentsMargins(12, 12, 12, 12)
    #     layout.setSpacing(8)

    #     # Путь к GIF — пробуем несколько мест (корректируй по своему проекту)
    #     gif_path = "cow.gif"
    #     movie = None
    #     try:
    #         movie = QMovie(str(gif_path))
    #     except Exception:
    #         movie = None

    #     gif_label = QLabel()
    #     gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    #     if movie is not None and movie.isValid():
    #         # При желании можно задать размер: movie.setScaledSize(QSize(96,96))
    #         # movie.setScaledSize(QSize(96, 96))
    #         gif_label.setMovie(movie)
    #         movie.start()
    #         # Сохраним в атрибуты, чтобы остановить позже
    #         self._loading_movie = movie
    #     else:
    #         gif_label.setText("Загрузка...\n(анимация недоступна)")
    #         gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    #     layout.addWidget(gif_label)

    #     # Текст под GIF
    #     lbl = QLabel("Анализ таблицы моделью...\n(имитация загрузки 5 секунд)")
    #     lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #     layout.addWidget(lbl)

    #     # Прогресс-бар только для UI (без реальной работы)
    #     progress = QProgressBar()
    #     progress.setRange(0, 0)  # бесконечный индикатор
    #     layout.addWidget(progress)

    #     # Покажем диалог и сохраним ссылку, чтобы закрыть позже
    #     loading.show()
    #     self._loading_dialog = loading

    #     # 5 секунд "пустой" работы — placeholder
    #     #QTimer.singleShot(5000, lambda: self._finish_analysis())

    # def analyze_clicked(self):
    #     # Сигнал — анализ начался
    #     self.analysis_started.emit()
    #     # Отключаем кнопку
    #     self.analyze_btn.setEnabled(False)
    #     self.close()
    #     QTimer.singleShot(100, lambda: self._finish_analysis())
    #     #self._finish_analysis()

    def analyze_clicked(self):
        self.analysis_started.emit()
        self.analyze_btn.setEnabled(False)
        self.close()
        
        self.worker.moveToThread(self.thread)

        # Подключаем сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Запускаем
        self.thread.start()

    def _analysis_error(self, msg):
        QMessageBox.critical(self, "Ошибка", f"Проблема с анализом:\n{msg}")
        self.analyze_btn.setEnabled(True)
        self.analysis_finished.emit()
              

    def _finish_analysis(self):
        """Вызывается по окончании 'загрузки' — формируем JSON и сохраняем файл"""
        loading_dialog = self._loading_dialog

        try:
            data = {
                "meta": {
                    "name": self.name_edit.text(),
                    "complex": self.complex_edit.text(),
                    "period": self.period_edit.text(),
                    "excel": self.excel_path or None,
                    "created_at": datetime.now().isoformat()
                },
                "ration_rows": self._collect_table_data(self.left_table),
                "nutrients_rows": self._collect_table_data(self.right_table)
            }

            # Формируем имя файла: имя_дата_время.json
            safe_name = self.name_edit.text().strip() or "report"  # todo: имя Unnamed если без имени
            # очищаем пробелы и запрещённые символы простым способом
            safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in ("-", "_")).strip() or "report"
            filename = f"{safe_name}_{date.today().isoformat()}_{int(time.time())}.json"
            file_path = self.reports_dir / filename

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # работа мл моделей
            try:
                result_acids = predict_from_file(file_path)
                data["result_acids"] = {
                    k: float(v[0])
                    for k, v in result_acids.items()
                }
            except Exception as e:
                mb = QMessageBox(self)
                mb.setIcon(QMessageBox.Icon.Critical)
                mb.setWindowTitle("Ошибка")
                mb.setText(f"Проблема с прогоном моделей:\n{str(e)}")
                mb.exec()
                self.status_label.setText("Ошибка при сохранении JSON.")
                os.remove(file_path)

            data["report"] = "\n".join([k + " " + str(v[0]) for k, v in result_acids.items()]) # todo: переделать в норм отчет

            # Перезаписываем файл с добавленным результатом
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


        except Exception as e:
            # Используем экземпляр QMessageBox для показа ошибки
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Icon.Critical)
            mb.setWindowTitle("Ошибка")
            mb.setText(f"Не удалось сохранить JSON:\n{str(e)}")
            mb.exec()
            self.status_label.setText("Ошибка при сохранении JSON.")

        finally:
            # Остановим анимацию, если была
            try:
                if getattr(self, "_loading_movie", None) is not None:
                    try:
                        self._loading_movie.stop()
                    except Exception:
                        pass
                    self._loading_movie = None
            except Exception:
                pass

            # Закрываем окно загрузки и включаем кнопку
            try:
                if loading_dialog is not None:
                    loading_dialog.close()
            except Exception:
                pass
            self.analyze_btn.setEnabled(True)
            self._loading_dialog = None
            self.analysis_finished.emit()
            #self.close()


    # === JSON API ===
    def load_from_json(self, data, type_of_table):
        """Заполняет таблицу из массива JSON"""
        '''
        if type_of_table=="left":
            self.left_table.setRowCount(0)
            for row_data in ration_data:
                self.add_row_for_left_table()
                row = self.left_table.rowCount() - 1
                for c in range(2):
                    value = row_data[c] #if c < len(row_data) else ""
                    item = self.left_table.item(row, c)
                    if item:
                        item.setText(str(value))
            self.status_label.setText(f"Загружено {len(ration_data)} строк")
            # Пересчитываем размеры после загрузки данных
            QTimer.singleShot(0, self.setup_columns_ratio)
        '''

        if type_of_table == "left":
            self.left_table.setRowCount(0)  # Очищаем таблицу
    
            for row_data in data:
                row_position = self.left_table.rowCount()
                self.left_table.insertRow(row_position)  # Добавляем новую строку

                # Первая колонка: "Ингредиенты"
                ingredient_value = row_data.get("Ингредиенты", "")
                ingredient_item = QTableWidgetItem(str(ingredient_value))
                self.left_table.setItem(row_position, 0, ingredient_item)

                sv_value = row_data.get("%СВ", "")
                sv_item = QTableWidgetItem(str(sv_value))
                self.left_table.setItem(row_position, 1, sv_item)

            self.status_label.setText(f"Загружено {len(data)} строк")
            QTimer.singleShot(0, self.setup_columns_ratio)

        if type_of_table == "right":
            nutrients = {nutrient["Нутриент"]: nutrient["СВ"] for nutrient in data}

            for row in range(self.right_table.rowCount()):
                # Получаем значение из левой колонки (ключ)
                key_item = self.right_table.item(row, 0)


                if key_item is not None:
                    #key_text = " ".join(key_item.text().split(" ")[:-1])
                    key_text = key_item.text()

                    # Ищем соответствующее значение в словаре
                    value = nutrients.get(key_text)  # Используем get чтобы избежать KeyError
                    print(key_text, value)
                    # Создаем или получаем элемент для правой колонки
                    value_item = self.right_table.item(row, 1)
                    if value_item is None:
                        value_item = QTableWidgetItem()
                        self.right_table.setItem(row, 1, value_item)

                    value_item.setText(value)

    def to_json(self):
        """Возвращает содержимое таблицы как список списков"""
        data = []
        for r in range(self.table.rowCount()):
            row = []
            for c in range(2):
                item = self.table.item(r, c)
                row.append(item.text() if item else "")
            data.append(row)
        return data


class RefactorReport(NewReport):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.json_path = None


    def _finish_analysis(self):
        """Вызывается по окончании 'загрузки' — формируем JSON и сохраняем файл"""
        loading_dialog = self._loading_dialog

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)


            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # работа мл моделей
            try:
                result_acids = predict_from_file(self.json_path)
                data["result_acids"] = {
                    k: float(v[0])
                    for k, v in result_acids.items()
                }
            except Exception as e:
                mb = QMessageBox(self)
                mb.setIcon(QMessageBox.Icon.Critical)
                mb.setWindowTitle("Ошибка")
                mb.setText(f"Проблема с прогоном моделей:\n{str(e)}")
                mb.exec()
                self.status_label.setText("Ошибка при сохранении JSON.")


            data["report"] = "\n".join([k + " " + str(v[0]) for k, v in result_acids.items()]) # todo: переделать в норм отчет

            # Перезаписываем файл с добавленным результатом
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)


        except Exception as e:
            # Используем экземпляр QMessageBox для показа ошибки
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Icon.Critical)
            mb.setWindowTitle("Ошибка")
            mb.setText(f"Не удалось сохранить JSON:\n{str(e)}")
            mb.exec()
            self.status_label.setText("Ошибка при сохранении JSON.")

        finally:
            # Остановим анимацию, если была
            try:
                if getattr(self, "_loading_movie", None) is not None:
                    try:
                        self._loading_movie.stop()
                    except Exception:
                        pass
                    self._loading_movie = None
            except Exception:
                pass

            # Закрываем окно загрузки и включаем кнопку
            try:
                if loading_dialog is not None:
                    loading_dialog.close()
            except Exception:
                pass
            self.analyze_btn.setEnabled(True)
            self._loading_dialog = None

    def get_json_path(self, path):
        self.json_path = path

class AnalysisWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self):
        try:
            self.func()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))