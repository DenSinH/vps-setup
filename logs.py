import os
import psycopg2
import msgspec.json
import msgspec.structs
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

class LogSchema(msgspec.Struct):
    ClientAddr: str
    ClientHost: str
    ClientPort: str
    ClientUsername: str
    DownstreamContentSize: int
    DownstreamStatus: int
    Duration: int
    OriginContentSize: int
    OriginDuration: int
    OriginStatus: int
    Overhead: int
    RequestAddr: str
    RequestContentSize: int
    RequestCount: int
    RequestHost: str
    RequestMethod: str
    RequestPath: str
    RequestPort: str
    RequestProtocol: str
    RequestScheme: str
    RetryAttempts: int
    RouterName: str
    ServiceAddr: str
    ServiceName: str
    ServiceURL: str
    StartLocal: str
    StartUTC: str
    TLSCipher: str
    TLSVersion: str
    entryPointName: str
    level: str
    msg: str
    time: str

log_decoder = msgspec.json.Decoder(LogSchema)

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
        client_username TEXT,
        downstream_content_size INT,
        downstream_status INT,
        duration INT,
        origin_content_size INT,
        origin_duration INT,
        origin_status INT,
        overhead INT,
        request_addr TEXT,
        request_content_size INT,
        request_count INT,
        request_host TEXT,
        request_method TEXT,
        request_path TEXT,
        request_port TEXT,
        request_protocol TEXT,
        request_scheme TEXT,
        retry_attempts INT,
        router_name TEXT,
        service_addr TEXT,
        service_name TEXT,
        service_url TEXT,
        start_local TIMESTAMP,
        start_utc TIMESTAMP,
        tls_cipher TEXT,
        tls_version TEXT,
        entry_point_name TEXT,
        level TEXT,
        msg TEXT,
        time TIMESTAMP
    );
    """
    cur.execute(create_table_query)
    conn.commit()
    cur.close()
    conn.close()

def process_log_line(log_line) -> LogSchema:
    try:
        log_data = log_decoder.decode(log_line)
        return log_data
    except msgspec.DecodeError as e:
        return None

def insert_log_to_db(log_entry: LogSchema):
    conn = _get_conn()
    cur = conn.cursor()
    insert_query = """
        INSERT INTO access_logs (client_addr, client_host, client_port, request_method, request_path, status_code, elapsed_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    cur.execute(insert_query, msgspec.structs.astuple(log_entry))
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
            else:
                print("Failed to process log line:", line)

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
