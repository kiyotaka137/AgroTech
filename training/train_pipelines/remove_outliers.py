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

# берём сборку датасета из проекта
from ohe_lin import get_ohe_train_test_data


def _linear_in_input_space(pipeline, X):
    """
    Вернёт коэффициенты и интерсепт линейной модели в ИСХОДНОМ масштабе,
    даже если обучали в стандартизированном (Pipeline(StandardScaler -> Ridge)).
    """
    scaler = None
    lr = None
    for _, step in pipeline.steps:
        if isinstance(step, StandardScaler):
            scaler = step
        else:
            lr = step

    if lr is None or scaler is None:
        raise ValueError("Ожидается Pipeline(StandardScaler() -> LinearModel).")

    w_scaled = lr.coef_.ravel()
    b_scaled = lr.intercept_.item() if np.ndim(lr.intercept_) else float(lr.intercept_)

    scale = scaler.scale_.copy()
    scale[scale == 0] = 1.0
    mu = scaler.mean_

    w_input = w_scaled / scale
    b_input = b_scaled - float(np.dot(w_scaled, mu / scale))
    return w_input, b_input


def _fit_global_model(X, y, alpha=0.01):
    pipe = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
    pipe.fit(X, y)
    return pipe


def _residuals_for_feature(model, X, y, j):
    """Резидуалы относительно 'линии' по признаку j из общей модели."""
    w, b = _linear_in_input_space(model, X)
    X_mean = np.asarray(X).mean(axis=0)
    offset = b + float(np.dot(w, X_mean) - w[j] * X_mean[j])
    y_line = w[j] * np.asarray(X)[:, j] + offset
    return y - y_line


def _mad_mask(residuals, k=3.0):
    med = np.median(residuals)
    mad = np.median(np.abs(residuals - med))
    robust_sigma = 1.4826 * mad
    if robust_sigma == 0:
        return np.zeros_like(residuals, dtype=bool)
    return np.abs(residuals - med) > (k * robust_sigma)


def compute_outlier_mask(X, y, alpha=0.01, k=3.0, features=None):
    """
    Булева маска выбросов (True=выброс) — объединение выбросов по всем/выбранным признакам.
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
        masks.append(_mad_mask(res, k=k))

    if not masks:
        return np.zeros(len(y), dtype=bool)

    return np.logical_or.reduce(masks)


def main():
    parser = argparse.ArgumentParser(description="Удаление выбросов из OHE-датасета (union по признакам)")
    parser.add_argument("--column-coef", default="% СВ", help="Колонка с коэффициентом в исходных CSV")
    parser.add_argument("--target-name", default="target", help="Имя столбца таргета (если нет — возьмём 'target')")
    parser.add_argument("--alpha", type=float, default=0.01, help="Ridge(alpha) для общей линейной модели")
    parser.add_argument("--k", type=float, default=3.0, help="Порог MAD в сигмах")
    parser.add_argument("--only-features", nargs="*", default=None, help="Список имён признаков для поиска выбросов")
    parser.add_argument("--save-dir", default="clean_data", help="Куда сохранить результаты")
    args = parser.parse_args()

    # get_ohe_train_test_data НЕ принимает target_name, просто читаем df
    df = get_ohe_train_test_data(column_coef=args.column_coef)

    # аккуратно выбираем целевую колонку
    target_col = args.target_name if args.target_name in df.columns else (
        "target" if "target" in df.columns else None
    )
    if target_col is None:
        raise ValueError(f"Не нашли колонку таргета: ни '{args.target_name}', ни 'target' нет в df.columns")

    X = df.drop(columns=[target_col])
    y = df[target_col]

    mask_outliers = compute_outlier_mask(X, y, alpha=args.alpha, k=args.k, features=args.only_features)
    kept_mask = ~mask_outliers

    df_clean = df.loc[kept_mask].reset_index(drop=True)

    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

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
        "target_col": target_col,
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
