import pandas as pd

from database_demo import connection

df = pd.read_sql_query(
    "SELECT * FROM bookings",
    connection
)

print(df)