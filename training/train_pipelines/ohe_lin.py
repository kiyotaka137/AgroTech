import pandas as pd
import numpy as np
import joblib as jl
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score, LeaveOneOut


from training import name_mapping, change_mapping, uniq_ration, uniq_step, uniq_changed_ration

target_path = "training/data/Для Хакатона/targets.csv"
rations_path = "training/parsed_data/{table}.csv"
step_path = "training/parsed_data/step_analize/{table}.csv"

def get_ohe_train_test_data(mapping=name_mapping, uniq=uniq_ration, column_coef="% СВ", target_col="Лауриновая"):  # todo: сделать выбор таргетов множественным
    targets = pd.read_csv(target_path, sep=";")
    uniq_dict = {elem: ind for ind, elem in enumerate(uniq)}
    data = []

    for table, elem in enumerate(targets["Рацион"].values):
        row = [0] * len(uniq) + [targets.loc[table, target_col]]

        if elem[-1] == '.':
            elem = elem[:-1]
        ration = pd.read_csv(rations_path.format(table=elem.strip()), sep="|")

        for i, ingr in enumerate(ration["Ингредиенты"]):
            clear_elem = mapping[ingr]
            row[uniq_dict[clear_elem]] += float(ration.loc[i, column_coef].replace(",", "."))

        data.append(row)

    columns = uniq + ["target"]
    df = pd.DataFrame(data, columns=columns)
    return df


def get_ohe_step_data(mapping=change_mapping(), uniq=uniq_changed_ration, column_coef="% СВ", target_col="Лауриновая"):
    targets = pd.read_csv(target_path, sep=";")
    uniq_dict = {elem: ind for ind, elem in enumerate(uniq)}
    uniq_step_dict = {elem: ind + len(uniq) for ind, elem in enumerate(uniq_step)}

    data = []

    for table, elem in enumerate(targets["Рацион"].values):
        row = [0] * (len(uniq) + len(uniq_step))

        if elem[-1] == '.':
            elem = elem[:-1]
        ration = pd.read_csv(rations_path.format(table=elem.strip()), sep="|")
        step_data = pd.read_csv(step_path.format(table=elem.strip()), sep="|", header=None)

        for i, ingr in enumerate(ration["Ингредиенты"]):
            clear_elem = mapping[ingr]
            row[uniq_dict[clear_elem]] += float(ration.loc[i, column_coef].replace(",", "."))

        for i, element in enumerate(step_data.iloc[:, 0].values):
            val_elem = step_data.iloc[i, 1]

            if not val_elem or (type(val_elem) == str and not val_elem.strip()):
                val_elem = np.nan
            elif type(val_elem) == str:
                val_elem = float(val_elem.replace(",", "."))

            row[uniq_step_dict[element]] += val_elem

        row += [targets.loc[table, target_col]]
        data.append(row)

    columns = uniq + uniq_step + ["target"]
    df = pd.DataFrame(data, columns=columns)
    return df


def minimal_infer():
    pass


if __name__ == "__main__":
    dataset = get_ohe_step_data(target_col="Линоленовая")
    print(dataset['ЧЭЛ 3x NRC (МДжоуль/кг)'])
#     dataset = dataset.drop(["RD Крахмал 3xУровень 1 (%)", "НСУ (%)", "CHO B3 pdNDF (%)", "peNDF (%)", "CHO B3 медленная фракция (%)"], axis=1)
#     dataset.dropna(inplace=True)
#     loocv = True
#     cv = True
#
#     minimal_infer()
#
#
#     if loocv:
#         X = dataset.drop(["target"], axis=1).to_numpy()
#         y = dataset["target"].to_numpy()
#
#         model = Ridge(alpha=0.5)
#         loo = LeaveOneOut()
#
#         y_true, y_pred = [], []
#
#         for train_idx, test_idx in loo.split(X):
#             X_train, X_test = X[train_idx], X[test_idx]
#             y_train, y_test = y[train_idx], y[test_idx]
#
#             model.fit(X_train, y_train)
#             pred = model.predict(X_test)
#
#             y_true.append(y_test[0])
#             y_pred.append(pred[0])
#
#         y_true, y_pred = np.array(y_true), np.array(y_pred)
#         rmse = np.sqrt(mean_squared_error(y_true, y_pred))
#         r2 = r2_score(y_true, y_pred)
#
#         print(f"LOOCV RMSE (по всем объектам): {rmse:.4f}")
#         print(f"LOOCV R²   (по всем объектам): {r2:.4f}")
#
#         final_model = Ridge(alpha=0.5)
#         final_model.fit(X, y)
#         jl.dump(final_model, "models/classic_pipe/ridge_model.pkl")
#
#         print(uniq_ration)
#         print(final_model.coef_)
#
#         for p, t in zip(y_pred, y_true):
#             print(round(p, 2), t)
#         print(f"RMSE: {rmse}, R2: {r2}")
#
#     elif cv:
#         X = dataset.drop("target", axis=1)
#         y = dataset["target"]
#
#         model = Ridge(alpha=0.5)
#         folds = 99
#
#         rmse_scores = np.sqrt(-cross_val_score(
#             model, X, y, cv=folds, scoring="neg_mean_squared_error"
#         ))
#         print(rmse_scores)
#         print(f"CV RMSE: {rmse_scores.mean():.4f}")
#
#         r2_scores = cross_val_score(model, X, y, cv=folds, scoring="r2")
#         print(f"CV R2  : {r2_scores.mean():.4f}")
#
#         model.fit(X, y)
#
#     else:
#         X_train, X_test, y_train, y_test = train_test_split(dataset.drop("target", axis=1), dataset["target"], test_size=0.1, random_state=42)
#
#         model = Ridge(alpha=0.5)
#         model.fit(X_train, y_train)
#
#         pred = model.predict(X_test)
#         rmse = np.sqrt(mean_squared_error(y_test, pred))
#         r2 = r2_score(y_test, pred)
#
#         for p, t in zip(pred, y_test):
#             print(round(p, 2), t)
#         print(f"RMSE: {rmse}, R2: {r2}")
#
# # LOOCV RMSE (по всем объектам): 0.4131
# # LOOCV R²   (по всем объектам): 0.3987
