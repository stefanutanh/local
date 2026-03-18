import streamlit as st
# Ställ in sidans titel och ikon
st.set_page_config(page_title="AI Chatbot", page_icon=None)

import requests
from dotenv import load_dotenv
import os
import sqlite3
import pandas as pd
import re
import time
import logging
from login import login_page, logout
from prompts import generate_sql_prompt, check_role_access

# Konfiguration
load_dotenv()
logging.basicConfig(
    filename="query_log.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding='utf-8'
)

# Miljövariabler för Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Ladda CSS för styling
def load_css(file_name):
    """Ladda CSS-fil för styling"""
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass

# Kontrollera om Ollama är igång, cachas i 30 sekunder för att undvika onödiga förfrågningar
@st.cache_data(ttl=30)
def check_ollama_status() -> bool:
    """Kontrollera om Ollama är igång — cachas i 30 sekunder"""
    try:
        response = requests.get(f"{OLLAMA_URL}", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

# Hämta schema från session_state om det finns, annars ladda från databasen
def get_schema(role: str) -> str:
    cache_key = f"schema_{role}"
    if cache_key not in st.session_state:
        from prompts import load_schema_from_db
        st.session_state[cache_key] = load_schema_from_db(role=role)
    return st.session_state[cache_key]

# Rendera sidebar med status och användarinfo
def render_sidebar():
    with st.sidebar:
        st.markdown("**Model status**")
        ollama_ok = check_ollama_status()
        ollama_color = "#2ecc71" if ollama_ok else "#e74c3c"
        ollama_label = "Available" if ollama_ok else "Unavailable"
 
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <span style="width:10px; height:10px; border-radius:50%;
                    background:{ollama_color}; display:inline-block;"></span>
                <span>{OLLAMA_MODEL} — {ollama_label}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("---")
        st.markdown('<div style="flex-grow: 1;"></div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="bottom-content">
                <p class="user-title">Logged in as:</p>
                <p class="user-role">{st.session_state.user_name}, {st.session_state.user_title}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Log out", key="logout_btn"):
            logout()

# Extraherar SQL ur AI-svaret
def extract_sql(raw: str) -> str:
    code_match = re.search(r'```sql\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()
    
    sql_match = re.search(r"(SELECT|WITH|PRAGMA)\b.*", raw, re.IGNORECASE | re.DOTALL)
    if sql_match:
        return sql_match.group(0).split(';')[0].strip() + ';'
    return raw.strip()

# Validerar att SQL är en SELECT-fråga och inte innehåller farliga operationer
def validate_sql(sql: str):
    sql_stripped = sql.strip().lstrip(";").strip().upper()
    allowed_starts = ("SELECT", "WITH", "PRAGMA")
    if not any(sql_stripped.startswith(kw) for kw in allowed_starts):
        return False, "Endast SELECT-frågor är tillåtna. Frågan blockerades av säkerhetsskäl."
    dangerous = ("DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "REPLACE", "ATTACH")
    for word in dangerous:
        if re.search(rf"\b{word}\b", sql_stripped):
            return False, f"Frågan innehåller otillåten operation ({word}) och blockerades."
    return True, ""

# Kör SQL-frågan säkert, validerar innan körning och fångar upp eventuella fel
def execute_sql_query(sql_query):
    try:
        sql_clean = extract_sql(sql_query)
        ok, validation_err = validate_sql(sql_clean)
        if not ok:
            return None, sql_clean, validation_err
        with sqlite3.connect('AdventureWorks.db') as conn:
            df = pd.read_sql_query(sql_clean, conn)
        return df, sql_clean, None
    except Exception as e:
        return None, None, str(e)

# Om SQL-frågan misslyckas, försök igen med felmeddelandet som kontext för att hjälpa AI:n att korrigera sig
def retry_with_error(original_prompt, failed_sql, error_msg, schema):
    retry_prompt = f"""{generate_sql_prompt(original_prompt, schema=schema)}

Föregående försök genererade denna SQL:
```sql
{failed_sql}
```

Det gav följande fel:
{error_msg}

Analysera felet och generera en korrekt SQL-fråga. Tänk igenom varje kolumnnamn och alias noggrant innan du svarar.
SQL:"""
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": retry_prompt, "stream": False},
            timeout=60
        )
        return r.json().get("response", "")
    except Exception:
        return None

# Rendera en enkel visualisering (st.bar_chart) om det finns numeriska kolumner i resultatet
def render_visualization(df):
    if df is None or df.empty or len(df.columns) < 2:
        return
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    if not num_cols:
        return

    non_num_cols = [c for c in df.columns if c not in num_cols]
    index_col = non_num_cols[0] if non_num_cols else df.columns[0]

    value_col = next((c for c in num_cols if c != index_col), None)
    if value_col is None:
        return

    with st.expander("Snabbanalys", expanded=True):
        chart_df = df[[index_col, value_col]].set_index(index_col)
        st.bar_chart(chart_df)

# Huvudfunktion som hanterar inloggning, rendering av chatten och interaktionen med AI
def main():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()
        return

    load_css('style.css')
    render_sidebar()
    
    st.title("Lokal AI-Chatbot")
    st.caption("All data hanteras lokalt via Llama. Ingen data lämnar datorn.")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Hej {st.session_state.user_name}! Vad vill du analysera idag?"}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("df") is not None:
                st.dataframe(msg["df"], width='stretch')
                if msg.get("sql"):
                    with st.expander("Visa SQL-fråga"):
                        st.code(msg["sql"], language="sql")

    if prompt := st.chat_input("Ställ en fråga om databasen..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Tänker..."):
                # Kontrollera rollbaserad åtkomst innan frågan skickas till AI
                access_ok, access_err = check_role_access(prompt, st.session_state.user_role)
                if not access_ok:
                    st.warning(f"🔒 Åtkomst nekad: {access_err}")
                    st.session_state.messages.append({
                        "role": "assistant", "content": f"🔒 Åtkomst nekad: {access_err}",
                        "df": None, "sql": None
                    })
                    st.stop()

                # Använd cachat schema istället för att ladda om vid varje fråga
                schema = get_schema(role=st.session_state.user_role)
                full_prompt = generate_sql_prompt(prompt, role=st.session_state.user_role, schema=schema)
                ollama_ok = check_ollama_status()
                if not ollama_ok:
                    st.error(
                        "Lokal AI (Ollama) är inte tillgänglig. "
                        "Kontrollera att Ollama körs (`ollama serve`) och försök igen."
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "Lokal AI är inte tillgänglig just nu. Starta Ollama och försök igen.",
                        "df": None, "sql": None
                    })
                    st.stop()

                try:
                    t_start = time.time()
                    r = requests.post(f"{OLLAMA_URL}/api/generate", 
                                      json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
                                      timeout=60)
                    gen_time = time.time() - t_start
                    response = r.json().get("response", "")
                except Exception as e:
                    logging.error(f"FAIL | role={st.session_state.user_role} | model={OLLAMA_MODEL} | error={e} | query={prompt!r}")
                    st.error(f"Kopplingsfel mot Ollama: {e}. Kontrollera att tjänsten körs.")
                    return

                sql_query = extract_sql(response)
                friendly_text = response.replace(sql_query, "").replace("```sql", "").replace("```", "").strip()
                if not friendly_text: friendly_text = "Här är resultatet:"

                st.write(friendly_text)
                df, clean_sql, err = execute_sql_query(sql_query)

                # Om SQL misslyckades — försök en gång till med felmeddelandet som kontext
                if err:
                    with st.spinner("SQL-fel, försöker igen..."):
                        retry_response = retry_with_error(prompt, sql_query, err, schema)
                        if retry_response:
                            retry_sql = extract_sql(retry_response)
                            df, clean_sql, err = execute_sql_query(retry_sql)

                # Logga resultatet
                status = "FAIL" if err else "OK"
                logging.info(
                    f"{status} | role={st.session_state.user_role} | model=Local ({OLLAMA_MODEL}) | "
                    f"gen_time={gen_time:.2f}s | query={prompt!r}"
                )

                if err:
                    st.error(f"Kunde inte generera giltig SQL efter två försök: {err}")
                elif df is not None:
                    if df.empty:
                        st.warning("Inga rader hittades.")
                    else:
                        st.dataframe(df, width='stretch')
                        render_visualization(df)
                        with st.expander("Visa SQL-fråga"):
                            st.code(clean_sql, language="sql")
                
                # Spara bara en förhandsgranskning av df (max 100 rader) för att spara minne
                df_preview = df.head(100) if df is not None else None
                st.session_state.messages.append({
                    "role": "assistant", "content": friendly_text, "df": df_preview, "sql": clean_sql
                })
                # Begränsa chatthistoriken till de senaste 20 meddelandena
                if len(st.session_state.messages) > 20:
                    st.session_state.messages = st.session_state.messages[-20:]

if __name__ == "__main__":
    main()