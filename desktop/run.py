from desktop.window_manager import window_manager
from desktop.main import send_new_reports
import sys

if __name__ == "__main__":

    window_manager.show_main_window()
    window_manager.exec()

    # Отправляем отчеты после закрытия окна
    send_new_reports()
