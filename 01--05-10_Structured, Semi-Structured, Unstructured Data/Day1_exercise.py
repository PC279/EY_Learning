import pandas as pd
import numpy as np

data = {
"Employee": ["Aisha", "Rahul", "Neha", "Omar", "Priya", "Karan", "Fatima","Vikram"],
"Department": ["HR", "IT", "Finance", "IT", "HR", "Finance", "IT", "HR"],
"Training_Hours": [12, 18, 10, 22, 15, 8, 20, 14],
"Assessment_Score": [78, 88, 72, 91, 84, 69, 95, 80],
"Completed": ["Yes", "Yes", "No", "Yes", "Yes", "No", "Yes", "Yes"]
}
df = pd.DataFrame(data)
#print(df)

# print(df.head(4))

# print(df[["Assessment_Score"]])

# print(df[df["Department"] == "IT" ])

# print(df[df["Assessment_Score"] > 80 ])

# print(df[df["Completed"] == "Yes"])

# print(df[(df["Department"]=="IT") & (df["Assessment_Score"] > 85)])

# df["Passed"] = np.where(df["Assessment_Score"] >= 75, "Pass", "Fail")
# print(df)

#average_score = df["Assessment_Score"].mean()
#print(average_score)

#highest_assessment_score = df["Assessment_Score"].max()
#print(highest_assessment_score)

#lowest_assessment_score = df["Assessment_Score"].min()
#print(lowest_assessment_score)

#Avg_Training_Hours = df["Training_Hours"].mean()
#print(Avg_Training_Hours)

#df_sorted = df.sort_values(by=["Assessment_Score"], ascending=False)
#print(df_sorted)

# print(df.groupby("Department")["Assessment_Score"].mean())

# print(df.groupby("Department")["Training_Hours"].sum())

# print(df.groupby("Department")["Employee"].count())

# print((df["Completed"] == "Yes").sum())

#scores = df["Assessment_Score"].to_numpy()
#print(scores)
#print("Mean:", np.mean(scores))
#print("Max:", np.max(scores))
#print("Min:", np.min(scores))
#print("Standard Deviation:", np.std(scores))

import matplotlib.pyplot as plt

#avg_score = df.groupby("Department")["Assessment_Score"].mean()
#print(avg_score)
#avg_score.plot(kind="bar")

#plt.title("Average Score by Department")
#plt.xlabel("Department")
#plt.ylabel("Average Score")
#plt.show()

#total_hours = df.groupby("Department")["Training_Hours"].sum()
#print(total_hours)

#total_hours.plot(kind="bar")

#plt.title("Total Hours by Department")
#plt.xlabel("Department")
#plt.ylabel("Total Hours")
#plt.show()

#import seaborn as sns
#avg_score = df.groupby("Department")["Assessment_Score"].mean()
#print(avg_score)

#sns.violinplot(x="Department", y="Assessment_Score", data=df)
#plt.show()

detailed = df.groupby("Department")[("Assessment_Score")].agg([
    "mean",
    "median",
    "max",
    "std"
])

print(detailed)

