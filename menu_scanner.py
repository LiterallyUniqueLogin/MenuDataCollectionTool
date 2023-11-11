
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

def create_images_from_pdf(pdf_fname):
    doc = fitz.open(pdf_fname)
    image_files = []
    for page in doc:
        image_file = tempfile.NamedTemporaryFile(suffix='.png')
        image_fname = image_file.name
        page.get_pixmap(matrix=fitz.Matrix(8,8)).save(image_fname) #r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023_pymupdf.png")
        image_files.append(image_file)
    return image_files

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
        self.temp_highlighted = []

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
            rect[0] -= 1
            rect[1] -= 2
            rect[2] += 2
            rect[3] += 4
            rect[1] = rect[1] + height_adjust
            if not clicked:
                painter.setPen(Gui.QPen(Core.Qt.red, 2))
            else:
                painter.setPen(Gui.QPen(Core.Qt.green, 2))
            painter.drawRect(*rect)

    def mousePressEvent(self, event):
        x = event.localPos().x()
        y = event.localPos().y() - max(math.floor((self.height() - self.pixmap_height)/2), 0)
        for box in self.boxes:
            if box[0] <= x/self.ratio <= box[0] + box[2] and box[1] <= y/self.ratio <= box[1] + box[3]:
                if (self.application.keyboardModifiers() & Core.Qt.ShiftModifier) != Core.Qt.ShiftModifier:
                    self.menu_item_edit.setText(box[4])
                    self.unhighlight()
                    self.temp_highlighted = [box]
                else:
                    self.menu_item_edit.setText(self.menu_item_edit.text() + " " + box[4])
                    self.temp_highlighted.append(box)
                self.boxes[box] = True

        self.repaint()

    def unhighlight(self):
        for old_box in self.temp_highlighted:
            self.boxes[old_box] = False
        self.temp_highlighted = []

# Model view tutorial I've used
# https://doc.qt.io/qt-6/modelview.html#2-5-the-minimal-editing-example
# Model view tutorials that I haven't used much:
# https://doc.qt.io/qt-6/model-view-programming.html#model-view-classes


