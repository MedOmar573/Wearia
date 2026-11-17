import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(dbname='postgres', user='postgres', password='admin', host='localhost', port=5432)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
with conn.cursor() as cur:
    cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'wearia_db' AND pid != pg_backend_pid()")
    cur.execute("DROP DATABASE IF EXISTS wearia_db")
    cur.execute("CREATE DATABASE wearia_db")
    print("Fresh wearia_db database recreated successfully in PostgreSQL!")
conn.close()
