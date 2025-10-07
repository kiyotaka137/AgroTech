from catboost import CatBoostRegressor
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, VotingRegressor
from sklearn.svm import SVR
from sklearn.model_selection import train_test_split, RandomizedSearchCV, GridSearchCV
from sklearn.metrics import mean_squared_error, r2_score, make_scorer
from sklearn.model_selection import train_test_split, cross_val_score, LeaveOneOut, KFold

from training.train_pipelines.ohe_lin import get_ohe_train_test_data, get_ohe_step_data
import joblib

import numba
numba.config.DISABLE_JIT = True

import shap

def get_data():
    dataset_all = get_ohe_step_data()
    dataset_all = dataset_all.drop(["CHO B3 медленная фракция (%)",
                                    "CHO B3 pdNDF (%)",
                                    "НСУ (%)",
                                    "RD Крахмал 3xУровень 1 (%)"],
                                   axis=1)
    dataset_all = dataset_all.fillna({
        "aNDFom фуража (%)": dataset_all["aNDFom фуража (%)"].median(),
        "СЖ (%)": dataset_all["СЖ (%)"].median(),
        "Растворимая клетчатка (%)": dataset_all["Растворимая клетчатка (%)"].median(),
        "peNDF (%)": dataset_all["peNDF (%)"].median(),
        "ОЖК (%)": dataset_all["ОЖК (%)"].median(),
        "CHO C uNDF (%)": dataset_all["CHO C uNDF (%)"].median()
    })

    dataset, test = train_test_split(dataset_all, train_size=0.9)
    #print(f"size of train {len(dataset)}")
    #print(f"size of test {len(test)}")

    return dataset, test