class PolarsTableModel(Core.QAbstractTableModel):
    def __init__(self, df, df_schema, out_fname):
        super().__init__()
        self.df = df
        self.df_schema = df_schema

        self.highlight_cells = []
        self.out_fname = out_fname
        self.curr_district = None
        self.curr_district_type = None

    def rowCount(self, index): # unclear what index is fore
        return self.df.shape[0]

    def columnCount(self, index): # unclear what index is fore
        return self.df.shape[1]

    def headerData(self, section, orientation, role):
        if role == Core.Qt.DisplayRole and orientation == Core.Qt.Horizontal and section < self.df.shape[1]:
            section = (section + 2) % self.df.shape[1]
            return Core.QVariant(self.df.columns[section])
        if role == Core.Qt.DisplayRole and orientation == Core.Qt.Vertical and section < self.df.shape[0]:
            return Core.QVariant(section+1)
        return Core.QVariant()

    def data(self, index, role):
        if index.row() >= self.df.shape[0] or index.column() >= self.df.shape[1]:
            return Core.QVariant()

        if role in (Core.Qt.DisplayRole, Core.Qt.EditRole):
            return Core.QVariant(self.df[index.row(), (index.column() + 2) % self.df.shape[1]])

        if role == Core.Qt.BackgroundRole and (index.row(), index.column()) in self.highlight_cells:
            return Gui.QBrush(Gui.QColor(0, 255, 0))

        return Core.QVariant()

    def setData(self, index, value, role):
        if role != Core.Qt.EditRole:
            return False
        if index.row() >= self.df.shape[0] or index.column() >= self.df.shape[1]:
            return False
        self.df[index.row(), (index.column() + 2) % self.df.shape[1]] = value

        self.save()
        self.reorganize()
        
        return True

    def deleteRows(self, rows):
        if not rows:
            return
        rows = [row.row() for row in rows]
        self.beginRemoveRows(Core.QModelIndex(), min(rows), max(rows))
        self.df = self.df.with_row_count('row_nr').filter(~pl.col('row_nr').is_in(rows)).drop('row_nr')
        self.endRemoveRows()
        self.save()
        self.reorganize()

    def flags(self, index):
        return Core.Qt.ItemIsSelectable | Core.Qt.ItemIsEditable | Core.Qt.ItemIsEnabled

    def insert_new_menu_item(self, menu_item_data):
        row = self.df.with_row_count().filter(
            (pl.col('school_district') == menu_item_data[0]) &
            (pl.col('district_type') == menu_item_data[1]) &
            (pl.col('menu_item') == menu_item_data[2])
        )
        assert row.shape[0] <= 1
        old_highlight_cells = self.highlight_cells

        if row.shape[0] == 0:
            self.beginInsertRows(Core.QModelIndex(), 0, 0)
            self.df = pl.DataFrame([menu_item_data], schema=self.df_schema).vstack(self.df)
            self.endInsertRows()

            self.highlight_cells = []
            for col in range(self.df.shape[1]):
                self.highlight_cells.append((0, col))
            self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0, self.df.shape[1] - 1), [Core.Qt.BackgroundRole])
        else:
            row_nr = row['row_nr'].item()
            self.df = self.df.with_row_count().with_columns([
                pl.when(
                    pl.col('row_nr') != row_nr
                ).then(
                    pl.col('count')
                ).otherwise(
                    pl.col('count') + menu_item_data[3]
                )
            ]).drop('row_nr')
            cell = self.createIndex(row_nr, 1)
            self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

        for cell in old_highlight_cells:
            self.dataChanged.emit(self.createIndex(*cell), self.createIndex(*cell), [Core.Qt.BackgroundRole])

        self.save()

    def remove_menu_item_data(self, menu_item_data):
        row = self.df.with_row_count().filter(
            (pl.col('school_district') == menu_item_data[0]) &
            (pl.col('district_type') == menu_item_data[1]) &
            (pl.col('menu_item') == menu_item_data[2])
        )
        assert row.shape[0] == 1
        old_highlight_cells = self.highlight_cells

        if row['count'].item() == menu_item_data[3]:
            self.delete_rows([row['row_nr'].item()])
            self.highlight_cells = []
        else:
            row_nr = row['row_nr'].item()
            self.df = self.df.with_row_count().with_columns([
                pl.when(
                    pl.col('row_nr') != row_nr
                ).then(
                    pl.col('count')
                ).otherwise(
                    pl.col('count') - menu_item_data[3]
                )
            ]).drop('row_nr')
            cell = self.createIndex(row_nr, 1)
            self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

        for cell in old_highlight_cells:
            self.dataChanged.emit(self.createIndex(*cell), self.createIndex(*cell), [Core.Qt.BackgroundRole])

    def save(self):
        if self.out_fname:
            self.df.sort(by=['school_district', 'district_type', 'menu_item']).write_csv(self.out_fname)

    def focus_school_district(self, school_district, district_type):
        self.curr_district = school_district
        self.curr_district_type = district_type
        self.reorganize()

    def reorganize(self):
        self.df = self.df.sort(by=[
            pl.col('school_district') != self.curr_district,
            (pl.col('school_district') != self.curr_district) | (pl.col('district_type') != self.curr_district_type),
            'school_district',
            'district_type',
        ])
        self.highlight_first = False
        self.count_highlight = None
        self.dataChanged.emit(self.createIndex(0,0), self.createIndex(*self.df.shape), [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

class UndoRedo:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []

    def do(self, action):
        action.do()
        self.undo_stack.append(action)
        self.redo_stack = []

    def undo(self):
        if self.undo_stack:
            action = self.undo_stack.pop()
            action.undo()
            self.redo_stack.append(action)

    def redo(self):
        if self.redo_stack:
            action = self.redo_stack.pop()
            action.do()
            self.undo_stack.append(action)

class InsertNewMenuItemAction:
    def __init__(self, table_model, menu_item_data, menu_item_edit, palette):
        self.table_model = table_model
        self.menu_item_data = menu_item_data
        self.menu_item_edit = menu_item_edit
        self.palette = palette

    def do(self):
        self.table_model.insert_new_menu_item(self.menu_item_data)
        self.menu_item_edit.setPalette(self.palette)

    def undo(self):
        self.table_model.remove_menu_item_data(self.menu_item_data)
        self.menu_item_edit.setPalette(self.palette)

class MyWindow(Widgets.QMainWindow):
    def __init__(self, app, df_schema):
        super().__init__()

        self.setWindowState(Core.Qt.WindowMaximized)

        self.application = app
        self.df_schema = df_schema
        self.undo_redo = UndoRedo()

        central_widget = Widgets.QWidget()
        self.setCentralWidget(central_widget)
        central_layout = Widgets.QHBoxLayout(central_widget)

        self.left_column = Widgets.QVBoxLayout()
        central_layout.addLayout(self.left_column)

        self.load_menus_layout = Widgets.QHBoxLayout()
        self.left_column.addLayout(self.load_menus_layout)

        self.load_menus_button = Widgets.QPushButton("Load menu(s)")
        self.load_menus_button.clicked.connect(self.load_menus)
        self.load_menus_layout.addWidget(self.load_menus_button)
        self.load_menus_layout.addStretch()
   
        # these will be unhidden later
        self.page_back_button = Widgets.QPushButton("<")
        self.page_back_button.clicked.connect(self.previous_menu)
        self.page_back_button.setVisible(False)
        self.load_menus_layout.addWidget(self.page_back_button)
        self.page_forward_button = Widgets.QPushButton(">")
        self.page_forward_button.clicked.connect(self.next_menu)
        self.page_forward_button.setVisible(False)
        self.load_menus_layout.addWidget(self.page_forward_button)

        self.curr_image_widget = None
        self.image_widgets = None

        right_column = Widgets.QVBoxLayout()
        central_layout.addLayout(right_column)

        load_layout = Widgets.QHBoxLayout()
        right_column.addLayout(load_layout)
        self.choose_new_table_button = Widgets.QPushButton("Start new table")
        self.choose_new_table_button.clicked.connect(self.choose_new_table)
        load_layout.addWidget(self.choose_new_table_button)

        self.load_existing_table_button = Widgets.QPushButton("Load existing table")
        self.load_existing_table_button.clicked.connect(self.load_existing_table)
        load_layout.addWidget(self.load_existing_table_button)
        load_layout.addStretch()

        school_name_row = Widgets.QHBoxLayout()
        right_column.addLayout(school_name_row)
        school_name_row.addWidget(Widgets.QLabel("School name:"))
        self.school_name_edit = Widgets.QLineEdit()
        self.school_name_edit.installEventFilter(self)
        school_name_row.addWidget(self.school_name_edit)

        school_type_col = Widgets.QVBoxLayout()
        school_name_row.addLayout(school_type_col)
        school_type_col.addWidget(Widgets.QLabel("School type:"))
        self.school_type_select = Widgets.QComboBox()
        self.school_type_select.installEventFilter(self)
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
        # the second parameter means this widget will stretch at rate 1
        # since nothing else is given a stretch parameter, this means this widget
        # is the only widget that will stretch when the window resizes
        item_layout.addLayout(menu_item_layout, 1)

        menu_item_layout.addWidget(Widgets.QLabel("Menu item name:"))
        self.menu_item_edit = Widgets.QLineEdit()
        self.menu_item_edit.installEventFilter(self)
        self.menu_item_edit.setMinimumWidth(400)
        menu_item_layout.addWidget(self.menu_item_edit)

        self.plant_based_buttons = Widgets.QButtonGroup()
        self.plant_based_buttons.buttonClicked.connect(self.plant_based_changed)
        plant_based_layout = Widgets.QVBoxLayout()
        plant_based_layout.addWidget(Widgets.QLabel("Plant based:"))
        item_layout.addLayout(plant_based_layout)
        for id_, text in enumerate(("Yes", "Maybe?", "No")):
            button = Widgets.QRadioButton(text)
            button.click()
            plant_based_layout.addWidget(button)
            self.plant_based_buttons.addButton(button, id_)

        self.veg_buttons = Widgets.QButtonGroup()
        self.veg_buttons.buttonClicked.connect(self.veg_changed)
        veg_layout = Widgets.QVBoxLayout()
        veg_layout.addWidget(Widgets.QLabel("Vegetarian:"))
        item_layout.addLayout(veg_layout)
        for id_, text in enumerate(("Yes", "Maybe?", "No")):
            button = Widgets.QRadioButton(text)
            button.click()
            veg_layout.addWidget(button)
            self.veg_buttons.addButton(button, id_)

        data_layout = Widgets.QVBoxLayout()
        item_layout.addLayout(data_layout)
        count_layout = Widgets.QHBoxLayout()

        data_layout.addWidget(Widgets.QLabel("Data input mode:"))
        self.data_mode_buttons = Widgets.QButtonGroup()
        data_mode_layout = Widgets.QHBoxLayout()
        data_layout.addLayout(data_mode_layout)
        for id_, text in enumerate(("Count", "Date")):
            button = Widgets.QRadioButton(text)
            data_mode_layout.addWidget(button)
            self.data_mode_buttons.addButton(button, id_)
        self.data_mode_buttons.button(0).click()

        self.count_label = Widgets.QLabel("Count:")
        count_layout.addWidget(self.count_label)
        self.item_count = Widgets.QLineEdit()
        self.item_count.installEventFilter(self)
        self.item_count.setInputMask("00")
        self.item_count.setText("1")
        self.item_count.setMaximumWidth(50)
        count_layout.addWidget(self.item_count)
        self.item_count_sticky = Widgets.QCheckBox("sticky")
        count_layout.addWidget(self.item_count_sticky)
        data_layout.addLayout(count_layout)
        data_layout.addStretch()
        self.data_mode_buttons.buttonClicked.connect(lambda _ : self.change_count_layout_visibility())
       
        self.table_model = None
        self.table_view = Widgets.QTableView()
        self.table_view.installEventFilter(self)
        self.table_view.setCornerButtonEnabled(False)
        right_column.addWidget(self.table_view, 1)
        self.manual_resize_menu_item = False
        self.manual_resize_school_district = False
        self.manual_resize_district_type = False
        self.table_view.horizontalHeader().sectionResized.connect(self.catch_manual_resize)

        self.school_name_edit.textEdited.connect(lambda _ : self.table_model.focus_school_district(self.school_name_edit.text().strip(), self.school_type_select.currentText().strip()) if self.table_model else None)
        self.school_type_select.currentTextChanged.connect(lambda _ : self.table_model.focus_school_district(self.school_name_edit.text().strip(), self.school_type_select.currentText().strip()) if self.table_model else None)

    def change_count_layout_visibility(self):
        for widget in self.count_label, self. item_count, self.item_count_sticky:
            widget.setVisible(self.data_mode_buttons.checkedId() == 0)

    def catch_manual_resize(self, index, oldSize, newSize):
        if index == 0:
            self.manual_resize_menu_item = True
        if index == 4:
            self.manual_resize_school_district = True
        if index == 5:
            self.manual_resize_district_type = True

    def choose_new_table(self):
        fname = Widgets.QFileDialog.getSaveFileName(self, "File to start new table", filter="CSV files (*.csv)")[0]
        if fname:
            if not fname.endswith('.csv'):
                fname += '.csv'
            df = pl.DataFrame(schema=self.df_schema)
            self.table_model = PolarsTableModel(df, df_schema, fname)
            self.table_view.setModel(self.table_model)
            self.set_table_view_sizing()
        for button in self.choose_new_table_button, self.load_existing_table_button:
            button.setPalette(self.application.palette())

    def load_existing_table(self):
        fname = Widgets.QFileDialog.getOpenFileName(self, "CSV file to load", filter="CSV files (*.csv)")[0]
        if fname:
            df = pl.read_csv(fname)
            # TODO don't crash if not true
            assert list(df.columns) == list(self.df_schema.keys())
            self.table_model = PolarsTableModel(df, self.df_schema, fname)
            self.table_view.setModel(self.table_model)
            self.set_table_view_sizing()
        for button in self.choose_new_table_button, self.load_existing_table_button:
            button.setPalette(self.application.palette())

    def set_table_view_sizing(self):
        for col in range(6):
            self.table_view.horizontalHeader().resizeSections(Widgets.QHeaderView.ResizeToContents)
            self.table_view.horizontalHeader().setSectionResizeMode(col, Widgets.QHeaderView.Interactive)

    def load_menus(self):
        dialog = Widgets.QFileDialog(self)
        dialog.setFileMode(Widgets.QFileDialog.ExistingFiles)
        dialog.setFileMode(Widgets.QFileDialog.ExistingFiles)
        dialog.setNameFilter("PDFs and Images (*.pdf *.png *.jpg *.jpeg *.gif *.tiff)")
        if not dialog.exec():
            return

        self.menu_file_names = dialog.selectedFiles()
        self.curr_menu_idx = 0
        self.curr_menu_page = 0
        self.temp_image_files = []
        self.image_widgets = []
        self.pixmaps = []
        self.base_heights = []
        self.base_widths = []
        self.setup_new_menu(0)
        if len(self.menu_file_names) > 1 or len(self.image_widgets[0]) > 1:
            self.page_back_button.setVisible(True)
            self.page_forward_button.setVisible(True)
        else:
            self.page_back_button.setVisible(False)
            self.page_forward_button.setVisible(False)

    def setup_new_menu(self, idx):
        assert idx == len(self.image_widgets)
        fname = self.menu_file_names[idx]
        if fname.endswith('.pdf'):
            image_files = create_images_from_pdf(fname)
            self.temp_image_files.extend(image_files)
            image_fnames = [file.name for file in image_files]
        else:
            image_fnames = [fname]

        self.image_widgets.append([])
        self.pixmaps.append([])
        self.base_heights.append([])
        self.base_widths.append([])
        for image_fname in image_fnames:
            text_dict = ocr(image_fname)
            boxes = [
                (line_block["x"], line_block["y"], line_block["w"], line_block["h"], line_block["text"])
                for p in text_dict.values()
                for b in p.values()
                for par in b.values()
                for l in par.values()
                for line_block in l
            ]

            pixmap = Gui.QPixmap(image_fname)
            self.pixmaps[-1].append(pixmap)
            self.base_heights[-1].append(self.pixmaps[-1][-1].height())
            self.base_widths[-1].append(self.pixmaps[-1][-1].width())
            image_widget = MyImageWidget(self.application, boxes)
            image_widget.setMinimumWidth(100)
            image_widget.setMinimumHeight(100)
            image_widget.setPixmap(self.pixmaps[-1][-1])
            image_widget.installEventFilter(self)
            image_widget.set_menu_item_edit(self.menu_item_edit)
            image_widget.setVisible(False) # will show later
            self.image_widgets[-1].append(image_widget)

            # the second parameter means this widget will stretch at rate 1
            # since nothing else is given a stretch parameter, this means this widget
            # is the only widget that will stretch when the window resizes
            self.left_column.addWidget(image_widget, 1)

        self.load_menus_button.setPalette(self.application.palette())
        self.swap_to_image(idx, 0)

    def swap_to_image(self, image_idx, page):
        if self.curr_image_widget is not None:
            self.curr_image_widget.setVisible(False)
            self.curr_image_widget.unhighlight()

        if self.curr_menu_idx != image_idx:
            self.item_count.setText("1")
            self.plant_based_buttons.button(2).click()
            self.veg_buttons.button(2).click()
            self.item_count_sticky.setChecked(False)
            self.menu_item_edit.clear()
            self.school_name_edit.clear()
            self.school_type_select.clearEditText()
            
        self.curr_menu_idx = image_idx
        self.curr_menu_page = page
        self.curr_image_widget = self.image_widgets[self.curr_menu_idx][self.curr_menu_page]
        self.curr_image_widget.setVisible(True)
        self.eventFilter(self.curr_image_widget, Gui.QResizeEvent(Core.QSize(), Core.QSize()))

    def previous_menu(self):
        if self.curr_menu_page > 0:
            self.swap_to_image(self.curr_menu_idx, self.curr_menu_page - 1)
        elif self.curr_menu_idx > 0:
            self.swap_to_image(self.curr_menu_idx - 1, len(self.image_widgets[self.curr_menu_idx - 1]) - 1)

    def next_menu(self):
        if self.curr_menu_page < len(self.image_widgets[self.curr_menu_idx]) - 1:
            self.swap_to_image(self.curr_menu_idx, self.curr_menu_page + 1)
        elif self.curr_menu_idx < len(self.image_widgets) - 1:
            self.swap_to_image(self.curr_menu_idx + 1, 0)
        elif len(self.image_widgets) < len(self.menu_file_names):
            self.setup_new_menu(len(self.image_widgets))

    # from https://stackoverflow.com/questions/27676034/pyqt-place-scaled-image-in-centre-of-label
    def eventFilter(self, source, event):
        if (source is self.curr_image_widget and event.type() == Core.QEvent.Resize and self.curr_image_widget is not None):
            # re-scale the pixmap when the label resizes
            ratio = min(self.curr_image_widget.width()/self.base_widths[self.curr_menu_idx][self.curr_menu_page], self.curr_image_widget.height()/self.base_heights[self.curr_menu_idx][self.curr_menu_page])
            self.curr_image_widget.ratio = ratio
            self.curr_image_widget.setPixmap(
                self.pixmaps[self.curr_menu_idx][self.curr_menu_page].scaled(
                    math.floor(self.base_widths[self.curr_menu_idx][self.curr_menu_page]*ratio), math.floor(self.base_heights[self.curr_menu_idx][self.curr_menu_page]*ratio), transformMode=Core.Qt.SmoothTransformation
                )
            )
        if event.type() == Core.QEvent.KeyPress:
            self.keyPressEvent(event)

        out = super().eventFilter(source, event)
        if event.type() == Core.QEvent.KeyPress and event.key() == Core.Qt.Key_Return:
            return True
        else:
            return out

    def keyPressEvent(self, event):
        # add to table
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_Return:
            if self.table_model is None:
                for button in self.choose_new_table_button, self.load_existing_table_button:
                    palette = button.palette()
                    palette.setColor(palette.Button, Gui.QColor(Core.Qt.red))
                    button.setPalette(palette)
                return

            if self.curr_image_widget is None:
                palette = self.load_menus_button.palette()
                palette.setColor(palette.Button, Gui.QColor(Core.Qt.red))
                self.load_menus_button.setPalette(palette)
                return
            
            missing_school_deets = False
            if self.school_name_edit.text().strip() == '':
                palette = self.school_name_edit.palette()
                palette.setColor(palette.Base, Gui.QColor(Gui.QColorConstants.Svg.lightcoral))
                self.school_name_edit.setPalette(palette)
                missing_school_deets = True
            else:
                self.school_name_edit.setPalette(self.application.palette())

            if self.school_type_select.currentText().strip() == '':
                palette = self.school_type_select.palette()
                palette.setColor(palette.Base, Gui.QColor(Gui.QColorConstants.Svg.lightcoral))
                self.school_type_select.setPalette(palette)
                missing_school_deets = True
            else:
                self.school_type_select.setPalette(self.application.palette())

            if missing_school_deets:
                return

            if self.menu_item_edit.text().strip() == '':
                palette = self.menu_item_edit.palette()
                palette.setColor(palette.Base, Gui.QColor(Gui.QColorConstants.Svg.lightcoral))
                self.menu_item_edit.setPalette(palette)
                return

            menu_item_data = [
                self.school_name_edit.text(),
                self.school_type_select.currentText(),
                self.menu_item_edit.text(),
                int(self.item_count.text()),
                ['Y', '?', 'N'][self.plant_based_buttons.checkedId()],
                ['Y', '?', 'N'][self.veg_buttons.checkedId()]
            ]
            self.undo_redo.do(InsertNewMenuItemAction(self.table_model, menu_item_data, self.menu_item_edit, self.application.palette()))

            if not self.item_count_sticky.isChecked():
                self.item_count.setText("1")
            for col, should_not_resize in [(0, self.manual_resize_menu_item), (4, self.manual_resize_school_district), (5, self.manual_resize_district_type)]:
                if not should_not_resize:
                    self.table_view.resizeColumnToContents(col)
            self.menu_item_edit.clear()
            self.plant_based_buttons.button(2).click()
            self.veg_buttons.button(2).click()
            self.curr_image_widget.temp_highlighted = []
            
        # switch plant based status
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_P and \
           (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier:
            self.plant_based_buttons.button((self.plant_based_buttons.checkedId() + 1) % 3).click()

        # switch plant based status
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_V and \
           (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier:
            self.veg_buttons.button((self.veg_buttons.checkedId() + 1) % 3).click()

        # swtich data mode status
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_M and \
           (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier:
            self.data_mode_buttons.button((self.data_mode_buttons.checkedId() + 1) % 2).click()

        # delete selected table contents
        if event.type() == Core.QEvent.KeyPress and \
           event.key() in (Core.Qt.Key_Backspace, Core.Qt.Key_Delete):
            for idx in self.table_view.selectedIndexes():
                self.table_model.setData(idx, '', Core.Qt.EditRole)
            self.table_model.deleteRows(self.table_view.selectionModel().selectedRows())

        # undo
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_Z and \
           (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier and \
           (self.application.keyboardModifiers() & Core.Qt.ShiftModifier) != Core.Qt.ShiftModifier:
            self.undo_redo.undo()

        # redo
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_Z and \
           (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier and \
           (self.application.keyboardModifiers() & Core.Qt.ShiftModifier) == Core.Qt.ShiftModifier:
            self.undo_redo.redo()

    def plant_based_changed(self):
        if self.plant_based_buttons.checkedId() == 0:
            self.veg_buttons.button(0).click()
        if self.plant_based_buttons.checkedId() == 1 and self.veg_buttons.checkedId() == 2:
            self.veg_buttons.button(1).click()

    def veg_changed(self):
        if self.veg_buttons.checkedId() == 2:
            self.plant_based_buttons.button(2).click()

# --- Start everything ---
app = Widgets.QApplication([])

df_schema={
    'school_district': str,
    'district_type': str,
    'menu_item': str,
    'count': int,
    'plant_based': str,
    'vegetarian': str
}

window = MyWindow(
    app,
    df_schema,
)

window.show()
app.exec()

#pdf_fname = '/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf'
