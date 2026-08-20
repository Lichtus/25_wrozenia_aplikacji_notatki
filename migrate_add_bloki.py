#!/usr/bin/env python3
"""
Dodaje kolumny dla struktury notatki ze spotkania:
  notatki.uczestnicy, notatki.bloki
  zadania.osoba, zadania.czas_w_nagraniu
"""
import sqlite3
import sys

BAZA = sys.argv[1] if len(sys.argv) > 1 else "data/voice_notes.db"
DOCELOWE = {
    "notatki": {"uczestnicy": "TEXT", "bloki": "TEXT"},
    "zadania": {"osoba": "VARCHAR(80)", "czas_w_nagraniu": "VARCHAR(10)"},
}

conn = sqlite3.connect(BAZA)
for tabela, kolumny in DOCELOWE.items():
    istniejace = [k[1] for k in conn.execute(f"PRAGMA table_info({tabela})")]
    for kolumna, typ in kolumny.items():
        if kolumna in istniejace:
            print(f"{tabela}.{kolumna}: już istnieje")
        else:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {kolumna} {typ}")
            print(f"{tabela}.{kolumna}: dodano")
conn.commit()
for tabela in DOCELOWE:
    print(f"{tabela}: {len([k[1] for k in conn.execute(f'PRAGMA table_info({tabela})')])} kolumn")
conn.close()
