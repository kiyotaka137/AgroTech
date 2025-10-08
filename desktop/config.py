import os

def get_server_url():
    """Получает URL сервера из .env файла"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('SERVER_URL='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        return 'http://localhost:8000'  # значение по умолчанию

def save_server_url(url):
    """Сохраняет URL сервера в .env файл"""
    with open('.env', 'w') as f:
        f.write(f'SERVER_URL={url}\n')