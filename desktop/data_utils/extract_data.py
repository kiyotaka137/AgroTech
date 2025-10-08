from PyPDF2 import PdfReader
import pandas as pd
import numpy as np
import re
import xlrd
from typing import List, Tuple, Optional, Dict, Any


COLUMNS = ['Ингредиенты', 'СВ %', 'ГП кг', 'СВ кг', '% ГП', '% СВ']

import xlrd
import pandas as pd
import numpy as np
from typing import List, Tuple, Any, Optional, Dict

COLUMNS = ['Ингредиенты', 'СВ %', 'ГП кг', 'СВ кг', '% ГП', '% СВ']

def parse_excel_ration(path: str, sheet: Optional[int] = 0, max_search_rows: int = 100
                               ) -> Tuple[List[Tuple[str, float]], Dict[str, float]]:
    """
    Читает .xls и возвращает:
      1. ration_data — список (Ингредиент, %СВ)
      2. step_table — словарь сводного анализа {Нутриент: СВ}
    Поиск первой таблицы заканчивается при нахождении "Общие значения".
    """
    book = xlrd.open_workbook(path)
    sheet = book.sheet_by_index(sheet)

    # --- 1. Ищем заголовок первой таблицы ---
    header_row_idx = None
    for r in range(min(sheet.nrows, max_search_rows)):
        row = sheet.row_values(r)
        if any("Ингредиент" in str(cell) for cell in row) and any("СВ" in str(cell) for cell in row):
            header_row_idx = r
            break
    if header_row_idx is None:
        raise ValueError(f"Не найден заголовок первой таблицы в первых {max_search_rows} строках.")

    # --- 2. Читаем таблицу до "Общие значения" ---
    table_rows = []
    end_row_idx = header_row_idx + 1
    for r in range(header_row_idx + 1, sheet.nrows):
        row = sheet.row_values(r)
        if any("Общие значения" in str(cell) for cell in row):
            break
        table_rows.append(row)
        end_row_idx = r

    # --- 3. DataFrame только с нужными колонками ---
    df1 = pd.DataFrame(table_rows, columns=[str(c).strip() for c in sheet.row_values(header_row_idx)])
    needed_cols = ["Ингредиенты", "СВ кг"]

    # Попытка сопоставления похожих названий
    for target in needed_cols:
        if target not in df1.columns:
            for col in df1.columns:
                if target.lower() in col.lower():
                    df1 = df1.rename(columns={col: target})

    # Приведение к числу
    df1["СВ кг"] = pd.to_numeric(df1["СВ кг"].astype(str).str.replace(",", "."), errors="coerce")

    # --- 4. Сумма всех СВ кг ---
    total_sv = df1["СВ кг"].sum()
    if total_sv == 0:
        raise ValueError("Сумма СВ кг равна нулю, невозможно вычислить %СВ.")

    # --- 5. Формируем список кортежей (Ингредиент, %СВ) ---
    ration_data = [(row["Ингредиенты"], row["СВ кг"] / total_sv * 100) 
                   for _, row in df1.iterrows() if pd.notna(row["СВ кг"])]

    step_table = parse_step_table_excel(sheet, start_row=end_row_idx+1)

    return ration_data, step_table


def parse_step_table_excel(sheet, start_row: int, max_search_rows: int = 1000) -> Dict[str, float]:
    """
    Парсит вторую таблицу (сводный анализ) начиная со строки start_row.
    Поддерживает несколько блоков под друг другом, игнорирует мусор и пустые строки.
    Возвращает словарь {Нутриент: СВ}.
    """
    step_table = {}
    r = start_row
    while r < min(sheet.nrows, start_row + max_search_rows):
        row = sheet.row_values(r)

        # Ищем заголовок блока
        header_cols = {}
        for idx, cell in enumerate(row):
            c = str(cell).replace("\n", " ").strip().lower()
            if "нутриент" in c or "показатель" in c:
                header_cols['name'] = idx
            elif "св" in c or "dm" in c:
                header_cols['value'] = idx

        if 'name' in header_cols and 'value' in header_cols:
            # Нашли заголовок блока, читаем строки до пустой/мусорной строки
            r += 1
            while r < sheet.nrows:
                r_row = sheet.row_values(r)
                # Проверка на пустую строку
                if all(str(c).strip() == "" for c in r_row):
                    break

                # Извлекаем название и значение
                name_cell = str(r_row[header_cols['name']]).replace("\n", " ").strip()
                val_cell = r_row[header_cols['value']]

                if name_cell and str(val_cell).strip():
                    try:
                        step_table[name_cell] = float(val_cell)
                    except:
                        pass
                r += 1
        else:
            r += 1

    return step_table


