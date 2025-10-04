import json
from pathlib import Path
from datetime import datetime

class ReportLoader:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_path = Path(__file__).parent / reports_dir
        self.reports_path.mkdir(parents=True, exist_ok=True) 

    def list_reports(self):
        """
        Возвращает список JSON-файлов в порядке убывания даты изменения
        """
        files = [f for f in self.reports_path.glob("*.json")]
        return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)

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

    def get_report_info(self, path: Path):
        """
        Возвращает словарь с именем и датой последнего изменения файла
        """
        mtime = path.stat().st_mtime
        return {
            "name": path.stem,
            "modified": datetime.fromtimestamp(mtime)
        }
