# new_report_window.py
import sys
import json
import time
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QLineEdit, QLabel, QAbstractItemView, QComboBox, QFileDialog,
    QHeaderView, QSizePolicy, QProgressBar
)
from PyQt6.QtGui import QFont, QMovie
from PyQt6.QtCore import (Qt, QTimer, QSize)

from data_utils import COLUMNS, parse_excel_ration, parse_pdf_for_tables


class NewReport(QDialog):
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

        font = QFont("Segoe UI", 10)
        self.setFont(font)

        # Пути выбранных файлов
        self.excel_path = None

        # Поля для управления загрузочным диалогом/анимацией
        self._loading_dialog = None
        self._loading_movie = None

        self._build_main()
        self._build_statusbar()

        # стартовая строка-пример
        self.add_row(default=True)

        QTimer.singleShot(100, self.setup_columns_ratio)

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

        # Кнопки Excel
        files_layout = QHBoxLayout()
        files_layout.addStretch()

        self.excel_btn = QPushButton("Excel"); self.excel_btn.clicked.connect(self.choose_excel_file)
        self.pdf_btn = QPushButton("PDF"); self.pdf_btn.clicked.connect(self.choose_pdf_file)

        files_layout.addWidget(self.excel_btn)
        files_layout.addWidget(self.pdf_btn)

        files_layout.addStretch()
        main_layout.addLayout(files_layout)

        # Таблица
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # todo: исправить что таблица странно выглядит
        # Убираем все автоматические настройки размера
        header = self.table.horizontalHeader()

        # Fixed режим запрещает пользователю менять размеры, но позволяет программе
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)

        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Стили для таблицы
        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: lightgray;
            }
            QHeaderView::section {
                border: 1px solid lightgray;
                padding: 4px;
                background-color: #f0f0f0;
            }
        """)

        main_layout.addWidget(self.table, 1)

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

    def setup_columns_ratio(self):
        """Настройка соотношения столбцов 4:1:1:1:1"""
        if self.table.width() == 0:
            QTimer.singleShot(10, self.setup_columns_ratio)
            return

        total_width = self.table.width()
        column_count = self.table.columnCount()

        # Защитимся от деления при неверном количестве колонок
        if column_count < 5:
            per = total_width // max(1, column_count)
            for i in range(column_count):
                self.table.setColumnWidth(i, per)
            return

        first_col_width = int(total_width * 4 / 8)
        other_col_width = int(total_width * 1 / 8)

        self.table.setColumnWidth(0, first_col_width)
        for i in range(1, 5):
            if i < column_count:
                self.table.setColumnWidth(i, other_col_width)

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
            # Используем экземпляр QMessageBox вместо статического вызова
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Icon.Information)
            mb.setWindowTitle("Удаление")
            mb.setText("Нет выделенных строк.")
            mb.exec()
            return
        rows = sorted([idx.row() for idx in selected], reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.status_label.setText(f"Удалено {len(rows)} строк(и).")


    def filling_table_from_file(self, rows):
        """
        таблица заполняется из строк спаршенных с пдф/эксель
        """
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(COLUMNS))

        # лёгкое форматирование чисел
        def fmt(v) -> str:
            if isinstance(v, float):
                # 2 знака после запятой, запятая как десятичный
                return f"{v:.3f}".replace(".", ",")
            return "" if v is None else str(v)

        numeric_cols_idx = set(range(1, len(COLUMNS)))

        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(fmt(value))

                if c in numeric_cols_idx:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                self.table.setItem(r, c, item)


    def choose_excel_file(self):  # todo: загрузка excel таблицы в self.table использовать parse_excel из data_utils можно импортить как from data_utils
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать Excel/CSV", "", "Excel/CSV files (*.xlsx *.xls *.csv);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

            rows = parse_excel_ration(path)
            self.filling_table_from_file(rows)


    def choose_pdf_file(self):  # todo: загрузка pdf таблицы в self.table, аналогично excel
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать PDF файл", "", "PDF files (*.pdf);;Все файлы (*)")
        if path:
            self.excel_path = path
            self.status_label.setText(f"Выбран Excel: {Path(path).name}")

            ration_rows, step_rows = parse_pdf_for_tables(path)
            self.filling_table_from_file(ration_rows)

    def _collect_table_data(self):
        """Собираем данные из таблицы в список словарей"""
        rows = []
        for r in range(self.table.rowCount()):
            row_data = {}
            empty_row = True
            for c, col_name in enumerate(COLUMNS):
                item = self.table.item(r, c)
                text = item.text() if item is not None else ""
                if text.strip():
                    empty_row = False
                row_data[col_name] = text
            # Пропускаем полностью пустые строки
            if not empty_row:
                rows.append(row_data)
        return rows

    def analyze_clicked(self):
        """
        При нажатии: показываем модальное окно загрузки (имитация) 5 секунд,
        затем собираем таблицу в JSON и сохраняем файл в папке reports.
        """
        # Отключаем кнопку чтобы избежать повторных нажатий
        self.analyze_btn.setEnabled(False)

        # --- Создаём простое модальное окно загрузки с GIF ---
        loading = QDialog(self)
        loading.setWindowTitle("Анализ — загрузка")
        loading.setModal(True)
        loading.setWindowModality(Qt.WindowModality.ApplicationModal)
        loading.resize(360, 180)

        layout = QVBoxLayout(loading)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Путь к GIF — пробуем несколько мест (корректируй по своему проекту)
        gif_path = "cow.gif"
        movie = None
        try:
            movie = QMovie(str(gif_path))
        except Exception:
            movie = None

        gif_label = QLabel()
        gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if movie is not None and movie.isValid():
            # При желании можно задать размер: movie.setScaledSize(QSize(96,96))
            # movie.setScaledSize(QSize(96, 96))
            gif_label.setMovie(movie)
            movie.start()
            # Сохраним в атрибуты, чтобы остановить позже
            self._loading_movie = movie
        else:
            gif_label.setText("Загрузка...\n(анимация недоступна)")
            gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(gif_label)

        # Текст под GIF
        lbl = QLabel("Анализ таблицы моделью...\n(имитация загрузки 5 секунд)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        # Прогресс-бар только для UI (без реальной работы)
        progress = QProgressBar()
        progress.setRange(0, 0)  # бесконечный индикатор
        layout.addWidget(progress)

        # Покажем диалог и сохраним ссылку, чтобы закрыть позже
        loading.show()
        self._loading_dialog = loading

        # 5 секунд "пустой" работы — placeholder
        QTimer.singleShot(5000, lambda: self._finish_analysis())

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
                "rows": self._collect_table_data()
            }

            # Папка для сохранения
            reports_dir = Path("desktop/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            # Формируем имя файла: имя_дата_время.json
            safe_name = self.name_edit.text().strip() or "report"
            # очищаем пробелы и запрещённые символы простым способом
            safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in ("-", "_")).strip() or "report"
            filename = f"{safe_name}_{date.today().isoformat()}_{int(time.time())}.json"
            file_path = reports_dir / filename

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
            self.close()



