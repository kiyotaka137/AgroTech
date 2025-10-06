import pandas as pd
import numpy as np
import joblib as jl


def predict_from_file(model_path: str, input_csv: str, output_csv: str):
    """
    Аргументы:
        model_path: путь к файлу модели (.pkl)
        input_csv: CSV с признаками (без столбца таргета)
        output_csv: путь для сохранения CSV с предсказаниями
    """
    model = jl.load(model_path)
    print(f"Модель загружена: {model_path}")

    data = pd.read_csv(input_csv)
    print(f"Загружено {len(data)} строк из {input_csv}")

    preds = model.predict(data)

    data["prediction"] = preds

    data.to_csv(output_csv, index=False)
    print(f"Результаты сохранены в {output_csv}")
