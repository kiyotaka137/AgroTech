# one_bin_classification.py
"""
Бинарная линейная классификация по диапазону значения ЦЕЛЕВОГО СТОЛБЦА из targets.csv.

ВАЖНО: в вашем targets.csv НЕТ колонки "Кислотность". Поэтому по умолчанию
используем колонку "Лауриновая" (есть в вашем файле). Если хотите другой столбец,
передайте --target-col "<имя_колонки_в_targets.csv>".

Скрипт:
- Собирает OHE-признаки по вашей схеме (training.name_mapping, training.uniq_ration).
- Берёт целевой столбец из targets.csv (по умолчанию "Лауриновая") и бинаризует:
  1, если значение в [range_min, range_max], иначе 0.
- Пайплайн: SimpleImputer -> StandardScaler -> LogisticRegression(class_weight='balanced').
- Подбирает C по ROC-AUC (Stratified KFold) на обучающей части.
- Подбирает ПОРОГ по OOF-предсказаниям (максимальный F1) на обучающей части.
- Оценивает на тесте и печатает метрики + confusion matrix.
- По желанию сохраняет model.joblib и meta.json (порог, список фич, C, метрики).

Пример запуска:
python one_bin_classification.py \
  --target-col "Лауриновая" \
  --range-min 2.0 --range-max 4.4 \
  --column-coef "% СВ" \
  --cv-splits 5 \
  --save-dir ./clf_artifacts
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Ожидается в вашем проекте (как в ohe_lin.py / plot.py)
try:
    from training import name_mapping, uniq_ration
except Exception as e:
    raise ImportError(
        "Не удалось импортировать training.name_mapping и training.uniq_ration. "
        "Убедитесь, что training.py доступен в PYTHONPATH."
    ) from e

# --- Пути по умолчанию (как в ваших скриптах) ---
target_path = "../data/Для Хакатона/targets.csv"
rations_path = "../parsed_data/{table}.csv"

# --- Константы ---
DROP_FEATURES_DEFAULT = ["сорго", "подсолнечник", "лен", "сено", "пшеница", "зерно"]
C_GRID = np.logspace(-3, 3, 21)  # более плотная сетка
# ВАЖНО: по умолчанию берём реальную колонку из вашего targets.csv
DEFAULT_TARGET_COL = "Лауриновая"
# Ваш диапазон для положительного класса:
DEFAULT_RANGE = (2.0, 4.4)

# ------------------------------ Утилиты ------------------------------
def _to_float(x):
    """Безопасное преобразование в float (учитывает запятые, пустые строки, None)."""
    try:
        if isinstance(x, str):
            x = x.strip().replace(",", ".")
            if x == "" or x.lower() in {"nan", "none"}:
                return np.nan
        return float(x)
    except Exception:
        return np.nan


def _read_ration_table(name: str, column_coef: str) -> pd.DataFrame:
    """Читает CSV рациона и возвращает DataFrame с колонками 'Ингредиенты' и column_coef."""
    path = rations_path.format(table=str(name).strip())
    df = pd.read_csv(path, sep="|")
    if "Ингредиенты" not in df.columns:
        raise ValueError(f"В файле '{path}' нет колонки 'Ингредиенты'.")
    if column_coef not in df.columns:
        raise ValueError(f"В файле '{path}' нет колонки '{column_coef}'. Доступны: {list(df.columns)}")
    return df


def get_ohe_dataset(
    *,
    column_coef: str = "% СВ",
    target_col: str = DEFAULT_TARGET_COL,
    drop_features: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    Собирает датасет:
      - OHE-признаки по ration-файлам (суммируем долю по каждому ингредиенту)
      - колонка 'measure' из targets[target_col]
    Возвращает DataFrame: [uniq_ration ... , measure]
    """
    targets = pd.read_csv(target_path, sep=";")
    if target_col not in targets.columns:
        raise ValueError(
            f"Колонка '{target_col}' не найдена в targets.csv. "
            f"Доступны: {list(targets.columns)}"
        )

    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_ration)}
    data: List[List[float]] = []

    for row_idx, ration_name in enumerate(targets["Рацион"].values):
        # Чистим имя файла рациона
        if isinstance(ration_name, str) and ration_name.endswith("."):
            ration_name = ration_name[:-1]

        # OHE-вектор
        vec = [0.0] * len(uniq_ration)

        ration_df = _read_ration_table(ration_name, column_coef)
        for i, ingr in enumerate(ration_df["Ингредиенты"]):
            clear = name_mapping.get(ingr, ingr)  # fallback на оригинал, если нет в словаре
            if clear not in uniq_dict:
                warnings.warn(f"Ингредиент '{clear}' отсутствует в uniq_ration — пропускаю.")
                continue
            col_idx = uniq_dict[clear]
            coef_val = _to_float(ration_df.loc[i, column_coef])
            if np.isnan(coef_val):
                coef_val = 0.0
            vec[col_idx] += float(coef_val)

        measure = _to_float(targets.loc[row_idx, target_col])
        data.append(vec + [measure])

    columns = list(uniq_ration) + ["measure"]
    df = pd.DataFrame(data, columns=columns)

    # Удалим заранее известные «плохие» признаки (если присутствуют)
    if drop_features:
        drop_cols = [c for c in drop_features if c in df.columns]
        if drop_cols:
            df = df.drop(columns=drop_cols)

    return df


