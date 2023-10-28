# Set up logging first in case other imports fail

import datetime
import logging
import sys

logging.basicConfig(filename='menu_scanner.log', encoding='utf-8', level=logging.DEBUG)
logger = logging.getLogger(__name__)
# dd/mm/YY H:M:S
logger.info('Starting ' + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

if hasattr(sys, '_MEIPASS'):
    logger.debug('Path: ' + str(sys.path))
    logger.debug('Temp dir: ' + sys._MEIPASS)
    logger.debug('Temp dir contents: ' + str(os.listdir(sys._MEIPASS)))

    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

# Other imports

import math
import os
import os.path
import stat
import tempfile

# import cv2 for images
import fitz
import PyQt5.QtWidgets as Widgets
import PyQt5.QtGui as Gui
import PyQt5.QtCore as Core
import pytesseract

if hasattr(sys, '_MEIPASS'):
    # --- get tesseract runnable ---
    # make unpacked exe file actually executable
    os.chmod(os.path.join(sys._MEIPASS, 'tesseract.exe'), stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)
    # fix pytesseract command which cannot locate the exe
    pytesseract.pytesseract.tesseract_cmd = os.path.join(sys._MEIPASS, 'tesseract.exe')
    # point tesseract to the unpacked tessdata
    os.environ["TESSDATA_PREFIX"] = sys._MEIPASS

# load the input image, convert it from BGR to RGB channel ordering,
# and use Tesseract to localize each area of text in the input image
#file_path = r"\Users\Jonathan\Downloads\Screenshot 2023-10-21 144424.png" #args["image"]
#image = cv2.imread(file_path)
#rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

#doc = fitz.open(r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023.pdf")
doc = fitz.open('/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf')
image_file = tempfile.NamedTemporaryFile(suffix='.png')
image_fname = image_file.name
doc[0].\
    get_pixmap(matrix=fitz.Matrix(8,8)).\
    save(image_fname) #r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023_pymupdf.png")

app = Widgets.QApplication([])

pix_width = Gui.QPixmap(image_fname).width()

#results = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
results = pytesseract.image_to_data(image_fname, output_type=pytesseract.Output.DICT)

# loop over each of the individual text localizations
text_dict = {}
for i in range(0, len(results["text"])):
#    conf = int(results["conf"][i])
#    if conf < 0.2:
#        continue
    force_break = "|" in results["text"][i]

    text = "".join([c if ord(c) < 128 and c not in "_|" else "" for c in results["text"][i]]).strip()
    if text == "":
        continue


    curr_text_dict = text_dict
    for level in "page_num", "block_num", "par_num", "line_num":
        if results[level][i] not in curr_text_dict:
            if level != "line_num":
                curr_text_dict[results[level][i]] = {}
            else:
                curr_text_dict[results[level][i]] = []
        curr_text_dict = curr_text_dict[results[level][i]]

    line_blocks = curr_text_dict
    if len(line_blocks) == 0:
        new = True
    else:
        curr_text_dict = line_blocks[-1]
        assert curr_text_dict["num"] < results["word_num"][i]
        assert curr_text_dict["x"] < results["left"][i]
        new = results["left"][i] - (curr_text_dict["x"] + curr_text_dict["w"]) > 0.01*pix_width

    if force_break or new:
        curr_text_dict = {}
        line_blocks.append(curr_text_dict)
        curr_text_dict["x"] = results["left"][i]
        curr_text_dict["y"] = results["top"][i]
        curr_text_dict["w"] = results["width"][i]
        curr_text_dict["h"] = results["height"][i]
        curr_text_dict["num"] = results["word_num"][i]
        curr_text_dict["text"] = text
    else:
#        curr_text_dict["x"] = min(curr_text_dict["x"], results["left"][i])
#        curr_text_dict["y"] = min(curr_text_dict["y"], results["top"][i])
#        curr_text_dict["w"] = max(curr_text_dict["w"], results["width"][i])
#        curr_text_dict["h"] = max(curr_text_dict["h"], results["height"][i])
        curr_text_dict["w"] = results["width"][i] + results["left"][i] - curr_text_dict["x"]
        curr_text_dict["h"] = max(curr_text_dict["h"], results["height"][i] + results["top"][i] - curr_text_dict["y"])
        curr_text_dict["num"] = results["word_num"][i]
        curr_text_dict["text"] += " " + text

    # extract the bounding box coordinates of the text region from
    # the current result
#    x = results["left"][i]
#    y = results["top"][i]
#    w = results["width"][i]
#    h = results["height"][i]
#    # extract the OCR text itself along with the confidence of the
#    # text localization
#    text = results["text"][i]
#    conf = int(results["conf"][i])

# filter out weak confidence text localizations
#    if conf > args["min_conf"]:
#        # display the confidence and text to our terminal
#        print("Confidence: {}".format(conf))
#        print("Text: {}".format(text))
#        print("")
#        # strip out non-ASCII text so we can draw the text on the image
#        # using OpenCV, then draw a bounding box around the text along
#        # with the text itself
#        text = "".join([c if ord(c) < 128 else "" for c in text]).strip()
#        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
#        cv2.putText(image, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
#            0.5, (0, 0, 255), 1)
# show the output image

#for p in text_dict.values():
#    for b in p.values():
#        for par in b.values():
#            for l in par.values():
#                cv2.rectangle(image, (l["x"], l["y"]), (l["x"] + l["w"], l["y"] + l["h"]), (0, 255, 0), 2)
#                cv2.putText(image, "!" + l["text"], (l["x"], l["y"] - 10), cv2.FONT_HERSHEY_SIMPLEX,
#                    0.5, (0, 0, 255), 1)

#cv2.imshow("Image", image)
#cv2.waitKey(0)

class MyImageWidget(Widgets.QLabel):
    def __init__(self, boxes):
        super().__init__()

        self.boxes = {box: False for box in boxes}
        self.ratio = 1

    def set_menu_item_edit(self, menu_item_edit):
        self.menu_item_edit = menu_item_edit

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.pixmap_height = pixmap.height()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = Gui.QPainter(self)
        height_adjust = math.floor((self.height() - self.pixmap_height)/2)
        for box, clicked in self.boxes.items():
            rect = [math.floor(self.ratio*val) for val in box]
            rect[1] = rect[1] + height_adjust
            if not clicked:
                painter.setPen(Gui.QPen(Core.Qt.red, 2))
            else:
                painter.setPen(Gui.QPen(Core.Qt.green, 2))
            painter.drawRect(*rect)

    def mousePressEvent(self, event):
        x = event.localPos().x()
        y = event.localPos().y()
        height_adjust = math.floor((self.height() - self.pixmap_height)/2)
        for box in self.boxes:
            if box[0] <= x/self.ratio <= box[0] + box[2] and box[1] <= y/self.ratio <= box[1] + box[3]:
                self.boxes[box] = True
                self.menu_item_edit.setText(box["text"])
                self.repaint()

class MyWindow(Widgets.QMainWindow):
    def __init__(self, path, boxes):
        super().__init__()

        central_widget = Widgets.QWidget()
        self.setCentralWidget(central_widget)
        central_layout = Widgets.QHBoxLayout(central_widget)

        self.pixmap = Gui.QPixmap(path)
        self.base_height = self.pixmap.height()
        self.base_width = self.pixmap.width()
        self.image_widget = MyImageWidget(boxes) #Widgets.QLabel()
        self.image_widget.setMinimumWidth(100)
        self.image_widget.setMinimumHeight(100)
        self.image_widget.setPixmap(self.pixmap)
        self.image_widget.installEventFilter(self)

        central_layout.addWidget(self.image_widget)
        right_column = Widgets.QVBoxLayout()
        central_layout.addLayout(right_column)
        right_column.addWidget(Widgets.QLabel("Menu item name"))
        self.menu_item_edit = Widgets.QLineEdit()
        self.menu_item_edit.setMaximumWidth(100)
        right_column.addWidget(self.menu_item_edit)
        self.image_widget.set_menu_item_edit(self.menu_item_edit)
        #right_column.setSpacing(100)

    # from https://stackoverflow.com/questions/27676034/pyqt-place-scaled-image-in-centre-of-label
    def eventFilter(self, source, event):
        if (source is self.image_widget and event.type() == Core.QEvent.Resize):
            # re-scale the pixmap when the label resizes
            ratio = min(self.image_widget.width()/self.base_width, self.image_widget.height()/self.base_height)
            self.image_widget.ratio = ratio
            self.image_widget.setPixmap(
                self.pixmap.scaled(math.floor(self.base_width*ratio), math.floor(self.base_height*ratio), transformMode=Core.Qt.SmoothTransformation)
            )
#            self.image_widget.setPixmap(self.pixmap.scaled(
#                self.image_widget.size(), Core.Qt.KeepAspectRatio,
#, menu_item_edit                Core.Qt.SmoothTransformation))
        return super().eventFilter(source, event)

#window = Widgets.QLabel()
#window.setPixmap(PyQt5.QtGui.QPixmap(path))
#window = Widgets.QMainWindow()

window = MyWindow(
    image_fname,
    [(line_block["x"], line_block["y"], line_block["w"], line_block["h"], line_block["text"])
        for p in text_dict.values()
        for b in p.values()
        for par in b.values()
        for l in par.values()
        for line_block in l]
)

window.show()
app.exec()

