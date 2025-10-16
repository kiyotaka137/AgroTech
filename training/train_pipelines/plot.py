# plot.py
"""
Расширенный EDA-плоттер признаков с «линейкой» из общей линейной модели и подсветкой выбросов.

Что нового:
- Подсветка «выбросов» (точки, сильно отклонённые от прямой для выбранного признака).
- Прямая строится из мультифакторной линейной модели (остальные признаки — на средних), как раньше.
- Порог выброса по умолчанию — робастный: |residual| > k * sigma_MAD,
  где sigma_MAD = 1.4826 * median(|residual - median(residual)|).
- Можно задать метод/порог явными параметрами (см. аргументы функций ниже).
- Улучшено построение решётки субплотов: автоматически подбирается размер решётки под число признаков.
- Возвращаем полезные значения: фигуры/оси, маски выбросов.

Примеры:
    # один признак
    fig, ax, mask = plot_feature_from_ohe(
        feature="сенаж",
        column_coef="% СВ",
        target_name="target",
        outlier_method="mad",
        outlier_k=3.0,
        show=True
    )

    # все признаки
    res = plot_all_features_from_ohe(
        column_coef="% СВ",
        target_name="target",
        save_dir="eda_plots",
        show=False,       # не открывать окна
        outlier_method="mad",
        outlier_k=3.0
    )
    # res — список словарей с ключами: fig, ax, feat_name, outlier_mask
"""

import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple, Optional, Dict, List

from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# берём «эталонную» функцию прямо из твоего файла
from ohe_lin import get_ohe_train_test_data
_CLEAN_PATH = os.getenv("OHE_CLEAN_PATH", "clean_data/ohe_clean.csv")
_DROPPED_PATH = os.getenv("DROPPED_IDX", "clean_data/ohe_dropped_indices.csv")

# Сохраняем оригинальную функцию на всякий случай
from ohe_lin import get_ohe_train_test_data as _orig_get_ohe

def get_ohe_train_test_data(column_coef="% СВ"):
    """
    Если найден очищенный CSV — читаем его.
    Иначе — собираем исходный OHE и, если есть файл индексов выбросов, фильтруем по нему.
    """
    if os.path.exists(_CLEAN_PATH):
        return pd.read_csv(_CLEAN_PATH)

    df = _orig_get_ohe(column_coef=column_coef)
    if os.path.exists(_DROPPED_PATH):
        drop_idx = pd.read_csv(_DROPPED_PATH)["dropped_idx"].to_numpy()
        df = df.drop(index=drop_idx).reset_index(drop=True)
    return df

# ============================ МОДЕЛЬ И ЛИНИЯ ============================

def _fit_global_lr(X, y, model=None):
    """Обучает линейную модель на всех признаках (по умолчанию: StandardScaler -> Ridge)."""
    if model is None:
        model = make_pipeline(StandardScaler(), Ridge(alpha=0.01))
    model.fit(X, y)
    return model


def _coef_intercept_in_input_space(model, X):
    """
    Для модели или Pipeline(StandardScaler, Linear/Ridge/Lasso) возвращает
    коэффициенты и интерсепт в ПРОСТРАНСТВЕ ВХОДНЫХ признаков (до скейлера).
    """
    # Случай: голая линейная модель без пайплайна
    if not hasattr(model, "steps"):
        coef = np.atleast_1d(model.coef_).astype(float).ravel()
        intercept = float(np.atleast_1d(getattr(model, "intercept_", 0.0))[0])
        return coef, intercept

    # Случай: Pipeline
    steps = dict(model.named_steps)
    # ожидаем StandardScaler и линейную модель на выходе
    scaler = steps.get("standardscaler", None)
    final = None
    for name in ("ridge", "lasso", "linearregression"):
        if name in steps:
            final = steps[name]
            break
    if scaler is None or final is None:
        # не тот пайплайн — пытаемся взять как есть
        coef = np.atleast_1d(getattr(model, "coef_", getattr(final, "coef_", None)))
        intercept = getattr(model, "intercept_", getattr(final, "intercept_", 0.0))
        coef = np.atleast_1d(coef).astype(float).ravel()
        intercept = float(np.atleast_1d(intercept)[0])
        return coef, intercept

    w = np.atleast_1d(final.coef_).astype(float).ravel()
    b = float(np.atleast_1d(getattr(final, "intercept_", 0.0))[0])

    mu = np.atleast_1d(getattr(scaler, "mean_", np.zeros_like(w))).astype(float)
    sigma = np.atleast_1d(getattr(scaler, "scale_", np.ones_like(w))).astype(float)

    # защита от нулевых масштабов (константные признаки)
    sigma_safe = np.where(sigma == 0.0, 1.0, sigma)

    coef_input = w / sigma_safe
    intercept_input = b - float(np.dot(w, mu / sigma_safe))
    return coef_input, intercept_input


