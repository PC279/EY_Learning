#1
import fitz
import pymupdf
import pytesseract
from PIL import Image

# print(pytesseract.get_tesseract_version())

doc = fitz.open("EY_Scanned_PDF_OCR_Practice.pdf")

# print(len(doc))

# page = doc[0]
#
# pix = page.get_pixmap()
#
# pix.save("page1.png")

image = Image.open("page1.png")

text = pytesseract.image_to_string(image)

# print(text)
#
# print(type(text))

# if "Forklift FL-17" in text:
#     print("Found Forklift FL-17 in text")

# if "injuries" in text.lower():
#     print("Found injuries in text")

# print("Number of time word inspection appreared in text: ", text.lower().count("inspection") )

lines = text.split("\n")
# for line in lines:
#     if "inspection" in line.lower():
#         print(line)

# for line in lines:
#     if "Loading Bay" in line:
#         print(line)

with open("ocr_result.txt","w") as f:
    f.write(text)