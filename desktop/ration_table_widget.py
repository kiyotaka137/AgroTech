# ration_table_widget.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QTimer
from datetime import date
from PyQt6.QtWidgets import QHeaderView

COLUMNS = [
    "Ингредиенты", "СВ %", "ГП кг" ,"%ГП","%СВ"
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
        
        # Убираем все автоматические настройки размера
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        
        # Устанавливаем ручное управление размерами
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table)

        # === Нижняя панель: кнопки + статус ===
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(10)

        # Левая колонка с кнопками и статусом
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(2)

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
        
        # Отложенная настройка размеров столбцов
        QTimer.singleShot(0, self.setup_columns_ratio)

    def setup_columns_ratio(self):
        """Настройка соотношения столбцов 4:1:1:1:1"""
        if self.table.width() == 0:
            QTimer.singleShot(10, self.setup_columns_ratio)
            return
            
        total_width = self.table.width()
        column_count = self.table.columnCount()
        
        first_col_width = int(total_width * 4 / 8)
        other_col_width = int(total_width * 1 / 8)
        
        self.table.setColumnWidth(0, first_col_width)
        for i in range(1, 5):
            self.table.setColumnWidth(i, other_col_width)

    def _make_button(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b


    def add_row(self, default=False):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Убеждаемся, что соотношение столбцов правильное
        self.setup_columns_ratio()
        
        for c, col_name in enumerate(COLUMNS):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, c, item)

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
        """
        Заполняет таблицу из массива JSON.
        ration_data может быть:
        - {"rows": [...]} — список словарей
        - [[...], [...]] — список списков
        """
        # Если пришел словарь с ключом "rows"
        if isinstance(ration_data, dict) and "rows" in ration_data:
            ration_data = ration_data["rows"]

        # Если это список словарей, конвертируем в список списков
        normalized_data = []
        for row in ration_data:
            if isinstance(row, dict):
                normalized_data.append([row.get(col, "") for col in COLUMNS])
            else:
                normalized_data.append(row)

        self.table.setRowCount(0)
        for row_data in normalized_data:
            self.add_row(default=False)
            row = self.table.rowCount() - 1
            for c, col_name in enumerate(COLUMNS):
                value = row_data[c] if c < len(row_data) else ""
                item = self.table.item(row, c)
                if item:
                    item.setText(str(value))

        self.status_label.setText(f"Загружено {len(normalized_data)} строк")
        QTimer.singleShot(0, self.setup_columns_ratio)

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
    
    def resizeEvent(self, event):
        """При изменении размера окна пересчитываем столбцы"""
        super().resizeEvent(event)
        QTimer.singleShot(10, self.setup_columns_ratio)