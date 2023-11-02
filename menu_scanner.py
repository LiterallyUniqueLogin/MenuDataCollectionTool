
# tutorials
# https://www.pythonguis.com/tutorials/creating-your-first-pyqt-window/
# https://www.pythontutorial.net/pyqt/
# and
# https://superuser.com/questions/1791373/location-of-wsl-home-directory-in-windows

import datetime
import logging
import sys

# ---- Set up logging first in case imports fail ------

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
import polars as pl
import PyQt5.QtWidgets as Widgets
import PyQt5.QtGui as Gui
import PyQt5.QtCore as Core
import pytesseract

# ---- Set up tessseract ----

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

def create_image_from_pdf(pdf_fname):
    doc = fitz.open(pdf_fname)
    image_file = tempfile.NamedTemporaryFile(suffix='.png')
    image_fname = image_file.name
    doc[0].\
        get_pixmap(matrix=fitz.Matrix(8,8)).\
        save(image_fname) #r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023_pymupdf.png")
    return image_file

def ocr(image_fname):
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
            curr_text_dict["w"] = results["width"][i] + results["left"][i] - curr_text_dict["x"]
            curr_text_dict["h"] = max(curr_text_dict["h"], results["height"][i] + results["top"][i] - curr_text_dict["y"])
            curr_text_dict["num"] = results["word_num"][i]
            curr_text_dict["text"] += " " + text

    return text_dict

class MyImageWidget(Widgets.QLabel):
    def __init__(self, application, boxes):
        super().__init__()

        self.boxes = {box: False for box in boxes}
        self.ratio = 1
        self.application = application

    def set_menu_item_edit(self, menu_item_edit):
        self.menu_item_edit = menu_item_edit

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.pixmap_height = pixmap.height()

    # from https://likegeeks.com/pyqt5-drawing-tutorial/#Draw_on_Image
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = Gui.QPainter(self)
        height_adjust = math.floor((self.height() - self.pixmap_height)/2)
        for box, clicked in self.boxes.items():
            rect = [math.floor(self.ratio*val) for val in box[:4]]
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
                if not self.application.keyboardModifiers() & Core.Qt.ShiftModifier:
                    self.menu_item_edit.setText(box[4])
                else:
                    self.menu_item_edit.setText(self.menu_item_edit.text() + " " + box[4])

                self.repaint()

class PolarsTableModel(Core.QAbstractTableModel):
    def __init__(self, df, df_schema, out_fname):
        super().__init__()
        self.df = df
        self.df_schema = df_schema

        self.highlight_first = False
        self.count_highlight = None
        self.out_fname = out_fname

    def rowCount(self, index): # unclear what index is fore
        return self.df.shape[0]

    def columnCount(self, index): # unclear what index is fore
        return self.df.shape[1] - 2

    def headerData(self, section, orientation, role):
        if role == Core.Qt.DisplayRole and orientation == Core.Qt.Horizontal and section < self.df.shape[1] - 2:
            return Core.QVariant(self.df.columns[section + 2])
        return Core.QVariant()

    def data(self, index, role):
        if index.row() >= self.df.shape[0] or index.column() >= self.df.shape[1] - 2:
            return Core.QVariant()

        if role == Core.Qt.DisplayRole:
            return Core.QVariant(self.df[index.row(), index.column() + 2])

        if role == Core.Qt.BackgroundRole and self.highlight_first and index.row() == 0:
            return Gui.QBrush(Gui.QColor(0, 255, 0))

        if role == Core.Qt.BackgroundRole and index.row() == self.count_highlight and index.column() == 1:
            return Gui.QBrush(Gui.QColor(0, 255, 0))

        return Core.QVariant()

    def insert_new_menu_item(self, menu_item_data):
        row = self.df.with_row_count().filter(pl.col('menu_item') == menu_item_data[2])
        assert row.shape[0] <= 1
        if row.shape[0] == 0:
            self.beginInsertRows(Core.QModelIndex(), 0, 0)
            self.df = pl.DataFrame([menu_item_data], schema=self.df_schema).vstack(self.df)
            self.endInsertRows()
            if not self.highlight_first:
                self.highlight_first = True
                self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, 2), [Core.Qt.BackgroundRole])
            if self.count_highlight:
                old_count_cell = self.createIndex(self.count_highlight, 1)
                self.dataChanged.emit(old_count_cell, old_count_cell, [Core.Qt.BackgroundRole])
            self.count_highlight = None
        else:
            row_nr = row['row_nr'].item()
            self.df = self.df.with_columns([
                pl.when(
                    pl.col('menu_item') != menu_item_data[2]
                ).then(
                    pl.col('count')
                ).otherwise(
                    pl.col('count') + menu_item_data[3]
                )
            ])
            cell = self.createIndex(row_nr, 1)
            if self.highlight_first:
                self.highlight_first = False
                self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, 2), [Core.Qt.BackgroundRole])
            elif self.count_highlight:
                old_count_cell = self.createIndex(self.count_highlight, 1)
                self.dataChanged.emit(old_count_cell, old_count_cell, [Core.Qt.BackgroundRole])
            self.count_highlight = row_nr
            self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole]) # should possibly be EditRole
        self.save()

    def save(self):
        if self.out_fname:
            self.df.write_csv(self.out_fname)

