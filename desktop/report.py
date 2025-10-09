from __future__ import annotations
import json, re, shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union, Iterable
from pathlib import Path
from datetime import datetime
import markdown
import re
import sys
from urllib.parse import quote



from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QTextEdit, QTextBrowser, QVBoxLayout

try:
    import markdown
    _HAS_MD = True
except Exception:
    _HAS_MD = False



IMG_TAG_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"([^>]*)>', flags=re.I)

# Тип для удобства
Textish = Union[QTextEdit, QTextBrowser]

CSS_DEFAULT = """
body { font-family: Segoe UI, Roboto, Arial, sans-serif; line-height:1.6; margin:16px; }
h1,h2,h3 { margin-top:1.2em; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #d0d7de; padding: 6px 8px; }
th { background: #f6f8fa; text-align: left; }
pre code { display:block; padding:8px; background:#f6f8fa; border-radius:6px; }
code { background:#f6f8fa; padding:2px 4px; border-radius:4px; }
img { max-width:100%; height:auto; }
"""


# ==========================
# УТИЛИТЫ
# ==========================

def to_float_ru(s: str | float | int | None) -> Optional[float]:
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

def posix_path(p: Path) -> str:
    # Для Markdown лучше использовать прямые слеши
    return p.as_posix()

def slug(s: str) -> str:
    # Простейший слаг для имён файлов
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"[^\w\-.А-Яа-яЁё_]", "", s)
    return s

# ==========================
# НОРМАЛИЗАЦИЯ (фоллбэк)
# ==========================

BASE_ALIASES = {
    "жом": "свекла",
    "жмых": "рапс",
    "жир": "защищённый жир/жиры",
    "дрожжи": "концентраты",
    "лед": "концентраты",
    "шрот соев": "соя",
    "соев": "соя",
    "шрот рапс": "рапс",
    "рапс": "рапс",
    "кукуруз": "кукуруза",
    "солнух": "подсолнечник",
    "подсолнеч": "подсолнечник",
    "судан": "суданская трава",
    "сено": "сено",
    "силос": "силос",
    "сенаж": "сенаж",
    "свекл": "свекла",
    "премикс": "премикс/минералы",
    "соль": "соль/минералы",
    "поташ": "буфер/минералы",
}


def _resolve_graph_path(key: str,
                        graphics: dict[str, str],
                        out_report_md: Path,
                        default_filename: str | None = None) -> str | None:
    """
    Берём путь из JSON[graphics][key], иначе ищем в desktop/graphics/<report_id>/<default_filename|key+'.png'>
    """
    p = graphics.get(key)
    if p:
        return str(Path(p))
    gdir = _graphics_dir_for(out_report_md)
    if gdir:
        name = default_filename or f"{key}.png"
        cand = gdir / name
        if cand.exists():
            return str(cand)
    return None

def normalize_ingredient(name: str) -> str:
    raw = name.strip()
    if re.match(r"^\d{4}\.\d{2}\.\d{2}\.\d{1,2}\.\d{2}(?:\s*/\s*\d{2}\.\d{2}\.\d{4})?$", raw):
        return "корм (код)"
    low = raw.lower()
    for k, v in BASE_ALIASES.items():
        if k in low:
            return v
    if "жир" in low:
        return "защищённый жир/жиры"
    if "шрот" in low:
        return "белковый шрот"
    return raw

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
        normalized = r.get("Normalized")
        normalized = normalized if (isinstance(normalized, str) and normalized.strip()) else normalize_ingredient(name)
        out.append(RationRow(original=name, normalized=normalized, dm_percent=dm))
    return out

# ==========================
# ЦЕЛИ / КЛАССИФИКАЦИЯ КИСЛОТ
# ==========================

DEFAULT_TARGETS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "Лауриновая" : (2.0, 4.4),
    "Линолевая" : (2.2, 5.0),
    "Олеиновая" : (20.0, 28.0),
    "Пальмитиновая" : (21.0, 32.0),
    "Стеариновая" : (8.0, 13.5)  # обновлено по твоему правилу
}

def classify_acids(current: Dict[str, float],
                   targets: Dict[str, Tuple[Optional[float], Optional[float]]] = DEFAULT_TARGETS
                   ) -> Dict[str, str]:
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

# ==========================
# РЕНДЕРИНГ ОТЧЁТА
# ==========================

REPORT_HEADER = """# Отчёт по профилю жирных кислот и рациону

**Комплекс:** {complex}  
**Период:** {period}  
**Дата отчёта:** {now}  
"""

