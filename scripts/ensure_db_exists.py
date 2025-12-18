import os
import sys
import psycopg
from psycopg import sql

def ensure_db_exists():
    """
    Attempts to connect to the 'postgres' system database to check if the 
    target application database exists. If not, it attempts to create it.
    """
    target_dbname = os.environ.get("DB_NAME", "clustr")
    
    # We need to connect to 'postgres' db to perform administrative tasks
    # or to check for other databases.
    dsn_params = {
        "dbname": "postgres",
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
    }

    print(f"Checking if database '{target_dbname}' exists...")

    try:
        # Connect to 'postgres' system database
        # autocommit=True is required for CREATE DATABASE
        conn = psycopg.connect(**dsn_params, autocommit=True)
    except Exception as e:
        print(f"Skipping database creation check. Could not connect to system 'postgres' database: {e}")
        print("This is expected if using a restricted database user or service.")
        return

    try:
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_dbname,))
        exists = cur.fetchone()

        if not exists:
            print(f"Database '{target_dbname}' does not exist. Attempting to create...")
            # Use psycopg.sql to safely format the identifier
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
            print(f"Database '{target_dbname}' created successfully.")
        else:
            print(f"Database '{target_dbname}' already exists.")

    except Exception as e:
        print(f"Error during database check/creation: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    ensure_db_exists()
