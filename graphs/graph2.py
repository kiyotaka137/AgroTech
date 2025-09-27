import pandas as pd
import seaborn as sns
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


def plot_multiple_dfs(dfs: list, titles: list = None, nrows: int = 1, ncols: int = None):
    """
    Строит несколько датафреймов на одной фигуре.
    dfs: список DataFrame
    titles: список названий
    nrows, ncols: разбиение на подграфики (по умолчанию всё в одну строку)
    """
    n = len(dfs)
    if ncols is None:
        ncols = n
    fig, axes = plt.subplots(nrows, ncols, figsize=(6*ncols, 5*nrows))
    axes = axes.flatten()  # превращаем в список для удобства
    
    for i, df in enumerate(dfs):
        sns.barplot(data=df, x="ingredient", y="coef", palette="viridis", ax=axes[i])
        axes[i].set_xlabel("Ингредиенты")
        axes[i].set_ylabel("Коэффициент")
        axes[i].tick_params(axis="x", rotation=30)
        if titles and i < len(titles):
            axes[i].set_title(titles[i])
        else:
            axes[i].set_title(f"График {i+1}")
    
    # скрываем пустые оси, если графиков меньше чем мест
    for j in range(i+1, len(axes)):
        axes[j].axis("off")
    
    plt.tight_layout()
    plt.show()


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