ACID_ORDER = ["Лауриновая", "Линолевая", "Олеиновая", "Пальмитиновая", "Стеариновая"]

def copy_asset(src: str | Path, assets_dir: Path, new_name: Optional[str] = None) -> Optional[Path]:
    if not src:
        return None
    src_path = Path(src)
    if not src_path.exists():
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    dst_name = new_name if new_name else src_path.name
    dst = assets_dir / dst_name
    if src_path.resolve() != dst.resolve():
        shutil.copy2(src_path, dst)
    return dst


import re

ACID_ORDER = ["Лауриновая", "Линолевая", "Олеиновая", "Пальмитиновая", "Стеариновая"]


def to_file_url(p: str | Path) -> str:
    p = Path(p).resolve().as_posix()
    return "file:///" + quote(p, safe="/:")

def _infer_report_id(out_report_md: Path) -> str:
    # report_2025-10-07_1759855680.md → report_2025-10-07_1759855680
    stem = out_report_md.stem
    return stem[:-7] if stem.endswith("_report") else stem


def _graphics_dir_for(out_report_md: Path) -> Path | None:
    # ищем папку desktop рядом вверх по дереву
    for parent in out_report_md.resolve().parents:
        if parent.name.lower() == "desktop":
            rep_id = _infer_report_id(out_report_md)
            return (parent / "graphics" / rep_id).resolve()
    return None

def render_acid_graphs_first(graphics: dict[str, str],
                                 out_report_md: Path) -> str:
        """
        1) Если есть сводный график 'uni' → показываем только его (в самом начале).
        2) Иначе — показываем 5 графиков по кислотам (если найдены).
        """
        # 1) сводный 'uni'
        uni_path = _resolve_graph_path("uni", graphics, out_report_md, default_filename="uni_acids.png")
        print(uni_path)
        if uni_path:
            return (
                "\n## Важность рациона для жирных кислот (сводный график)\n\n"
                f'<img src="{to_file_url(uni_path)}" alt="uni_acids" width="960">\n'
            )

        # 2) по-кислотные графики
        lines = ["\n## Важность рациона для жирных кислот (графики)\n"]
        any_added = False
        for acid in ACID_ORDER:
            path = _resolve_graph_path(acid, graphics, out_report_md, default_filename=f"{acid}.png")
            if not path:
                continue
            lines.append(f'**{acid}**  \n<img src="{to_file_url(path)}" alt="{acid}" width="720">')
            any_added = True

        return ("\n\n".join(lines) + "\n") if any_added else ""


def render_other_graphs(graphics: dict[str, str], out_report_md: Path) -> str:
    """
    Секция «прочие графики».
    1) Если есть сводный график нутриентов 'uni_nutri' → показываем только его.
    2) Иначе — показываем графики по числовым ключам "0","1",...
       (или ищем их в desktop/graphics/<report_id>/<n>.png).
    """
    # 1) приоритет — сводный по нутриентам
    uni_nutri_path = _resolve_graph_path("uni_nutri", graphics, out_report_md, default_filename="uni_nutri.png")
    if uni_nutri_path:
        return (
            "\n## Нутриенты: сводный график\n\n"
            f'<img src="{to_file_url(uni_nutri_path)}" alt="uni_nutri" width="960">\n'
        )

    # 2) фоллбэк — числовые ключи
    keys = sorted([k for k in graphics.keys() if re.fullmatch(r"\d+", k)], key=lambda x: int(x))
    lines = ["\n## Прочие графики\n"]
    any_added = False

    if not keys:
        # если JSON не содержит числовых ключей — попробуем 0..63 рядом в graphics/<report_id>
        keys = [str(i) for i in range(64)]

    for k in keys:
        path = _resolve_graph_path(k, graphics, out_report_md, default_filename=f"{k}.png")
        if not path:
            continue
        lines.append(f'<img src="{to_file_url(path)}" alt="graph_{k}" width="720">')
        any_added = True

    return ("\n\n".join(lines) + "\n") if any_added else ""


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
    for k in ACID_ORDER:
        if k not in acids:
            continue
        v = acids[k]
        lo, hi = targets.get(k, (None, None))
        target = f"{'' if lo is None else f'{lo:.1f}'} — {'' if hi is None else f'{hi:.1f}'}".strip()
        if target == "—":
            target = "n/a"
        lines.append(f"| {k} | {v:.2f}% | {target} | {status.get(k,'')} |")
    return "\n".join(lines)

