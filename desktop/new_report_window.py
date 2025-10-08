# new_report_window.py
import os
import json
import time
import traceback
from datetime import date, datetime
from pathlib import Path 

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QLabel, QAbstractItemView, QComboBox, QFileDialog,
    QHeaderView, QSizePolicy, QProgressBar,QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QMovie, QColor, QFontDatabase
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from PyQt6.QtCore import (Qt, QTimer, QSize, pyqtSignal, QObject, QThread, pyqtSlot)

from desktop.data_utils import parse_excel_ration, parse_pdf_for_tables, predict_from_file
from .report import write_report_files

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
        self.setObjectName("newReportDlg")

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

        self._build_statusbar()  # <- сначала создаём self.status_label
        self._build_main()  # <- потом используем его внутри футера

        # стартовые 5 строк
        for _ in range(5):
            self.add_row_for_left_table()

        QTimer.singleShot(100, self.setup_columns_ratio)
        self.reports_dir = Path("desktop/reports")


    def resizeEvent(self, event):
        """При изменении размера окна пересчитываем столбцы"""
        super().resizeEvent(event)
        QTimer.singleShot(50, self.setup_columns_ratio)
        QTimer.singleShot(0, self._fit_footer_by_one_row)


    def _build_main(self):
        container = QWidget()
        container.setObjectName("container")
        main_layout = QVBoxLayout(container)
        self.setLayout(main_layout)

        '''# Поля ввода
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
        fields_layout.addStretch() '''

        # Поля ввода (одна строка)
        fields_layout = QHBoxLayout()
        name_lbl = QLabel("Имя:");
        name_lbl.setFixedWidth(40)
        self.name_edit = QLineEdit(placeholderText="Введите имя");
        self.name_edit.setFixedWidth(160)

        complex_lbl = QLabel("Комплекс:");
        complex_lbl.setFixedWidth(80)
        self.complex_edit = QLineEdit(placeholderText="Введите комплекс");
        self.complex_edit.setFixedWidth(160)

        period_lbl = QLabel("Дата:");
        period_lbl.setFixedWidth(60)
        self.period_edit = QLineEdit(placeholderText="например: 2025-01");
        self.period_edit.setFixedWidth(120)

        fields_layout.addWidget(name_lbl);
        fields_layout.addWidget(self.name_edit)
        fields_layout.addSpacing(8)
        fields_layout.addWidget(complex_lbl);
        fields_layout.addWidget(self.complex_edit)
        fields_layout.addSpacing(8)
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
        #self.excel_btn.setFixedHeight(btn_h)
        #self.pdf_btn.setFixedHeight(btn_h)

        head_font = self.font()  # шрифт окна; доступен уже сейчас


        for b in (self.excel_btn, self.pdf_btn):
            b.setProperty("pill", True)  # тот же селектор, что для нижних
            b.setFont(head_font)
            #b.setMinimumHeight(34)  # компактнее для верхней панели (можно 32–36)
            #b.setMinimumWidth(92)  # чтобы не схлопывались
            b.setCursor(Qt.CursorShape.PointingHandCursor)

            sh = QGraphicsDropShadowEffect(self)
            sh.setBlurRadius(4)
            sh.setOffset(0, 2)
            sh.setColor(QColor(0, 0, 0, 40))
            b.setGraphicsEffect(sh)

        fields_layout.addSpacing(8)
        fields_layout.addWidget(self.excel_btn)
        fields_layout.addWidget(self.pdf_btn)

        # добавляем строку в разметку ТЕПЕРЬ, после кнопок
        main_layout.addLayout(fields_layout)

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
        
        for _pane in (left_container, right_container):
            _pane.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

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
        '''self.left_table.setStyleSheet("""
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
""")'''
        self.right_table.setShowGrid(True)
        '''self.right_table.setStyleSheet("""
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
""")'''

        # заполняется начальными значениями правая таблица нутриенов
        for r, nutrient in enumerate(ROWSLEFT):
            self.add_row_for_right_table()
            item = QTableWidgetItem(nutrient)
            self.right_table.setItem(r, 0, item)

        for row in range(self.right_table.rowCount()):
            # Первый столбец — фиксированный (нельзя редактировать)
            item_fixed = self.right_table.item(row, 0)
            item_fixed.setFlags(item_fixed.flags() & ~Qt.ItemFlag.ItemIsEditable)


        ''''# добавить/удалить  для левой таблицы
        left_buttons_layout = QHBoxLayout()
        left_buttons_layout.addWidget(self._make_button("Добавить строку", self.add_row_for_left_table))
        left_buttons_layout.addWidget(self._make_button("Удалить выделенные", self.remove_selected_for_left_table))
        left_buttons_layout.addStretch()'''


        #сплитер для разделения таблиц
        # splitter=QSplitter(Qt.Orientation.Horizontal)
        # left_layout.addWidget(self.left_table)
        # right_layout.addWidget(self.right_table)
        
        # #left_layout.addLayout(left_buttons_layout)
        # splitter.addWidget(left_container)
        # splitter.addWidget(right_container)

        # splitter.setHandleWidth(0)           # ручка исчезнет визуально
        # splitter.setChildrenCollapsible(False)  # запрещает "сплющивание" таблиц
         

        # # установка соотношения таблиц
        # splitter.setStretchFactor(0, 6)
        # splitter.setStretchFactor(1, 6)
        # main_layout.addWidget(splitter,1)

        # гарантируем, что верх — сплиттер растягивается, низ — фикс
        #splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Контейнер для таблиц
        tables_container = QWidget()
        tables_layout = QHBoxLayout(tables_container)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(16)  # расстояние между таблицами

        #Блокируем горизонтальную промотку
        self.left_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.left_table.horizontalScrollBar().setDisabled(True)

        self.right_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.right_table.horizontalScrollBar().setDisabled(True)

        # Добавляем таблицы
        tables_layout.addWidget(self.left_table)
        tables_layout.addWidget(self.right_table)

        # Определяем растяжение, чтобы обе таблицы занимали равные части
        tables_layout.setStretch(0, 6)  # левая таблица
        tables_layout.setStretch(1, 6)  # правая таблица

        # Добавляем контейнер с таблицами в основной layout
        main_layout.addWidget(tables_container, 1)

        # Гарантируем, что контейнер растягивается
        tables_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        # распределяем высоту между элементами главного лэйаута:
        # 0 — строка полей, 1 — сплиттер, 2 — футер, 3 — статусбар
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)  # ← основной растягиваемый блок
        main_layout.setStretch(2, 0)
        # статусбар добавляется позже, но на всякий:
        # main_layout.setStretch(3, 0)

        '''# Нижняя полоса слева: "Добавить строку" и "Удалить выделенные"
        footer_left_layout = QHBoxLayout()
        footer_left_layout.setContentsMargins(12, 10, 12, 0)  # вровень с нижней областью
        footer_left_layout.setSpacing(12)

        self.btn_add_row_left = self._make_button("Добавить строку", self.add_row_for_left_table)
        self.btn_remove_row_left = self._make_button("Удалить выделенные", self.remove_selected_for_left_table)

        footer_left_layout.addWidget(self.btn_add_row_left)
        footer_left_layout.addWidget(self.btn_remove_row_left)
        footer_left_layout.addStretch()

        main_layout.addLayout(footer_left_layout) '''

        # единый блок: фон под таблицами + стили заголовков + красивая кнопка
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
            padding: 8px 10px;            /* компактнее, чем у analyze */
            font-weight: 600;
        }
        QPushButton[pill="true"]:enabled:hover  { background: #D1D5DB; } /* gray-300 */
        QPushButton[pill="true"]:enabled:pressed{ background: #9CA3AF; } /* gray-400 */
        QPushButton[pill="true"]:disabled {
            background: #F3F4F6;          /* gray-100 */
            color: #6B7280;               /* gray-500 */
            border-color: #E5E7EB;
        }
        """)

        QTimer.singleShot(0, self.setup_columns_ratio)

        # Кнопка "Анализировать"
        #analyze_layout = QHBoxLayout()
        #analyze_layout.addStretch()
        self.analyze_btn = QPushButton("Анализировать")

        # Крупнее и жирнее только для этой кнопки
        if self._inter_family:
            f = QFont(self._inter_family, 16, QFont.Weight.DemiBold)  # 16px, полужирный
        else:
            f = QFont(self.font().family(), 16, QFont.Weight.DemiBold)  # fallback

        # чуть увеличим кернинг
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 103)
        self.analyze_btn.setFont(f)

        # сделаем кнопку побольше
        self.analyze_btn.setMinimumHeight(48)  # было 36/44 — станет выше
        self.analyze_btn.setMinimumWidth(240)

        self.analyze_btn.setProperty("primary", True)

        # делаем кнопку приятнее по ощущениям
        self.analyze_btn.setObjectName("analyzeBtn")
        self.analyze_btn.setMinimumSize(220, 36)  # адаптивная высота/ширина
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # мягкая тень (работает в Qt через графический эффект)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.analyze_btn.setGraphicsEffect(shadow)

        #self.analyze_btn.setFixedSize(400, 50)
        self.analyze_btn.clicked.connect(self.analyze_clicked)
        #analyze_layout.addWidget(self.analyze_btn)
        #analyze_layout.addStretch()
        #analyze_layout.addStretch()
        #main_layout.addLayout(analyze_layout)

        '''# нижняя полоса: слева кнопки левой таблицы, справа/по центру — уже созданная self.analyze_btn
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(12, 10, 12, 10)
        bottom_layout.setSpacing(12)

        # две кнопки для левой таблицы (переехали вниз)
        self.btn_add_row_left = self._make_button("Добавить строку", self.add_row_for_left_table)
        self.btn_remove_row_left = self._make_button("Удалить выделенные", self.remove_selected_for_left_table)

        bottom_layout.addWidget(self.btn_add_row_left)
        bottom_layout.addWidget(self.btn_remove_row_left)

        bottom_layout.addStretch()

        # НЕ создаём кнопку заново — используем уже существующую self.analyze_btn
        bottom_layout.addWidget(self.analyze_btn)

        bottom_layout.addStretch()

        main_layout.addLayout(bottom_layout)'''

        # 1) Нижняя строка с утилитами слева (атрибут)
        self.bottom_tools_layout = QHBoxLayout()
        self.bottom_tools_layout.setContentsMargins(12, 2, 12, 0)
        self.bottom_tools_layout.setSpacing(10)

        self.btn_add_row_left = self._make_button("Добавить строку", self.add_row_for_left_table)
        self.btn_remove_row_left = self._make_button("Удалить выделенные", self.remove_selected_for_left_table)
        # --- сделать нижние кнопки как "Анализировать" ---
        # тот же шрифт, высота, скругление и тень через то же свойство primary
        same_font = self.analyze_btn.font()
        same_height = self.analyze_btn.minimumHeight()

        for b in (self.btn_add_row_left, self.btn_remove_row_left):
            # такой же “тип” кнопки, на него уже есть стили в QSS:
            #b.setProperty("primary", True)


            # размеры и шрифт подгоняем к analyze_btn
            b.setFont(same_font)
            #b.setMinimumHeight(same_height)  # если хочешь меньше — поставь, например, 44
            b.setMinimumWidth(160)  # можно убрать/изменить по вкусу

            same_font = self.analyze_btn.font()

            for b in (self.btn_add_row_left, self.btn_remove_row_left):
                b.setFont(same_font)
                b.setProperty("pill", True)  # ← будем красить как “пилюлю”
                b.setMinimumHeight(40)  # ← сделать меньше, чем у Analyze (было 48)
                b.setMinimumWidth(180)  # при желании уменьши/увеличь
                b.setCursor(Qt.CursorShape.PointingHandCursor)

                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(20)
                shadow.setOffset(0, 2)
                shadow.setColor(QColor(0, 0, 0, 50))
                b.setGraphicsEffect(shadow)

            # тень как у analyze_btn
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 60))
            b.setGraphicsEffect(shadow)
        # --- / ---

        self.bottom_tools_layout.addWidget(self.btn_add_row_left)
        self.bottom_tools_layout.addWidget(self.btn_remove_row_left)
        self.bottom_tools_layout.addStretch()

        # 2) Отдельная строка — центральная кнопка (атрибут)
        self.bottom_center_layout = QHBoxLayout()
        self.bottom_center_layout.setContentsMargins(12, 0, 12, 2)
        self.bottom_center_layout.setSpacing(0)
        self.bottom_center_layout.addStretch()
        self.bottom_center_layout.addWidget(self.analyze_btn, 0, Qt.AlignmentFlag.AlignCenter)
        self.bottom_center_layout.addStretch()

        # 3) Футер-обёртка
        self.footer = QWidget()
        self.footer.setObjectName("footer")
        self.footer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.footer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(12, 0, 12, 4)
        footer_layout.setSpacing(2)

        footer_layout.addLayout(self.bottom_tools_layout)
        footer_layout.addLayout(self.bottom_center_layout)

        # переносим статус внутрь футера
        self.status_label.setParent(self.footer)
        self.status_label.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(self.status_label)

        main_layout.addWidget(self.footer)

        # первый автоподгон футера
        QTimer.singleShot(0, self._fit_footer_by_one_row)

        '''def _lower_footer_by_one_row_safe():
            try:
                row_h = self.right_table.verticalHeader().defaultSectionSize()

                footer_layout = self.footer.layout()
                m = footer_layout.contentsMargins()
                spacing = footer_layout.spacing()

                # реальные размеры вложенных строк
                tools_h = bottom_tools_layout.sizeHint().height()
                center_h = max(bottom_center_layout.sizeHint().height(),
                               self.analyze_btn.sizeHint().height())

                # минимальная высота, чтобы ничего не обрезалось
                content_min = m.top() + tools_h + spacing + center_h + m.bottom()

                # целим «опустить границу» на высоту одной строки, но не меньше контента
                target_h = max(content_min, content_min - row_h)

                self.footer.setFixedHeight(int(target_h))
            except Exception:
                pass

        QTimer.singleShot(0, _lower_footer_by_one_row_safe)'''

    def _row_px(self) -> int:
        """Реальная высота строки правой таблицы (если нет строк — дефолт секции)."""
        vh = self.right_table.verticalHeader()
        if self.right_table.rowCount() > 0:
            return vh.sectionSize(0)
        return vh.defaultSectionSize()

    def _fit_footer_by_one_row(self):
        """
        Уменьшаем суммарную высоту футера (включая статус) на высоту одной строки правой таблицы,
        но не клипаем кнопку.
        """
        footer_layout = self.footer.layout()
        m = footer_layout.contentsMargins()
        spacing = footer_layout.spacing()

        tools_h = self.bottom_tools_layout.sizeHint().height() if getattr(self, "bottom_tools_layout", None) is not None else 0

        center_layout_h = self.bottom_center_layout.sizeHint().height() if getattr(self, "bottom_center_layout", None) is not None else 0
        analyze_h = self.analyze_btn.sizeHint().height() if getattr(self, "analyze_btn", None) is not None else 0
        center_h = max(center_layout_h, analyze_h)

        status_h = self.status_label.sizeHint().height() if getattr(self, "status_label", None) is not None else 0

        content_min = m.top() + tools_h + spacing + center_h + spacing + status_h + m.bottom()

        # целимся «опустить» на одну строку
        target = max(content_min, content_min - self._row_px())
        self.footer.setFixedHeight(int(target))

    def _make_button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _build_statusbar(self):
        # У QDialog нет statusBar, поэтому добавляем QLabel снизу
        self.status_label = QLabel("Готово")
        #self.layout().addWidget(self.status_label)



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
        columns = COLUMNSRIGHT
        row = table.rowCount()
        table.insertRow(row)

        # ширины пересчитываем по месту
        self.setup_columns_ratio()

        for c, _ in enumerate(columns):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.right_table.setItem(row, c, item)


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

            rows_rationtable, rows_nutrient = parse_excel_ration(path)
            print(rows_nutrient)
            self.filling_left_table_from_file(rows_rationtable)
            self.filling_right_table_from_file(rows_nutrient)


    def choose_pdf_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать PDF файл", "", "PDF files (*.pdf);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

            rows_rationtable, rows_nutrient = parse_pdf_for_tables(path)
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

    def on_text_changed(self, text):
        # Когда текст вводится — возвращаем прежний стиль
        if text.strip():
            self.name_edit.setStyleSheet(self.original_style)

    def analyze_clicked(self):
        text = self.name_edit.text().strip()

        if not text:
            # Если пустое — красная обводка
            self.original_style = self.name_edit.styleSheet()
            self.name_edit.textChanged.connect(self.on_text_changed)
            self.name_edit.setStyleSheet("border: 2px solid #e06c75;")
            return
       

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
                jsonname = os.path.splitext(os.path.basename(file_path))[0]
                md_path = "desktop/final_reports/" + jsonname + ".md"

                write_report_files(
                    input_json_path=file_path,
                    out_report_md=md_path,
                    update_json_with_report=True,
                    copy_images=True  # todo: без картинок для серверной части
                )

            except Exception as e:
                print("ошибка в _finish", e)
                # mb = QMessageBox(self)
                # mb.setIcon(QMessageBox.Icon.Critical)
                # mb.setWindowTitle("Ошибка")
                # mb.setText(f"Проблема с прогоном моделей:\n{str(e)}")
                # mb.exec()
                # self.status_label.setText("Ошибка при сохранении JSON.")
                os.remove(file_path)

            # data["report"] = "\n".join([k + " " + str(v[0]) for k, v in result_acids.items()]) # todo: переделать в норм отчет
            #
            # # Перезаписываем файл с добавленным результатом
            # with open(file_path, "w", encoding="utf-8") as f:
            #     json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            # Используем экземпляр QMessageBox для показа ошибки
            print("ошибка в _finish", e)

            # mb = QMessageBox(self)
            # mb.setIcon(QMessageBox.Icon.Critical)
            # mb.setWindowTitle("Ошибка")
            # mb.setText(f"Не удалось сохранить JSON:\n{str(e)}")
            # mb.exec()
            # self.status_label.setText("Ошибка при сохранении JSON.")

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

    def analyze_clicked(self):
        self.analysis_started.emit()
        self.analyze_btn.setEnabled(False)

        self.worker.moveToThread(self.thread)

        # Подключаем сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Запускаем
        self.thread.start()


    def _finish_analysis(self):
        """Вызывается по окончании 'загрузки' — формируем JSON и сохраняем файл"""
        loading_dialog = self._loading_dialog

        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # работа мл моделей
            try:
                result_acids = predict_from_file(self.json_path)
                jsonname = os.path.splitext(os.path.basename(self.json_path))[0]
                md_path = "desktop/final_reports/" + jsonname + ".md"

                write_report_files(
                    input_json_path=self.json_path,
                    out_report_md=md_path,
                    update_json_with_report=True,
                    copy_images=True  # todo: без картинок для серверной части
                )

            except Exception as e:
                mb = QMessageBox(self)
                mb.setIcon(QMessageBox.Icon.Critical)
                mb.setWindowTitle("Ошибка")
                mb.setText(f"Проблема с прогоном моделей:\n{str(e)}")
                mb.exec()
                self.status_label.setText("Ошибка при сохранении JSON.")
                os.remove(self.json_path)

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


    def get_json_path(self, path):
        self.json_path = path

class AdminNewReport(NewReport):
    """
    Вариант окна, где удалены/скрыты кнопки:
      - Excel, PDF (верхняя панель)
      - Добавить строку, Удалить выделенные (нижняя панель)
      - Анализировать (центральная кнопка)
    Реализовано через наследование: после инициализации базового окна
    скрываем/удаляем виджеты и корректируем footer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        

      
        # Список имен атрибутов-кнопок, которые нужно скрыть/удалить
        btn_names = [
            "excel_btn", "pdf_btn",
            "btn_add_row_left", "btn_remove_row_left",
            "analyze_btn"
        ]

        # Скрываем кнопки, если они существуют
        for name in btn_names:
            w = getattr(self, name, None)
            if w is not None:
                try:
                    w.hide()
                except Exception:
                    pass
                # разорвать связь с layout'ом (если нужно)
                try:
                    w.setParent(None)
                except Exception:
                    pass
                # убрать ссылку чтобы GC мог убрать (по желанию)
                try:
                    delattr(self, name)
                except Exception:
                    # если delattr не работает (например, свойство не найдено) — игнорируем
                    pass

        # Если присутствуют layout'ы нижней панели — очистим их (убираем пустые места)
        try:
            if hasattr(self, "bottom_tools_layout"):
                # извлекаем все элементы и удаляем из layout'а
                l = self.bottom_tools_layout
                for i in reversed(range(l.count())):
                    it = l.takeAt(i)
                    if it:
                        w = it.widget()
                        if w:
                            try:
                                w.setParent(None)
                            except Exception:
                                pass
            if hasattr(self, "bottom_center_layout"):
                l = self.bottom_center_layout
                for i in reversed(range(l.count())):
                    it = l.takeAt(i)
                    if it:
                        w = it.widget()
                        if w:
                            try:
                                w.setParent(None)
                            except Exception:
                                pass
        except Exception:
            pass

        # Оставим только статус в футере — подгоняем высоту
        try:
            # переместим статус (если ещё не перемещён)
            if hasattr(self, "status_label") and self.status_label.parent() is not self.footer:
                self.status_label.setParent(self.footer)
            # починим отступы футера
            if hasattr(self, "footer") and self.footer is not None:
                footer_layout = self.footer.layout()
                if footer_layout is not None:
                    footer_layout.setContentsMargins(12, 4, 12, 4)
                    footer_layout.setSpacing(4)
                    # удалим всё кроме status_label
                    # сначала соберём, что в лэйауте
                    for i in reversed(range(footer_layout.count())):
                        item = footer_layout.itemAt(i)
                        if item:
                            widget = item.widget()
                            # оставим только статус (по объекту сравнения)
                            if widget is not None and widget is not self.status_label:
                                footer_layout.removeWidget(widget)
                                try:
                                    widget.setParent(None)
                                except Exception:
                                    pass
                    # затем добавим статус_label в конец, если нужно
                    if self.status_label.parent() is not self.footer:
                        footer_layout.addWidget(self.status_label)
            # финальная подгонка
            QTimer.singleShot(0, self._fit_footer_by_one_row)
        except Exception:
            pass

        # Если хотите, можно и полностью удалить метод analyze_clicked у экземпляра:
        try:
            if hasattr(self, "analyze_btn") is False:
                # если analyze_btn удалён, то де-факто кнопки нет — но чтобы быть уверенным,
                # можем подменить метод на no-op
                self.analyze_clicked = lambda *a, **k: None
        except Exception:
            pass

        QTimer.singleShot(0,self._remove_name_complex_date_fields)
    def _remove_name_complex_date_fields(self):
            """Безопасно удаляет QLabel и QLineEdit 'Имя', 'Комплекс', 'Дата'."""
            try:
                # найдём layout, где лежат поля и подписи
                fields_layout = None
                if hasattr(self, "name_edit"):
                    parent = self.name_edit.parent()
                    if parent:
                        # ищем QHBoxLayout, где находится name_edit
                        layout = parent.layout()
                        if layout:
                            for i in range(layout.count()):
                                item = layout.itemAt(i)
                                sub = item.layout()
                                if sub and isinstance(sub, QHBoxLayout):
                                    # нашли тот, где поля и QLabel
                                    for j in range(sub.count()):
                                        w = sub.itemAt(j).widget()
                                        if w is self.name_edit:
                                            fields_layout = sub
                                            break
                            if fields_layout is None and isinstance(layout, QHBoxLayout):
                                # fallback — может это и есть fields_layout
                                fields_layout = layout

                if fields_layout is None:
                    return  # не нашли — просто выходим

                # Удаляем из fields_layout все QLabel и QLineEdit с нужным текстом
                for i in reversed(range(fields_layout.count())):
                    item = fields_layout.itemAt(i)
                    w = item.widget()
                    if not w:
                        continue
                    if isinstance(w, QLineEdit):
                        fields_layout.removeWidget(w)
                        w.deleteLater()
                    elif isinstance(w, QLabel) and w.text().strip(":") in ("Имя", "Комплекс", "Дата"):
                        fields_layout.removeWidget(w)
                        w.deleteLater()

            except Exception as e:
                print("Ошибка при удалении полей:", e)


class AnalysisWorker(QObject):
    finished = pyqtSignal(object)   # отдадим результат в GUI
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())
