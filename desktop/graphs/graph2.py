import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Optional, Sequence
import matplotlib.axes
import numpy as np
import matplotlib.pyplot as plt

def parse_coeffs(raw: str):
    """Парсит сырой текст в DataFrame с колонками ['ingredient', 'coef']"""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    records = []
    for ln in lines:
        parts = ln.rsplit(maxsplit=1)
        if len(parts) == 2:
            name, coef_str = parts
            try:
                coef = float(coef_str.replace(',', '.'))
            except:
                coef = None
            records.append({'ingredient': name, 'coef': coef})
    return pd.DataFrame(records)

def plot_multiple_dfs(dfs: List[pd.DataFrame],
                      titles: Optional[List[str]] = None,
                      axes: Optional[Sequence[plt.Axes]] = None,
                      nrows: int = 1,
                      ncols: Optional[int] = None):
    """
    Обновлённая версия — использует matplotlib.axes.Axes.bar вместо sns.barplot,
    чтобы избежать FutureWarning при передаче palette без hue.
    Возвращает Figure если сама создаёт фигуру (axes is None).
    """
    n = len(dfs)
    if ncols is None:
        ncols = n

    created_fig = False
    if axes is None:
        fig, raw_axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
        created_fig = True
        if hasattr(raw_axes, "flatten"):
            axes_list = list(raw_axes.flatten())
        else:
            axes_list = [raw_axes]
    else:
        if hasattr(axes, "flatten"):
            axes_list = list(axes.flatten())
            fig = axes_list[0].figure if len(axes_list) else None
        else:
            try:
                axes_list = list(axes)
                fig = axes_list[0].figure if len(axes_list) else None
            except TypeError:
                axes_list = [axes]
                fig = axes_list[0].figure

    if len(axes_list) < n:
        raise ValueError("Недостаточно осей (axes) для рисования всех dfs")

    for i, df in enumerate(dfs):
        ax = axes_list[i]
        if not {'ingredient', 'coef'}.issubset(set(df.columns)):
            raise ValueError("Каждый df должен содержать колонки ['ingredient','coef']")

        # Простой matplotlib bar с цветами из colormap viridis
        x = np.arange(len(df))
        colors = plt.cm.viridis(np.linspace(0, 1, len(df)))
        ax.bar(x, df['coef'].values, color=colors)
        ax.set_xticks(x)
        ax.set_xticklabels(df['ingredient'], rotation=30, ha='right')

        ax.set_xlabel("Ингредиенты")
        ax.set_ylabel("Коэффициент")
        if titles and i < len(titles):
            ax.set_title(titles[i])
        else:
            ax.set_title(f"График {i+1}")

    # скрываем пустые оси
    for j in range(n, len(axes_list)):
        axes_list[j].axis("off")

    if created_fig:
        fig.tight_layout()
        return fig



# --- примеры данных ---
raw1 = """
Кукуруза 0.87
Ячмень 0.69
Соль 0.10
"""

raw2 = """
Кукуруза 0.92
Ячмень 0.71
Соль 0.15
"""

raw3 = """
Кукуруза 0.78
Ячмень 0.65
Соль 0.12
"""

raw4 = """
Кукуруза 0.95
Ячмень 0.72
Соль 0.20
"""

raw5 = """
Кукуруза 0.81
Ячмень 0.68
Соль 0.11
"""

raw6 = """
Кукуруза 0.89
Ячмень 0.70
Соль 0.18
"""

# --- парсим в датафреймы ---
df1 = parse_coeffs(raw1)
df2 = parse_coeffs(raw2)
df3 = parse_coeffs(raw3)
df4 = parse_coeffs(raw4)
df5 = parse_coeffs(raw5)
df6 = parse_coeffs(raw6)

# --- строим 6 графиков в сетке 2x3 ---
plot_multiple_dfs(
    [df1, df2, df3, df4, df5, df6],
    titles=["Рацион 1", "Рацион 2", "Рацион 3", "Рацион 4", "Рацион 5", "Рацион 6"],
    nrows=2, ncols=3
)