def parse_pdf_for_tables(pdf_path: str):
    """Парсит таблицу с рационом из текста"""

    text = extract_text_with_pypdf2(pdf_path)
    if not text:
        return None

    start_pattern = r'Рецепт:.*?Ингредиенты'
    match = re.search(start_pattern, text, re.DOTALL)
    if not match:
        return None

    # Ищем блок таблицы (от "Ингредиенты" до "Общие значения")
    table_block_pattern = r'Ингредиенты(.*?)Общие значения'
    match = re.search(table_block_pattern, text, re.DOTALL)

    if not match:
        return None

    table_text = match.group(1)
    lines = table_text.strip().split('\n')

    ration_data = []

    for line in lines:
        line = line.strip()
        if not line or '₽' in line:  # Пропускаем пустые строки и строку с заголовком цены
            continue

        # Улучшенный паттерн для парсинга строк таблицы
        # Формат: Название число число число число число число
        pattern = r'(.+?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)\s+([\d,]+(?:\s*\d{3})*(?:,\d+)?)'
        match = re.match(pattern, line)

        if match:
            row = []
            for i, value in enumerate(match.groups()):
                if i == 0:  # Название ингредиента
                    # Очищаем название от лишних пробелов
                    ingredient = re.sub(r'\s+', ' ', value.strip())
                    # Убираем слеши в конце названий
                    if ingredient.endswith('/'):
                        ingredient = ingredient[:-1].strip()
                    row.append(ingredient)
                else:
                    # Заменяем запятые на точки для десятичных и убираем пробелы
                    cleaned = re.sub(r'\s+', '', value.replace(',', '.'))
                    try:
                        row.append(float(cleaned))
                    except ValueError:
                        row.append(cleaned)
            ration_data.append([row[0], row[5]])

    step_table = parse_step_table_pdf(text)
    return ration_data, step_table


def parse_step_table_pdf(text: str):
    """
    Парсит из текста PDF раздел 'Сводный анализ: Лактирующая корова'
    и возвращает только два поля: name (нутриент) и dm (значение по СВ).

    Формат результата: [{"name": str, "dm": float|None}, ...]
    """

    def to_float(s: str) -> Optional[float]:
        if not s:
            return None
        s = re.sub(r"\s+", "", s).replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    if not text:
        return None

    # --- Ищем начало раздела ---
    start_pat = r"Сводный анализ:\s*Лактирующая корова"
    sm = re.search(start_pat, text, flags=re.IGNORECASE)
    if not sm:
        return None

    # Берём всё после заголовка
    block = text[sm.end():]

    # --- Обрезаем, если нашли следующий крупный раздел ---
    # Ищем что-то вроде "Сводка", "Экономический отчёт", "Рецепт" и т.п.
    next_section = re.search(r"\b(Сводка|Экономический|Рецепт|Ингредиенты)\b", block, flags=re.IGNORECASE)
    if next_section:
        block = block[:next_section.start()]

    # --- Обработка строк ---
    lines = [ln.strip() for ln in block.splitlines()]
    lines = [
        ln for ln in lines
        if ln
        and not re.match(r"^Нутриент\s+Единица", ln, re.IGNORECASE)
        and not re.match(r"^(Единица|Итого|Всего)\b", ln, re.IGNORECASE)
    ]

    # Паттерны для разных форматов
    pat5 = re.compile(r"^(?P<name>.+?)\s+\S+\s+(?P<dm>[\d\s,]+)\s+[\d\s,]+\s+\S+\s*$")
    pat3 = re.compile(r"^(?P<name>.+?)\s+\S+\s+(?P<dm>[\d\s,]+)\s*$")

    out = {}

    for raw in lines:
        m = pat5.match(raw) or pat3.match(raw)
        if m:
            name = re.sub(r"\s+", " ", m.group("name")).strip(" :")
            dm = to_float(m.group("dm"))
            out[name] = dm
            continue

        # fallback: ищем первое число
        parts = raw.split()
        num_idx = next((i for i, t in enumerate(parts) if re.fullmatch(r"[\d\s,]+", t)), None)
        if num_idx is not None and num_idx >= 1:
            name = " ".join(parts[:num_idx-1]).strip(" :") or parts[0]
            dm = to_float(parts[num_idx])
            out[name] = dm

    return out


def extract_text_with_pypdf2(pdf_path):
    """Извлекает текст с помощью PyPDF2"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

    except Exception as e:
        text = ""

    return text


if __name__ == "__main__":
    print(sum([i for _, i in parse_excel_ration("test_data/ds.xlsx")]))
    pdf_path = "test_data/Д0 Высокое 25.02.25_ЭНАЛБ.pdf"
    ration_table = parse_pdf_for_tables(pdf_path)[0]
    step = parse_step_table(extract_text_with_pypdf2(pdf_path))
    print(step)
    print([i for _, i in ration_table])