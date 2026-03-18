import sqlite3
# Definiera vilka tabeller varje roll har tillgång till. None betyder full tillgång.
ROLE_TABLE_ACCESS = {
    "sales": {
        "SalesLT_SalesOrderHeader", "SalesLT_SalesOrderDetail", 
        "SalesLT_Product", "SalesLT_Customer", "SalesLT_Address"
    },
    "analyst": {
        "SalesLT_SalesOrderHeader", "SalesLT_SalesOrderDetail", "SalesLT_Product"
    },
    "admin": None,
}
# Användare definierade i .env eller med standardlösenord
_TABLE_KEYWORDS = {
    "kund": "SalesLT_Customer", "customer": "SalesLT_Customer",
    "adress": "SalesLT_Address", "epost": "SalesLT_Customer"
}
# Kontrollera om en fråga innehåller tabeller som inte är tillåtna för rollen
def check_role_access(user_query, role):
    allowed_tables = ROLE_TABLE_ACCESS.get(role, set())
    if allowed_tables is None: return True, ""
    
    query_lower = user_query.lower()
    for kw, table in _TABLE_KEYWORDS.items():
        if kw in query_lower and table not in allowed_tables:
            return False, "Du har inte behörighet att utföra den här datan."
    return True, ""

# Ladda databasschema och filtrera bort tabeller som inte är tillåtna för rollen (undvik att göra detta i produktion)
def load_schema_from_db(db_path="AdventureWorks.db", role="admin"):
    """Ladda databasschema och filtrera bort tabeller som inte är tillåtna för rollen (undvik att göra detta i produktion)"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cursor.fetchall()]
            
            schema_info = []
            for table in tables:
                cursor.execute(f"PRAGMA table_info('{table}');")
                cols = ", ".join([f"{c[1]}" for c in cursor.fetchall()])
                schema_info.append(f"- {table} (Kolumner: {cols})")
            return "\n".join(schema_info)
    except Exception as e:
        return f"Kunde inte ladda schema: {e}"

# Generera SQL-prompt. Om schema inte skickas in laddas det från databasen (undvik detta i produktion).
def generate_sql_prompt(user_query, role="admin", schema=None):
    """Generera SQL-prompt. Om schema inte skickas in laddas det från databasen (undvik detta i produktion)."""
    if schema is None:
        schema = load_schema_from_db(role=role)
    
    return f"""Du är en teknisk AI-assistent som skriver SQLite-frågor för AdventureWorks DW 2022.
Svara alltid på svenska.

VIKTIGA REGLER:
1. ANVÄND EXAKTA NAMN: Använd tabellnamn exakt som de står i SCHEMAT, inklusive prefix som 'dbo_' eller 'SalesLT_'.
2. INGA EGNA REGLER: Hitta inte på begränsningar om vad tabeller får heta. Använd det som finns i listan.
3. FORMAT: Svara alltid med en kort förklarande mening på svenska, sedan SQL-koden i ett ```sql-block.
4. AVSLUTA ALLTID sql-blocket med ```.
5. En fråga = en SQL-sats. Använd inte semikolon mitt i blocket.
6. Faktatabelller (Fact*) innehåller mätvärden. Dimensionstabeller (Dim*) innehåller beskrivande info. Joina dem via gemensamma nycklar, t.ex. CustomerKey, ProductKey, EmployeeKey.

SCHEMA (Dessa tabeller finns i databasen):
{schema}

--- FEW-SHOT EXEMPEL ---

Fråga: Visa alla tabeller
Svar: Här är tabellerna som finns i databasen:
```sql
SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';
```

Fråga: Visa kolumnerna i en tabell
Svar: Här är kolumnerna i tabellen:
```sql
PRAGMA table_info('dbo_FactInternetSales');
```

Fråga: Vilka är de 10 kunder som har handlat mest totalt?
Svar: Här är de 10 kunder med högst total köpesumma:
```sql
SELECT
    c.FirstName || ' ' || c.LastName AS Kund,
    ROUND(SUM(f.SalesAmount), 2) AS TotalKöp
FROM dbo_FactInternetSales f
JOIN dbo_DimCustomer c ON f.CustomerKey = c.CustomerKey
GROUP BY c.CustomerKey
ORDER BY TotalKöp DESC
LIMIT 10;
```

