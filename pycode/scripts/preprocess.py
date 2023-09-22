"""
Iterates through all mounted cds listed in convert.py and prints out the file extensions found on each cd. This way,
I can make sure there's some handler in the conversion script for each type of file on the disk.
"""
import logging
import os

from pycode.config.config import Config
from pycode.objects.mysql_connection import MysqlConnection
from pycode.scripts.convert import drive_to_cd_number_pairs

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    config = Config()
    db_conn = MysqlConnection(config)
    file_endings = {}
    record_count = 0
    for (cd_number, mounted_drive) in drive_to_cd_number_pairs:
        logging.info("Checking file extensions on CD {0}...".format(cd_number))
        for root, dirs, files in os.walk(mounted_drive):
            for file in files:
                record_count += 1
                file_name, file_extension = os.path.splitext(file)
                if file_extension not in file_endings:
                    file_endings[file_extension] = 0
                file_endings[file_extension] += 1

    logging.info("File endings found:")
    for key, value in sorted(file_endings.items(), key=lambda item: item[1], reverse=True):
        logging.info("{0}: {1}".format(key, value))
    logging.info("Total number of files: {0}".format(record_count))
