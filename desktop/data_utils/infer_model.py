import json
import pandas as pd
import numpy as np
import joblib as jl

from training import change_mapping, uniq_ration, uniq_step, uniq_changed_ration, name_mapping


def extract_to_row(ingridients):
    row = [0] * (len(uniq_changed_ration) + len(uniq_step) - 5)  # todo: тут жесткий костыль
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


def predict_from_file(json_report, model_path: str="models/classic_pipe/lasso_model.pkl"): # todo: надо наверн возвращать список кислот
    model = jl.load(model_path)

    data = [load_data_from_json(json_report)]
    pred = model.predict(data)

    return pred

# if __name__ == '__main__':
#     print(predict_from_file("../reports/report_2025-10-05_1759679897.json", "../../models/classic_pipe/ridge_model.pkl"))