def main():
    # === Загрузка dataset и работа с None ===
    dataset, test = get_data()
    X = dataset.drop("target", axis=1).to_numpy()
    y = dataset["target"].to_numpy()


    # === Модели ===
    models = {
        'catboost': CatBoostRegressor(
            iterations=40,
            max_depth=3,
            learning_rate=0.15,
            random_seed=42,
            l2_leaf_reg=7,
            verbose=0
        ),
        'random_forest': RandomForestRegressor(
            random_state=42,
            bootstrap=True,
            max_depth=3,
            min_samples_split=6,
            min_samples_leaf=2,
            n_estimators=20
        ),
        'ridge': Ridge(alpha=0.5),
        'svr': SVR(
            C=1,
            epsilon=0.05,
            gamma='scale'
        )
    }

    # === Пайплайн ===
    pipelines = [
        (name, Pipeline([('scaler', StandardScaler()), (name, model)]))
        for name, model in models.items()
    ]
    ensemble = VotingRegressor(pipelines, weights=[0.273, 0.259, 0.21, 0.258])

    # === LOOCV ===
    loo = LeaveOneOut()
    y_true, y_pred = [], []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        ensemble.fit(X_train, y_train)
        pred = ensemble.predict(X_test)

        y_true.append(y_test[0])
        y_pred.append(pred[0])

    y_true, y_pred = np.array(y_true), np.array(y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    print(f"LOOCV RMSE (ensemble): {rmse:.4f}")
    print(f"LOOCV R²   (ensemble): {r2:.4f}")

    # === Финальная модель ===
    ensemble.fit(X, y)

    # === Метрики ===
    X_test = test.drop("target", axis=1).to_numpy()
    y_test = test["target"].to_numpy()

    pred = ensemble.predict(X_test)

    for p, t in zip(pred, y_test):
        print(f"{p:.4f} {t:.4f}")

    rmse_test = np.sqrt(mean_squared_error(y_test, pred))
    r2_test = r2_score(y_test, pred)
    print(f"RMSE (по тестовой выборке): {rmse_test:.4f}")
    print(f"R²   (по тестовой выборке): {r2_test:.4f}")

    # === Сохраняем модель ===
    #joblib.dump(ensemble, '../../models/classic_pipe/acids/ensemble.pkl')


    # === Смотрим что влияет ===

    from desktop.data_utils.predictor import set_ensemble, ensemble_predict
    set_ensemble(ensemble)
    feature_names = dataset.drop("target", axis=1).columns.tolist()
    sample_idx = 0
    X_single = X_test[sample_idx:sample_idx + 1]
    #
    # explainer = shap.Explainer(ensemble.predict, X, feature_names=feature_names)
    # shap_values_single = explainer(x_single)
    #
    # print(shap_values_single)
    #
    # shap.plots.waterfall(shap_values_single[0], max_display=len(dataset.columns))
    # shap.summary_plot(shap_values_single, x_single, feature_names=feature_names)
    #joblib.dump(feature_names, "../../models/classic_pipe/feature_names.pkl")

    explainer = shap.Explainer(
        ensemble_predict,
        masker=X,
        feature_names=feature_names
    )

    joblib.dump(explainer, "../../models/classic_pipe/acid_explainers/Стеариновая_explainer.pkl")

def gridsearch():
    # Best
    # params: {'catboost__catboost__depth': 2, 'catboost__catboost__iterations': 40, 'catboost__catboost__l2_leaf_reg': 7,
    #          'catboost__catboost__learning_rate': 0.15, 'random_forest__rf__max_depth': 3,
    #          'random_forest__rf__max_features': 'sqrt', 'random_forest__rf__min_samples_leaf': 2,
    #          'random_forest__rf__min_samples_split': 6, 'random_forest__rf__n_estimators': 20,
    #          'ridge__ridge__alpha': 0.5, 'svr__svr__C': 1.0, 'svr__svr__epsilon': 0.05, 'svr__svr__gamma': 'scale'}
    # Best
    # RMSE: 0.26746196743823764

    dataset, test = get_data()
    X = dataset.drop("target", axis=1).to_numpy()
    y = dataset["target"].to_numpy()

    # Пайплайны моделей
    pipe_cat = Pipeline([
        ('scaler', StandardScaler()),
        ('catboost', CatBoostRegressor(random_seed=42, verbose=0))
    ])

    pipe_tree = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestRegressor(random_state=42))
    ])

    pipe_ridge = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge())
    ])

    pipe_svr = Pipeline([
        ('scaler', StandardScaler()),
        ('svr', SVR())
    ])

    ensemble = VotingRegressor([
        ('catboost', pipe_cat),
        ('random_forest', pipe_tree),
        ('ridge', pipe_ridge),
        ('svr', pipe_svr)
    ])

    # Параметры для GridSearch
    param_grid = {
        # CatBoost — уточняем вокруг лучших значений
        'catboost__catboost__iterations': [40, 50, 60],  # ±10 от 50
        'catboost__catboost__depth': [2, 3, 4],  # оставить, т.к. дискретный и важный
        'catboost__catboost__learning_rate': [0.15, 0.2, 0.25],  # уточнить вокруг 0.2
        'catboost__catboost__l2_leaf_reg': [3, 5, 7, 10],  # добавить больше регуляризации

        # Random Forest — уточнение
        'random_forest__rf__n_estimators': [20, 30, 40],  # ±10 от 30
        'random_forest__rf__max_depth': [2, 3, 4, None],  # добавить None на всякий случай
        'random_forest__rf__min_samples_split': [4, 5, 6],  # ±1 от 5
        'random_forest__rf__min_samples_leaf': [1, 2, 3],  # ±1 от 2
        'random_forest__rf__max_features': ['sqrt'],  # оставить только лучшее

        # Ridge — расширить вокруг alpha=1
        'ridge__ridge__alpha': [0.5, 0.8, 1.0, 1.5, 2.0, 5.0],  # тонкий поиск

        # SVR — уточнение
        'svr__svr__C': [0.8, 1.0, 1.2],  # ±0.2 от 1
        'svr__svr__epsilon': [0.05, 0.1, 0.15],  # уточнить
        'svr__svr__gamma': ['scale']  # оставить только лучшее
    }

    # GridSearchCV
    grid_search = GridSearchCV(
        ensemble,
        param_grid,
        scoring='neg_root_mean_squared_error',  # минимизируем RMSE
        cv=5,
        n_jobs=-1,
        verbose=2
    )

    grid_search.fit(X, y)

    print("Best params:", grid_search.best_params_)
    print("Best RMSE:", -grid_search.best_score_)

