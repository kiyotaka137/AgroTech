#!/usr/bin/env python3
# training/ohe.py

import os
import glob
import ast
import sys
import argparse
import pandas as pd
import numpy as np
from sklearn.preprocessing import MultiLabelBinarizer

DATA_DIR_DEFAULT = "parsed_data"

def read_all_csvs(csv_dir):
    paths = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    print(f"Ищу CSV в {csv_dir} -> найдено {len(paths)} файлов")
    for p in paths:
        print(" -", p)
    if not paths:
        return [], [("NO_FILES", "Нет файлов *.csv в папке")]

    dfs = []
    failed = []
    for p in paths:
        success = False
        last_err = ""
        # сначала пробуем C-движок (поддерживает low_memory)
        for enc in ("cp1251", "utf-8-sig", "utf-8"):
            try:
                df_tmp = pd.read_csv(p, engine="c", encoding=enc, low_memory=False)
                dfs.append(df_tmp)
                success = True
                last_err = f"OK engine=c enc={enc}"
                break
            except Exception as e:
                last_err = f"engine=c enc={enc} error: {e}"
        if not success:
            # fallback: python engine — без low_memory, с on_bad_lines='skip'
            for enc in ("cp1251", "utf-8-sig", "utf-8"):
                try:
                    df_tmp = pd.read_csv(p, engine="python", encoding=enc, on_bad_lines="skip")
                    dfs.append(df_tmp)
                    success = True
                    last_err = f"OK engine=python enc={enc} (on_bad_lines=skip)"
                    break
                except Exception as e:
                    last_err = f"engine=python enc={enc} error: {e}"
        if not success:
            failed.append((p, last_err))
            print("  НЕ УДАЛОСЬ прочитать:", p, ":", last_err)
        else:
            print("  Прочитан:", p, "->", last_err)

    return dfs, failed

def find_column(df, candidates):
    cols = list(df.columns)
    # точные совпадения
    for c in candidates:
        if c in cols:
            return c
    # частичные совпадения в lower
    lc = [c.lower() for c in cols]
    for cand in candidates:
        cand_l = cand.lower()
        for i, col in enumerate(lc):
            if cand_l in col:
                return cols[i]
    return None

def parse_ingredient_cell(x):
    if pd.isna(x):
        return []
    if isinstance(x, (list, tuple, set)):
        return [str(i).strip() for i in x if str(i).strip()!='']
    s = str(x).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            L = ast.literal_eval(s)
            if isinstance(L, (list, tuple, set)):
                return [str(i).strip() for i in L if str(i).strip()!='']
        except Exception:
            pass
    for sep in (";", ",", "|", "/"):
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()!='']
            if parts:
                return parts
    if "  " in s:
        parts = [p.strip() for p in s.split("  ") if p.strip()!='']
        if parts:
            return parts
    return [s] if s!='' else []

