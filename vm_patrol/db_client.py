import psycopg2
from psycopg2.extras import RealDictCursor

class DBClient:
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.database,
                user=self.user,
                password=self.password,
                host=self.host
            )
            return True
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False

    def insert_scan_result(self, vm_info):
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO scan_results (ip, os, version, architecture, detected_os)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (vm_info['ip'], vm_info['os'], vm_info['version'], vm_info['architecture'], vm_info['detected_os']))
        result = cur.fetchone()
        self.conn.commit()
        cur.close()
        return result

    def close(self):
        if self.conn:
            self.conn.close()
