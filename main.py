# cow_feed_predictor_pyqt5_columns_with_player.py
import sys
from datetime import date
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QLabel, QStatusBar, QAbstractItemView, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# --- Настройки столбцов ---
COLUMNS = [
    "Дата",
    "ID коровы",
    "Ингредиенты",
    "СВ (%)",
    "%ГП",
    "кгСВ",
    "кг%ГП%",
    "СВ ₽/Тонна"
]

FEATURE_ORDER = [
    "СВ (%)",
    "%ГП",
    "кгСВ",
    "кг%ГП%",
    "СВ ₽/Тонна"
]

INGREDIENT_TYPES = [
    "Сено", "Комбикорм", "Силос", "Сенаж",
    "Концентрат", "Шрот", "Витамины/Минералы",
    "Комбинация", "Другое"
]

STYLE = """
QMainWindow {
    background: qlineargradient(x1:0 y1:0, x2:1 y2:1,
                stop:0 #fbfcfe, stop:1 #eef6fb);
}
QTableWidget {
    background: white;
    border-radius: 8px;
    alternate-background-color: #f9fbff;
    gridline-color: #e6eef9;
    font-size: 13px;
}
QHeaderView::section {
    background-color: #2b73d1;
    color: white;
    padding: 6px;
    border: 0px;
    font-weight: bold;
}
QPushButton {
    background-color: #2b73d1;
    color: white;
    border-radius: 8px;
    padding: 10px;
    font-weight: 600;
    font-size: 14px;
}
QPushButton:hover { background-color: #1f5fb0; }
QLineEdit {
    padding: 6px;
    border-radius: 6px;
    border: 1px solid #cbdff6;
    background: #ffffff;
}
"""

class CowFeedPredictor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Прогноз молока по рациону коров (PyQt5)")
        self.resize(1000, 700)
        self.setStyleSheet(STYLE)

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
        main_layout = QVBoxLayout()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

       # Фрагмент кода из _build_main() с кнопками Excel/PDF по центру
        # Верхняя область: поля Имя / Комплекс / Период
        fields_layout = QHBoxLayout()
        name_lbl = QLabel("Имя:")
        name_lbl.setFixedWidth(60)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите имя")
        self.name_edit.setFixedWidth(220)

        complex_lbl = QLabel("Комплекс:")
        complex_lbl.setFixedWidth(80)
        self.complex_edit = QLineEdit()
        self.complex_edit.setPlaceholderText("Введите комплекс")
        self.complex_edit.setFixedWidth(220)

        period_lbl = QLabel("Период:")
        period_lbl.setFixedWidth(60)
        self.period_edit = QLineEdit()
        self.period_edit.setPlaceholderText("например: 2025-01")
        self.period_edit.setFixedWidth(160)

        fields_layout.addWidget(name_lbl)
        fields_layout.addWidget(self.name_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(complex_lbl)
        fields_layout.addWidget(self.complex_edit)
        fields_layout.addSpacing(10)
        fields_layout.addWidget(period_lbl)
        fields_layout.addWidget(self.period_edit)
        fields_layout.addStretch()
        main_layout.addLayout(fields_layout)

        # Кнопки Excel и PDF по центру
        files_layout = QHBoxLayout()
        files_layout.addStretch()  # растяжка слева
        self.excel_btn = QPushButton("Excel")
        self.excel_btn.clicked.connect(self.choose_excel_file)
        self.pdf_btn = QPushButton("PDF")
        self.pdf_btn.clicked.connect(self.choose_pdf_file)
        files_layout.addWidget(self.excel_btn)
        files_layout.addSpacing(10)
        files_layout.addWidget(self.pdf_btn)
        files_layout.addStretch()  # растяжка справа
        main_layout.addLayout(files_layout)


        
        # Таблица
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        main_layout.addWidget(self.table, 1)

        # Кнопка "Анализировать" большая, по центру
        analyze_layout = QHBoxLayout()
        analyze_layout.addStretch()
        self.analyze_btn = QPushButton("Анализировать")
        self.analyze_btn.setFixedHeight(50)
        self.analyze_btn.setMinimumWidth(400)
        self.analyze_btn.clicked.connect(self.analyze_clicked)
        analyze_layout.addWidget(self.analyze_btn)
        analyze_layout.addStretch()
        main_layout.addLayout(analyze_layout)

        # Отдельно: кнопки "Добавить / Удалить"
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
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Готово")

    def _make_ingredient_combobox(self, selected_text: str = None):
        cb = QComboBox()
        cb.addItems(INGREDIENT_TYPES)
        cb.setEditable(False)
        if selected_text:
            try:
                cb.setCurrentIndex(INGREDIENT_TYPES.index(selected_text))
            except ValueError:
                cb.setCurrentIndex(0)
        return cb

    def add_row(self, default=False):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(len(COLUMNS)):
            col = COLUMNS[c]
            if col == "Ингредиенты":
                cb = self._make_ingredient_combobox()
                self.table.setCellWidget(r, c, cb)
            else:
                item = QTableWidgetItem("")
                if col in FEATURE_ORDER:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(r, c, item)

        if default:
            today = date.today().isoformat()
            self.table.item(r, 0).setText(today)
            self.table.item(r, 1).setText("001")
            cb = self.table.cellWidget(r, 2)
            if isinstance(cb, QComboBox):
                try:
                    cb.setCurrentIndex(INGREDIENT_TYPES.index("Комбинация"))
                except ValueError:
                    cb.setCurrentIndex(0)
            for key, val in [("СВ (%)", "88.0"), ("%ГП", "14.5"), ("кгСВ", "6.8"), ("кг%ГП%", "0.99"), ("СВ ₽/Тонна", "20000")]:
                if key in COLUMNS:
                    self.table.item(r, COLUMNS.index(key)).setText(val)

    def remove_selected(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "Удаление", "Нет выделенных строк.")
            return
        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.statusBar().showMessage(f"Удалено {len(rows)} строк(и).", 3000)

    # Заглушки для Excel / PDF
    def choose_excel_file(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Excel/CSV", "", "Excel/CSV files (*.xlsx *.xls *.csv);;Все файлы (*)")
        if not path:
            return
        self.excel_path = path
        self.statusBar().showMessage(f"Выбран Excel: {Path(path).name}", 4000)

    def choose_pdf_file(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать PDF", "", "PDF files (*.pdf);;Все файлы (*)")
        if not path:
            return
        self.pdf_path = path
        self.statusBar().showMessage(f"Выбран PDF: {Path(path).name}", 4000)

    # Заглушка для кнопки "Анализировать"
    def analyze_clicked(self):
        name = self.name_edit.text().strip()
        complex_ = self.complex_edit.text().strip()
        period = self.period_edit.text().strip()
        excel = self.excel_path or "(не выбран)"
        pdf = self.pdf_path or "(не выбран)"
        msg = f"Имя: {name}\nКомплекс: {complex_}\nПериод: {period}\n\nExcel: {excel}\nPDF: {pdf}\n\n(Здесь будет запуск анализа.)"
        QMessageBox.information(self, "Анализ", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = CowFeedPredictor()
    win.show()
    sys.exit(app.exec_())