def parse_percent(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", ".").replace(" ", "")
    if s.endswith("%"):
        try:
            return float(s[:-1]) / 100.0
        except:
            return np.nan
    try:
        v = float(s)
        if v > 1.5:  # например 12 -> 0.12
            return v / 100.0
        return v
    except:
        return np.nan

def main():
    parser = argparse.ArgumentParser(description="Create OHE and weighted OHE from parsed_data CSVs")
    parser.add_argument("--data-dir", default=DATA_DIR_DEFAULT, help="папка с CSV (default: parsed_data)")
    parser.add_argument("--ingredient-col", default=None, help="имя колонки ингредиентов (если не указан, автопоиск)")
    parser.add_argument("--weight-col", default=None, help="имя колонки веса (СВ % или гп). Если не указан — автопоиск")
    parser.add_argument("--out-ohe", default=None, help="путь для ohe_raw.csv (дефолт parsed_data/ohe_raw.csv)")
    parser.add_argument("--out-weighted", default=None, help="путь для weighted_ohe.csv (дефолт parsed_data/weighted_ohe.csv)")
    args = parser.parse_args()

    data_dir = args.data_dir
    out_ohe = args.out_ohe or os.path.join(data_dir, "ohe_raw.csv")
    out_weighted = args.out_weighted or os.path.join(data_dir, "weighted_ohe.csv")

    dfs, failed = read_all_csvs(data_dir)
    if len(dfs) == 0:
        print("Не найдено CSV для чтения. Ошибки/файлы:", failed)
        sys.exit(1)

    df = pd.concat(dfs, ignore_index=True, sort=False)

    # --- Автофиксер склеенных заголовков, если где-то есть колонка с '|' в имени ---
    def try_split_merged_column(df):
        for col in list(df.columns):
            if "|" in str(col):
                # если имя колонки содержит ожидаемые под-имена — считаем, что это склеенный заголовок
                header_parts = [p.strip() for p in str(col).split("|") if p.strip()]
                if any(h.lower() in ("ингредиенты", "ингредиент", "св", "% св", "% св", "гп", "% гп", "%") for h in
                       header_parts):
                    # split each row of that column by '|' into new columns
                    parts_df = df[col].astype(str).str.split("|", expand=True)
                    # если разных колонок в данных больше/меньше, подрезаем/дополняем именами
                    n = parts_df.shape[1]
                    names = header_parts[:n] + [f"col_{i}" for i in range(len(header_parts), n)]
                    parts_df.columns = names
                    df = pd.concat([df.drop(columns=[col]), parts_df], axis=1)
                    print("Разделил склеенную колонку", col, "на:", parts_df.columns.tolist())
                    return df
        return df

    df = try_split_merged_column(df)
    # --- конец фикса ---

    print("Прочитано файлов:", len(dfs), "Общий размер DF:", df.shape)

    ing_candidates = ["Ингредиенты", "Ингредиент", "ingredients", "ingredient", "Состав", "components", "components_list"]
    weight_candidates = ["СВ %", "СВ%", "%СВ", "СВ", "гп", "ГП", "gp", "gp_percent", "percent", "%", "массовая доля", "массовая_доля"]

    ing_col = args.ingredient_col or find_column(df, ing_candidates)
    if not ing_col:
        print("Не удалось найти колонку ингредиентов. Доступные колонки:", list(df.columns[:80]))
        sys.exit(1)
    print("Использую колонку ингредиентов:", ing_col)

    weight_col = args.weight_col or find_column(df, weight_candidates)
    if weight_col:
        print("Найдена колонка веса:", weight_col)
    else:
        print("Колонка веса не найдена автоматически. Будет сохранён только OHE (без взвешивания).")

    # Парсим ингредиенты
    print("Парсю ингредиенты...")
    df["_parsed_ingredients"] = df[ing_col].apply(parse_ingredient_cell)

    # OHE (MultiLabelBinarizer)
    mlb = MultiLabelBinarizer(sparse_output=False)
    try:
        X_ohe = mlb.fit_transform(df["_parsed_ingredients"])
    except Exception as e:
        print("Ошибка при OHE:", e)
        sys.exit(1)

    ohe_cols = list(mlb.classes_)
    X_ohe_df = pd.DataFrame(X_ohe, columns=ohe_cols, index=df.index)
    X_ohe_df.to_csv(out_ohe, index=False, encoding="utf-8-sig")
    print("Сохранён OHE (raw):", out_ohe, "количество признаков:", len(ohe_cols))

    if not weight_col:
        print("Колонка веса не указана/не найдена. Завершение.")
        sys.exit(0)

    # Парсим веса и домножаем
    print("Парсю значения веса и домножаю OHE...")
    weights = df[weight_col].apply(parse_percent).fillna(0.0).astype(float).values
    X_weighted = X_ohe * weights.reshape(-1, 1)
    X_weighted_df = pd.DataFrame(X_weighted, columns=[f"W_{c}" for c in ohe_cols], index=df.index)

    out_df = pd.concat([df[[ing_col, weight_col]].reset_index(drop=True),
                        X_ohe_df.reset_index(drop=True),
                        X_weighted_df.reset_index(drop=True)], axis=1)
    out_df.to_csv(out_weighted, index=False, encoding="utf-8-sig")
    print("Сохранён взвешенный OHE:", out_weighted)
    print("Готово.")

if __name__ == "__main__":
    main()