def _make_line_from_global(model, X, j, x_line):
    """
    Линия для признака j из мультифакторной модели (остальные на средних).
    Корректно работает и для Pipeline(StandardScaler -> Ridge).
    """
    # пересчёт коэффициентов в пространство X
    coef, intercept = _coef_intercept_in_input_space(model, X)

    means = np.nanmean(X, axis=0)  # средние в ИСХОДНОМ масштабе
    base = intercept + float(np.dot(coef, means) - coef[j] * means[j])
    return base + coef[j] * x_line


def _predict_on_line_for_points(model, X, j, x_values):
    """
    Возвращает предсказания ИМЕННО «линейной» модели для текущего признака j при фиксировании остальных на средних,
    рассчитанные для конкретных значений x_values (масштаб исходных признаков).
    Это нужно, чтобы сравнивать реальные y с "прямой" по этому признаку.
    """
    coef, intercept = _coef_intercept_in_input_space(model, X)
    means = np.nanmean(X, axis=0)
    base = intercept + float(np.dot(coef, means) - coef[j] * means[j])
    return base + coef[j] * x_values


# ============================ ВЫБРОСЫ (OUTLIERS) ============================

def _residuals_to_line(model, X, y, j) -> np.ndarray:
    """
    Резидуалы относительно прямой по признаку j (остальные на средних).
    residual = y - y_line(x_j)
    """
    x_j = X[:, j]
    y_line_at_x = _predict_on_line_for_points(model, X, j, x_j)
    residuals = y - y_line_at_x
    return residuals


def _outlier_mask(residuals: np.ndarray,
                  method: str = "mad",
                  k: float = 3.0,
                  abs_threshold: Optional[float] = None,
                  quantile: float = 0.98) -> np.ndarray:
    """
    Возвращает булеву маску выбросов по резидуалам.

    method:
        - "mad" (по умолчанию): |r - med(r)| / 1.4826 > k
        - "std": |r - mean(r)| / std(r) > k
        - "abs": |r| > abs_threshold (нужно задать abs_threshold)
        - "quantile": |r| > Q, где Q = quantile(|r|)

    k: множитель порога для "mad"/"std" (по умолчанию 3.0)
    abs_threshold: абсолютный порог для метода "abs" (в единицах таргета)
    quantile: квантииль для метода "quantile" (например, 0.98)
    """
    r = residuals.astype(float)

    if method == "mad":
        med = np.nanmedian(r)
        mad = np.nanmedian(np.abs(r - med))
        sigma = 1.4826 * mad  # робастная оценка σ
        if sigma == 0 or np.isnan(sigma):
            # fallback — если все одинаковые
            return np.zeros_like(r, dtype=bool)
        return np.abs(r - med) > k * sigma

    elif method == "std":
        mu = np.nanmean(r)
        sd = np.nanstd(r)
        if sd == 0 or np.isnan(sd):
            return np.zeros_like(r, dtype=bool)
        return np.abs(r - mu) > k * sd

    elif method == "abs":
        if abs_threshold is None or abs_threshold <= 0:
            raise ValueError("Для метода 'abs' нужно положительное abs_threshold.")
        return np.abs(r) > float(abs_threshold)

    elif method == "quantile":
        thr = np.nanquantile(np.abs(r), float(quantile))
        return np.abs(r) > thr

    else:
        raise ValueError(f"Неизвестный method='{method}'. Доступно: mad|std|abs|quantile")


# ============================ ВИЗУАЛИЗАЦИЯ ============================