def render_importance_for_acids(importance_acid: Dict[str, Dict[str, float]], top_k: int = 6) -> str:
    def esc(s: str) -> str:
        # На всякий: экранируем вертикальные черты в названиях факторов
        return s.replace("|", "\\|")

    if not importance_acid:
        return ""

    lines = ["\n## Важность факторов для кислот (↑ повышает, ↓ понижает)\n"]

    for acid in ACID_ORDER:
        imp = importance_acid.get(acid)
        if not imp:
            continue

        items = sorted(imp.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]

        # Подзаголовок + пустая строка перед таблицей — критично для Markdown
        lines.append(f"### {acid}")
        lines.append("")  # <-- пустая строка обязательна

        # Таблица с выравниванием: название слева, вес справа, стрелка по центру
        lines.append("| Фактор | Вес | Направление |")
        lines.append("|:--|--:|:--:|")

        for name, w in items:
            arrow = "↑" if w > 0 else ("↓" if w < 0 else "·")
            lines.append(f"| {esc(name)} | {w:.2f} | {arrow} |")

        lines.append("")  # разделительная пустая строка между таблицами

    return "\n".join(lines)


def render_importance_for_nutrients(importance_nutrient: Dict[str, Dict[str, float]], top_k: int = 5) -> str:
    """
    Для каждого нутриента: какие категории/ингредиенты сильнее всего его **повышают** (Top+)
    и что, наоборот, связано со снижением (Top-).
    """
    if not importance_nutrient:
        return ""
    lines = ["\n## Что увеличить/снизить для изменения нутриентов\n"]
    for nutrient, imp_map in importance_nutrient.items():
        items = sorted(imp_map.items(), key=lambda kv: kv[1], reverse=True)
        top_pos = [(n, w) for n, w in items if w > 0][:top_k]
        top_neg = sorted([(n, w) for n, w in imp_map.items() if w < 0], key=lambda kv: kv[1])[:top_k]

        lines.append(f"**{nutrient}**")
        if top_pos:
            lines.append("_Чтобы повысить:_")
            for n, w in top_pos:
                lines.append(f"- {n} (вес {w:.2f})")
        if top_neg:
            lines.append("_Что обычно снижает:_")
            for n, w in top_neg:
                lines.append(f"- {n} (вес {w:.2f})")
        lines.append("")
    return "\n".join(lines)


def build_report(doc: dict, out_report_md: Path) -> str:
    meta = doc.get("meta", {}) or {}
    acids = doc.get("result_acids", {}) or {}
    graphics = doc.get("graphics", {}) or {}
    importance_acid = doc.get("importance_acid", {}) or {}
    importance_nutrient = doc.get("importance_nutrient", {}) or {}
    ration_rows = doc.get("ration_rows", []) or []
    ration = normalize_ration_rows(ration_rows)

    parts = [
        REPORT_HEADER.format(
            complex=meta.get("complex", "") or "-",
            period=meta.get("period", "") or "-",
            now=datetime.now().strftime("%Y-%m-%d %H:%M")
        ),
        # 1) первыми — графики кислот из соседней graphics/
        render_acid_graphs_first(graphics, out_report_md),
        # 2) таблица ЖК
        render_acids_table(acids),
        # 3) важности для кислот
        render_importance_for_acids(importance_acid),
        # 4) состав рациона
        render_ration_table(ration),
        # 5) нутриентные рекомендации
        render_importance_for_nutrients(importance_nutrient),
        # 6) прочие графики
        render_other_graphs(graphics, out_report_md),
        "\n> Дисклеймер: модельные ориентиры; проверяйте баланс рациона перед изменениями.\n"
    ]
    return "\n".join([p for p in parts if p])

# ==========================
# IO-ОБВЁРТКИ
# ==========================

def load_json(path: str | Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str | Path, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def write_report_files(input_json_path: str | Path,
                       out_report_md: str | Path | None = None,
                       update_json_with_report: bool = True) -> tuple[str, str]:
    input_json_path = Path(input_json_path)
    doc = load_json(input_json_path)

    if out_report_md is None:
        stem = input_json_path.with_suffix("").name
        out_report_md = input_json_path.with_name(stem + ".md")  # или "_report.md" — как тебе удобнее
    out_report_md = Path(out_report_md)

    report_md = build_report(doc, out_report_md=out_report_md)

    out_report_md.parent.mkdir(parents=True, exist_ok=True)
    out_report_md.write_text(report_md, encoding="utf-8")

    if update_json_with_report:
        doc["report"] = report_md
        save_json(input_json_path, doc)

    return str(input_json_path), str(out_report_md)


# ==========================
# CLI
# =========================


def _wrap_html(body: str, css: Optional[str]) -> str:
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css or CSS_DEFAULT}</style></head><body>{body}</body></html>'

