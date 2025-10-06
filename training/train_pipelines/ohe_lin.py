import pandas as pd
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import (
    train_test_split, cross_val_score, LeaveOneOut, GridSearchCV, KFold
)

from training import name_mapping, uniq_ration

target_path = "../data/Для Хакатона/targets.csv"
rations_path = "../parsed_data/{table}.csv"

# сетка значений для alpha (логарифмическая шкала)
ALPHA_GRID = np.logspace(-4, 3, 25)
# список признаков к удалению
DROP_FEATURES = ["сорго", "подсолнечник", "лен", "сено", "пшеница", "зерно"]


def build_model(alpha=0.5):
    """Pipeline: StandardScaler -> Ridge(alpha)."""
    return make_pipeline(
        StandardScaler(),
        Ridge(alpha=alpha)
    )


def get_ohe_train_test_data(column_coef="% СВ"):  # todo: сделать выбор таргетов множественным
    targets = pd.read_csv(target_path, sep=";")
    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_ration)}
    data = []

    for table, elem in enumerate(targets["Рацион"].values):
        row = [0] * len(uniq_ration) + [targets.loc[table, "Лауриновая"]]

        if elem[-1] == '.':
            elem = elem[:-1]
        ration = pd.read_csv(rations_path.format(table=elem.strip()), sep="|")

        for i, ingr in enumerate(ration["Ингредиенты"]):
            clear_elem = name_mapping[ingr]
            row[uniq_dict[clear_elem]] += float(ration.loc[i, column_coef].replace(",", "."))

        data.append(row)

    columns = uniq_ration + ["target"]
    df = pd.DataFrame(data, columns=columns)
    return df


if __name__ == "__main__":
    dataset = get_ohe_train_test_data()
    loocv = True
    cv = True   # если оба True — выведем и LOO, и 5-fold CV

    # --- подготовка X, y и отбрасывание 6 колонок ---
    X_df = dataset.drop(columns=[c for c in ["target"] + DROP_FEATURES if c in dataset.columns])
    y_sr = dataset["target"]
    X_all = X_df.astype(float).to_numpy()
    y_all = y_sr.astype(float).to_numpy()

    # ---------- если включён хотя бы один режим (LOOCV или CV), подберём alpha по R^2 один раз ----------
    best_alpha = None
    best_model_cv = None
    grid = None
    inner_cv = None
    if loocv or cv:
        pipe = build_model()  # StandardScaler -> Ridge(alpha=?)
        param_grid = {"ridge__alpha": ALPHA_GRID}
        inner_cv = KFold(n_splits=5, shuffle=True, random_state=42)

        grid = GridSearchCV(
            estimator=pipe,
            param_grid=param_grid,
            cv=inner_cv,
            scoring="r2",      # подбор по R^2
            n_jobs=-1,
            refit=True
        )
        grid.fit(X_all, y_all)
        best_alpha = grid.best_params_["ridge__alpha"]
        best_model_cv = grid.best_estimator_

    # ----------------------------- LOOCV (если loocv=True) -----------------------------
    if loocv:
        model_loo = build_model(alpha=best_alpha)

        y_true, y_pred = [], []
        loo = LeaveOneOut()
        for tr, te in loo.split(X_all):
            model_loo.fit(X_all[tr], y_all[tr])
            y_pred.append(model_loo.predict(X_all[te])[0])
            y_true.append(y_all[te][0])

        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)

        print(f"LOOCV alpha: {best_alpha:.6g}")
        print(f"LOOCV RMSE: {rmse:.4f}")
        print(f"LOOCV R^2:  {r2:.4f}")

        # финальная модель на всех данных (если нужно дальше использовать)
        final_model_loo = build_model(alpha=best_alpha).fit(X_all, y_all)

    # ------------------------------ CV (если cv=True) ----------------------------------
    if cv:
        # считаем и R^2, и RMSE на тех же фолдах, что использовались в GridSearch
        r2_scores = cross_val_score(
            best_model_cv, X_all, y_all, cv=inner_cv, scoring="r2", n_jobs=-1
        )
        rmse_scores = -cross_val_score(
            best_model_cv, X_all, y_all, cv=inner_cv, scoring="neg_root_mean_squared_error", n_jobs=-1
        )

        print(f"CV(5-fold) alpha: {best_alpha:.6g}")
        print(f"CV(5-fold) RMSE: {rmse_scores.mean():.4f}")
        print(f"CV(5-fold) R^2:  {r2_scores.mean():.4f}")

        final_model_cv = best_model_cv.fit(X_all, y_all)

    # ------------------------------ Holdout 90/10 (если оба выключены) ----------------------------------
    if not (loocv or cv):
        X_train, X_test, y_train, y_test = train_test_split(
            X_all, y_all, test_size=0.1, random_state=42
        )

        pipe = build_model()
        param_grid = {"ridge__alpha": ALPHA_GRID}

        grid = GridSearchCV(
            estimator=pipe,
            param_grid=param_grid,
            cv=5,
            scoring="r2",   # подбор по R^2
            n_jobs=-1,
            refit=True
        ).fit(X_train, y_train)

        best_alpha = grid.best_params_["ridge__alpha"]
        best_model = grid.best_estimator_

        pred = best_model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        r2 = r2_score(y_test, pred)

        print(f"Holdout alpha:     {best_alpha:.6g}")
        print(f"Holdout Test RMSE: {rmse:.4f}")
        print(f"Holdout Test R^2:  {r2:.4f}")
