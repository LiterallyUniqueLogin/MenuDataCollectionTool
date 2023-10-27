import fitz

#doc = fitz.open("/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023.pdf")
doc = fitz.open(r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023.pdf")
doc[0].\
        get_pixmap(matrix=fitz.Matrix(4,4)).\
        save(r"\Users\Jonathan\Downloads\Banta ESD Elementary Lunch Menu October 2023_pymupdf.png")
        #save("/mnt/c/Users/Jonathan/Downloads/Banta ESD Elementary Lunch Menu October 2023_pymupdf.png")
