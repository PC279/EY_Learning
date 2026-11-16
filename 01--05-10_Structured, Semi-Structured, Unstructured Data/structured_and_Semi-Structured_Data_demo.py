#import pandas as pd

#df = pd.read_csv("ev_sessions.csv")

#print(df)

#print(df.columns)

#print(df.shape)
# print(df.dtypes)
# print(df[["Station", "kWh", "Amount"]])

import json

import pandas as pd

with open("support_tickets.json") as file:
    tickets = json.load(file)

df = pd.json_normalize(tickets)

print(df)

# print(tickets)
#print(tickets[0])
#print(tickets[0]["issue"])

# for t in tickets:
#    print(t["ticket_id"], t["issue"])

# print(tickets[0]["customer"]["name"])

#handle optional fields
# print(tickets[1]["priority"]) this will show error as there is no priority

#print(tickets[0].get("priority", "Not Assigned"))
#print(tickets[1].get("priority", "Not Assigned"))
#print(tickets[2].get("priority", "Not Assigned"))



