import math

import PyQt5.QtWidgets as Widgets
import PyQt5.QtGui as Gui
import PyQt5.QtCore as Core

#path = "/mnt/c/Users/Jonathan/Downloads/Screenshot 2023-10-21 144424.png"
path = r"\Users\Jonathan\Downloads\Screenshot 2023-10-21 144424.png"
#path = "/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf"
#path = r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023.pdf"

app = Widgets.QApplication([])

class MyImageWidget(Widgets.QLabel):
    def __init__(self, boxes):
        super().__init__()

        self.boxes = boxes

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = Gui.QPainter(self)
        painter.setPen(Gui.QPen(Core.Qt.red, 8))
        for box in self.boxes:
            painter.drawRect(*box)


class MyWindow(Widgets.QMainWindow):
    def __init__(self, path):
        super().__init__()

        central_widget = Widgets.QWidget()
        self.setCentralWidget(central_widget)
        central_layout = Widgets.QHBoxLayout(central_widget)

        self.pixmap = Gui.QPixmap(path)
        self.base_height = self.pixmap.height()
        self.base_width = self.pixmap.width()
        self.image_widget = MyImageWidget([[40, 40, 400, 200]]) #Widgets.QLabel()
        self.image_widget.setMinimumWidth(100)
        self.image_widget.setMinimumHeight(100)
        self.image_widget.setPixmap(self.pixmap)
        self.image_widget.installEventFilter(self)

        central_layout.addWidget(self.image_widget)
        button = Widgets.QPushButton("foo")
        button.setMaximumWidth(100)
        central_layout.addWidget(button)
        central_layout.setSpacing(100)

    # from https://stackoverflow.com/questions/27676034/pyqt-place-scaled-image-in-centre-of-label
    def eventFilter(self, source, event):
        if (source is self.image_widget and event.type() == Core.QEvent.Resize):
            # re-scale the pixmap when the label resizes
            ratio = min(self.image_widget.width()/self.base_width, self.image_widget.height()/self.base_height)
            self.image_widget.setPixmap(
                self.pixmap.scaled(math.floor(self.base_width*ratio), math.floor(self.base_height*ratio), transformMode=Core.Qt.SmoothTransformation)
            )
#            self.image_widget.setPixmap(self.pixmap.scaled(
#                self.image_widget.size(), Core.Qt.KeepAspectRatio,
#                Core.Qt.SmoothTransformation))
        return super().eventFilter(source, event)
 



#window = Widgets.QLabel()
#window.setPixmap(PyQt5.QtGui.QPixmap(path))
#window = Widgets.QMainWindow()
window = MyWindow(path)

#image_pixmap = PyQt5.QtGui.QPixmap(path)
#image_widget.setPixmap(image_pixmap)
#
#def resize_event_filter(self, obj,  event):
#    if (event.type() == Core.QEvent.Resize):
#        image_pixmap.scaled(image_widget.size(), Core.Qt.KeepAspectRatio)
#    image_widget.eventFilter(obj, event)
#
#image_widget.eventFilter = resize_event_filter

window.show()
app.exec()

#class MyImageWidget(Widgets.QWdiget):
#    def __init__(self, path):
#        super().__init__()
#
#        self.pixmap = PyQt5.QtGui.QPixmap(path)
#
#    def paintEvent(self, e):
#        super.paintEvent(e)
#        painter = 
#        self.pixmap
#
