with open("wildlife_report.txt") as f:
    text = f.read()

lines = text.splitlines()

words = text.split()

# print("Total number of words:",len(words))


words_small = text.lower().split()
#print(words_small)

# print("elephant" in words_small)
# print(text.lower().split().count("elephant"))

for line in lines:
    if "trail" in line:
        print(line)

for line in lines:
    if "animal" in line:
        print(line)
