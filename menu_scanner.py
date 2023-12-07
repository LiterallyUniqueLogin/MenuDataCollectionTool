# todo load school types
# Todo calendar dates
# todo instructional movie

# Mention:
# automatic resorting
# loading a PDF with multiple pages
# loading multiple PDFs - reenter school in between
# random details
# delete will work on main table first if focused, not the other places to type
# Undo redo/enter needs main table not to be focused
# closing requires focusing

# not doing
# highlighting deleted rows somehow

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

class SetDataAction:
    def __init__(self, table_model, index, value):
        self.table_model = table_model
        self.value = value
        self.col = index.column()
        self.row_uid = self.table_model.df.with_row_count('row_nr').filter(pl.col('row_nr') == index.row()).select('uid').item()

    def do(self):
        self.old_value = self.table_model.set_data_helper(self.row_uid, self.col, self.value)

    def undo(self):
        self.table_model.set_data_helper(self.row_uid, self.col, self.old_value)

class SetDatasAction:
    def __init__(self, table_model, indices, values):
        self.table_model = table_model
        self.values = values
        self.cols = [index.column() for index in indices]
        self.row_uids = [
            self.table_model.df.with_row_count('row_nr').filter(pl.col('row_nr') == index.row()).select('uid').item()
            for index in indices
        ]

    def do(self):
        self.old_values = []
        first = True
        for row_uid, col, value in zip(self.row_uids, self.cols, self.values):
            self.old_values += [self.table_model.set_data_helper(row_uid, col, value)]
            if first:
                first = False
                self.table_model.add_highlights = True
        self.table_model.add_highlights = False

    def undo(self):
        first = True
        for row_uid, col, old_value in zip(self.row_uids, self.cols, self.old_values):
            self.table_model.set_data_helper(row_uid, col, old_value)
            if first:
                first = False
                self.table_model.add_highlights = True
        self.table_model.add_highlights = False

class DeleteRowsAction:
    def __init__(self, table_model, rows):
        self.table_model = table_model
        self.rows = rows

    def do(self):
        self.old_row_contents = self.table_model.delete_rows_helper(self.rows)

    def undo(self):
        self.table_model.insert_rows_helper(self.rows, self.old_row_contents)

