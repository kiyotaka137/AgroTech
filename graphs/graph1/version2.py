import pandas as pd
import matplotlib.pyplot as plt

def plot_acid_measurements(data):
    """
    Строит график для кислот:
    - acid: номер/название кислоты
    - value: измеренный показатель (рисуется как колонка)
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

    fig, ax = plt.subplots(figsize=(10, 6))

    # Рисуем колонки вручную с нужными цветами
    colors = ["steelblue" if inside else "red" for inside in df["inside"]]
    ax.bar(df["acid"], df["value"], color=colors, width=0.6, zorder=2)

    # Добавляем допустимый диапазон и "шапки"
    for _, r in df.iterrows():
        ax.vlines(r['acid'], r['lower'], r['upper'], color="black", linewidth=2, zorder=3)
        ax.plot([r['acid'] - 0.15, r['acid'] + 0.15], [r['lower'], r['lower']], color="black", linewidth=2, zorder=3)
        ax.plot([r['acid'] - 0.15, r['acid'] + 0.15], [r['upper'], r['upper']], color="black", linewidth=2, zorder=3)

    # Настройки графика
    ax.set_xlabel("Номер кислоты")
    ax.set_ylabel("Показатель")
    ax.set_title("Измерения кислот и допустимые диапазоны")
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    plt.tight_layout()
    plt.show()
data = {
    "acid": [1, 2, 3, 4, 5],
    "value": [7.5, 2.0, 6.8, 8.9, 4.1],
    "lower": [6.0, 3.5, 5.0, 7.0, 4.5],
    "upper": [8.0, 5.0, 7.0, 9.5, 6.0],
}

plot_acid_measurements(data)