@dataclass
class FitResult:
    best_estimator: any
    best_C: float
    oof_threshold: float
    report: str
    test_metrics: dict
    confusion: List[List[int]]


def build_estimator(C: float = 1.0, class_weight: str | dict | None = "balanced"):
    """Pipeline линейного классификатора."""
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(with_mean=True),
        LogisticRegression(
            C=C,
            max_iter=2000,
            solver="lbfgs",
            class_weight=class_weight,
        ),
    )


def tune_C(X: np.ndarray, y: np.ndarray, *, cv_splits: int = 5) -> Tuple[any, float]:
    """Подбираем C по ROC-AUC на Stratified KFold."""
    base = build_estimator()
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
    grid = GridSearchCV(
        estimator=base,
        param_grid={"logisticregression__C": C_GRID},
        scoring="roc_auc",
        cv=cv,
        refit=True,
        n_jobs=-1,
    )
    grid.fit(X, y)
    return grid.best_estimator_, float(grid.best_params_["logisticregression__C"])


def find_best_threshold_oof(estimator, X: np.ndarray, y: np.ndarray, *, cv_splits: int = 5) -> float:
    """
    Строит OOF-предсказания вероятностей и выбирает порог, максимизирующий F1.
    Возвращает порог (float в [0, 1]).
    """
    cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=1337)
    y_scores = np.zeros_like(y, dtype=float)

    for tr_idx, val_idx in cv.split(X, y):
        est = clone(estimator)
        est.fit(X[tr_idx], y[tr_idx])
        proba = est.predict_proba(X[val_idx])[:, 1]
        y_scores[val_idx] = proba

    precisions, recalls, thresholds = precision_recall_curve(y, y_scores)
    # precision_recall_curve возвращает thresholds на 1 короче
    f1s = 2 * precisions[:-1] * recalls[:-1] / np.clip(precisions[:-1] + recalls[:-1], 1e-12, None)
    best_idx = int(np.nanargmax(f1s))
    best_thr = float(thresholds[best_idx])
    return best_thr


def evaluate_scores(y_true: np.ndarray, y_score: np.ndarray, thr: float) -> Tuple[dict, np.ndarray]:
    """Считает метрики и матрицу ошибок при заданном пороге."""
    y_pred = (y_score >= thr).astype(int)

    metrics = {
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }
    cm = confusion_matrix(y_true, y_pred)
    return metrics, cm


