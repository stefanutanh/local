import pyodbc
import sqlite3
import pandas as pd
import os 

# Inställningar för SQL Server
sql_server_config = (
    "Driver={ODBC Driver 17 for SQL Server};"
    r"Server=localhost\SQLEXPRESS;"
    "Database=AdventureWorksDW2022;" 
    "Trusted_Connection=yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

db_file = 'AdventureWorks.db'

# RADERA GAMMAL DATABAS OM DEN FINNS
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"Raderade gammal fil: {db_file}")

# Anslut till båda databaserna
sql_conn = pyodbc.connect(sql_server_config)
sqlite_conn = sqlite3.connect(db_file) # Skapar nu en helt ny, tom fil

# Hämta alla tabeller från SQL Server
cursor = sql_conn.cursor()
cursor.execute("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
tables = cursor.fetchall()

print(f"Hittade {len(tables)} tabeller. Startar migrering till en ren databas...")

for schema, table_name in tables:
    target_table = f"{schema}_{table_name}"
    print(f"Migrerar {schema}.{table_name} -> {target_table}...")
    
    query = f"SELECT * FROM [{schema}].[{table_name}]"
    df = pd.read_sql(query, sql_conn)
    df.to_sql(target_table, sqlite_conn, if_exists='replace', index=False)

print("Migreringen är klar! Du har nu en helt ren AdventureWorksDW-databas.")
sql_conn.close()
sqlite_conn.close()