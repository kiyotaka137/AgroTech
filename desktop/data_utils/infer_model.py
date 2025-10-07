import json
import pandas as pd
import numpy as np
import joblib as jl

from .config import acids, for_dropping, medians_of_data
from training import change_mapping, uniq_ration, uniq_step, uniq_changed_ration, name_mapping


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

    return data.to_numpy()


def predict_from_file(json_report, model_path="models/classic_pipe"):
    acids_dict = dict()

    data = load_data_from_json(json_report)
    data = clear_data(data)

    for acid in acids:
        model = jl.load(f"{model_path}/{acid}_ensemble.pkl")
        logit = model.predict(data)
        acids_dict[acid] = logit

    return acids_dict

if __name__ == '__main__':
    #print(load_data_from_json("../reports/Норм_2025-10-07_1759796029.json"))
    print(predict_from_file(json_report="desktop/reports/Норм_2025-10-07_1759796029.json",
                           model_path="models/classic_pipe"))
