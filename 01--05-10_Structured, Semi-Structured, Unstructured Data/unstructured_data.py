with open("incident_notes.txt") as f:
    text = f.read()

words = text.split()
# return list named words with elements split by spaces, tab, newline
print('word count', len(words))

print(text.lower().split().count("vibration"))