def fit_and_report(
    df: pd.DataFrame,
    *,
    range_min: float,
    range_max: float,
    test_size: float = 0.2,
    seed: int = 42,
    cv_splits: int = 5,
    save_dir: str | None = None,
) -> FitResult:
    """
    Основной сценарий обучения и отчёта.
    """
    # бинаризация таргета
    measure = df["measure"].to_numpy().astype(float)
    y = ((measure >= range_min) & (measure <= range_max)).astype(int)

    feature_cols = [c for c in df.columns if c != "measure"]
    X = df[feature_cols].to_numpy().astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    # подбор C
    best_est, best_C = tune_C(X_train, y_train, cv_splits=cv_splits)

    # подбор порога по OOF
    best_thr = find_best_threshold_oof(best_est, X_train, y_train, cv_splits=cv_splits)

    # финальное обучение и оценка
    best_est.fit(X_train, y_train)
    test_scores = best_est.predict_proba(X_test)[:, 1]
    test_metrics, cm = evaluate_scores(y_test, test_scores, thr=best_thr)

    report = (
        f"Лучший C по ROC-AUC: {best_C:.6g}\n"
        f"Подобранный порог (по OOF, макс F1): {best_thr:.4f}\n"
        f"Доли классов (train): 1 -> {y_train.mean():.3f}, 0 -> {1 - y_train.mean():.3f}\n"
        f"Метрики на тесте (порог={best_thr:.4f}):\n"
        f"  ROC-AUC: {test_metrics['roc_auc']:.4f}\n"
        f"  PR-AUC:  {test_metrics['pr_auc']:.4f}\n"
        f"  Acc:     {test_metrics['accuracy']:.4f}\n"
        f"  BalAcc:  {test_metrics['balanced_accuracy']:.4f}\n"
        f"  F1:      {test_metrics['f1']:.4f}\n"
        f"  Prec:    {test_metrics['precision']:.4f}\n"
        f"  Recall:  {test_metrics['recall']:.4f}\n"
        f"Confusion matrix (TN FP / FN TP):\n{cm}"
    )

    # сохранение артефактов
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        try:
            import joblib

            model_path = os.path.join(save_dir, "model.joblib")
            joblib.dump(best_est, model_path)

            meta = {
                "best_C": best_C,
                "threshold": best_thr,
                "feature_cols": feature_cols,
                "range": [range_min, range_max],
                "test_metrics": test_metrics,
            }
            with open(os.path.join(save_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            warnings.warn(f"Не удалось сохранить артефакты модели: {e}")

    return FitResult(
        best_estimator=best_est,
        best_C=best_C,
        oof_threshold=best_thr,
        report=report,
        test_metrics=test_metrics,
        confusion=cm.tolist(),
    )


# -------------------------------------- CLI --------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Бинарная классификация по диапазону значения столбца из targets.csv.")
    p.add_argument("--column-coef", default="% СВ", help="Колонка долей в ration csv (по умолчанию '% СВ').")
    p.add_argument(
        "--target-col",
        default=DEFAULT_TARGET_COL,
        help="Имя столбца в targets.csv, по которому бинаризуем (напр., 'Лауриновая').",
    )
    p.add_argument("--range-min", type=float, default=DEFAULT_RANGE[0], help="Мин. граница диапазона (включительно).")
    p.add_argument("--range-max", type=float, default=DEFAULT_RANGE[1], help="Макс. граница диапазона (включительно).")
    p.add_argument("--test-size", type=float, default=0.2, help="Размер тестовой выборки.")
    p.add_argument("--seed", type=int, default=42, help="RandomState.")
    p.add_argument("--cv-splits", type=int, default=5, help="Число фолдов в StratifiedKFold.")
    p.add_argument(
        "--drop-features",
        nargs="*",
        default=DROP_FEATURES_DEFAULT,
        help="Какие признаки удалить, если они присутствуют.",
    )
    p.add_argument("--save-dir", default=None, help="Папка для сохранения model.joblib и meta.json.")
    return p.parse_args()


def main():
    args = parse_args()

    # Сбор датасета
    df = get_ohe_dataset(
        column_coef=args.column_coef,
        target_col=args.target_col,
        drop_features=args.drop_features,
    )

    # Обучение и отчёт
    fit_res = fit_and_report(
        df,
        range_min=args.range_min,
        range_max=args.range_max,
        test_size=args.test_size,
        seed=args.seed,
        cv_splits=args.cv_splits,
        save_dir=args.save_dir,
    )

    print("\n" + "=" * 80)
    print(fit_res.report)
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
