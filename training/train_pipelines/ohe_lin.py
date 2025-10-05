import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score, LeaveOneOut


from training import name_mapping, uniq_ration

target_path = "../data/Для Хакатона/targets.csv"
rations_path = "../parsed_data/{table}.csv"


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
    return dfw


def minimal_infer():
    pass


if __name__ == "__main__":
    dataset = get_ohe_train_test_data()
    loocv = True
    cv = True

    minimal_infer()


    if loocv:
        X = dataset.drop(["target"], axis=1).to_numpy()
        y = dataset["target"].to_numpy()

        model = Ridge(alpha=0.5)
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
        r2 = r2_score(y_true, y_pred)

        print(f"LOOCV RMSE (по всем объектам): {rmse:.4f}")
        print(f"LOOCV R²   (по всем объектам): {r2:.4f}")

        final_model = Lasso(alpha=0.5)
        final_model.fit(X, y)

        print(uniq_ration)
        print(final_model.coef_)

        for p, t in zip(y_pred, y_true):
            print(round(p, 2), t)
        print(f"RMSE: {rmse}, R2: {r2}")


    elif cv:
        X = dataset.drop("target", axis=1)
        y = dataset["target"]

        model = Ridge(alpha=0.5)
        folds = 99

        rmse_scores = np.sqrt(-cross_val_score(
            model, X, y, cv=folds, scoring="neg_mean_squared_error"
        ))
        print(rmse_scores)
        print(f"CV RMSE: {rmse_scores.mean():.4f}")

        r2_scores = cross_val_score(model, X, y, cv=folds, scoring="r2")
        print(f"CV R2  : {r2_scores.mean():.4f}")

        model.fit(X, y)

    else:
        X_train, X_test, y_train, y_test = train_test_split(dataset.drop("target", axis=1), dataset["target"], test_size=0.1, random_state=42)

        model = Ridge(alpha=0.5)
        model.fit(X_train, y_train)

        pred = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        r2 = r2_score(y_test, pred)

        for p, t in zip(pred, y_test):
            print(round(p, 2), t)
        print(f"RMSE: {rmse}, R2: {r2}")

# LOOCV RMSE (по всем объектам): 0.4131
# LOOCV R²   (по всем объектам): 0.3987
