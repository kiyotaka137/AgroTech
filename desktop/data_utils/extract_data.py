from PyPDF2 import PdfReader
import pandas as pd
import numpy as np
import re
from typing import List, Tuple, Sequence, Optional, Dict, Any


COLUMNS = ['Ингредиенты', 'СВ %', 'ГП кг', 'СВ кг', '% ГП', '% СВ']

def parse_excel_ration(
    path: str,
    sheet: Optional[str | int] = 0
) -> List[Tuple[Any, Any]]:
    """
    Читает Excel и возвращает список кортежей в порядке COLUMNS
    """

    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")

    def norm(s: str) -> str:
        return str(s).strip().replace("\n", " ").replace("\t", " ")

    df.columns = [norm(c) for c in df.columns]

    # 4. проверяем, что все нужные колонки есть; если нет — пробуем подобрать по «похожести»
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        # простая эвристика для подбора по «началу»/«вхождению»
        def find_like(target: str) -> Optional[str]:
            tl = target.lower()
            for col in df.columns:
                cl = col.lower()
                if cl == tl or tl in cl or cl in tl:
                    return col
            return None

        rename_map = {}
        for need in missing:
            guess = find_like(need)
            if guess:
                rename_map[guess] = need
        if rename_map:
            df = df.rename(columns=rename_map)

    # финальная валидация
    still_missing = [c for c in COLUMNS if c not in df.columns]
    if still_missing:
        raise ValueError(f"В Excel отсутствуют нужные колонки: {still_missing}. Найдены: {list(df.columns)}")


    numeric_cols = COLUMNS[1:]
    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .replace({"None": np.nan, "nan": np.nan, "": np.nan})
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[COLUMNS]
    df = df.dropna(how="all")

    full_rows: List[Tuple[Any, Any, Any, Any, Any]] = list(df.itertuples(index=False, name=None))
    rows = [(row[0], row[5]) for row in full_rows]
    return rows


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

    step_table = parse_step_table(text)
    return ration_data, step_table


def parse_step_table(text: str):
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
    print(sum([i for _, i in parse_excel_ration("test_data/Гилево Д1 25.07.25_АФМ.xlsx")]))
    pdf_path = "test_data/Д0 Высокое 25.02.25_ЭНАЛБ.pdf"
    ration_table = parse_pdf_for_tables(pdf_path)[0]
    step = parse_step_table(extract_text_with_pypdf2(pdf_path))
    print(step)
    print([i for _, i in ration_table])