import sqlite3
import json

DB_PATH = "education_platform.db"


def check_database():
    """Verifică conținutul bazei de date"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 60)
    print("📊 VERIFICARE BAZĂ DE DATE")
    print("=" * 60)

    # Lista toate tabelele
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    tables = cursor.fetchall()

    print(f"\n✅ Tabele create ({len(tables)}):")
    for table in tables:
        print(f"   - {table['name']}")

    # Pentru fiecare tabelă, arată câte înregistrări sunt
    print("\n" + "=" * 60)
    print("📈 NUMĂR DE ÎNREGISTRĂRI")
    print("=" * 60)

    for table in tables:
        table_name = table['name']
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']
        print(f"   {table_name}: {count} înregistrări")

    # Arată conținutul pentru tabelele cu date
    print("\n" + "=" * 60)
    print("📋 CONȚINUT TABELE")
    print("=" * 60)

    for table in tables:
        table_name = table['name']
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count = cursor.fetchone()['count']

        if count > 0:
            print(f"\n🔹 {table_name.upper()}:")
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()

            for i, row in enumerate(rows, 1):
                print(f"\n   Înregistrarea #{i}:")
                for key in row.keys():
                    value = row[key]
                    # Încearcă să parseze JSON dacă e posibil
                    if key in ['report_content', 'interests'] and value:
                        try:
                            value = json.loads(value)
                            value = json.dumps(value, indent=6, ensure_ascii=False)
                        except:
                            pass
                    print(f"      {key}: {value}")

            if count > 5:
                print(f"\n   ... și încă {count - 5} înregistrări")

    conn.close()
    print("\n" + "=" * 60)
    print("✅ Verificare completă!")
    print("=" * 60)


def check_specific_table(table_name):
    """Verifică o tabelă specifică"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        print(f"\n📊 Tabelă: {table_name}")
        print(f"Înregistrări: {len(rows)}\n")

        for i, row in enumerate(rows, 1):
            print(f"Înregistrarea #{i}:")
            for key in row.keys():
                value = row[key]
                if key in ['report_content', 'interests'] and value:
                    try:
                        value = json.loads(value)
                        value = json.dumps(value, indent=2, ensure_ascii=False)
                    except:
                        pass
                print(f"  {key}: {value}")
            print()

    except sqlite3.Error as e:
        print(f"❌ Eroare: {e}")
    finally:
        conn.close()


def show_table_structure(table_name):
    """Arată structura unei tabele"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    print(f"\n🏗️ Structura tabelei: {table_name}")
    print("-" * 60)
    print(f"{'Coloană':<20} {'Tip':<15} {'Not Null':<10} {'Default'}")
    print("-" * 60)

    for col in columns:
        cid, name, type_, notnull, default, pk = col
        print(f"{name:<20} {type_:<15} {bool(notnull)!s:<10} {default}")

    conn.close()


def quick_check():
    """Verificare rapidă - doar numărul de înregistrări"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    tables = cursor.fetchall()

    print("\n📊 VERIFICARE RAPIDĂ")
    print("-" * 40)

    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "⚪"
        print(f"{status} {table_name:<25} {count} înregistrări")

    conn.close()


if __name__ == "__main__":
    import sys

    # Verificare completă implicit
    if len(sys.argv) == 1:
        check_database()

    # Verificare tabelă specifică
    elif len(sys.argv) == 2:
        if sys.argv[1] == "--quick":
            quick_check()
        else:
            check_specific_table(sys.argv[1])

    # Structura tabelei
    elif len(sys.argv) == 3 and sys.argv[1] == "--structure":
        show_table_structure(sys.argv[2])