def params_for_ensamble():
    dataset, test = get_data()
    X = dataset.drop("target", axis=1).to_numpy()
    y = dataset["target"].to_numpy()

    pipe_cat = Pipeline([
        ('scaler', StandardScaler()),
        ('catboost', CatBoostRegressor(
            iterations=40,
            max_depth=3,
            learning_rate=0.15,
            random_seed=42,
            l2_leaf_reg=7,
            verbose=0
        ))
    ])

    pipe_tree = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestRegressor(
            random_state=42,
            bootstrap=True,
            max_depth=3,
            min_samples_split=6,
            min_samples_leaf=2,
            n_estimators=20
        ))
    ])

    pipe_ridge = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', Ridge(alpha=10))
    ])

    pipe_svr = Pipeline([
        ('scaler', StandardScaler()),
        ('svr', SVR(
            C=1,
            epsilon=0.05,
            gamma='scale'
        ))
    ])

    mean_rmse = [0, 0, 0, 0]

    for _ in range(10):
        for ind, model in enumerate([pipe_cat, pipe_tree, pipe_ridge, pipe_svr]):
            loo = LeaveOneOut()
            y_true, y_pred = [], []

            for train_idx, test_idx in loo.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]

                model.fit(X_train, y_train)
                pred = model.predict(X_test)

                y_true.append(y_test[0])
                y_pred.append(pred[0])

            y_true, y_pred = np.array(y_true), np.array(y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            mean_rmse[ind] += rmse

    mean_rmse = [f"{item / 10:.4f}" for item in mean_rmse]
    print("Средний RMSE по 10 обучениям по LOOCV")
    print(f"CatBoost - {mean_rmse[0]}")
    print(f"RandomTree - {mean_rmse[1]}")
    print(f"Ridge - {mean_rmse[2]}")
    print(f"SVR - {mean_rmse[3]}")
    print("Коэффициенты для моделей")
    weight = []
    for item in mean_rmse:
        weight.append(1 / float(item))
    weight = [round(item / sum(weight), 3) for item in weight]
    print(weight)
    # weight = [0.273, 0.259, 0.21, 0.258]

def predict_nutr():
    model = CatBoostRegressor(
            iterations=40,
            max_depth=2,
            learning_rate=0.15,
            random_seed=42,
            l2_leaf_reg=7,
            verbose=0
    )
    pipe_cat = Pipeline([
        ('scaler', StandardScaler()),
        ('catboost', model)
    ])

    uniq_step = ['K (%)', 'aNDFom фуража (%)', 'СЖ (%)', 'Растворимая клетчатка (%)',
                 'Крахмал (%)', 'peNDF (%)', 'aNDFom (%)', 'ЧЭЛ 3x NRC (МДжоуль/кг)',
                 'Сахар (ВРУ) (%)', 'ОЖК (%)', 'НВУ (%)', 'CHO C uNDF (%)', 'СП (%)',
                 ]
    dataset, test = get_data()

    X = dataset.drop(uniq_step + ['target'], axis=1).to_numpy()

    for ind, target in enumerate(uniq_step):
        print(f"=== {target} ===")
        y = dataset[target].to_numpy()
        loo = LeaveOneOut()
        y_true, y_pred = [], []

        for train_idx, test_idx in loo.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            pipe_cat.fit(X_train, y_train)
            pred = pipe_cat.predict(X_test)

            y_true.append(y_test[0])
            y_pred.append(pred[0])

        y_true, y_pred = np.array(y_true), np.array(y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        print(f"LOOCV RMSE (LOOCV): {rmse:.4f}")
        print(f"LOOCV R²   (LOOCV): {r2:.4f}")

        pipe_cat.fit(X, y)

        # === Метрики ===
        X_test = test.drop(uniq_step + ["target"], axis=1).to_numpy()
        y_test = test[target].to_numpy()

        pred = pipe_cat.predict(X_test)

        for p, t in zip(pred, y_test):
             print(f"{p:.4f} {t:.4f}")

        rmse_test = np.sqrt(mean_squared_error(y_test, pred))
        r2_test = r2_score(y_test, pred)
        print(f"RMSE (по тестовой выборке): {rmse_test:.4f}")
        print(f"R²   (по тестовой выборке): {r2_test:.4f}")

        #joblib.dump(pipe_cat, f'../../models/classic_pipe/nutri/{ind}_catboost.pkl')

        from desktop.data_utils.predictor import set_ensemble, ensemble_predict
        set_ensemble(model)
        feature_names = dataset.drop(uniq_step + ["target"], axis=1).columns.tolist()
        sample_idx = 0
        X_single = X_test[sample_idx:sample_idx + 1]

        explainer = shap.Explainer(
            ensemble_predict,
            masker=X,
            feature_names=feature_names
        )

        shap_val = explainer(X_single)
        shap.plots.waterfall(shap_val[0])

        joblib.dump(pipe_cat, f'../../models/classic_pipe/nutri_explainers/{ind}_explainers.pkl')


if __name__ == "__main__":
    main()
    #gridsearch()
    #params_for_ensamble()
    #predict_nutr()