def plot_feature_from_ohe(
    feature,
    *,
    column_coef: str = "% СВ",
    target_name: str = "target",
    save_path: Optional[str] = None,
    show: bool = True,
    model=None,  # если передать заранее обученную модель — используем её
    outlier_method: str = "mad",
    outlier_k: float = 3.0,
    outlier_abs_threshold: Optional[float] = None,
    outlier_quantile: float = 0.98,
    scatter_kwargs: Optional[Dict] = None,
    outlier_scatter_kwargs: Optional[Dict] = None,
):
    """
    Строит график для ОДНОГО признака:
      x — значения выбранного признака,
      y — target,
      линия — из мультифакторной модели (остальные фиксируются на средних).
    Дополнительно подсвечивает выбросы (резидуалы относительно этой линии по методу outlier_method).

    Возвращает: fig, ax, outlier_mask (булева маска длины n)
    """
    # 1) Собираем датасет
    df = get_ohe_train_test_data(column_coef=column_coef)
    DROP_PATH = os.getenv("DROPPED_IDX", "clean_data/ohe_dropped_indices.csv")
    if os.path.exists(DROP_PATH):
        drop_idx = pd.read_csv(DROP_PATH)["dropped_idx"].to_numpy()
        df = df.drop(index=drop_idx).reset_index(drop=True)
    #df = pd.read_csv("clean_data/ohe_clean.csv")

    if target_name not in df.columns:
        raise ValueError(f"Колонка '{target_name}' не найдена в датасете.")
    y = df[target_name].to_numpy().astype(float)
    feature_cols = [c for c in df.columns if c != target_name]

    if isinstance(feature, int):
        feat_name = feature_cols[feature]
        j = feature
    else:
        feat_name = str(feature)
        if feat_name not in feature_cols:
            raise ValueError(f"Признак '{feat_name}' не найден. Доступно: {feature_cols[:10]} ...")
        j = feature_cols.index(feat_name)

    X = df[feature_cols].to_numpy().astype(float)
    x = X[:, j]

    # 2) Обучаем/берём глобальную линейную модель
    model = _fit_global_lr(X, y, model=model)

    # 3) Линия
    x_min, x_max = float(np.nanmin(x)), float(np.nanmax(x))
    if np.isclose(x_min, x_max):
        x_min, x_max = x_min - 1e-6, x_max + 1e-6
    x_line = np.linspace(x_min, x_max, 200)
    y_line = _make_line_from_global(model, X, j, x_line)

    # 4) Резидуалы и выбросы
    residuals = _residuals_to_line(model, X, y, j)
    mask_out = _outlier_mask(
        residuals,
        method=outlier_method,
        k=float(outlier_k),
        abs_threshold=outlier_abs_threshold,
        quantile=float(outlier_quantile),
    )

    # 5) Рисуем
    fig, ax = plt.subplots()

    # базовые параметры точек
    base_sc_kw = dict(s=25, alpha=0.85, edgecolor="none")
    base_sc_kw.update(scatter_kwargs or {})

    # базовые параметры для выбросов (поверх обычных)
    out_sc_kw = dict(s=35, alpha=0.95, edgecolor="k", linewidth=0.6, color="tab:red", label="Выбросы")
    out_sc_kw.update(outlier_scatter_kwargs or {})

    # сначала все «нормальные» точки
    ax.scatter(x[~mask_out], y[~mask_out], label="Нормальные", **base_sc_kw)
    # поверх — выбросы
    if mask_out.any():
        ax.scatter(x[mask_out], y[mask_out], **out_sc_kw)

    # линия модели
    ax.plot(x_line, y_line, label="Линия (глобальная Ridge)", color="tab:blue", linewidth=1.6)

    ax.set_xlabel(feat_name)
    ax.set_ylabel(target_name)
    ax.set_title(f"{feat_name} vs {target_name}\noutliers: {int(mask_out.sum())} из {len(y)}")
    ax.legend()

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        fig.savefig(save_path, bbox_inches="tight", dpi=160)
    if show:
        plt.show()

    return fig, ax, mask_out


def _auto_grid(n: int, max_cols: int = 4) -> Tuple[int, int]:
    """Подбирает разумную решётку (rows, cols) для n графиков."""
    cols = min(max_cols, max(1, int(round(math.sqrt(n)))))
    rows = math.ceil(n / cols)
    # для эстетики делаем кол-во колонок не больше 4
    cols = min(cols, max_cols)
    rows = math.ceil(n / cols)
    return rows, cols


