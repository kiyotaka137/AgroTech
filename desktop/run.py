from desktop.window_manager import window_manager

from .main import send_new_reports

if __name__ == "__main__":
    window_manager.show_main_window()

    window_manager.exec()

    send_new_reports()