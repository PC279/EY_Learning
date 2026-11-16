import pandas as pd
import json

from jinja2 import visitor

with open("festival_events.json") as file:
    events = json.load(file)

df = pd.json_normalize(events)
# print(df)

#for e in events:
 #   print(e["name"])


#for e in events:
 #   print(e["name"], e["location"]["city"])

# print(df[df["visitors"] > 700])

for e in events:
    print(e["event_id"],e["name"], e.get("features","No features listed"))