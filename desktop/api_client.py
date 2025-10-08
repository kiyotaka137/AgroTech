import requests
from typing import Optional, Dict, Any, List

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Базовый метод для выполнения запросов"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else None
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса к {url}: {e}")
            return None

    def get_all_records(self) -> Optional[List[Dict]]:
        """Получить все записи (GET /records/)"""
        return self._request('GET', '/records/')

    def add_records(self, records: List[Dict]) -> Optional[Dict]:
        """Добавить записи (POST /records/)"""
        return self._request('POST', '/records/', json={"root": records})

    def get_record_by_name(self, name: str) -> Optional[Dict]:
        """Получить запись по name (GET /records/{name})"""
        return self._request('GET', f'/records/{name}')

    def get_all_names(self) -> Optional[List[str]]:
        """Получить все имена (GET /records/names/all)"""
        return self._request('GET', '/records/names/all')

    