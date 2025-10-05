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
from ohe_lin import get_ohe_train_test_data


def main():
    dataset_all = get_ohe_train_test_data()
    dataset, test = train_test_split(dataset_all, train_size=0.9)
    print(f"size of train {len(dataset)}")
    print(f"size of test {len(test)}")

    X = dataset.drop("target", axis=1).to_numpy()
    y = dataset["target"].to_numpy()

    # RandomForest
    # params: {'rf__bootstrap': True, 'rf__max_depth': 5, 'rf__max_features': 'sqrt', 'rf__min_samples_leaf': 1,
    #          'rf__min_samples_split': 5, 'rf__n_estimators': 50}
    # R²: 0.5535147138143428
    # RMSE: 0.22328066921910897

    # CatBoost
    # params: {'catboost__bagging_temperature': 0, 'catboost__depth': 3, 'catboost__iterations': 50,
    #          'catboost__l2_leaf_reg': 5, 'catboost__learning_rate': 0.1}
    # RMSE(LOOCV): 0.10169803847922505
    # R² (train set): 0.767628552492993

    # SVR
    # params: {'svr__C': 1, 'svr__coef0': 0.0, 'svr__degree': 2, 'svr__epsilon': 0.2, 'svr__gamma': 0.1,
    # RMSE(LOOCV): 0.1052154231531089

    # Ridge
    # params: {'ridge__alpha': 10}
    # RMSE(LOOCV): 0.14686108882238277

    # Объявляем модели

    model_cat = CatBoostRegressor(
        iterations=50,  # число деревьев
        depth=3,  # глубина дерева
        learning_rate=0.1,  # скорость обучения
        random_seed=42,
        l2_leaf_reg=5,
        bagging_temperature=0,
        verbose=0  # убираем лог обучения
    )

    model_tree = RandomForestRegressor(
        random_state=42,
        bootstrap=True,
        max_depth=5,
        min_samples_split=5,
        min_samples_leaf=1,
        n_estimators=50
    )

    model_ridge = Ridge(alpha=10)

    model_svr = SVR(
        C=1,
        coef0=0.0,
        degree=2,
        epsilon=0.2,
        gamma=0.1
    )

    # 2. Создаём пайплайн
    pipe_cat = Pipeline([
        ('scaler', StandardScaler()),
        ('catboost', model_cat)
    ])

    pipe_tree = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', model_tree)
    ])

    pipe_ridge = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', model_ridge)
    ])

    pipe_svr = Pipeline([
        ('scaler', StandardScaler()),
        ('svr', model_svr)
    ])

    ensemble = VotingRegressor([
        ('catboost', pipe_cat),
        ('random_forest', pipe_tree),
        ('ridge', pipe_ridge),
        ('svr', pipe_svr)
    ])

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

    model_cat = CatBoostRegressor(
        iterations=50,  # число деревьев
        depth=3,  # глубина дерева
        learning_rate=0.1,  # скорость обучения
        random_seed=42,
        l2_leaf_reg=5,
        bagging_temperature=0,
        verbose=0  # убираем лог обучения
    )

    model_tree = RandomForestRegressor(
        random_state=42,
        bootstrap=True,
        max_depth=5,
        min_samples_split=5,
        min_samples_leaf=1,
        n_estimators=50
    )

    model_ridge = Ridge(alpha=10)

    model_svr = SVR(
        C=1,
        coef0=0.0,
        degree=2,
        epsilon=0.2,
        gamma=0.1
    )

    # 2. Создаём пайплайн
    pipe_cat = Pipeline([
        ('scaler', StandardScaler()),
        ('catboost', model_cat)
    ])

    pipe_tree = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', model_tree)
    ])

    pipe_ridge = Pipeline([
        ('scaler', StandardScaler()),
        ('ridge', model_ridge)
    ])

    pipe_svr = Pipeline([
        ('scaler', StandardScaler()),
        ('svr', model_svr)
    ])

    ensemble_final = VotingRegressor([
        ('catboost', pipe_cat),
        ('random_forest', pipe_tree),
        ('ridge', pipe_ridge),
        ('svr', pipe_svr)
    ])

    ensemble_final.fit(X, y)

    X_test = test.drop("target", axis=1).to_numpy()
    y_test = test["target"].to_numpy()

    logit = ensemble_final.predict(X_test)
    y_true, y_pred = np.array(logit), np.array(y_test)
    for x, y in zip(logit, y_test):
        print(f"{x:.4f} {y:.4f}")
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    print(f"LRMSE (по тестовой выборке): {rmse:.4f}")
    print(f"R²   (по тестовой выборке): {r2:.4f}")

if __name__ == "__main__":
    main()