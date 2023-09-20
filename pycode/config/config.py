import json
from pathlib import Path


class Config:
    def __init__(self):
        self.config_file = "config.json"
        with open("{0}\\{1}".format(Path(__file__).parent.absolute(), self.config_file), "r") as config_file:
            self.config = json.load(config_file)

    def get_mysql_config(self):
        return self.config['mysql']

    def get_mysql_host(self):
        return self.config['mysql']['host']

    def get_mysql_database(self):
        return self.config['mysql']['database']

    def get_image_base_dir(self):
        return self.config['image_base_dir']

    def get_tumblr_urls(self):
        return self.config['tumblr_urls']

    def get_blogname(self):
        return self.config['blogname']

    def get_standard_tags(self):
        return self.config['tumblr_standard_tags']

    def get_standard_attribution(self):
        return self.config['tumblr_standard_attribution']

    def get_default_post_state(self):
        return self.config['tumblr_default_post_state']

