import datetime as dt
import pickle

table_name = "tokens"
# various statements and queries associated with the Token class but kept outside of it so we can use them without
# instantiating a Token first
create_token_table_statement = f"CREATE TABLE IF NOT EXISTS {table_name} (" \
                               "id INT AUTO_INCREMENT PRIMARY KEY, " \
                               "token BLOB NOT NULL, expires_on " \
                               "DATETIME NOT NULL);"
delete_expired_tokens_statement = f"DELETE FROM {table_name} WHERE expires_on < NOW();"

select_all_tokens_query = f"SELECT id, token, expires_on FROM {table_name} ORDER BY expires_on DESC;"
get_latest_token_query = f"SELECT id, token, expires_on FROM {table_name} ORDER BY expires_on DESC LIMIT 1;"


class Token:
    def __init__(self, id=None, token=None, db_record=None):
        self.id = id
        self.token = token
        if db_record is not None:
            self.id = db_record['id']
            self.token = pickle.loads(db_record['token'])

    def __repr__(self):
        return f"Token(id={self.id}, expires_on={self.token['expires_at']})"

    def get_insert_statement(self):
        insert_statement = f"INSERT INTO {table_name} (token, expires_on) VALUES (%s, %s);"
        expiration_time = dt.datetime.utcfromtimestamp(self.token['expires_at'])
        values = (pickle.dumps(self.token), expiration_time.isoformat())
        return insert_statement, values

    def get_delete_statement(self):
        delete_statement = f"DELETE FROM {table_name} WHERE id = %s;"
        values = (self.id,)
        return delete_statement, values

