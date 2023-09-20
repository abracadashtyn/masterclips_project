import keyring
import mysql.connector

from pycode.objects.clipart_image import create_image_table_statement
from pycode.objects.token import create_token_table_statement


class MysqlConnection:
    def __init__(self, config):
        config = config
        self.user = keyring.get_password("mysql", "username")
        self.password = keyring.get_password("mysql", "password")
        self.host = config.get_mysql_host()
        self.database = config.get_mysql_database()

        # check if the target database exists; if not, create it
        try:
            self.conn = self.get_connection()
        except mysql.connector.DatabaseError:
            self.create_database()
            self.conn = self.get_connection()

    def __del__(self):
        self.close_connection()

    def create_database(self):
        db_conn = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password
        )
        cursor = db_conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS {0};".format(self.database))
        cursor.close()

    def get_connection(self):
        return mysql.connector.connect(host=self.host, user=self.user, password=self.password, database=self.database)

    def close_connection(self):
        self.conn.close()

    def execute_sql_statement(self, statement, values=None):
        cursor = self.conn.cursor()
        if values is not None:
            cursor.execute(statement, values)
        else:
            cursor.execute(statement)
        self.conn.commit()
        cursor.close()

    def execute_sql_query(self, query, values=None):
        cursor = self.conn.cursor()
        if values is not None:
            cursor.execute(query, values)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results

    def set_up_tables(self):
        self.execute_sql_statement(create_token_table_statement)
        self.execute_sql_statement(create_image_table_statement)