class PolarsTableModel(Core.QAbstractTableModel):
    def __init__(self, df, df_schema, out_fname, undo_redo):
        super().__init__()
        self.df_schema = df_schema.copy()
        self.df_schema['uid'] = int
        # add a uid to each row
        self.df = df.hstack([pl.Series('uid', list(range(df.shape[0])), dtype=pl.Int64)])
        self.uid_cap = df.shape[0]
        self.undo_redo = undo_redo
        self.out_fname = out_fname

        self.highlight_cells = []
        self.add_highlights = False
        self.curr_district = None
        self.curr_district_type = None

    def rowCount(self, index): # unclear what index is for
        return self.df.shape[0]

    def columnCount(self, index): # unclear what index is for
        return self.df.shape[1] - 1

    def headerData(self, section, orientation, role):
        if role == Core.Qt.DisplayRole and orientation == Core.Qt.Horizontal and section < self.df.shape[1] - 1: 
            section = (section + 2) % (self.df.shape[1] - 1)
            return Core.QVariant(self.df.columns[section])
        if role == Core.Qt.DisplayRole and orientation == Core.Qt.Vertical and section < self.df.shape[0]:
            return Core.QVariant(section+1)
        return Core.QVariant()

    def data(self, index, role):
        if index.row() >= self.df.shape[0] or index.column() >= self.df.shape[1] - 1:
            return Core.QVariant()

        if role in (Core.Qt.DisplayRole, Core.Qt.EditRole):
            return Core.QVariant(self.df[index.row(), (index.column() + 2) % (self.df.shape[1] - 1)])

        if role == Core.Qt.BackgroundRole:
            uid = self.df.with_row_count('row_nr').filter(pl.col('row_nr') == index.row())['uid'].item()
            if (uid, index.column()) in self.highlight_cells:
                return Gui.QBrush(Gui.QColor(0, 255, 0))

        return Core.QVariant()

    def setData(self, index, value, role):
        print('in set data')
        if role != Core.Qt.EditRole:
            return False
        if index.row() >= self.df.shape[0] or index.column() >= self.df.shape[1] - 1:
            return False

        if value != self.df[index.row(), (index.column() + 2) % (self.df.shape[1] - 1)]:
            self.undo_redo.do(SetDataAction(self, index, value))
        return True

    def set_data_helper(self, row_uid, column, value):
        row = self.df.with_row_count('row_nr').filter(pl.col('uid') == row_uid).select('row_nr').item()
        old_value = self.df[row, (column + 2) % (self.df.shape[1] - 1)]
        if old_value != value:
            self.df[row, (column + 2) % (self.df.shape[1] - 1)] = value

            self.save()
            self.reorganize()
            new_highlight_cells = [(row_uid, column)]
            self.update_highlight(new_highlight_cells)
        
        return old_value

    def deleteRows(self, rows):
        if not rows:
            return
        rows = [row.row() for row in rows]
        self.undo_redo.do(DeleteRowsAction(self, rows))

    def delete_rows_helper(self, rows):
        self.beginRemoveRows(Core.QModelIndex(), min(rows), max(rows))
        deleted_row_contents = self.df.with_row_count('row_nr').filter(pl.col('row_nr').is_in(rows))
        print('in delete_rows_helper, deleting: ', deleted_row_contents)
        print('current df before deletion', self.df)
        self.df = self.df.with_row_count('row_nr').filter(~pl.col('row_nr').is_in(rows)).drop('row_nr')
        self.update_highlight([])
        self.endRemoveRows()
        self.save()
        self.reorganize()
        return deleted_row_contents

    # assumes rows are contiguous
    def insert_rows_helper(self, rows, deleted_row_contents):
        self.beginInsertRows(Core.QModelIndex(), min(rows), max(rows))
        print('in insert rows helper, reinserting: ', deleted_row_contents)
        print('current df before reinsertion', self.df)
        self.df = pl.concat([
            self.df.with_row_count('row_nr').with_columns([
                pl.when(
                    pl.col('row_nr') < min(rows)
                ).then(
                    pl.col('row_nr')
                ).otherwise(
                    pl.col('row_nr') + len(rows)
                )
            ]),
            deleted_row_contents
        ]).sort(by=['row_nr']).drop('row_nr')
        self.update_highlight([(uid, column) for uid in deleted_row_contents['uid'] for column in range(self.df.shape[1] - 1)])
        self.endInsertRows()
        self.save()
        self.reorganize()

    def flags(self, index):
        return Core.Qt.ItemIsSelectable | Core.Qt.ItemIsEditable | Core.Qt.ItemIsEnabled

    def insert_new_menu_item(self, menu_item_data):
        row = self.df.with_row_count('row_nr').filter(
            (pl.col('school_district').str.to_uppercase() == menu_item_data[0].upper()) &
            (pl.col('district_type').str.to_uppercase() == menu_item_data[1].upper()) &
            (pl.col('menu_item').str.to_uppercase() == menu_item_data[2].upper())
        )
        assert row.shape[0] <= 1

        if row.shape[0] == 0:
            self.beginInsertRows(Core.QModelIndex(), 0, 0)
            print('inserting new menu item')
            next_uid = self.get_next_uid()
            self.df = pl.DataFrame([[*menu_item_data, next_uid]], schema=self.df_schema).vstack(self.df)
            self.endInsertRows()

            new_highlight_cells = []
            for col in range(self.df.shape[1] - 1):
                new_highlight_cells.append((next_uid, col))
        else:
            uid = row['uid'].item()
            print('inserting preexstining menu item')
            self.df = self.df.with_columns([
                pl.when(
                    pl.col('uid') != uid
                ).then(
                    pl.col('count')
                ).otherwise(
                    pl.col('count') + menu_item_data[3]
                )
            ])
            cell = self.createIndex(row['row_nr'].item(), 1)
            self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])
            new_highlight_cells = [(uid, 1)]

        self.update_highlight(new_highlight_cells)

        self.save()
        print(self.df)

    def remove_menu_item_data(self, menu_item_data):
        row = self.df.with_row_count('row_nr').filter(
            (pl.col('school_district').str.to_uppercase() == menu_item_data[0].upper()) &
            (pl.col('district_type').str.to_uppercase() == menu_item_data[1].upper()) &
            (pl.col('menu_item').str.to_uppercase() == menu_item_data[2].upper())
        )
        assert row.shape[0] == 1

        if row['count'].item() == menu_item_data[3]:
            self.deleteRows([self.createIndex(row['row_nr'].item(), 0)])
            new_highlight_cells = []
        else:
            uid = row['uid'].item()
            print('removing menu item')
            self.df = self.df.with_columns([
                pl.when(
                    pl.col('uid') != uid
                ).then(
                    pl.col('count')
                ).otherwise(
                    pl.col('count') - menu_item_data[3]
                )
            ])
            new_highlight_cells = [(uid, 1)]

        self.update_highlight(new_highlight_cells)

    def update_highlight(self, new_cells):
        if not self.add_highlights:
            old_highlight_cells = self.highlight_cells

            self.highlight_cells = new_cells
            for cell in self.highlight_cells:
                row = self.df.with_row_count('row_nr').filter(pl.col('uid') == cell[0]).select('row_nr').item()
                cell = self.createIndex(row, cell[1])
                self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

            print(old_highlight_cells)
            for cell in old_highlight_cells:
                temp_df = self.df.with_row_count('row_nr').filter(pl.col('uid') == cell[0])
                if temp_df.shape[0] == 0:
                    continue
                assert temp_df.shape[0] == 1
                row = temp_df.select('row_nr').item()
                cell = self.createIndex(row, cell[1])
                self.dataChanged.emit(cell, cell, [Core.Qt.BackgroundRole])
        else:
            self.highlight_cells += new_cells
            for cell in new_cells:
                row = self.df.with_row_count('row_nr').filter(pl.col('uid') == cell[0]).select('row_nr').item()
                cell = self.createIndex(row, cell[1])
                self.dataChanged.emit(cell, cell, [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

    def save(self):
        if self.out_fname:
            self.df.sort(by=[
                pl.col('school_district').str.to_uppercase(),
                pl.col('district_type').str.to_uppercase(),
                pl.col('menu_item').str.to_uppercase()
            ]).drop('uid').write_csv(self.out_fname)

    def focus_school_district(self, school_district, district_type):
        self.curr_district = school_district
        self.curr_district_type = district_type
        self.reorganize()

    def reorganize(self):
        print('reorganizing, preorganize df', self.df)
        self.df = self.df.sort(by=[
            pl.col('school_district').str.to_uppercase() != self.curr_district.upper(),
            (pl.col('school_district').str.to_uppercase() != self.curr_district.upper()) | (pl.col('district_type').str.to_uppercase() != self.curr_district_type.upper()),
            pl.col('school_district').str.to_uppercase(),
            pl.col('district_type').str.to_uppercase(),
            # organize by menu item alphabetically, but only when not in the current district
            pl.when(
                (pl.col('school_district').str.to_uppercase() != self.curr_district.upper()) | (pl.col('district_type').str.to_uppercase() != self.curr_district_type.upper())
            ).then(
                pl.col('menu_item').str.to_uppercase()
            ).otherwise('')
        ])
        print('reorganizing, posrtorganize df', self.df)
        self.dataChanged.emit(self.createIndex(0,0), self.createIndex(self.df.shape[0], self.df.shape[1] - 1), [Core.Qt.DisplayRole, Core.Qt.BackgroundRole])

    def get_next_uid(self):
        self.uid_cap += 1
        return self.uid_cap

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

    def clear(self):
        self.undo_stack = []
        self.redo_stack = []

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

class PreviousMenuAction:
    def __init__(self, my_window):
        self.window = my_window

    def do(self):
        self.window.previous_menu()

    def undo(self):
        self.window.next_menu()

class NextMenuAction:
    def __init__(self, my_window):
        self.window = my_window

    def do(self):
        self.window.next_menu()

    def undo(self):
        self.window.previous_menu()

class MyCalendarWidget(Widgets.QCalendarWidget):
    def __init__(self):
        super().__init__()
        self.setVerticalHeaderFormat(self.NoVerticalHeader)
        self.setDateEditEnabled(False)
        self.setFirstDayOfWeek(Core.Qt.Sunday)

        self.selected_dates = [self.selectedDate()]
        self.clicked.connect(self.date_selected)

        self.highlight_format = Gui.QTextCharFormat()
        self.highlight_format.setBackground(self.palette().brush(Gui.QPalette.Highlight))
        self.highlight_format.setForeground(self.palette().color(Gui.QPalette.HighlightedText))

        self.unhighlight_format = Gui.QTextCharFormat()
        self.unhighlight_format.setBackground(Gui.QColor(Core.Qt.white))
        self.unhighlight_format.setForeground(Gui.QColor(Core.Qt.black))

        #self.setDateTextFormat(self.selectedDate(), Gui.QTextCharFormat())
        #self.setSelectedDate(Core.QDate())
#        selection = self.selectedDate()
#        if selection.dayOfWeek() >= 6:
#            color = Core.Qt.red
#        else:
#            color = Core.Qt.black
#        hide_init_select_format = Gui.QTextCharFormat()
#        hide_init_select_format.setForeground(Gui.QBrush(Gui.QColor(color)))
#        hide_init_select_format.setBackground(Gui.QBrush(Gui.QColor(Core.Qt.white)))
#        self.setDateTextFormat(selection, hide_init_select_format)
#        self.setStyleSheet('''
#            QCalendarWidget QAbstractItemView {
#                selection-background-color: white;
#                selection-color: black;
#            }
#        ''')

    def date_selected(self, date):
        if Widgets.QApplication.instance().keyboardModifiers() & Core.Qt.ShiftModifier:
            self.selected_dates.append(date)
            for date2 in self.selected_dates:
                self.setDateTextFormat(date2, self.highlight_format)
        else:
            for date2 in self.selected_dates:
                self.setDateTextFormat(date2, self.unhighlight_format)
            self.selected_dates = [date]
        print(f'selected dates {self.selected_dates}')

class MyCalendarDialog(Widgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setSizeGripEnabled(True)
        central_layout = Widgets.QVBoxLayout()
        self.setLayout(central_layout)
        self.calendar_widget = MyCalendarWidget()
        self.calendar_widget.installEventFilter(self)
        central_layout.addWidget(self.calendar_widget)
        button = Widgets.QPushButton("Done", self)
        button.setDefault(True)
        button.clicked.connect(self.accept)
        button.installEventFilter(self)
        central_layout.addWidget(button)

    def keyPressEvent(self, event):
        # TODO make this work
        if event.type() == Core.QEvent.KeyPress and \
           event.key() == Core.Qt.Key_Return:
            self.accept()

    def dates(self):
        return self.calendar_widget.selected_dates

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
        self.page_back_button.clicked.connect(lambda _ : self.undo_redo.do(PreviousMenuAction(self)) if self.curr_menu_page > 0 or self.curr_menu_idx > 0 else None)
        self.page_back_button.setVisible(False)
        self.load_menus_layout.addWidget(self.page_back_button)
        self.page_forward_button = Widgets.QPushButton(">")
        self.page_forward_button.clicked.connect(lambda _ : self.undo_redo.do(NextMenuAction(self)) if self.curr_menu_page < len(self.image_widgets[self.curr_menu_idx]) - 1 or self.curr_menu_idx < len(self.menu_file_names) else None)

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

        calendar_dialog = MyCalendarDialog()
        ret_code = calendar_dialog.exec()
        if ret_code == Widgets.QDialog.Rejected:
            print("rejected")
        else:
            assert ret_code == Widgets.QDialog.Accepted
            print(f"accepted with dates {calendar_dialog.dates()}")

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
            self.table_model = PolarsTableModel(df, df_schema, fname, self.undo_redo)
            self.table_model.focus_school_district(self.school_name_edit.text().strip(), self.school_type_select.currentText().strip())
            self.table_view.setModel(self.table_model)
            self.set_table_view_sizing()
        for button in self.choose_new_table_button, self.load_existing_table_button:
            button.setPalette(self.application.palette())

    def load_existing_table(self):
        fname = Widgets.QFileDialog.getOpenFileName(self, "CSV file to load", filter="CSV files (*.csv)")[0]
        if fname:
            df = pl.read_csv(fname)
            if list(df.columns) != list(self.df_schema.keys()):
                box = Widgets.QMessageBox()
                box.setText(
                    f"Can only load CSVs with exactly the columns {list(self.df_schema.keys())}. "
                    f"Instead, was asked to load a CSV with the columns {list(df.columns)}. "
                    "Aborting loading the CSV."
                )
                box.exec()
                return
            # TODO don't crash if not true
            assert list(df.columns) == list(self.df_schema.keys())
            self.table_model = PolarsTableModel(df, self.df_schema, fname, self.undo_redo)
            self.table_model.focus_school_district(self.school_name_edit.text().strip(), self.school_type_select.currentText().strip())
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
        self.undo_redo.clear()
        self.reset_widgets_new_menu()
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

    def reset_widgets_new_menu(self):
        self.item_count.setText("1")
        self.plant_based_buttons.button(2).click()
        self.veg_buttons.button(2).click()
        self.item_count_sticky.setChecked(False)
        self.menu_item_edit.clear()
        self.school_name_edit.clear()
        self.school_type_select.clearEditText()

    def swap_to_image(self, image_idx, page):
        if self.curr_image_widget is not None:
            self.curr_image_widget.setVisible(False)
            self.curr_image_widget.unhighlight()

        if self.curr_menu_idx != image_idx:
            self.reset_widgets_new_menu()
                        
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
        if event.type() == Core.QEvent.KeyPress:
            print('in event filter', source, event)
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
        else:
            self.key_press_consumed = False

        if self.key_press_consumed:
#            if event.type() == Core.QEvent.KeyPress:
#                print('returning true from event filter', source, event)
            return True

#        if event.type() == Core.QEvent.KeyPress:
#            print('returning super() from event filter', source, event)
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        print('in key press event', event)
        if event.type() != Core.QEvent.KeyPress:
            self.key_press_consumed = False
            return

        # add to table
        if event.key() == Core.Qt.Key_Return:
            if self.table_model is None:
                for button in self.choose_new_table_button, self.load_existing_table_button:
                    palette = button.palette()
                    palette.setColor(palette.Button, Gui.QColor(Core.Qt.red))
                    button.setPalette(palette)
                self.key_press_consumed = True
                return

            if self.table_view.state() == Widgets.QAbstractItemView.EditingState:
                self.key_press_consumed = False
                self.menu_item_edit.setPalette(self.application.palette())
                return

            if self.curr_image_widget is None:
                palette = self.load_menus_button.palette()
                palette.setColor(palette.Button, Gui.QColor(Core.Qt.red))
                self.load_menus_button.setPalette(palette)
                self.key_press_consumed = True
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
                self.key_press_consumed = True
                return

            if self.menu_item_edit.text().strip() == '':
                palette = self.menu_item_edit.palette()
                palette.setColor(palette.Base, Gui.QColor(Gui.QColorConstants.Svg.lightcoral))
                self.menu_item_edit.setPalette(palette)
                self.key_press_consumed = True
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
            self.key_press_consumed = True
            return
            
        # switch plant based status
        if (
            event.key() == Core.Qt.Key_P and \
            (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier
        ):
            self.plant_based_buttons.button((self.plant_based_buttons.checkedId() + 1) % 3).click()
            self.key_press_consumed = True
            return

        # switch plant based status
        if (
            event.key() == Core.Qt.Key_V and \
            (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier
        ):
            self.veg_buttons.button((self.veg_buttons.checkedId() + 1) % 3).click()
            self.key_press_consumed = True
            return

        # swtich data mode status
        if (
            event.key() == Core.Qt.Key_M and \
            (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier
        ):
            self.data_mode_buttons.button((self.data_mode_buttons.checkedId() + 1) % 2).click()
            self.key_press_consumed = True
            return

        # delete selected table contents
        if event.key() in (Core.Qt.Key_Backspace, Core.Qt.Key_Delete):
            if len(self.table_view.selectionModel().selectedRows()) > 0:
                self.table_model.deleteRows(self.table_view.selectionModel().selectedRows())
                self.key_press_consumed = True
            else:
                indices = list(self.table_view.selectedIndexes())
                if len(indices) > 0:
                    self.undo_redo.do(SetDatasAction(self.table_model, indices, ['' for _ in range(len(indices))]))
                    self.key_press_consumed = True
                else:
                    self.key_press_consumed = False
                self.table_view.setSelection(Core.QRect(0, 0, self.table_model.df.shape[0], self.table_model.df.shape[1] - 1), Core.QItemSelectionModel.Clear)
            return

        # undo
        if (
            event.key() == Core.Qt.Key_Z and \
            (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier and \
            (self.application.keyboardModifiers() & Core.Qt.ShiftModifier) != Core.Qt.ShiftModifier
        ):
            self.undo_redo.undo()
            self.key_press_consumed = True
            return

        # redo
        if (
            event.key() == Core.Qt.Key_Z and \
            (self.application.keyboardModifiers() & Core.Qt.ControlModifier) == Core.Qt.ControlModifier and \
            (self.application.keyboardModifiers() & Core.Qt.ShiftModifier) == Core.Qt.ShiftModifier
        ):
            self.undo_redo.redo()
            self.key_press_consumed = True
            return

        self.key_press_consumed = False

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
