import json
from pathlib import Path

class ReportLoader:
    def __init__(self, reports_dir: str = "reports"):
        # Путь относительно текущего файла
        self.reports_path = Path(__file__).parent / reports_dir
        self.reports_path.mkdir(parents=True, exist_ok=True)  # создаем папку если нет

    def list_reports(self):
        """
        Возвращает список всех JSON-файлов в папке reports
        """
        return sorted([f for f in self.reports_path.glob("*.json")])

    def load_report(self, filename: str):
        """
        Считывает JSON файл по имени и возвращает словарь
        """
        file_path = self.reports_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Файл {filename} не найден в папке {self.reports_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
