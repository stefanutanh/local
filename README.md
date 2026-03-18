# LLM-baserad AI Chatbot

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![Ollama](https://img.shields.io/badge/LLM-Ollama-green)

En lokal AI-chatbot byggd i Python med Streamlit och Ollama. Chatboten tolkar frågor på naturligt språk och genererar automatiskt SQL-frågor mot en AdventureWorksDW 2022-databas — allt körs helt lokalt utan att data lämnar maskinen.

---

## Funktioner

- Naturligt språk till SQL via lokalt LLM (Ollama)
- Streamlit-baserat webbgränssnitt
- Rollbaserad åtkomstkontroll (sales, analyst, admin)
- Automatisk visualisering av frågeresultat
- Felhantering med automatiskt omförsök vid SQL-fel
- Körs helt lokalt — ingen data lämnar datorn

---

## Förutsättningar

Följande måste vara installerat innan du börjar:

- Python 3.x
- [Ollama](https://ollama.com/)
- SQL Server med AdventureWorksDW 2022 *(behövs bara för att generera databasen)*

---

## Installation

### 1. Klona projektet

```bash
git clone https://github.com/stefanutanh/local.git
cd regionlocal
```

### 2. Skapa och aktivera virtuell miljö

```bash
python3 -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Installera beroenden

```bash
pip install -r requirements.txt
```

### 4. Skapa `.env`-fil

Skapa en fil som heter `.env` i projektets rotkatalog med följande innehåll:

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

USER_SALES_PASSWORD=demo123
USER_ANALYST_PASSWORD=demo123
USER_ADMIN_PASSWORD=admin123
```

### 5. Ladda ner och starta Ollama-modellen

```bash
ollama pull llama3.1
ollama serve
```

### 6. Konfigurera databasen

Projektet kräver en lokal SQLite-databas genererad från AdventureWorksDW 2022.

Om den inte ligger i rotkatalogen och du har SQL Server med AdventureWorksDW 2022 installerat, kör migreringsskriptet:

```bash
python scripts/sql.py
```

Detta skapar filen `AdventureWorks.db` i projektets rotkatalog.

### 7. Starta appen

```bash
streamlit run local.py
```

---

## Testanvändare

| Användarnamn | Lösenord | Roll                 |
|-------------|----------|----------------------|
| sales       | demo123  | Sales Manager        |
| analyst     | demo123  | Analyst              |
| admin       | admin123 | System Administrator |

---

## Projektstruktur

```
regionlocal/
│
├── AdventureWorks.db       # SQLite-databas 
├── local.py                # Huvudapplikation
├── login.py                # Inloggningslogik
├── prompts.py              # SQL-promptgenerering och rollåtkomst
├── requirements.txt
├── style.css
├── testfrågor.md           # Exempelfrågor att testa med
├── .env.example           # Miljövariabler 
└── scripts/
    └── sql.py              # Migreringsskript: SQL Server → SQLite
```

---