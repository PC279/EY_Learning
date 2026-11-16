# SECTION A - Data Handling and Data Types

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

#A1
df = pd.read_csv("urban_mobility.csv")
print(df.head(5))

#A2
df["Energy_Per_Km"] = df["Energy_Used_kWh"]/df["Distance_Km"]
print(df)

#A3
van = df[(df["Vehicle_Type"] == "Electric Van") & (df["Maintenance_Flag"] == "Yes")]
print(van)

#A4
group = df.groupby("Vehicle_Type").agg(
     Avg_Distance_Km=("Distance_Km", "mean"),
     Total_Trips_Count=("Trips_Count", "sum")
)

print(group)

#A5
energy_used = df["Energy_Used_kWh"].to_numpy()
print(np)
#
print("mean:", np.mean(energy_used))
print("max :", np.max(energy_used))
print("min :", np.min(energy_used))

#A6
avg_energy = df.groupby("Vehicle_Type")["Energy_Used_kWh"].mean()
#
avg_energy.plot(kind="bar")
plt.title("Average Energy Used by Vehicle Type")
plt.xlabel("Vehicle Type")
plt.ylabel("Average Energy Used (kWh)")
plt.show()

#A7
# with open("equipment_events.json") as file:
    equipment_events = json.load(file)

for e in equipment_events:
    print(f"event_id: {e["event_id"]}, asset type: {e["asset"]["type"]}, site: {e['asset']['site']}, severity: {e['severity']}")

#A8
print("Events with temperature above 70")
for e in equipment_events:
    if e["temperature"] > 70:
        actions = e.get("actions", "No actions recorded")
        print(e)

#A9
with open("coastal_monitoring_log.txt") as file:
    text = file.read()

print("Total number of words:", len(text.split()))
print("Number of times word inspection came in text:", text.lower().count("inspection"))

#A10
keywords = ("boardwalk", "maintenance", "wind")
for line in text.splitlines():
    if any(k in line.lower() for k in keywords):
        print(line)


# urban_mobility.csv is structured. Its data sits in a fixed table of rows and columns, where every record has the same fields and data types, so it loads directly into a Pandas DataFrame.
#
# equipment_events.json is semi structured. It uses labeled fields and nested objects (such as asset holding type and site), but it has no rigid schema. Records can differ from one another, as EVT502 and EVT505 have no actions field while the others do.
#
# coastal_monitoring_log.txt is unstructured. It is plain written sentences with no fields, columns or tags, so any information in it, such as word counts or keyword matches, has to be pulled out with text processing.

