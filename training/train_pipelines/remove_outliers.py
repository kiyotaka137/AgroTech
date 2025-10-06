#!/usr/bin/env python3
# remove_outliers.py
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

# Берём сборку датасета из вашего проекта
from ohe_lin import get_ohe_train_test_data


def _linear_in_input_space(pipeline, X):
    """
    Возвращает коэффициенты и интерсепт линейной модели (Ridge/LinearRegression)
    в ИСХОДНОМ масштабе признаков, даже если модель была обучена в стандартизированном.
    """
    # Ожидаем Pipeline(StandardScaler(), Ridge/LinearRegression)
    scaler = None
    lr = None
    for step in pipeline.steps:
        if isinstance(step[1], StandardScaler):
            scaler = step[1]
        else:
            lr = step[1]

    if lr is None or scaler is None:
        raise ValueError("Ожидается Pipeline(StandardScaler() -> LinearModel).")

    w_scaled = lr.coef_.ravel()  # в пространстве z
    b_scaled = lr.intercept_.item() if np.ndim(lr.intercept_) else float(lr.intercept_)

    # Переход к исходному пространству x
    scale = scaler.scale_.copy()
    scale[scale == 0] = 1.0  # защита от деления на 0
    mu = scaler.mean_

    w_input = w_scaled / scale
    b_input = b_scaled - float(np.dot(w_scaled, mu / scale))
    return w_input, b_input


def _fit_global_model(X, y, alpha=0.01):
    pipe = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    pipe.fit(X, y)
    return pipe


def _residuals_for_feature(model, X, y, j):
    """
    Резидуалы относительно 'линии' по признаку j из общей модели,
    где остальные признаки зафиксированы на их средних значениях.
    """
    w, b = _linear_in_input_space(model, X)
    X_mean = np.asarray(X).mean(axis=0)

    # Предсказание на линии: y_line(x_j) = w_j * x_j + (b + sum_{i!=j} w_i * mean_i)
    offset = b + float(np.dot(w, X_mean) - w[j] * X_mean[j])
    y_line = w[j] * np.asarray(X)[:, j] + offset

    return y - y_line


def _mad_mask(residuals, k=3.0):
    med = np.median(residuals)
    mad = np.median(np.abs(residuals - med))
    robust_sigma = 1.4826 * mad
    if robust_sigma == 0:
        # Если все резидуалы ~ константа, выбросов нет
        return np.zeros_like(residuals, dtype=bool)
    return np.abs(residuals - med) > (k * robust_sigma)


def compute_outlier_mask(X, y, alpha=0.01, k=3.0, features=None):
    """
    Возвращает булеву маску выбросов (True = выброс) по объединению (union)
    выбросов по всем признакам (или по подмножеству features).
    """
    model = _fit_global_model(X, y, alpha=alpha)

    if features is None:
        feat_idx = range(X.shape[1])
    else:
        name_to_idx = {name: i for i, name in enumerate(X.columns)}
        feat_idx = [name_to_idx[f] for f in features if f in name_to_idx]

    masks = []
    for j in feat_idx:
        res = _residuals_for_feature(model, X.values, y.values, j)
        mask_j = _mad_mask(res, k=k)
        masks.append(mask_j)

    if not masks:
        return np.zeros(len(y), dtype=bool)

    # Объединение по всем признакам
    outlier_union = np.logical_or.reduce(masks)
    return outlier_union


def main():
    parser = argparse.ArgumentParser(description="Удаление выбросов из OHE-датасета (union по признакам)")
    parser.add_argument("--column-coef", default="% СВ", help="Название колонки с коэффициентом в исходных CSV")
    parser.add_argument("--target-name", default="target", help="Имя столбца таргета в собранном OHE датафрейме")
    parser.add_argument("--alpha", type=float, default=0.01, help="Ridge(alpha) для глобальной линейной модели")
    parser.add_argument("--k", type=float, default=3.0, help="Порог MAD в сигмах (обычно 2.5–3.5)")
    parser.add_argument("--only-features", nargs="*", default=None, help="Список признаков для поиска выбросов (по именам)")
    parser.add_argument("--save-dir", default="clean_data", help="Куда сохранить результаты")
    args = parser.parse_args()

    df = get_ohe_train_test_data(column_coef=args.column_coef, target_name=args.target_name)
    X = df.drop(columns=[args.target_name])
    y = df[args.target_name]

    mask_outliers = compute_outlier_mask(X, y, alpha=args.alpha, k=args.k, features=args.only_features)
    kept_mask = ~mask_outliers

    df_clean = df.loc[kept_mask].reset_index(drop=True)

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем
    clean_csv = save_dir / "ohe_clean.csv"
    dropped_csv = save_dir / "ohe_dropped_indices.csv"
    meta_json = save_dir / "outlier_meta.json"

    df_clean.to_csv(clean_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame({"dropped_idx": np.where(mask_outliers)[0]}).to_csv(dropped_csv, index=False)

    meta = {
        "method": "global-linear + MAD",
        "alpha": args.alpha,
        "k": args.k,
        "column_coef": args.column_coef,
        "target_name": args.target_name,
        "n_total": int(len(df)),
        "n_dropped": int(mask_outliers.sum()),
        "n_kept": int(kept_mask.sum()),
        "only_features": args.only_features,
    }
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved cleaned data to: {clean_csv}")
    print(f"Dropped indices to:   {dropped_csv}")
    print(f"Meta to:              {meta_json}")


if __name__ == "__main__":
    main()
