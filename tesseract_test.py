# Set up logging first in case other imports fail

import datetime
import logging
import sys

logging.basicConfig(filename='menu_scanner.log', encoding='utf-8', level=logging.DEBUG)
logger = logging.getLogger(__name__)
# dd/mm/YY H:M:S
logger.info('Starting ' + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

def handle_exception(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# Other imports

import os
import os.path
import stat

import cv2
import pytesseract

# Append to path so bundled executables are findable

logger.debug('Path: ' + str(sys.path))
logger.debug('Temp dir: ' + sys._MEIPASS)
logger.debug('Temp dir contents: ' + str(os.listdir(sys._MEIPASS)))

os.chmod(os.path.join(sys._MEIPASS, 'tesseract.exe'), stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR)

pytesseract.pytesseract.tesseract_cmd = os.path.join(sys._MEIPASS, 'tesseract.exe')
os.environ["TESSDATA_PREFIX"] = os.path.join(sys._MEIPASS, "tessdata")

# construct the argument parser and parse the arguments
#ap = argparse.ArgumentParser()
#ap.add_argument("-i", "--image", required=True,
#                    help="path to input image to be OCR'd")
#ap.add_argument("-c", "--min-conf", type=int, default=0,
#                    help="mininum confidence value to filter weak text detection")
#args = vars(ap.parse_args())

# load the input image, convert it from BGR to RGB channel ordering,
# and use Tesseract to localize each area of text in the input image
file_path = r"\Users\Jonathan\Downloads\Screenshot 2023-10-21 144424.png" #args["image"]
image = cv2.imread(file_path)
rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
results = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)

# loop over each of the individual text localizations
text_dict = {}
for i in range(0, len(results["text"])):
    conf = int(results["conf"][i])
    if conf < 0.6:
        continue
    text = "".join([c if ord(c) < 128 and c not in "_|" else "" for c in results["text"][i]]).strip()
    if text == "":
        continue


    curr_text_dict = text_dict
    for level in "page_num", "block_num", "par_num", "line_num":
        if results[level][i] not in curr_text_dict:
            curr_text_dict[results[level][i]] = {}
        curr_text_dict = curr_text_dict[results[level][i]]

    if "x" not in curr_text_dict:
        curr_text_dict["x"] = results["left"][i]
        curr_text_dict["y"] = results["top"][i]
        curr_text_dict["w"] = results["width"][i]
        curr_text_dict["h"] = results["height"][i]
        curr_text_dict["num"] = results["word_num"][i]
        curr_text_dict["text"] = text
    else:
        assert curr_text_dict["num"] < results["word_num"][i]
        assert curr_text_dict["x"] < results["left"][i]
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

for p in text_dict.values():
    for b in p.values():
        for par in b.values():
            for l in par.values():
                cv2.rectangle(image, (l["x"], l["y"]), (l["x"] + l["w"], l["y"] + l["h"]), (0, 255, 0), 2)
                cv2.putText(image, "!" + l["text"], (l["x"], l["y"] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 255), 1)

cv2.imshow("Image", image)
cv2.waitKey(0)
