import os
import psycopg2
import msgspec.json
import msgspec.structs
import msgspec
from sh import tail
import logging
import time


# Database connection parameters from environment variables
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'traefik_logs')
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']

LOG_FILE_PATH = '/var/log/traefik/access.log'
TRUNCATE_INTERVAL = 3600  # truncate the log file every hour

class LogEntry(msgspec.Struct, kw_only=True):
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
    RouterName: str = ''
    ServiceAddr: str = ''
    ServiceName: str = ''
    ServiceURL: str = ''
    StartLocal: str
    StartUTC: str
    TLSCipher: str
    TLSVersion: str
    entryPointName: str
    level: str
    msg: str
    time: str

log_decoder = msgspec.json.Decoder(LogEntry)

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
    logging.info(f"Creating database {DB_NAME}")
    conn = _get_conn()
    cur = conn.cursor()
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {DB_NAME} (
        id SERIAL PRIMARY KEY,
        client_addr TEXT,
        client_host TEXT,
        client_port TEXT,
        client_username TEXT,
        downstream_content_size BIGINT,
        downstream_status BIGINT,
        duration BIGINT,
        origin_content_size BIGINT,
        origin_duration BIGINT,
        origin_status BIGINT,
        overhead BIGINT,
        request_addr TEXT,
        request_content_size BIGINT,
        request_count BIGINT,
        request_host TEXT,
        request_method TEXT,
        request_path TEXT,
        request_port TEXT,
        request_protocol TEXT,
        request_scheme TEXT,
        retry_attempts BIGINT,
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

def process_log_line(log_line) -> LogEntry:
    try:
        log_data = log_decoder.decode(log_line)
        return log_data
    except msgspec.DecodeError as e:
        logging.warning(f"Failed to process log line: {log_line}:\n{e}")
        return None

def insert_log_to_db(log_entry: LogEntry):
    conn = _get_conn()
    cur = conn.cursor()
    data_tuple = msgspec.structs.astuple(log_entry)
    insert_query = f"""
        INSERT INTO {DB_NAME} (
            client_addr, client_host, client_port, client_username,
            downstream_content_size, downstream_status, duration, origin_content_size,
            origin_duration, origin_status, overhead, request_addr, request_content_size,
            request_count, request_host, request_method, request_path, request_port,
            request_protocol, request_scheme, retry_attempts, router_name, service_addr,
            service_name, service_url, start_local, start_utc, tls_cipher, tls_version,
            entry_point_name, level, msg, time
        ) VALUES (
            {', '.join('%s' for i in data_tuple)}
        );
    """
    try:
        cur.execute(insert_query, data_tuple)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.warning(f"Failed to insert log line {log_entry}:\n{e}")

def truncate_log_file():
    """ Truncate the log file """
    with open(LOG_FILE_PATH, "w") as log_file:
        log_file.truncate()
        logging.info("Log file truncated.")


def tail_log_file():
    """ Tail and process access log entries """
    logging.info("Tailing log file")
    last_truncate_time = time.time()
    while True:
        for line in tail("-f", LOG_FILE_PATH, _iter=True):
            if not line:
                continue
            
            # process and insert line
            log_entry = process_log_line(line)
            if log_entry:
                insert_log_to_db(log_entry)

            # truncate the log file periodically
            if time.time() - last_truncate_time > TRUNCATE_INTERVAL:
                break
        
        try:
            truncate_log_file()
            last_truncate_time = time.time()
        except OSError as e:
            logging.info(f"Failed to truncate log file: {e}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s %(name)s:%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    create_table()
    tail_log_file()
