import sys
from PyQt6.QtWidgets import QApplication
# если класс в том же файле — импорт не нужен; иначе:
from .new_report_window import AdminNewReport  # или NewReport

def main():
    # Не создаём второй QApplication, если он уже есть (удобно при интеграции)
    app = QApplication.instance()
    created_app = False
    if app is None:
        app = QApplication(sys.argv)
        created_app = True

    dlg = AdminNewReport()   # или NewReport()
    dlg.show()

    # Если мы создали QApplication — запускаем event loop и корректно выходим
    if created_app:
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
