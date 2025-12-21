import sqlite3
import datetime

DB_FILENAME = "access_log.db"

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    
    # Drop the table if it exists with wrong schema and recreate
    c.execute("DROP TABLE IF EXISTS access_log")
    
    c.execute("""
    CREATE TABLE access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,         -- yyyy-mm-dd
        entry_time TEXT,            -- HH:MM:SS
        exit_time TEXT,             -- HH:MM:SS
        result TEXT,                -- "allowed" or "denied"
        reason TEXT                 -- reason if denied
    );
    """)
    conn.commit()
    conn.close()

def get_today_date_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_time_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

def record_entry(name):
    """Record that `name` is entering. If denied, ask reason. Else insert a new row."""
    date = get_today_date_str()
    entry_time = get_time_str()

    # Ask result (allowed or denied)
    res = input(f"Is {name} allowed to enter? (allowed / denied): ").strip().lower()
    reason = None
    if res == "denied":
        reason = input("Enter reason for denial: ").strip()

    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()

    # Insert a new row with entry_time, exit_time left NULL
    c.execute("""
        INSERT INTO access_log (name, date, entry_time, exit_time, result, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, date, entry_time, None, res, reason))
    conn.commit()
    conn.close()

    print(f"Entry recorded for {name} at {entry_time} (result = {res})")

def record_exit(name):
    """Record exit time for `name` today, only if there is a row with no exit_time yet."""
    date = get_today_date_str()
    exit_time = get_time_str()

    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()

    # Find the record for this name, today, that has exit_time NULL
    c.execute("""
        SELECT id, entry_time, result FROM access_log
        WHERE name = ? AND date = ? AND (exit_time IS NULL)
          AND result = 'allowed'
        ORDER BY id DESC
        LIMIT 1
    """, (name, date))
    row = c.fetchone()
    if not row:
        print(f"No existing entry record found today for {name} to mark exit.")
    else:
        rec_id = row[0]
        c.execute("""
            UPDATE access_log
            SET exit_time = ?
            WHERE id = ?
        """, (exit_time, rec_id))
        conn.commit()
        print(f"Exit recorded for {name} at {exit_time}")

    conn.close()

def show_today():
    """Print a table of all today's records."""
    date = get_today_date_str()
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("""
        SELECT name, entry_time, exit_time, result, reason
        FROM access_log
        WHERE date = ?
        ORDER BY name
    """, (date,))
    rows = c.fetchall()
    conn.close()

    print(f"Logs for {date}:")
    print(f"{'Name':20} | {'Entry':10} | {'Exit':10} | {'Result':10} | {'Reason'}")
    print("-"*70)
    for (name, ent, ext, res, reason) in rows:
        ent = ent if ent else ""
        ext = ext if ext else ""
        reason = reason if reason else ""
        print(f"{name:20} | {ent:10} | {ext:10} | {res:10} | {reason}")

if __name__ == "__main__":
    init_db()

    while True:
        print("\nOptions:")
        print("1. Record entry")
        print("2. Record exit")
        print("3. Show today's log")
        print("4. Quit")
        choice = input("Choose option: ").strip()
        if choice == "1":
            name = input("Enter person name for entry: ").strip()
            record_entry(name)
        elif choice == "2":
            name = input("Enter person name for exit: ").strip()
            record_exit(name)
        elif choice == "3":
            show_today()
        elif choice == "4":
            print("Quitting.")
            break
        else:
            print("Invalid choice. Please try again.")