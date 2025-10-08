from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re

# ------------------------------
# УТИЛИТЫ
# ------------------------------

def to_float_ru(s: str | float | int | None) -> Optional[float]:
    """Безопасно парсим число из русской строки c запятой."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = s.strip()
    if not s:
        return None
    s = s.replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def pct(x: Optional[float], digits: int = 2) -> str:
    return "-" if x is None else f"{x:.{digits}f}%"

def find_first(patterns: List[str], text: str) -> bool:
    t = text.lower()
    return any(p in t for p in patterns)

# ------------------------------
# НОРМАЛИЗАЦИЯ ИНГРЕДИЕНТОВ
# ------------------------------


@dataclass
class RationRow:
    original: str
    normalized: str
    dm_percent: Optional[float]

def normalize_ration_rows(rows: List[Dict[str, str]]) -> List[RationRow]:
    out: List[RationRow] = []
    for r in rows:
        name = str(r.get("Ингредиенты", "")).strip()
        dm = to_float_ru(r.get("%СВ"))
        norm = r.get("Normalized", "")
        out.append(RationRow(
            original=name,
            normalized=norm,
            dm_percent=dm
        ))
    return out

# ------------------------------
# ПРОФИЛИ И РЕКОМЕНДАЦИИ (ЭВРИСТИКИ)
# ------------------------------

# Лёгкие ориентиры-«диапазоны по умолчанию».
# ВАЖНО: это лишь шаблон! Подставь свои целевые коридоры,
# используемые в твоей практике/лаборатории.
DEFAULT_TARGETS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "Пальмитиновая": (25.0, 31.0),   # ↑ при избытке пальмового жира
    "Стеариновая":   (8.0,  12.5),   # ↑ при стеариновых добавках/переплаве
    "Олеиновая":     (22.0, 28.0),   # ↑ от рапсовых/высокоолеиновых источников
    "Линолевая":     (1.5,  3.5),    # ↑ от соя/подсолнечник/кукуруза
    "Лауриновая":    (2.0,  4.4),
}

# Маппинг категорий -> вклад по жирным кислотам (знаки — направление влияния)
# Значения — «вес влияния» (условные единицы), используются для подсказок.
FA_INFLUENCE = {
    "защищённый жир/жиры": {"Пальмитиновая": +3.0, "Стеариновая": +1.0},
    "рапс":                {"Олеиновая": +2.5, "Линолевая": +1.0},
    "соя":                 {"Линолевая": +2.5},  # у сои высокая ω-6 (линолевая)
    "подсолнечник":        {"Линолевая": +3.0},  # особенно традиц. подсолнечник
    "кукуруза":            {"Линолевая": +1.5, "Олеиновая": +0.5},
    "свекла":              {"Пальмитиновая": -0.3},  # как «разбавитель» ЖК за счёт СВ/клетч.
    "сенаж":               {"Пальмитиновая": -0.2},
    "силос":               {"Пальмитиновая": -0.2},
    "белковый шрот":       {"Линолевая": +0.8},  # общее правило, если вид не уточнён
    "премикс/минералы":    {},
    "соль/минералы":       {},
    "буфер/минералы":      {},
    "корм (код)":          {},
}

def classify_acids(current: Dict[str, float],
                   targets: Dict[str, Tuple[Optional[float], Optional[float]]] = DEFAULT_TARGETS
                   ) -> Dict[str, str]:
    """
    Возвращает по каждой кислоте статус: 'низко'/'в норме'/'высоко'
    согласно целевым коридорам. Если в коридоре есть None, сравниваем по доступной границе.
    """
    status: Dict[str, str] = {}
    for name, val in current.items():
        lo, hi = targets.get(name, (None, None))
        if lo is not None and val < lo:
            status[name] = "низко"
        elif hi is not None and val > hi:
            status[name] = "высоко"
        else:
            status[name] = "в норме"
    return status

def suggest_changes(acids: Dict[str, float],
                    ration: List[RationRow],
                    targets: Dict[str, Tuple[Optional[float], Optional[float]]] = DEFAULT_TARGETS
                    ) -> Dict[str, List[str]]:
    """
    Формирует списки 'увеличить' / 'уменьшить' по категориям ингредиентов,
    чтобы сдвинуть профиль кислот в желаемую сторону.
    """
    status = classify_acids(acids, targets)
    present_cats = set(r.normalized for r in ration)

    increase: List[str] = []
    decrease: List[str] = []
    notes:    List[str] = []

    # ПАЛЬМИТИНОВАЯ
    if status.get("Пальмитиновая") == "высоко":
        if "защищённый жир/жиры" in present_cats:
            decrease.append("защищённый жир/жиры (особенно пальмовые фракции)")
        increase.extend(["рапс (жмых/шрот, масло высокоолеиновое при необходимости)",
                         "подсолнечник (для разбавления насыщенных ЖК)"])
        notes.append("Высокая пальмитиновая часто связана с пальмовыми защищёнными жирами.")

    if status.get("Пальмитиновая") == "низко":
        increase.append("защищённый жир/жиры (аккуратно, под задачу выхода молочного жира)")

    # СТЕАРИНОВАЯ
    if status.get("Стеариновая") == "высоко":
        decrease.append("жиры с высоким содержанием стеариновой (гидрогенизированные фракции)")
        notes.append("Переизбыток стеариновой иногда сопровождается снижением перевариваемости Ж.")
    if status.get("Стеариновая") == "низко":
        notes.append("Низкая стеариновая — обычно не проблема, корректируется общим балансом насыщ./ненасыщ. жиров.")

    # ОЛЕИНОВАЯ
    if status.get("Олеиновая") == "низко":
        increase.append("рапс / высокоолеиновый подсолнечник / кукуруза (масляные компоненты)")
    if status.get("Олеиновая") == "высоко":
        decrease.append("масла/жиры с высоким содержанием олеиновой (канола/высокоолеиновый подсолнечник)")

    # ЛИНОЛЕВАЯ
    if status.get("Линолевая") == "низко":
        increase.extend(["соя (шрот/жмых, при балансе по СП)", "подсолнечник", "кукуруза"])
    if status.get("Линолевая") == "высоко":
        decrease.extend(["соя", "подсолнечник"])
        notes.append("Слишком много линолевой (ω-6) может смещать баланс PUFA — следи за соотношением с ω-3.")

    # ЛАУРИН
    if status.get("Лауриновая") == "высоко":
        decrease.append("жиры с долей лауриновой (кокос/пальмоядровые компоненты)")
    if status.get("Лауриновая") == "низко":
        notes.append("Лауриновая обычно невелика; низкие значения редко требуют целевой коррекции.")

    # Уточнения по тому, что реально есть в рационе
    increase = sorted(set(increase))
    decrease = sorted(set(decrease))

    return {
        "increase": increase,
        "decrease": decrease,
        "notes": notes
    }

# ------------------------------
# ОТЧЁТ
# ------------------------------

REPORT_HEADER = """# Отчёт по профилю жирных кислот и рациону

