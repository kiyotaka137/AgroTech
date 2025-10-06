import requests
import os
import time
import PyPDF2
import pandas as pd
from io import StringIO

#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 - kul
#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 - sashakuly
#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 - попка
API_KEY = "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"
MODEL = "deepseek/deepseek-chat-v3.1:free"

def extract_text_with_pypdf2(pdf_path):
    """Извлекает текст с помощью PyPDF2"""
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text


def batch_query_deepseek(queries):
    """
    queries: dict[str, str] - словарь вида {"имя_файла": "prompt"}
    Каждый ответ сохраняется в отдельный CSV-файл <имя_файла>.csv
    """
    for i, (key, query) in enumerate(queries.items(), 1):
        print(f"Обработка запроса {i}/{len(queries)}: {key}")

        response = query_deepseek(query)

        if response:
            txt_path = f"parsed_data\\step_analize\\{key}_raw.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(response)

            try:
                df = pd.read_csv(StringIO(response), sep="|")

                output_path = f"parsed_data\\step_analize\\{key}.csv"
                df.to_csv(output_path, sep="|", index=False, encoding="utf-8")

                print(f"✓ Ответ сохранён: {output_path}")
            except Exception as e:
                print(f"⚠️ Не удалось сохранить {key}.csv: {e}")
        else:
            print(f"✗ Ошибка: не получен ответ для {key}")

        time.sleep(1)


def query_deepseek(prompt):
    """
    Отправляет запрос к DeepSeek через OpenRouter API
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 4000
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()

    result = response.json()
    return result['choices'][0]['message']['content']


def get_pdf_files_with_names(folder_path):
    """
    Возвращает список кортежей (полный_путь, имя_файла) для всех PDF в папке.
    """
    pdf_files = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            full_path = os.path.join(folder_path, filename)
            pdf_files.append((full_path, filename))

    return pdf_files


if __name__ == "__main__":
    FOLDER = "data/Для Хакатона/"

    ration_prompt = """Это распаршенный текст pdf файла
Можешь достать оттуда только табличку Рацион и вывести ТОЛЬКО ее в формате .csv с разделителем |
Без общих значений, если ячейка пустая, все равно добавь ее в таблицу csv
Выведи без дополнительных слов и кавычек сразу табличку ввиде csv
Текст:
{text}
"""

    analise_prompt = """Это распаршенный текст pdf файла
Можешь достать оттуда только табличку "Сводный анализ: Лактирующая корова" возьми только строчки с такими нутриенами:
ЧЭЛ 3x NRC (МДжоуль/кг)
СП (%)
Крахмал (%)
RD Крахмал 3xУровень 1 (%)
Сахар (ВРУ) (%)
НСУ (%)
НВУ (%)
aNDFom (%)
CHO B3 pdNDF (%)
Растворимая клетчатка (%)
aNDFom фуража (%)
peNDF (%)
CHO B3 медленная фракция (%)
CHO C uNDF (%)
СЖ (%)
ОЖК (%)
K (%)

Если какой то из этих строчек нет, то добавь пустую строчку с пустыми ячейками
Если какая то ячейка пустая то оставь ее пустой
Выведи ТОЛЬКО таблицу в формате .csv с разделителем |
Выведи без дополнительных слов и кавычек сразу табличку ввиде csv
Текст:
{text}
    """

    queries = dict()

    for name in os.listdir(FOLDER):
        full_path = os.path.join(FOLDER, name)
        if os.path.isdir(full_path):
            print(full_path)
            for i, (pdf, pdf_name) in enumerate(get_pdf_files_with_names(full_path)):
                base_name = os.path.splitext(pdf_name)[0]
                csv_path = os.path.join("parsed_data/step_analize", f"{base_name}.csv")

                if os.path.exists(csv_path):
                    print(f"Пропущено (уже обработано): {pdf_name}")
                    continue

                text_pdf = extract_text_with_pypdf2(pdf)
                queries[base_name] = analise_prompt.format(text=text_pdf)

    batch_query_deepseek(queries)
