#1. opening the pdf

import fitz
import pymupdf

doc = fitz.open("EY_Digital_PDF_Practice.pdf")

#to check the which kind of object the pymupdf has created
#print(type(doc))

#2 Counting number of pages
# print("Pages in documnet: ", len(doc))

#3 Extract and print text from page 1

# page = doc[0]
# print(type(page))
# print(page.get_text())

#4 EXtract text from all pages

# for page in doc:
#     print(page.get_text())

#5 Search for maintenance word

all_text_in_pdf = ""

# Convert all pages into one string
for page in doc:
    all_text_in_pdf = all_text_in_pdf + page.get_text()

all_text_lower = all_text_in_pdf.lower()

#
# if "maintenance" in all_text_lower:
#     print("Found word maintenance, it does exists")

#6 How many times word V303 appears

#print("Number of times V303 has appeared in text:",all_text_in_pdf.count("V303"))

#7 Page 2 text

# page2 = doc[1]
# print(page2.get_text())

#8. Save all text info

with open("digital_pdf_text.txt", "w", encoding="utf-8") as f:
    f.write(all_text_in_pdf)

