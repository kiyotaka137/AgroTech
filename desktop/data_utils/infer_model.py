import json
import pandas as pd
import numpy as np
import joblib as jl
import shap
import re

from .predictor import set_ensemble, ensemble_predict
from .config import acids, for_dropping, medians_of_data, main_acids, nutri, uniq_step
from training import change_mapping, cultures, uniq_step, uniq_changed_ration, name_mapping, feed_types


def fix_name(value):
    pattern = re.compile(r"\d{4}\.\d{2}\.(\d{2})\.?(\d{2})?")
    match = pattern.search(value)
    if not match:
        return None

    groups = match.groups()
    culture_code = groups[0]
    culture_name = cultures.get(culture_code)

    if culture_name:
        return f"{culture_name}"
    elif culture_name:
        return culture_name
    else:
        return None


def extract_to_row(ration, nutrients):
    row = [0] * (len(uniq_changed_ration) + len(uniq_step))
    columns = uniq_changed_ration + uniq_step

    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_changed_ration)}
    uniq_step_dict = {elem: ind + len(uniq_changed_ration) for ind, elem in enumerate(uniq_step)}

    name_mapping = change_mapping()

    for i, (elem, val) in enumerate(ration):
        clear_elem = name_mapping[elem]  # todo: сделать вилку с ллм
        row[uniq_dict[clear_elem]] += float(val.replace(",", "."))

    for i, (elem, val) in enumerate(nutrients):

        if not val or (type(val) == str and not val.strip()):
            val = np.nan
        elif type(val) == str:
            val = float(val.replace(",", "."))

        row[uniq_step_dict[elem]] += val

    df_row = pd.DataFrame([row], columns=columns)
    return df_row


def load_data_from_json(path_name: str):
    with open(path_name, "r", encoding="utf-8") as f:
        json_file = json.load(f)

    rational_rows = [(elem["Ингредиенты"], elem["%СВ"]) for elem in json_file['ration_rows']]
    nutrients_rows = [(elem["Нутриент"], elem["СВ"]) for elem in json_file['nutrients_rows']]

    final_row = extract_to_row(rational_rows, nutrients_rows)
    return final_row


def clear_data(data):
    for item in for_dropping:
        data = data.drop(item, axis=1)

    for key, value in medians_of_data.items():
        if data[key].isna()[0]:
            data.loc[0, key] = value

    return data


def predict_importance_acids(data, acid, explainer_path="models/classic_pipe/acid_explainers"):
    feature_names = jl.load(f"{explainer_path}/feature_names.pkl")
    explainer = jl.load(f"{explainer_path}/{acid}_explainer.pkl")

    X_single = pd.DataFrame([data], columns=feature_names)
    shap_values = explainer(X_single)

    shap_df = pd.DataFrame({
        "feature": feature_names,
        "shap_value": shap_values.values[0]
    })
    df = shap_df.sort_values(by="shap_value", key=abs, ascending=False)
    feature_val_dict = {f: round(v, 2) for f, v in zip(df["feature"], df["shap_value"])}

    #shap.plots.waterfall(shap_values[0])

    return feature_val_dict


def predict_importance_nutri(data, nutri_path="models/classic_pipe/nutri", importance_path="models/classic_pipe/nutri_explainers"):
    nutri_dict = dict()
    feature_names = jl.load(f"{importance_path}/feature_names.pkl")
    print(feature_names)

    data = data.drop(uniq_step, axis=1).to_numpy()

    for key, item in nutri.items():
        model = jl.load(f"{nutri_path}/{item}_catboost.pkl")
        logit = model.predict(data)

        explainer = jl.load(f"{importance_path}/{item}_explainer.pkl")
        X_single = pd.DataFrame([logit], columns=feature_names)
        shap_values = explainer(X_single)

        shap_df = pd.DataFrame({
            "feature": feature_names,
            "shap_value": shap_values.values[0]
        })
        df = shap_df.sort_values(by="shap_value", key=abs, ascending=False)
        feature_val_dict = {f: round(v, 2) for f, v in zip(df["feature"], df["shap_value"])}
        print(feature_val_dict)

    return nutri_dict

def cross_importance(importance_dict):
    for key, item in importance_dict.items():
        if key not in main_acids: continue
        print(f"{key} : ", end="")
        for ind, (sec_key, sec_item) in enumerate(item.items()):
            if ind == 5: break
            print(f"{sec_key} - {sec_item}", end="|")
        print()


def predict_from_file(json_report, model_path="models/classic_pipe/acids"):
    acids_dict = dict()
    importance_acid_dict = dict()
    importance_nutri_dict = dict()

    data = load_data_from_json(json_report)
    data = clear_data(data)

    #importance_nutri_dict = predict_importance_nutri(data)

    data = data.to_numpy()

    for acid in acids:
        model = jl.load(f"{model_path}/{acid}_ensemble.pkl")
        logit = model.predict(data)
        acids_dict[acid] = logit

        set_ensemble(model)
        importance = predict_importance_acids(data[0], acid)
        importance_acid_dict[acid] = importance

    #print(importance_dict)
    return acids_dict


if __name__ == '__main__':
    #print(load_data_from_json("../reports/Норм_2025-10-07_1759796029.json"))
    print(predict_from_file(json_report="desktop/reports/report_2025-10-07_1759855680.json",
                           model_path="models/classic_pipe/acids"))
    # print(predict_from_file(json_report="desktop/reports/Норм_2025-10-07_1759796029.json",
    #                        model_path="models/classic_pipe"))
