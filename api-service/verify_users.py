import sqlite3
import json
import os

# Buscar archivo de base de datos SQLite
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print(f"Archivos de base de datos encontrados: {db_files}")

if not db_files:
    print("No se encontraron archivos .db")
    exit(1)

db_path = db_files[0]
print(f"Usando base de datos: {db_path}\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar tablas existentes
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f'Tablas en la base de datos ({len(tables)}):')
for t in sorted(tables):
    print(f'  - {t[0]}')

conn.close()

print("\n" + "="*60)
print("NOTA: La aplicación está configurada para usar PostgreSQL")
print("según DATABASE_URL en el archivo .env")
print("="*60)
