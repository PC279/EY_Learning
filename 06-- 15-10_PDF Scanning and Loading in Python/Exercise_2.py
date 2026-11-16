#1

from pypdf import PdfReader
reader = PdfReader("EY_Digital_PDF_Practice.pdf")

#2 Number of pages
# print("Number of pages in PDF:", len(reader.pages))

#3
page1 = reader.pages[0]
# print(type(page1))
# print(page1.extract_text())

#4
page2 = reader.pages[1]
# print(page2.extract_text())

#5 Combine text from both of the pages
all_text = page1.extract_text() + page2.extract_text()

# print(all_text)

#6

# if "NorthStar Maintenance" in all_text:
#     print("Found")

#7
# print(all_text.count("vendor"))

#8
with open("pypdf_output.txt","w") as f:
    f.write(all_text)