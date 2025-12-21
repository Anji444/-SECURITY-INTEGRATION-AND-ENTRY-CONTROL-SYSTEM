import sqlite3
import datetime
import json
import requests
from typing import Optional

DB_FILENAME = "access_log.db"
CONFIG_FILE = "server_config.json"

# Default server configuration
DEFAULT_CONFIG = {
    "server_url": "http://your-server.com/api/access-logs",
    "api_key": "your-api-key-here",
    "sync_enabled": False
}

def load_config():
    """Load server configuration from file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create default config file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"Created default config file: {CONFIG_FILE}")
        print("Please update with your server details.")
        return DEFAULT_CONFIG

def save_config(config):
    """Save server configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    
    # Create the table if it doesn't exist
    c.execute("""
    CREATE TABLE IF NOT EXISTS access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        entry_time TEXT,
        exit_time TEXT,
        result TEXT,
        reason TEXT,
        synced INTEGER DEFAULT 0
    );
    """)
    
    # Check if synced column exists, if not add it
    c.execute("PRAGMA table_info(access_log)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'synced' not in columns:
        print("Adding 'synced' column to existing table...")
        c.execute("ALTER TABLE access_log ADD COLUMN synced INTEGER DEFAULT 0")
        conn.commit()
        print("Column added successfully.")
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_today_date_str():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def get_time_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

def record_entry(name):
    """Record that `name` is entering."""
    date = get_today_date_str()
    entry_time = get_time_str()

    res = input(f"Is {name} allowed to enter? (allowed / denied): ").strip().lower()
    reason = None
    if res == "denied":
        reason = input("Enter reason for denial: ").strip()

    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO access_log (name, date, entry_time, exit_time, result, reason, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (name, date, entry_time, None, res, reason))
    conn.commit()
    conn.close()

    print(f"Entry recorded for {name} at {entry_time} (result = {res})")

def record_exit(name):
    """Record exit time for `name` today."""
    date = get_today_date_str()
    exit_time = get_time_str()

    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()

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

def show_logs(period="today"):
    """Print a table of records based on the specified period."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    
    today = datetime.datetime.now()
    
    if period == "today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = start_date
        title = f"Logs for Today ({start_date})"
    elif period == "week":
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_date = start_of_week.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = f"Logs for This Week ({start_date} to {end_date})"
    elif period == "month":
        start_of_month = today.replace(day=1)
        start_date = start_of_month.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = f"Logs for This Month ({start_date} to {end_date})"
    else:
        print("Invalid period specified.")
        conn.close()
        return
    
    c.execute("""
        SELECT date, name, entry_time, exit_time, result, reason, synced
        FROM access_log
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC, entry_time DESC
    """, (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    print(f"\n{title}")
    print("="*100)
    print(f"{'Date':12} | {'Name':20} | {'Entry':10} | {'Exit':10} | {'Result':10} | {'Synced':8} | {'Reason'}")
    print("-"*100)
    
    if not rows:
        print("No records found for this period.")
    else:
        for (date, name, ent, ext, res, reason, synced) in rows:
            ent = ent if ent else ""
            ext = ext if ext else ""
            reason = reason if reason else ""
            sync_status = "Yes" if synced else "No"
            print(f"{date:12} | {name:20} | {ent:10} | {ext:10} | {res:10} | {sync_status:8} | {reason}")
        print(f"\nTotal records: {len(rows)}")

def show_custom_date_logs():
    """Show logs for a specific date entered by user."""
    date_str = input("Enter date (YYYY-MM-DD): ").strip()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Please use YYYY-MM-DD format.")
        return
    
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("""
        SELECT name, entry_time, exit_time, result, reason, synced
        FROM access_log
        WHERE date = ?
        ORDER BY entry_time DESC
    """, (date_str,))
    rows = c.fetchall()
    conn.close()

    print(f"\nLogs for {date_str}:")
    print("="*100)
    print(f"{'Name':20} | {'Entry':10} | {'Exit':10} | {'Result':10} | {'Synced':8} | {'Reason'}")
    print("-"*100)
    
    if not rows:
        print("No records found for this date.")
    else:
        for (name, ent, ext, res, reason, synced) in rows:
            ent = ent if ent else ""
            ext = ext if ext else ""
            reason = reason if reason else ""
            sync_status = "Yes" if synced else "No"
            print(f"{name:20} | {ent:10} | {ext:10} | {res:10} | {sync_status:8} | {reason}")
        print(f"\nTotal records: {len(rows)}")

def get_records_older_than_30_days():
    """Get all records older than 30 days."""
    thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, date, entry_time, exit_time, result, reason
        FROM access_log
        WHERE date < ?
        ORDER BY date, entry_time
    """, (thirty_days_ago,))
    rows = c.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    records = []
    for row in rows:
        records.append({
            "id": row[0],
            "name": row[1],
            "date": row[2],
            "entry_time": row[3],
            "exit_time": row[4],
            "result": row[5],
            "reason": row[6]
        })
    
    return records

