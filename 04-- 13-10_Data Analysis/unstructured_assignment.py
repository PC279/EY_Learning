# 1. Read and print the complete text file

with open("unstructured_data.txt", "r") as file:
    text = file.read()

print("\n=== Complete Report ===")
print(text)

# 2. Count the total number of words

words = text.split()

print("\n=== Total Words ===")
print(len(words))

# 3. Count the total number of lines

with open("unstructured_data.txt", "r") as file:
    lines = file.readlines()

print("\n=== Total Lines ===")
print(len(lines))

# 4. Check whether the word: maintenance appears

print("\n=== Maintenance Check ===")

if "maintenance" in text.lower():
    print("maintenance found")
else:
    print("maintenance not found")

# 5. Count how many times the word: conveyor appears

conveyor_count = text.lower().count("conveyor")

print("\n=== Conveyor Count ===")
print(conveyor_count)

# 6. Print only lines containing: team

print("\n=== Lines Containing 'team' ===")

for line in lines:
    if "team" in line.lower():
        print(line.strip())

# 7. Print only lines containing: incident

print("\n=== Lines Containing 'incident' ===")

for line in lines:
    if "incident" in line.lower():
        print(line.strip())

# 8. Find and print the sentence mentioning the damaged component

print("\n=== Damaged Component Sentence ===")

for line in lines:
    if "damaged" in line.lower():
        print(line.strip())

# 9. Convert to lowercase and save

lowercase_text = text.lower()

with open("lowercase_report.txt", "w") as file:
    file.write(lowercase_text)

print("\nLowercase report saved as lowercase_report.txt")

# 10. Keyword Summary

print("\n=== Keyword Summary ===")

keywords = [
    "maintenance",
    "injuries",
    "inspection",
    "replacement",
    "operations"
]

for keyword in keywords:

    # special handling because report contains
    # replaced/replacement variations

    if keyword == "replacement":
        found = (
            "replacement" in text.lower()
            or "replace" in text.lower()
            or "replaced" in text.lower()
        )
    else:
        found = keyword in text.lower()

    status = "Found" if found else "Not Found"

    print(f"{keyword} : {status}")