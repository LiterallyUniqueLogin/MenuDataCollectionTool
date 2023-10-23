import PyQt6.QtPdf
import PyQt6.QtPdfWidgets
import PyQt6.QtWidgets

#path = "/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf"
path = r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023.pdf"

app = PyQt6.QtWidgets.QApplication([])

#file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "test.pdf"))
document = PyQt6.QtPdf.QPdfDocument(None)
document.load(path)
view = PyQt6.QtPdfWidgets.QPdfView(None)
view.setPageMode(PyQt6.QtPdfWidgets.QPdfView.PageMode.MultiPage)

view.setDocument(document)
view.show()

button = PyQt6.QtWidgets.QPushButton("Push me!")
view,.


app.exec()