def plot_all_features_from_ohe(
    *,
    column_coef: str = "% СВ",
    target_name: str = "target",
    save_dir: Optional[str] = "eda_plots",
    show: bool = False,
    model=None,
    outlier_method: str = "mad",
    outlier_k: float = 3.0,
    outlier_abs_threshold: Optional[float] = None,
    outlier_quantile: float = 0.98,
    scatter_kwargs: Optional[Dict] = None,
    outlier_scatter_kwargs: Optional[Dict] = None,
) -> List[Dict]:
    """
    Строит графики для КАЖДОГО признака (кол-во графиков = кол-во признаков).
    Всё берётся из get_ohe_train_test_data().
    Подсвечивает выбросы по каждому признаку.

    Возвращает список словарей:
        {
            "fig": fig,
            "ax": ax,
            "feat_name": feat_name,
            "outlier_mask": mask_out  # длины n (для исходных точек)
        }
    """
    df = get_ohe_train_test_data(column_coef=column_coef)
    if target_name not in df.columns:
        raise ValueError(f"Колонка '{target_name}' не найдена в датасете.")
    y = df[target_name].to_numpy().astype(float)
    feature_cols = [c for c in df.columns if c != target_name]
    X = df[feature_cols].to_numpy().astype(float)

    # одна глобальная модель для всех линий
    model = _fit_global_lr(X, y, model=model)

    # авто-решётка под число признаков
    n_feats = len(feature_cols)
    rows, cols = _auto_grid(n_feats, max_cols=4)
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.4 * rows), constrained_layout=True)
    axes = np.array(axes).reshape(-1)

    results: List[Dict] = []

    # базовые параметры точек
    base_sc_kw = dict(s=16, alpha=0.85, edgecolor="none")
    base_sc_kw.update(scatter_kwargs or {})

    # параметры выбросов
    out_sc_kw = dict(s=24, alpha=0.95, edgecolor="k", linewidth=0.5, color="tab:red", label="Выбросы")
    out_sc_kw.update(outlier_scatter_kwargs or {})

    for j, feat_name in enumerate(feature_cols):
        ax = axes[j]
        x = X[:, j]

        # маска валидных точек для scatter (чтобы NaN не мешали)
        mask_valid = ~np.isnan(x) & ~np.isnan(y)
        x_valid = x[mask_valid]
        y_valid = y[mask_valid]

        # диапазон по оси X (игнорируем NaN)
        if x_valid.size == 0:
            ax.set_visible(False)
            continue

        x_min, x_max = float(np.nanmin(x_valid)), float(np.nanmax(x_valid))
        if np.isclose(x_min, x_max):
            eps = 1e-6
            x_min, x_max = x_min - eps, x_max + eps

        x_line = np.linspace(x_min, x_max, 200)
        y_line = _make_line_from_global(model, X, j, x_line)

        # Резидуалы и выбросы (считаем на всех, но отображаем для валидных)
        residuals = _residuals_to_line(model, X, y, j)
        mask_out_all = _outlier_mask(
            residuals,
            method=outlier_method,
            k=float(outlier_k),
            abs_threshold=outlier_abs_threshold,
            quantile=float(outlier_quantile),
        )
        mask_out_valid = mask_out_all[mask_valid]

        # Рисуем: сначала нормальные, потом выбросы поверх
        ax.scatter(x_valid[~mask_out_valid], y_valid[~mask_out_valid], label="Нормальные", **base_sc_kw)
        if mask_out_valid.any():
            ax.scatter(x_valid[mask_out_valid], y_valid[mask_out_valid], **out_sc_kw)

        ax.plot(x_line, y_line, linewidth=1.2, color="tab:blue", label="Линия (глобальная Ridge)")
        ax.set_xlabel(feat_name)
        ax.set_ylabel(target_name)
        ax.set_title(f"{feat_name} vs {target_name}\noutliers: {int(mask_out_valid.sum())}/{len(y_valid)}", fontsize=9)

        if j == 0:
            ax.legend()

        results.append({
            "fig": fig,
            "ax": ax,
            "feat_name": feat_name,
            "outlier_mask": mask_out_all  # маска по исходному порядку точек
        })

    # скрыть лишние оси, если их больше, чем признаков
    for k in range(n_feats, len(axes)):
        axes[k].set_visible(False)

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        out_path = os.path.join(save_dir, "all_features_with_outliers.png")
        fig.savefig(out_path, bbox_inches="tight", dpi=160)

    if show:
        plt.show()

    return results


# ============================ DEMO ============================

if __name__ == "__main__":
    # 1) Показать один график (с подсветкой выбросов)
    # plot_feature_from_ohe(
    #     feature="сенаж",        # или индекс признака: feature=0
    #     column_coef="% СВ",
    #     target_name="target",
    #     outlier_method="mad",   # mad | std | abs | quantile
    #     outlier_k=3.0,
    #     show=True
    # )

    # 2) Сохранить решётку графиков по всем признакам
    save_dir = os.path.join(os.path.dirname(__file__), "eda_plots")
    plot_all_features_from_ohe(
        column_coef="% СВ",
        target_name="target",
        save_dir=save_dir,
        show=True,               # осторожно: может открыть много окон
        outlier_method="mad",
        outlier_k=3.0
    )
    print(f"Готово! PNG-файл с сеткой лежит в: {save_dir}")