def _ensure_layout(w: QWidget) -> QVBoxLayout:
    lay = w.layout()
    if lay is None:
        lay = QVBoxLayout(w)
        w.setLayout(lay)
    return lay

def _convert_md_to_html(md_text: str) -> str:
    if not _HAS_MD:
        safe = md_text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        return f"<pre>{safe}</pre>"
    return markdown.markdown(md_text, extensions=["extra","tables","fenced_code","sane_lists"])

# --- НОВОЕ: автоматический поиск desktop/graphics/<report_id> ---

def _find_desktop_root(md_path: Path) -> Optional[Path]:
    for p in md_path.resolve().parents:
        if p.name.lower() == "desktop":
            return p
    return None

def _infer_report_id(md_path: Path) -> str:
    # 'report_2025-10-07_1759855680.md' -> 'report_2025-10-07_1759855680'
    # '..._report.md' тоже поддержим: отрежем суффикс
    stem = md_path.stem
    return stem[:-7] if stem.endswith("_report") else stem

def _compute_graphics_dir(md_path: Path) -> Optional[Path]:
    desktop_root = _find_desktop_root(md_path)
    if desktop_root is None:
        return None
    report_id = _infer_report_id(md_path)
    return (desktop_root / "graphics" / report_id).resolve()

def _best_existing_path(src: str, base_dir: Path, graphics_dir: Optional[Path]) -> Optional[Path]:
    # URL? оставляем
    if re.match(r'^(?:https?|file)://', src, flags=re.I):
        return None
    # абсолютный win/posix путь?
    if re.match(r'^[A-Za-z]:[\\/]|^\\\\|^/', src):
        p = Path(src)
        return p if p.exists() else None
    # относительный:
    # 1) пытаемся рядом с .md
    p1 = (base_dir / src).resolve()
    if p1.exists():
        return p1
    # 2) если есть desktop/graphics/<report_id>, ищем там по basename
    if graphics_dir is not None:
        p2 = (graphics_dir / Path(src).name).resolve()
        if p2.exists():
            return p2
    return None

def _absolutize_img_srcs(html: str, base_dir: Path, graphics_dir: Optional[Path]) -> str:
    def _subst(m: re.Match) -> str:
        src, tail = m.group(1), m.group(2)
        found = _best_existing_path(src, base_dir, graphics_dir)
        if found is None:
            return m.group(0)  # оставить как есть (вдруг baseUrl покроет)
        url = QUrl.fromLocalFile(str(found)).toString()
        return f'<img src="{url}"{tail}>'
    return IMG_TAG_RE.sub(_subst, html)

# --- основной API ---

def create_md_webview(
    target: Union[Textish, QWidget],
    md_path: Union[str, Path],
    *,
    engine: str = "webengine",
    css: Optional[str] = None,
) -> QWidget:
    md_path = Path(md_path)
    base_dir = md_path.parent.resolve()
    base_url = QUrl.fromLocalFile(str(base_dir) + "/")

    # 1) конвертируем MD -> HTML
    md_text = md_path.read_text(encoding="utf-8")
    body_html = _convert_md_to_html(md_text)
    html = _wrap_html(body_html, css)

    # 2) превращаем все src в абсолютные file://, подхватывая desktop/graphics/<report_id>
    graphics_dir = _compute_graphics_dir(md_path)
    html = _absolutize_img_srcs(html, base_dir, graphics_dir)

    # 3) отрисовка в заданный виджет
    if isinstance(target, (QTextEdit, QTextBrowser)):
        if isinstance(target, QTextBrowser):
            target.setOpenExternalLinks(True)
        target.document().setBaseUrl(base_url)
        target.setHtml(html)
        return target

    lay = _ensure_layout(target)
    viewer = target.property("_md_view")
    if viewer is not None:
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            if isinstance(viewer, QWebEngineView):
                viewer.setHtml(html, baseUrl=base_url)
                return viewer
        except Exception:
            pass
        if isinstance(viewer, QTextBrowser):
            viewer.document().setBaseUrl(base_url)
            viewer.setHtml(html)
            return viewer

    if engine in ("auto", "webengine"):
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            viewer = QWebEngineView()
            viewer.setHtml(html, baseUrl=base_url)
            lay.addWidget(viewer)
            target.setProperty("_md_view", viewer)
            return viewer
        except Exception:
            pass

    viewer = QTextBrowser()
    viewer.setOpenExternalLinks(True)
    viewer.document().setBaseUrl(base_url)
    viewer.setHtml(html)
    lay.addWidget(viewer)
    target.setProperty("_md_view", viewer)
    return viewer