Fråga: Vilka produkter säljer bäst i antal?
Svar: Här är de produkter som sålts i störst antal:
```sql
SELECT
    p.EnglishProductName AS Produkt,
    SUM(f.OrderQuantity) AS TotalAntal
FROM dbo_FactInternetSales f
JOIN dbo_DimProduct p ON f.ProductKey = p.ProductKey
GROUP BY p.ProductKey
ORDER BY TotalAntal DESC
LIMIT 10;
```

Fråga: Vilka produkter säljer bäst i intäkt?
Svar: Här är de produkter som genererat mest intäkter:
```sql
SELECT
    p.EnglishProductName AS Produkt,
    ROUND(SUM(f.SalesAmount), 2) AS TotalIntäkt
FROM dbo_FactInternetSales f
JOIN dbo_DimProduct p ON f.ProductKey = p.ProductKey
GROUP BY p.ProductKey
ORDER BY TotalIntäkt DESC
LIMIT 10;
```

Fråga: Hur ser försäljningen ut per år och månad?
Svar: Här är försäljningen grupperad per år och månad:
```sql
SELECT
    d.CalendarYear AS År,
    d.MonthNumberOfYear AS Månad,
    d.EnglishMonthName AS Månadsnamn,
    ROUND(SUM(f.SalesAmount), 2) AS TotalFörsäljning
FROM dbo_FactInternetSales f
JOIN dbo_DimDate d ON f.OrderDateKey = d.DateKey
GROUP BY d.CalendarYear, d.MonthNumberOfYear
ORDER BY År, Månad;
```

Fråga: Vilka säljare genererar mest intäkter?
Svar: Här är säljarna sorterade efter total intäkt:
```sql
SELECT
    e.FirstName || ' ' || e.LastName AS Säljare,
    ROUND(SUM(f.SalesAmount), 2) AS TotalIntäkt
FROM dbo_FactResellerSales f
JOIN dbo_DimEmployee e ON f.EmployeeKey = e.EmployeeKey
GROUP BY e.EmployeeKey
ORDER BY TotalIntäkt DESC
LIMIT 10;
```

Fråga: Hur många anställda finns per avdelning?
Svar: Här är antal anställda per avdelning:
```sql
SELECT
    DepartmentName AS Avdelning,
    COUNT(EmployeeKey) AS AntalAnställda
FROM dbo_DimEmployee
WHERE CurrentFlag = 1
GROUP BY DepartmentName
ORDER BY AntalAnställda DESC;
```

Fråga: Vilka produkter har lägst lagerstatus?
Svar: Här är produkterna med lägst lagersaldo:
```sql
SELECT
    p.EnglishProductName AS Produkt,
    SUM(i.UnitsBalance) AS LagerSaldo
FROM dbo_FactProductInventory i
JOIN dbo_DimProduct p ON i.ProductKey = p.ProductKey
GROUP BY p.ProductKey
ORDER BY LagerSaldo ASC
LIMIT 10;
```

Fråga: Vilka produktkategorier säljer bäst?
Svar: Här är produktkategorierna sorterade efter total försäljning:
```sql
SELECT
    pc.EnglishProductCategoryName AS Kategori,
    ROUND(SUM(f.SalesAmount), 2) AS TotalFörsäljning
FROM dbo_FactInternetSales f
JOIN dbo_DimProduct p ON f.ProductKey = p.ProductKey
JOIN dbo_DimProductSubcategory ps ON p.ProductSubcategoryKey = ps.ProductSubcategoryKey
JOIN dbo_DimProductCategory pc ON ps.ProductCategoryKey = pc.ProductCategoryKey
GROUP BY pc.ProductCategoryKey
ORDER BY TotalFörsäljning DESC;
```

Fråga: Finns det produkter som aldrig har sålts?
Svar: Här är produkter som inte finns i någon order:
```sql
SELECT
    p.EnglishProductName AS Produkt
FROM dbo_DimProduct p
LEFT JOIN dbo_FactInternetSales f ON p.ProductKey = f.ProductKey
WHERE f.ProductKey IS NULL;
```

--- SLUT PÅ EXEMPEL ---

FRÅGA: {user_query}
SQL:"""