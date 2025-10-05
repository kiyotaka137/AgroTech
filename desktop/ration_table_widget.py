# ration_table_widget.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from datetime import date

COLUMNS = [
    "Дата", "ID коровы", "Ингредиенты", "СВ (%)", "%ГП",
    "кгСВ", "кг%ГП%", "СВ ₽/Тонна"
]

INGREDIENT_TYPES = [
    "Сено", "Комбикорм", "Силос", "Сенаж",
    "Концентрат", "Шрот", "Витамины/Минералы",
    "Комбинация", "Другое"
]


class RationTableWidget(QWidget):
    """Виджет таблицы рациона с кнопками и JSON-совместимостью."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.add_row(default=True)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # === Таблица ===
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table)

        # === Нижняя панель: кнопки + статус ===
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)  # панель без внутренних отступов
        bottom_layout.setSpacing(10)

        # Левая колонка с кнопками и статусом
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)   # без лишнего сверху
        left_col.setSpacing(2)                     # расстояние между кнопками и статусом

        # Горизонтальный блок кнопок
        btns_layout = QHBoxLayout()
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.setSpacing(8)

        add_btn = self._make_button("Добавить строку", self.add_row)
        add_btn.setObjectName("addRowBtn")
        add_btn.setProperty("class", "borderButton")   # 🔹 добавляем класс для рамки

        remove_btn = self._make_button("Удалить выделенные", self.remove_selected)
        remove_btn.setObjectName("removeRowBtn")
        remove_btn.setProperty("class", "borderButton")  # 🔹 рамка

        btns_layout.addWidget(add_btn)
        btns_layout.addWidget(remove_btn)
        btns_layout.addStretch()
        left_col.addLayout(btns_layout)

        # Статус под кнопками
        self.status_label = QLabel("Готово")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("padding-left: 1px; color: #666; font-size: 12px;")
        left_col.addWidget(self.status_label)

        bottom_layout.addLayout(left_col)
        bottom_layout.addStretch()

        # Кнопка "Анализировать" справа
        analyze_btn = QPushButton("Анализировать")
        analyze_btn.setProperty("primary", True)
        analyze_btn.setFixedSize(160, 36)  # 🔹 уменьшили размер

        analyze_btn.clicked.connect(self.analyze_clicked)

        # Добавим небольшой отступ справа и снизу
        bottom_layout.addStretch()  # чтобы кнопка прижалась к правой стороне
        bottom_layout.addWidget(analyze_btn)
        bottom_layout.setContentsMargins(5, 5, 5, 5)  
        

        main_layout.addLayout(bottom_layout)

    def _make_button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _make_combobox(self, value=None):
        cb = QComboBox()
        cb.addItems(INGREDIENT_TYPES)
        if value in INGREDIENT_TYPES:
            cb.setCurrentIndex(INGREDIENT_TYPES.index(value))
        return cb

    # === Логика таблицы ===
    def add_row(self, default=False):
        row = self.table.rowCount()
        self.table.insertRow(row)

        for c, col_name in enumerate(COLUMNS):
            if col_name == "Ингредиенты":
                cb = self._make_combobox()
                self.table.setCellWidget(row, c, cb)
            else:
                item = QTableWidgetItem("")
                if col_name not in ("Дата", "ID коровы", "Ингредиенты"):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, c, item)

        if default:
            today = date.today().isoformat()
            self.table.item(row, 0).setText(today)
            self.table.item(row, 1).setText("001")
            cb = self.table.cellWidget(row, 2)
            cb.setCurrentIndex(INGREDIENT_TYPES.index("Комбинация"))
            self.table.item(row, 3).setText("88.0")
            self.table.item(row, 4).setText("14.5")
            self.table.item(row, 5).setText("6.8")
            self.table.item(row, 6).setText("0.99")
            self.table.item(row, 7).setText("20000")

        self.status_label.setText(f"Добавлена строка {row + 1}")

    def remove_selected(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.information(self, "Удаление", "Нет выделенных строк.")
            return

        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.status_label.setText(f"Удалено {len(rows)} строк(и)")

    # === JSON API ===
    def load_from_json(self, ration_data):
        """Заполняет таблицу из массива JSON"""
        self.table.setRowCount(0)
        for row_data in ration_data:
            self.add_row(default=False)
            row = self.table.rowCount() - 1
            for c, col_name in enumerate(COLUMNS):
                value = row_data[c] if c < len(row_data) else ""
                if col_name == "Ингредиенты":
                    cb = self.table.cellWidget(row, c)
                    if value in INGREDIENT_TYPES:
                        cb.setCurrentIndex(INGREDIENT_TYPES.index(value))
                else:
                    item = self.table.item(row, c)
                    if item:
                        item.setText(str(value))
        self.status_label.setText(f"Загружено {len(ration_data)} строк")

    def to_json(self):
        """Возвращает содержимое таблицы как список списков"""
        data = []
        for r in range(self.table.rowCount()):
            row = []
            for c, col_name in enumerate(COLUMNS):
                if col_name == "Ингредиенты":
                    cb = self.table.cellWidget(r, c)
                    row.append(cb.currentText() if cb else "")
                else:
                    item = self.table.item(r, c)
                    row.append(item.text() if item else "")
            data.append(row)
        return data

    # === Временный обработчик анализа ===
    def analyze_clicked(self):
        rows = self.table.rowCount()
        QMessageBox.information(self, "Анализ", f"Будет выполнен анализ для {rows} строк.")