def create_md_webview_for_Admin(
    target: Union[Textish, QWidget],
    md_text: str,
    *,
    base_dir: Union[str, Path] = None,
    graphics_dir: Union[str, Path] = None,
    engine: str = "webengine",
    css: Optional[str] = None,
) -> QWidget:
    """
    Создает или обновляет веб-просмотрщик для отображения Markdown текста БЕЗ изображений
    и без раздела "Важность рациона для жирных кислот (графики)".
    
    Args:
        target: Целевой виджет или контейнер
        md_text: Готовый текст в формате Markdown
        base_dir: Базовая директория для ресурсов (по умолчанию - текущая)
        graphics_dir: Директория с изображениями (по умолчанию - base_dir/graphics)
        engine: Движок для отображения ('webengine' или 'textbrowser')
        css: CSS стили для кастомизации
    """
    # Устанавливаем базовые директории
    if base_dir is None:
        base_dir = Path.cwd()
    base_dir = Path(base_dir).resolve()
    base_url = QUrl.fromLocalFile(str(base_dir) + "/")
    
    # Вычисляем директорию с графикой
    if graphics_dir is None:
        graphics_dir = base_dir / "graphics"
    else:
        graphics_dir = Path(graphics_dir).resolve()

    # 1) Удаляем раздел с графиками жирных кислот
    md_text_without_graphics_section = _remove_fatty_acids_graphics_section(md_text)

    # 2) Удаляем изображения из оставшегося Markdown текста
    md_text_cleaned = _remove_images_from_markdown(md_text_without_graphics_section)

    # 3) конвертируем MD -> HTML
    body_html = _convert_md_to_html(md_text_cleaned)
    html = _wrap_html(body_html, css)

    # 4) отрисовка в заданный виджет
    if isinstance(target, (QTextEdit, QTextBrowser)):
        if isinstance(target, QTextBrowser):
            target.setOpenExternalLinks(True)
        target.document().setBaseUrl(base_url)
        target.setHtml(html)
        return target

    lay = _ensure_layout(target)
    viewer = target.property("_md_view")
    if viewer is not None:
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            if isinstance(viewer, QWebEngineView):
                viewer.setHtml(html, baseUrl=base_url)
                return viewer
        except Exception:
            pass
        if isinstance(viewer, QTextBrowser):
            viewer.document().setBaseUrl(base_url)
            viewer.setHtml(html)
            return viewer

    if engine in ("auto", "webengine"):
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            viewer = QWebEngineView()
            viewer.setHtml(html, baseUrl=base_url)
            lay.addWidget(viewer)
            target.setProperty("_md_view", viewer)
            return viewer
        except Exception:
            pass

    viewer = QTextBrowser()
    viewer.setOpenExternalLinks(True)
    viewer.document().setBaseUrl(base_url)
    viewer.setHtml(html)
    lay.addWidget(viewer)
    target.setProperty("_md_view", viewer)
    return viewer


def _remove_fatty_acids_graphics_section(md_text: str) -> str:
    """
    Удаляет раздел "Важность рациона для жирных кислот (графики)" и все подразделы с кислотами.
    """
    import re
    
    # Удаляем весь раздел от "## Важность рациона для жирных кислот (графики)" 
    # до следующего заголовка "##" или конца текста
    pattern = r'## Важность рациона для жирных кислот \(графики\).*?(?=##|\Z)'
    md_text = re.sub(pattern, '', md_text, flags=re.DOTALL)
    
    return md_text


def _remove_images_from_markdown(md_text: str) -> str:
    """
    Удаляет все изображения из Markdown текста.
    
    Удаляет:
    - ![alt](src) - стандартный синтаксис
    - <img> теги - HTML синтаксис
    - ссылки на изображения в тексте
    """
    import re
    
    # Удаляем стандартный Markdown синтаксис изображений: ![alt](src)
    md_text = re.sub(r'!\[.*?\]\(.*?\)', '', md_text)
    
    # Удаляем HTML теги <img>
    md_text = re.sub(r'<img[^>]*>', '', md_text, flags=re.IGNORECASE)
    
    # Удаляем расширенные HTML теги <image> (редко используется)
    md_text = re.sub(r'<image[^>]*>', '', md_text, flags=re.IGNORECASE)
    
    return md_text

if __name__ == "__main__":
    write_report_files(
        input_json_path="desktop/reports/report_2025-10-07_1759855680.json",
        out_report_md="output2.md",
        update_json_with_report=True,
        copy_images=True
    )
    print("Готово.")