def send_to_server(records, config):
    """Send records to the main server."""
    if not config.get("sync_enabled", False):
        print("Server sync is disabled in config.")
        return False
    
    server_url = config.get("server_url")
    api_key = config.get("api_key")
    
    if not server_url or server_url == DEFAULT_CONFIG["server_url"]:
        print("Server URL not configured properly.")
        return False
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "records": records,
            "sync_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print(f"Sending {len(records)} records to server...")
        response = requests.post(server_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print("✓ Records successfully sent to server!")
            return True
        else:
            print(f"✗ Server returned error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error connecting to server: {e}")
        return False

def delete_old_records(record_ids):
    """Delete records by their IDs."""
    conn = sqlite3.connect(DB_FILENAME)
    c = conn.cursor()
    
    placeholders = ','.join('?' * len(record_ids))
    c.execute(f"DELETE FROM access_log WHERE id IN ({placeholders})", record_ids)
    deleted_count = c.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count

def sync_and_cleanup():
    """Sync old records to server and delete them locally."""
    config = load_config()
    
    # Get records older than 30 days
    old_records = get_records_older_than_30_days()
    
    if not old_records:
        print("No records older than 30 days to sync.")
        return
    
    print(f"\nFound {len(old_records)} records older than 30 days.")
    print("These records will be sent to the server and deleted locally.")
    
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Sync cancelled.")
        return
    
    # Send to server
    success = send_to_server(old_records, config)
    
    if success:
        # Delete records locally
        record_ids = [r["id"] for r in old_records]
        deleted = delete_old_records(record_ids)
        print(f"✓ Deleted {deleted} old records from local database.")
        print("Sync and cleanup completed successfully!")
    else:
        print("✗ Sync failed. Records were NOT deleted locally.")
        print("Please check your server configuration and try again.")

def configure_server():
    """Configure server settings."""
    config = load_config()
    
    print("\n" + "="*50)
    print("SERVER CONFIGURATION")
    print("="*50)
    print(f"Current settings:")
    print(f"  Server URL: {config.get('server_url')}")
    print(f"  API Key: {config.get('api_key')}")
    print(f"  Sync Enabled: {config.get('sync_enabled')}")
    print("="*50)
    
    print("\nWhat would you like to update?")
    print("1. Server URL")
    print("2. API Key")
    print("3. Enable/Disable Sync")
    print("4. Back to main menu")
    
    choice = input("Choose option: ").strip()
    
    if choice == "1":
        url = input("Enter server URL: ").strip()
        if url:
            config["server_url"] = url
            save_config(config)
            print("✓ Server URL updated.")
    elif choice == "2":
        key = input("Enter API key: ").strip()
        if key:
            config["api_key"] = key
            save_config(config)
            print("✓ API key updated.")
    elif choice == "3":
        enabled = input("Enable sync? (yes/no): ").strip().lower()
        config["sync_enabled"] = (enabled == "yes")
        save_config(config)
        print(f"✓ Sync {'enabled' if config['sync_enabled'] else 'disabled'}.")
    elif choice == "4":
        return
    else:
        print("Invalid choice.")

def show_sync_status():
    """Show current sync status and old records count."""
    config = load_config()
    old_records = get_records_older_than_30_days()
    
    print("\n" + "="*50)
    print("SYNC STATUS")
    print("="*50)
    print(f"Sync Enabled: {config.get('sync_enabled')}")
    print(f"Server URL: {config.get('server_url')}")
    print(f"Records older than 30 days: {len(old_records)}")
    print("="*50)

if __name__ == "__main__":
    init_db()
    load_config()  # Ensure config file exists

    while True:
        print("\n" + "="*50)
        print("ACCESS LOG SYSTEM")
        print("="*50)
        print("1. Record entry")
        print("2. Record exit")
        print("3. Show today's log")
        print("4. Show this week's log")
        print("5. Show this month's log")
        print("6. Show specific date's log")
        print("7. Sync old records to server & cleanup")
        print("8. Show sync status")
        print("9. Configure server settings")
        print("10. Quit")
        print("="*50)
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            name = input("Enter person name for entry: ").strip()
            if name:
                record_entry(name)
            else:
                print("Name cannot be empty.")
        elif choice == "2":
            name = input("Enter person name for exit: ").strip()
            if name:
                record_exit(name)
            else:
                print("Name cannot be empty.")
        elif choice == "3":
            show_logs("today")
        elif choice == "4":
            show_logs("week")
        elif choice == "5":
            show_logs("month")
        elif choice == "6":
            show_custom_date_logs()
        elif choice == "7":
            sync_and_cleanup()
        elif choice == "8":
            show_sync_status()
        elif choice == "9":
            configure_server()
        elif choice == "10":
            print("Quitting. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")