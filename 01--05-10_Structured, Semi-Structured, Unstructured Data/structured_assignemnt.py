import pandas as pd
import numpy as np

df = pd.read_csv("library_loans.csv")
#print(df)

# print(df[["Member_Name", "Book_Category","Fine"]])

# print(df[df["Fine"] > 50])

# df["Status"] = np.where(df["Fine"] == 0, "No Fine", "Fine Due")
# print(df)

#avg = df["Days_Borrowed"].mean()
#print("average number of days borrowed:", avg)

print(df.groupby("Book_Category")["Fine"].sum())