**Комплекс:** {complex}  
**Период:** {period}  
**Дата отчёта:** {now}  
"""

def render_ration_table(ration: List[RationRow]) -> str:
    lines = ["\n## Состав рациона (по % СВ)\n",
             "| Ингредиент (оригинал) | Нормализовано | %СВ |",
             "|---|---|---|"]
    for r in ration:
        lines.append(f"| {r.original} | {r.normalized} | {pct(r.dm_percent)} |")
    return "\n".join(lines)

def render_acids_table(acids: Dict[str, float],
                       targets: Dict[str, Tuple[Optional[float], Optional[float]]] = DEFAULT_TARGETS) -> str:
    lines = ["\n## Предсказанные жирные кислоты\n",
             "| Кислота | Значение | Целевой коридор | Статус |",
             "|---|---:|:---:|:---:|"]
    status = classify_acids(acids, targets)
    for k, v in acids.items():
        lo, hi = targets.get(k, (None, None))
        target = f"{'' if lo is None else f'{lo:.1f}'} — {'' if hi is None else f'{hi:.1f}'}".strip()
        if target == "—":
            target = "n/a"
        lines.append(f"| {k} | {v:.2f}% | {target} | {status.get(k,'')} |")
    return "\n".join(lines)

def render_recommendations(sugg: Dict[str, List[str]]) -> str:
    sections = ["\n## Рекомендации по корректировке\n"]
    inc = sugg.get("increase", [])
    dec = sugg.get("decrease", [])
    notes = sugg.get("notes", [])

    if inc:
        sections.append("**Увеличить долю/ввести:**")
        for x in inc:
            sections.append(f"- {x}")
        sections.append("")

    if dec:
        sections.append("**Снизить долю/ограничить:**")
        for x in dec:
            sections.append(f"- {x}")
        sections.append("")

    if notes:
        sections.append("**Примечания:**")
        for n in notes:
            sections.append(f"- {n}")
        sections.append("")

    sections.append("> ВНИМАНИЕ: предложения носят ориентировочный характер. ")
    sections.append("> Перед внедрением изменений проверь баланс СП/ЭС, крахмала, NDF, минералов и ограничений по жирам.")
    return "\n".join(sections)

def build_report(doc: Dict) -> str:
    meta = doc.get("meta", {})
    ration_rows = doc.get("ration_rows", []) or []
    acids = doc.get("result_acids", {}) or {}

    ration = normalize_ration_rows(ration_rows)
    sugg = suggest_changes(acids, ration)

    parts = [
        REPORT_HEADER.format(
            complex=meta.get("complex", "") or "-",
            period=meta.get("period", "") or "-",
            now=datetime.now().strftime("%Y-%m-%d %H:%M")
        ),
        render_ration_table(ration),
        render_acids_table(acids),
        render_recommendations(sugg),
    ]
    return "\n".join(parts)

# ------------------------------
# IO-ОБВЁРТКИ
# ------------------------------

def load_json(path: str | Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str | Path, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def write_report_files(input_json_path: str | Path,
                       out_report_md: Optional[str | Path] = None,
                       update_json_with_report: bool = True) -> Tuple[str, str | None]:
    """
    Возвращает (путь_к_json, путь_к_md_или_None)
    """
    input_json_path = str(input_json_path)
    doc = load_json(input_json_path)

    # Если в JSON пока нет 'result_acids', ничего не ломаем — просто сделаем отчёт из того, что есть.
    report_md = build_report(doc)

    # Сохраняем MD
    if out_report_md is None:
        stem = Path(input_json_path).with_suffix("").name
        out_report_md = Path(input_json_path).with_name(stem + "_report.md")
    with open(out_report_md, "w", encoding="utf-8") as f:
        f.write(report_md)

    # Опционально — вклеиваем отчёт в JSON
    if update_json_with_report:
        doc["report"] = report_md
        save_json(input_json_path, doc)

    return input_json_path, str(out_report_md)

# ------------------------------
# Пример CLI
# ------------------------------

if __name__ == "__main__":

    write_report_files(
        input_json_path="desktop/reports/report_2025-10-07_1759855680.json",
        out_report_md="output.md",
        update_json_with_report=True
    )
    print("Готово.")
