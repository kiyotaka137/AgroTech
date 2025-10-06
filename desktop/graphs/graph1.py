import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Optional, Sequence
import matplotlib.axes
def plot_acid_measurements(data, ax: Optional[matplotlib.axes.Axes] = None):
    """
    Рисует измерения кислот и допустимые диапазоны на переданном ax.
    Если ax is None -> создаёт фигуру и возвращает её (функция НЕ вызывает plt.show()).

    data: dict или DataFrame с колонками ['acid','value','lower','upper']
    ax: matplotlib.axes.Axes или None
    """
    # Подготовка DataFrame
    if isinstance(data, dict):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    # Проверки
    required = {'acid', 'value', 'lower', 'upper'}
    if not required.issubset(set(df.columns)):
        raise ValueError(f"Ожидаются колонки: {required}")

    # Признак внутри диапазона
    df['inside'] = df.apply(lambda r: r['lower'] <= r['value'] <= r['upper'], axis=1)

    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
        created_fig = True
    else:
        fig = ax.figure

    # Рисуем толстые вертикальные полосы (диапазоны)
    for _, r in df.iterrows():
        # x может быть числом или категорией; делаем vlines по значению x
        ax.vlines(r['acid'], r['lower'], r['upper'],
                  linewidth=12, alpha=0.25, zorder=1)

    # Рисуем точки измерений (черные если внутри, красные если нет)
    sns.scatterplot(
        x='acid', y='value', data=df, s=120, hue='inside',
        palette={True: "black", False: "red"}, legend=False, zorder=3, ax=ax
    )

    # "Шапки" на концах диапазонов — маленькие горизонтальные штрихи
    # Подбираем смещение по x для визуала (если x числовой)
    try:
        xs = pd.to_numeric(df['acid'], errors='coerce')
        numeric_x = not xs.isna().all()
    except Exception:
        numeric_x = False

    if numeric_x:
        for _, r in df.iterrows():
            ax.plot([r['acid'] - 0.12, r['acid'] + 0.12],
                    [r['lower'], r['lower']], linewidth=2, zorder=2)
            ax.plot([r['acid'] - 0.12, r['acid'] + 0.12],
                    [r['upper'], r['upper']], linewidth=2, zorder=2)
    else:
        # для нечисловых категорий рисуем горизонтальные линии через трансформацию данных
        for i, (_idx, r) in enumerate(df.iterrows()):
            ax.hlines(r['lower'], i - 0.12, i + 0.12, linewidth=2, zorder=2)
            ax.hlines(r['upper'], i - 0.12, i + 0.12, linewidth=2, zorder=2)

    # Оформление
    ax.set_xlabel("Номер кислоты")
    ax.set_ylabel("Показатель")
    ax.set_title("Измерения кислот и допустимые диапазоны")

    # Если x категориальный — явно выставим xticks
    if numeric_x:
        ax.set_xticks(df['acid'])
    else:
        ax.set_xticks(range(len(df)))
        ax.set_xticklabels(df['acid'])

    ax.grid(axis='y', linestyle='--', alpha=0.4)

    if created_fig:
        fig.tight_layout()
        return fig  # вызывающий код может обернуть в FigureCanvas и отобразить
    # иначе — ничего не возвращаем (рисование произошло на переданном ax)

