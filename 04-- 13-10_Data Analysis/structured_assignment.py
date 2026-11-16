import pandas as pd
import numpy as np

df = pd.read_csv("structured_data.csv")

# print(df.head())

#2.
#print(df[["Shipment_ID","Origin", "Destination", "Cost"]])

#3.
#print(df[df["Mode"] == "Road"])

#4.
#print(df[df["Weight_Kg"] > 150])

#5.
# df["Cost_per_Km"] = df["Cost"]/df["Distance_Km"]
# print(df)

#6.
#average_shipment_cost = df["Cost"].mean()
#highest_shipment_cost = df["Cost"].max()
#lowest_shipment_cost = df["Cost"].min()
#print(average_shipment_cost, highest_shipment_cost, lowest_shipment_cost)

#7.
#group_by_mode_total_cost = df.groupby("Mode")["Cost"].sum()
#print(group_by_mode_total_cost)

#8.
#group_by_mode_avg_weight = df.groupby("Mode")["Weight_Kg"].mean()
#print(group_by_mode_avg_weight)

#9.
#df_sorted = df.sort_values("Cost", ascending=False)
#print(df_sorted)

#10.
#result = df[(df["Delivery_Days"] <= 1) & (df["Cost"] < 5000)]
# print(result)