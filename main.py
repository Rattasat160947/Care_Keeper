import sys
from PySide6.QtWidgets import QApplication, QWidget

from gui import Ui_MainWindow

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.showMaximized()

    def Upload(self):
        pass

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
