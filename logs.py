import os
import psycopg2
import msgspec.json
import msgspec
import time

# Database connection parameters from environment variables
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'traefik_logs')
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']

LOG_FILE_PATH = '/var/log/traefik/access.log'
CHECK_INTERVAL = 5  # seconds
TRUNCATE_INTERVAL = 3600  # truncate the log file every hour

schema = msgspec.StructType({
    "ClientAddr": str,
    "ClientHost": str,
    "ClientPort": str,
    "RequestMethod": str,
    "RequestPath": str,
    "StatusCode": int,
    "ElapsedTime": str
})

def _get_conn():
    """ Get Postgres connection """
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER, 
        password=DB_PASS, 
        host=DB_HOST, 
        port=DB_PORT
    )

def create_table():
    """ Create access log table if it does not exist yet """
    conn = _get_conn()
    cur = conn.cursor()
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {DB_NAME} (
        id SERIAL PRIMARY KEY,
        client_addr TEXT,
        client_host TEXT,
        client_port TEXT,
        request_method TEXT,
        request_path TEXT,
        status_code INT,
        elapsed_time TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cur.execute(create_table_query)
    conn.commit()
    cur.close()
    conn.close()

def process_log_line(log_line):
    try:
        log_data = msgspec.json.decode(log_line, type=schema, strict=False)
        return (
            log_data['ClientAddr'],
            log_data['ClientHost'],
            log_data['ClientPort'],
            log_data['RequestMethod'],
            log_data['RequestPath'],
            log_data['StatusCode'],
            log_data['ElapsedTime']
        )
    except msgspec.DecodeError:
        return None

def insert_log_to_db(log_entry):
    conn = _get_conn()
    cur = conn.cursor()
    insert_query = """
        INSERT INTO access_logs (client_addr, client_host, client_port, request_method, request_path, status_code, elapsed_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    cur.execute(insert_query, log_entry)
    conn.commit()
    cur.close()
    conn.close()

def tail_log_file():
    """ Tail and process access log entries """
    last_truncate_time = time.time()
    with open(LOG_FILE_PATH, 'r+') as log_file:
        # move the cursor to the end of the file
        # this is so we do not duplicate entries on subsequent runs
        log_file.seek(0, os.SEEK_END)
        
        while True:
            line = log_file.readline()
            if not line:
                time.sleep(CHECK_INTERVAL)
                continue
            
            # process and insert line
            log_entry = process_log_line(line)
            if log_entry:
                insert_log_to_db(log_entry)

            # truncate the log file periodically
            if time.time() - last_truncate_time > TRUNCATE_INTERVAL:
                try:
                    log_file.truncate(0)
                    last_truncate_time = time.time()
                except OSError:
                    print("Failed to truncate log file...")
                    pass

if __name__ == '__main__':
    create_table()
    tail_log_file()
