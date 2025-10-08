import json
import pandas as pd
import numpy as np
import joblib as jl
from pathlib import Path
import shap
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

#from .llm_infer import llm_cleaning
from .predictor import set_ensemble, ensemble_predict
from .config import acids, for_dropping, medians_of_data, main_acids, nutri, nutri_for_predict
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


def extract_to_row(ration, nutrients, json_path):
    row = [0] * (len(uniq_changed_ration) + len(uniq_step))
    columns = uniq_changed_ration + uniq_step

    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_changed_ration)}
    uniq_step_dict = {elem: ind + len(uniq_changed_ration) for ind, elem in enumerate(uniq_step)}

    name_mapping = change_mapping()
    llm_elems = {}
    new_ration = []

    for i, (elem, val) in enumerate(ration):
        if elem in name_mapping:
            clear_elem = name_mapping[elem]
        else:
            clear_elem = fix_name(elem)
            if clear_elem is None:
                llm_elems[elem] = i

        new_ration.append((clear_elem, val))

    # if llm_elems:
    #     cleans = llm_cleaning(list(llm_elems.values))
    #     for k, v in cleans.items():
    #         new_ration[llm_elems[k]][0] = v

    new_ration_dct = {i[0] : j[0] for i, j in zip(ration, new_ration)}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # добавляем поле Normalized в каждый элемент ration_rows
    for json_row in data.get("ration_rows", []):
        json_row["Normalized"] = new_ration_dct[json_row.get("Ингредиенты", "")]

    # сохраняем обратно
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    for elem, val in new_ration:
        row[uniq_dict[elem]] += float(val.replace(",", "."))

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

    final_row = extract_to_row(rational_rows, nutrients_rows, path_name)
    return final_row


def clear_data(data):
    for item in for_dropping:
        data = data.drop(item, axis=1)

    for key, value in medians_of_data.items():
        if data[key].isna()[0]:
            data.loc[0, key] = value

    return data


def predict_importance_acids(data, acid, name,
                             explainer_path="models/classic_pipe/acid_explainers",
                             graphics_path="desktop/graphics"):
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

    amount_of_pos = 0
    amount_of_neg = 0
    time_copy = feature_val_dict.copy()

    for key1, item1 in time_copy.items():
        if item1 >= 0:
            if amount_of_pos >= 3:
                del feature_val_dict[key1]
            else:
                amount_of_pos += 1
        else:
            if amount_of_neg >= 3:
                del feature_val_dict[key1]
            else:
                amount_of_neg += 1

    output_dir = name.split('/')[-1][:-5]
    if not os.path.exists(f"{graphics_path}/{output_dir}"):
        os.makedirs(f"{graphics_path}/{output_dir}")

    shap.plots.waterfall(shap_values[0])
    plt.savefig(f"{graphics_path}/{output_dir}/{acid}.png", dpi=300, bbox_inches="tight")
    plt.close()

    with open(name, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        if "graphics" not in json_data:
            json_data["graphics"] = {}

        json_data["graphics"][acid] = str(Path(f"{graphics_path}/{output_dir}/{acid}.png").resolve())

    with open(name, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    return feature_val_dict


def predict_importance_nutri(data, name, nutri_path="models/classic_pipe/nutri",
                             importance_path="models/classic_pipe/nutri_explainers",
                             graphics_path="desktop/graphics"):
    nutri_dict = dict()
    feature_names = jl.load(f"{importance_path}/feature_names.pkl")

    data = data.drop(nutri_for_predict, axis=1).to_numpy()

    for key, item in nutri.items():
        model = jl.load(f"{nutri_path}/{key}_catboost.pkl")
        set_ensemble(model)
        logit = model.predict(data)

        explainer = jl.load(f"{importance_path}/{key}_explainers.pkl")
        X_single = pd.DataFrame(data, columns=feature_names)

        shap_values = explainer(X_single)

        shap_df = pd.DataFrame({
            "feature": feature_names,
            "shap_value": shap_values.values[0]
        })
        df = shap_df.sort_values(by="shap_value", key=abs, ascending=False)
        feature_val_dict = {f: round(v, 2) for f, v in zip(df["feature"], df["shap_value"])}

        amount_of_pos = 0
        amount_of_neg = 0
        time_copy = feature_val_dict.copy()

        for key1, item1 in time_copy.items():
            if item1 >= 0:
                if amount_of_pos >= 3:
                    del feature_val_dict[key1]
                else:
                    amount_of_pos += 1
            else:
                if amount_of_neg >= 3:
                    del feature_val_dict[key1]
                else:
                    amount_of_neg += 1

        nutri_dict[item] = feature_val_dict

        output_dir = name.split('/')[-1][:-5]
        if not os.path.exists(f"{graphics_path}/{output_dir}"):
            os.makedirs(f"{graphics_path}/{output_dir}")

        print(output_dir)
        shap.plots.waterfall(shap_values[0])
        plt.savefig(f"{graphics_path}/{output_dir}/{key}.png", dpi=300, bbox_inches="tight")
        plt.close()

        with open(name, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            if "graphics" not in json_data:
                json_data["graphics"] = {}
            json_data["graphics"][key] = str(Path(f"{graphics_path}/{output_dir}/{key}.png").resolve())


        with open(name, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

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
    json_report = str(json_report)
    acids_dict = dict()
    importance_acid_dict = dict()
    importance_nutri_dict = dict()

    data = load_data_from_json(json_report)
    data = clear_data(data)

    importance_nutri_dict = predict_importance_nutri(data, json_report)

    data = data.to_numpy()

    for acid in acids:
        model = jl.load(f"{model_path}/{acid}_ensemble.pkl")
        logit = model.predict(data)
        acids_dict[acid] = logit

        set_ensemble(model)
        importance = predict_importance_acids(data[0], acid, json_report)
        importance_acid_dict[acid] = importance

    # print(importance_nutri_dict)
    # print(importance_acid_dict)
    make_uni_acids(json_report)

    with open(json_report, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        json_data["importance_acid"] = importance_acid_dict
        json_data["importance_nutrient"] = importance_nutri_dict
        json_data["result_acids"] = {
            k: float(v[0])
            for k, v in acids_dict.items()
        }

        print(json_data["result_acids"])
    with open(json_report, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return acids_dict


def make_uni_acids(name, graphics_path="desktop/graphics", grid_size=(2, 2)):
    output_dir = name.split('/')[-1][:-5]

    images = [Image.open(f"{graphics_path}/{output_dir}/{name}.png") for name in main_acids]

    w, h = images[0].size
    cols, rows = grid_size

    grid_w = cols * w + (cols + 1)
    grid_h = rows * h + (rows + 1)
    grid = Image.new("RGB", (grid_w, grid_h), color="white")


    for idx, img in enumerate(images):
        r, c = divmod(idx, cols)
        if r >= rows:
            break

        grid.paste(img, (w * c, h * r))

    grid.save(f"{graphics_path}/{output_dir}/uni_acids.png")


if __name__ == '__main__':
    #print(load_data_from_json("desktop/reports/report_2025-10-07_1759855680.json"))
    print(predict_from_file(json_report="desktop/reports/report_2025-10-07_1759855680.json",
                           model_path="models/classic_pipe/acids"))
    # print(predict_from_file(json_report="desktop/reports/Норм_2025-10-07_1759796029.json",
    #                        model_path="models/classic_pipe"))
