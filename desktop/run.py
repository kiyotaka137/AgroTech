from desktop.window_manager import window_manager
from desktop.config import save_server_url, get_server_url
from desktop.main import send_new_reports
import sys

if __name__ == "__main__":
    try:
        # Получаем URL сервера из аргументов или .env файла
        if len(sys.argv) > 1:
            server_url = sys.argv[1]
            if server_url:  # Проверяем, что URL не пустой
                save_server_url(server_url)
            else:
                server_url = get_server_url()
        else:
            server_url = get_server_url()
        
        # Убедимся, что server_url не None
        if server_url is None:
            server_url = "http://localhost:8000"
            save_server_url(server_url)
            print("URL был None, установлено значение по умолчанию")
        
        window_manager.show_main_window()
        window_manager.exec()
        
        # Отправляем отчеты после закрытия окна
        send_new_reports(server_url)
        
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        # Сбрасываем URL по умолчанию
        save_server_url("http://localhost:8000")
        print("URL сброшен на значение по умолчанию")