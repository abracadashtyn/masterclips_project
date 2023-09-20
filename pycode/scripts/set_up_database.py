import logging

from pycode.config.config import Config
from pycode.objects.mysql_connection import MysqlConnection

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    config = Config()
    db_conn = MysqlConnection(config)
    db_conn.create_database()
    db_conn.set_up_tables()