import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def plot_acid_measurements(data):
    """
    Строит график для кислот:
    - acid: номер/название кислоты
    - value: измеренный показатель
    - lower: нижняя граница допустимого диапазона
    - upper: верхняя граница допустимого диапазона
    """
    # Преобразуем словарь в DataFrame, если нужно
    if isinstance(data, dict):
        df = pd.DataFrame(data)
    else:
        df = data.copy()

    # Флаг: внутри ли допустимого диапазона
    df['inside'] = df.apply(lambda r: r['lower'] <= r['value'] <= r['upper'], axis=1)

    # Создаём график
    fig, ax = plt.subplots(figsize=(10, 6))

    # Рисуем допустимые диапазоны как толстые вертикальные полосы
    for _, r in df.iterrows():
        ax.vlines(r['acid'], r['lower'], r['upper'], linewidth=12, alpha=0.25, zorder=1)

    # Рисуем точки измерений
    sns.scatterplot(
        x='acid', y='value', data=df, s=120, hue='inside',
        palette={True: "black", False: "red"}, legend=False, zorder=3, ax=ax
    )

    # Добавляем "шапки" на концах диапазонов
    for _, r in df.iterrows():
        ax.plot([r['acid'] - 0.12, r['acid'] + 0.12], [r['lower'], r['lower']], linewidth=2, zorder=2)
        ax.plot([r['acid'] - 0.12, r['acid'] + 0.12], [r['upper'], r['upper']], linewidth=2, zorder=2)

    # Подписи и оформление
    ax.set_xlabel("Номер кислоты")
    ax.set_ylabel("Показатель")
    ax.set_title("Измерения кислот и допустимые диапазоны")
    ax.set_xticks(df['acid'])
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    plt.show()
data = {
    "acid": [1, 2, 3, 4, 5],
    "value": [7.5, 4.2, 6.8, 8.9, 5.1],
    "lower": [6.0, 3.5, 5.0, 7.0, 4.5],
    "upper": [8.0, 5.0, 7.0, 9.5, 6.0],
}

plot_acid_measurements(data)
