import pandas as pd

from training import name_mapping, uniq_ration

target_path = "../data/Для Хакатона/targets.csv"
rations_path = "../parsed_data/{table}.csv"


def get_ohe_train_test_data(column_coef="% СВ"):
    targets = pd.read_csv(target_path, sep=";")
    uniq_dict = {elem: ind for ind, elem in enumerate(uniq_ration)}
    data = []

    for i, elem in enumerate(targets["Рацион"].values):
        row = [0] * len(uniq_ration)

        if elem[-1] == '.':
            elem = elem[:-1]
        ration = pd.read_csv(rations_path.format(table=elem.strip()), sep="|")

        for i, ingr in enumerate(ration["Ингредиенты"]):
            clear_elem = name_mapping[ingr]
            row[uniq_dict[clear_elem]] += float(ration.loc[i, column_coef].replace(",", "."))

        data.append(row)

    df = pd.DataFrame(data, columns=uniq_ration)
    return {
            "train": df[10:],
            "test": df[:10]
    }

if __name__ == "__main__":
    print(get_ohe_train_test_data()["train"])