"""
Saves files from the mounted cd images to the location of the user's choice, as specified by the image_base_dir param
in the config json. Files that end in .wmf, .tif, or .tiff will be converted to .png files. Everything else will just
be copied over. Records for everything will be inserted into the database.
"""
import logging
import os

from PIL import Image
from wand.image import Image as wima

from pycode.config.config import Config
from pycode.objects.clipart_image import get_image_by_file_data_query, ClipartImage
from pycode.objects.mysql_connection import MysqlConnection

# TODO make sure you change this to the appropriate cd number - mounted drive pairs for each run
drive_to_cd_number_pairs = [
    (2, "F:\\"),
    (3, "G:\\"),
    (4, "H:\\"),
    (5, "I:\\"),
    (6, "J:\\"),
    (7, "K:\\"),
    (8, "L:\\"),
    (9, "M:\\"),
    (10, "N:\\"),
]

endings_for_conversion = ['.WMF', '.wmf', '.tif', '.TIF', '.tiff', '.TIFF']
endings_for_save = ['.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG', '.gif', '.GIF', '.htm']

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    config = Config()
    db_conn = MysqlConnection(config)
    output_dir = config.get_image_base_dir()
    logging.info("Saving images to {0}".format(output_dir))

    for (cd_number, mounted_drive) in drive_to_cd_number_pairs:
        logging.info("Converting CD {0}...".format(cd_number))
        conversion_errors = []
        record_count = 0

        for root, dirs, files in os.walk(mounted_drive):
            for file in files:
                # only log every 1000 records to not overwhelm console with junk
                if record_count % 1000 == 0 and record_count > 0:
                    logging.info("\tprocessed {0}...".format(record_count))
                record_count += 1
                file_name, file_extension = os.path.splitext(file)
                failed = False

                if file_extension in endings_for_conversion + endings_for_save:
                    should_convert = True if file_extension in endings_for_conversion else False
                    logging.debug(f"Processing file {file} with extension {file_extension}. "
                                  f"Will convert? {should_convert}")

                    input_location = os.path.join(root, file)
                    output_filename = '{0}.png'.format(file_name) if should_convert else file
                    output_directory = root.replace(mounted_drive, output_dir)
                    if not os.path.exists(output_directory):
                        os.makedirs(output_directory)
                    output_location = os.path.join(output_directory, output_filename)
                    subdirectory = output_directory.replace("D:\\Files\\MasterclipsImages\\", "").rstrip('\\')

                    if os.path.exists(output_location):
                        logging.debug("File {0} already exists, skipping...".format(output_location))
                        # make sure the file was saved to the database - if not, add a record
                        query, values = get_image_by_file_data_query(output_filename, cd_number, subdirectory)
                        existing_records = db_conn.execute_sql_query(query, values)
                        if len(existing_records) == 0:
                            logging.debug("No existing records found for {0}. Creating a new one and inserting...".format(output_filename))
                            new_image = ClipartImage(filename=output_filename, origin_cd=cd_number,
                                                     subdirectories=subdirectory, failed_to_save=failed,
                                                     original_file_extension=file_extension.lstrip("."))
                            insert_statement, values = new_image.get_insert_statement()
                            db_conn.execute_sql_statement(insert_statement, values)
                        continue

                    # if the output location does not exist yet, the image has not been converted; do so now.
                    logging.debug(f"Converting {input_location} to {output_location}")

                    try:
                        with Image.open(input_location) as im:
                            im.save(output_location, "png" if should_convert else file_extension.lstrip("."))
                    except Exception as e:
                        logging.debug("Errored with Pillow: {0}. Trying Wand...".format(e))
                        try:
                            with wima(filename=input_location) as im:
                                im.save(filename=output_location)
                            logging.debug("Conversion completed successfully!")

                        except Exception as e2:
                            logging.debug("Conversion failed with both methods.")
                            conversion_errors.append((input_location, e, e2))
                            failed = True

                    new_image = ClipartImage(filename=output_filename, origin_cd=cd_number,
                                             subdirectories=subdirectory, failed_to_save=failed,
                                             original_file_extension=file_extension.lstrip("."))
                    insert_statement, values = new_image.get_insert_statement()
                    db_conn.execute_sql_statement(insert_statement, values)

                else:
                    logging.debug("Skipping file {0} with extension {1}".format(file, file_extension))

        logging.info("Total number of files viewed: {0}".format(record_count))
        logging.info("{0} conversion errors:".format(len(conversion_errors)))
        for error in conversion_errors:
            logging.info("{0}\nPillow error:\n{1}\n\nWand Error:\n{2}\n-------------------------".format(
                error[0], error[1], error[2]))

        logging.info("\n================================================\n")