class MyWindow(Widgets.QMainWindow):
    def __init__(self, app, df_schema, path, boxes):
        super().__init__()

        self.application = app

        central_widget = Widgets.QWidget()
        self.setCentralWidget(central_widget)
        central_layout = Widgets.QHBoxLayout(central_widget)

        self.pixmap = Gui.QPixmap(path)
        self.base_height = self.pixmap.height()
        self.base_width = self.pixmap.width()
        self.image_widget = MyImageWidget(app, boxes) #Widgets.QLabel()
        self.image_widget.setMinimumWidth(100)
        self.image_widget.setMinimumHeight(100)
        self.image_widget.setPixmap(self.pixmap)
        self.image_widget.installEventFilter(self)
        # the second parameter means this widget will stretch at rate 1
        # since nothing else is given a stretch parameter, this means this widget
        # is the only widget that will stretch when the window resizes
        central_layout.addWidget(self.image_widget, 1)

        right_column = Widgets.QVBoxLayout()
        central_layout.addLayout(right_column)

        load_layout = Widgets.QHBoxLayout()
        right_column.addLayout(load_layout)
        choose_new_table_button = Widgets.QPushButton("Start new table")
        choose_new_table_button.clicked.connect(self.choose_new_table)
        load_layout.addWidget(choose_new_table_button)

        load_existing_table_button = Widgets.QPushButton("Load existing table")
        load_existing_table_button.clicked.connect(self.load_existing_table)
        load_layout.addWidget(load_existing_table_button)

        school_name_row = Widgets.QHBoxLayout()
        right_column.addLayout(school_name_row)
        school_name_row.addWidget(Widgets.QLabel("School name:"))
        self.school_name_edit = Widgets.QLineEdit()
        school_name_row.addWidget(self.school_name_edit)

        school_type_col = Widgets.QVBoxLayout()
        school_name_row.addLayout(school_type_col)
        school_type_col.addWidget(Widgets.QLabel("School type:"))
        self.school_type_select = Widgets.QComboBox()
        self.school_type_select.addItems([
            "Elementary",
            "Middle",
            "High"
        ])
        self.school_type_select.setEditable(True)
        self.school_type_select.setInsertPolicy(Widgets.QComboBox.NoInsert)
        self.school_type_select.setCurrentIndex(-1)
        school_type_col.addWidget(self.school_type_select)

        item_layout = Widgets.QHBoxLayout()
        right_column.addLayout(item_layout)

        menu_item_layout = Widgets.QVBoxLayout()
        item_layout.addLayout(menu_item_layout)

        menu_item_layout.addWidget(Widgets.QLabel("Menu item name:"))
        self.menu_item_edit = Widgets.QLineEdit()
        self.menu_item_edit.setMinimumWidth(400)
        menu_item_layout.addWidget(self.menu_item_edit)
        self.image_widget.set_menu_item_edit(self.menu_item_edit)

        self.plant_based_buttons = Widgets.QButtonGroup()
        plant_based_layout = Widgets.QVBoxLayout()
        plant_based_layout.addWidget(Widgets.QLabel("Plant based?"))
        item_layout.addLayout(plant_based_layout)
        for id_, text in enumerate(("Yes", "Maybe?", "No")):
            button = Widgets.QRadioButton(text)
            button.click()
            plant_based_layout.addWidget(button)
            self.plant_based_buttons.addButton(button, id_)

        item_layout.addWidget(Widgets.QLabel("Count:"))
        self.item_count = Widgets.QLineEdit()
        self.item_count.setInputMask("00")
        self.item_count.setText("1")
        item_layout.addWidget(self.item_count)
        self.item_count_sticky = Widgets.QCheckBox("sticky")
        item_layout.addWidget(self.item_count_sticky)
       
        self.table_model = None
        self.table_view = Widgets.QTableView()
        right_column.addWidget(self.table_view, 1)

    def choose_new_table(self):
        fname = Widgets.QFileDialog.getSaveFileName(self, "File to start new table", filter="CSV files (*.csv)")[0]
        if fname:
            if not fname.endswith('.csv'):
                fname += '.csv'
            df = pl.DataFrame(schema=df_schema)
            self.table_model = PolarsTableModel(df, df_schema, fname)
            self.table_view.setModel(self.table_model)

    def load_existing_table(self):
        fname = Widgets.QFileDialog.getSaveFileName(self, "File to start new table", filter="CSV files (*.csv)")
        if fname is not None:
            fname = fname[0]
            if not fname.endswith('.csv'):
                fname += '.csv'
            df = pl.DataFrame(schema=df_schema)
            self.table_model = PolarsTableModel(df, df_schema, fname)
            self.table_view.setModel(self.table_model)

    # from https://stackoverflow.com/questions/27676034/pyqt-place-scaled-image-in-centre-of-label
    def eventFilter(self, source, event):
        if (source is self.image_widget and event.type() == Core.QEvent.Resize):
            # re-scale the pixmap when the label resizes
            ratio = min(self.image_widget.width()/self.base_width, self.image_widget.height()/self.base_height)
            self.image_widget.ratio = ratio
            self.image_widget.setPixmap(
                self.pixmap.scaled(math.floor(self.base_width*ratio), math.floor(self.base_height*ratio), transformMode=Core.Qt.SmoothTransformation)
            )
            #, menu_item_edit                Core.Qt.SmoothTransformation))
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        # add to table
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_Return and \
           not self.table_model is None:
            menu_item_data = [
                self.school_name_edit.text(),
                self.school_type_select.currentText(),
                self.menu_item_edit.text(),
                int(self.item_count.text()),
                ['Y', '?', 'N'][self.plant_based_buttons.checkedId()]
            ]
            self.table_model.insert_new_menu_item(menu_item_data)
            self.table_view.resizeColumnsToContents()
            self.menu_item_edit.clear()
            
        # switch plant based status
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_P and \
           self.application.keyboardModifiers() & Core.Qt.ControlModifier:
            self.plant_based_buttons.button((self.plant_based_buttons.checkedId() + 1) % 3).click()

# --- Start everything ---
app = Widgets.QApplication([])

df_schema={
    'school_district': str,
    'district_type': str,
    'menu_item': str,
    'count': int,
    'plant_based': str
}

pdf_fname = '/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf'
image_file = create_image_from_pdf(pdf_fname)
image_fname = image_file.name
text_dict = ocr(image_fname)

window = MyWindow(
    app,
    df_schema,
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

