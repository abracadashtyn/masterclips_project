import logging
import keyring

from requests_oauthlib import OAuth2Session
from pycode.objects.token import get_latest_token_query, Token


class TumblrConnection:
    def __init__(self, config, db_conn):
        self.config = config
        self.db_conn = db_conn
        self.urls = self.config.get_tumblr_urls()
        self.client_id = keyring.get_password("tumblr", "client_id")
        self.client_secret = keyring.get_password("tumblr", "client_secret")

        latest_token_record = self.db_conn.execute_sql_query(get_latest_token_query)
        if latest_token_record is None:
            logging.info("No token found; need to authenticate")
            self.session = OAuth2Session(client_id=self.client_id,
                                         redirect_uri=self.urls['redirect'],
                                         scope=['basic', 'write', 'offline_access'])

            authorization_url = self.session.authorization_url(self.urls['auth'])
            redirect_response = input(f"Click this link to authorize app: {authorization_url}\n"
                                      f"Then, paste the full redirect URL here: ")
            self.token_obj = Token(token=self.session.fetch_token(self.urls['token'],
                                                                  authorization_response=redirect_response,
                                                                  client_secret=self.client_secret))
            self.db_conn.execute_sql_statement(self.token_obj.get_insert_statement())
        else:
            logging.info("Token found; no need to authenticate")
            self.token_obj = Token(db_record=latest_token_record[0])
            self.session = OAuth2Session(client_id=self.client_id,
                                         token=self.token_obj.token,
                                         auto_refresh_url=self.urls['token'],
                                         auto_refresh_kwargs={"client_id": self.client_id,
                                                              "client_secret": self.client_secret},
                                         token_updater=self.update_token)

        self.post_url = self.urls['post'].format(blogname=self.config.get_blogname())
        self.photo_dir = self.config.get_image_base_dir()

    def update_token(self, token):
        self.token_obj = Token(token=token)
        self.db_conn.execute_sql_statement(self.token_obj.get_insert_statement())

    def send_post(self, tumblr_post):
        return self.session.post(self.post_url, files=tumblr_post.get_formatted())
