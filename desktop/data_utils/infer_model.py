import json
import pandas as pd
import numpy as np
import joblib as jl

import config
from training import change_mapping, uniq_ration, uniq_step, uniq_changed_ration, name_mapping


def extract_to_row(ingridients):
    row = [0] * (len(uniq_changed_ration) + len(uniq_step))  # todo: тут жесткий костыль
    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_changed_ration)}
    name_mapping = change_mapping()

    for elem in ingridients:  # todo: изменить когда в json будет храниться чисто 2 элемента
        clear_name = name_mapping[elem[0]]  # todo: сделать здесь проверку есть ли элемент в name_mapping если нет то ллм прикрутить
        row[uniq_dict[clear_name]] += float(elem[-1].replace(',', '.'))

    return row

def load_data_from_json(path_name: str):
    with open(path_name, "r", encoding="utf-8") as f:
        json_file = json.load(f)
    rows = [list(elem.values()) for elem in json_file['rows']]

    final_row = extract_to_row(rows)
    return final_row

def clear_data(data):
    for item in config.for_dropping:
        data = data.drop(item, axis=1)

    for key, value in config.medians_of_data:
        if data[key] is None:
            data[key] = value

    return data.to_numpy()

def predict_from_file(json_report, model_path, acids_list):
    acids_dict = dict()

    data = load_data_from_json(json_report)
    data = clear_data(data)

    for acid in acids_list:
        model = jl.load(f"{model_path}/{acid}_ensemble.pkl")
        logit = model.predict(data)
        acids_dict[acid] = logit

    return acids_dict

if __name__ == '__main__':
    print(predict_from_file(json_report="../reports/report_2025-10-05_1759679897.json",
                            model_path="../../models/classic_pipe",
                            acids_list=config.acids))