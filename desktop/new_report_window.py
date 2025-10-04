# new_report_window.py
import sys
from datetime import date
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QLabel, QStatusBar, QAbstractItemView, QComboBox, QFileDialog
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

# --- Настройки столбцов ---
COLUMNS = [
    "Дата", "ID коровы", "Ингредиенты", "СВ (%)", "%ГП",
    "кгСВ", "кг%ГП%", "СВ ₽/Тонна"
]

FEATURE_ORDER = ["СВ (%)", "%ГП", "кгСВ", "кг%ГП%", "СВ ₽/Тонна"]

INGREDIENT_TYPES = [
    "Сено", "Комбикорм", "Силос", "Сенаж",
    "Концентрат", "Шрот", "Витамины/Минералы",
    "Комбинация", "Другое"
]

class NewReport(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Прогноз молока по рациону коров (PyQt6)")
        self.resize(800, 600)
        with open("desktop/styles/new_report_window.qss", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        self.setModal(True)  
        
        font = QFont("Segoe UI", 10)
        self.setFont(font)

        # Пути выбранных файлов
        self.excel_path = None
        self.pdf_path = None

        self._build_main()
        self._build_statusbar()

        # стартовая строка-пример
        self.add_row(default=True)

    def _build_main(self):
        container = QWidget()
        container.setObjectName("container")
        main_layout = QVBoxLayout(container)
        self.setLayout(main_layout)

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

        period_lbl = QLabel("Период:")
        period_lbl.setFixedWidth(60)
        self.period_edit = QLineEdit(placeholderText="например: 2025-01")
        self.period_edit.setFixedWidth(160)

        fields_layout.addWidget(name_lbl); fields_layout.addWidget(self.name_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(complex_lbl); fields_layout.addWidget(self.complex_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(period_lbl); fields_layout.addWidget(self.period_edit)
        fields_layout.addStretch()
        main_layout.addLayout(fields_layout)

        # Кнопки Excel / PDF
        files_layout = QHBoxLayout()
        files_layout.addStretch()
        self.excel_btn = QPushButton("Excel"); self.excel_btn.clicked.connect(self.choose_excel_file)
        self.pdf_btn = QPushButton("PDF"); self.pdf_btn.clicked.connect(self.choose_pdf_file)
        files_layout.addWidget(self.excel_btn); files_layout.addSpacing(10); files_layout.addWidget(self.pdf_btn)
        files_layout.addStretch()
        main_layout.addLayout(files_layout)

        # Таблица
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.table, 1)

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

        # Кнопки Добавить / Удалить
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self._make_button("Добавить строку", self.add_row))
        bottom_layout.addWidget(self._make_button("Удалить выделенные", self.remove_selected))
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

    def _make_button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _build_statusbar(self):
        # У QDialog нет statusBar, поэтому добавляем QLabel снизу
        self.status_label = QLabel("Готово")
        self.layout().addWidget(self.status_label)

    def _make_ingredient_combobox(self, selected_text=None):
        cb = QComboBox()
        cb.addItems(INGREDIENT_TYPES)
        if selected_text and selected_text in INGREDIENT_TYPES:
            cb.setCurrentIndex(INGREDIENT_TYPES.index(selected_text))
        return cb

    def add_row(self, default=False):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c, col in enumerate(COLUMNS):
            if col == "Ингредиенты":
                self.table.setCellWidget(r, c, self._make_ingredient_combobox())
            else:
                item = QTableWidgetItem("")
                if col in FEATURE_ORDER:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, item)

        if default:
            today = date.today().isoformat()
            self.table.item(r, 0).setText(today)
            self.table.item(r, 1).setText("001")
            cb = self.table.cellWidget(r, 2)
            cb.setCurrentIndex(INGREDIENT_TYPES.index("Комбинация"))
            for key, val in [("СВ (%)", "88.0"), ("%ГП", "14.5"),
                             ("кгСВ", "6.8"), ("кг%ГП%", "0.99"),
                             ("СВ ₽/Тонна", "20000")]:
                self.table.item(r, COLUMNS.index(key)).setText(val)

    def remove_selected(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "Удаление", "Нет выделенных строк.")
            return
        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.status_label.setText(f"Удалено {len(rows)} строк(и).")

    def choose_excel_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Excel/CSV", "", "Excel/CSV files (*.xlsx *.xls *.csv);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

    def choose_pdf_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать PDF", "", "PDF files (*.pdf);;Все файлы (*)")
        if path:
            self.pdf_path = path
            self.status_label.setText(f"Выбран PDF: {Path(path).name}")

    def analyze_clicked(self):
        msg = f"Имя: {self.name_edit.text()}\nКомплекс: {self.complex_edit.text()}\nПериод: {self.period_edit.text()}\n\n"
        msg += f"Excel: {self.excel_path or '(не выбран)'}\nPDF: {self.pdf_path or '(не выбран)'}\n\n(Здесь будет запуск анализа.)"
        QMessageBox.information(self, "Анализ", msg)
