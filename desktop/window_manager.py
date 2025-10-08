from PyQt6.QtWidgets import QApplication
import sys

class WindowManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.current_window = None
        
        # Загружаем стили
        with open("desktop/styles/styles_light.qss", "r", encoding="utf-8") as f:
            self.app.setStyleSheet(f.read())
    
    def show_main_window(self):
        from .main import MainWindow
        if self.current_window:
            self.current_window.close()
        self.current_window = MainWindow()
        self.current_window.show()
        return self.current_window
    
    def show_admin_window(self):
        from .admin_main_window import AdminMainWindow
        if self.current_window:
            self.current_window.close()
        self.current_window = AdminMainWindow()
        self.current_window.show()
        return self.current_window
    
    def exec(self):
        send_new_reports()
        return self.app.exec()

# Глобальный экземпляр
window_manager = WindowManager()