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
        self.post_url = self.urls['post'].format(blogname=self.config.get_blogname())
        self.photo_dir = self.config.get_image_base_dir()
        self.token_obj = None
        self.session = None

    def auth_if_token_present(self):
        latest_token_record = self.db_conn.execute_sql_query(get_latest_token_query)
        if latest_token_record is None or len(latest_token_record) == 0:
            logging.info("No token found; need to authenticate")
            return False
        else:
            logging.info("Token found; no need to authenticate")
            self.token_obj = Token(db_record=latest_token_record[0])
            self.session = OAuth2Session(client_id=self.client_id,
                                         token=self.token_obj.token,
                                         auto_refresh_url=self.urls['token'],
                                         auto_refresh_kwargs={"client_id": self.client_id,
                                                              "client_secret": self.client_secret},
                                         token_updater=self.update_token)
            return True

    def get_auth_url(self):
        self.session = OAuth2Session(client_id=self.client_id,
                                     redirect_uri=self.urls['redirect'],
                                     scope=['basic', 'write', 'offline_access'])

        authorization_url = self.session.authorization_url(self.urls['auth'])
        return authorization_url[0]

    def token_from_redirect_response(self, redirect_response):
        self.token_obj = Token(token=self.session.fetch_token(self.urls['token'],
                                                              authorization_response=redirect_response,
                                                              client_secret=self.client_secret))
        self.db_conn.execute_sql_statement(*self.token_obj.get_insert_statement())

    def update_token(self, token):
        self.token_obj = Token(token=token)
        self.db_conn.execute_sql_statement(*self.token_obj.get_insert_statement())

    def send_post(self, tumblr_post):
        if self.session is None or self.token_obj is None:
            logging.error("Session or token object is None; cannot post! Please authenticate first")
            return None
        return self.session.post(self.post_url, files=tumblr_post.get_formatted())
