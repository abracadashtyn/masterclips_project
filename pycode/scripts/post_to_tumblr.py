import logging
import os
import threading
import tkinter as tk

from pycode.config.config import Config
from pycode.objects.clipart_image import get_recently_posted_images_query, get_random_fresh_image_query, ClipartImage, \
    get_image_by_file_data_query
from pycode.objects.mysql_connection import MysqlConnection
from pycode.objects.tumblr_connection import TumblrConnection
from pycode.objects.tumblr_post import TumblrPost
from PIL import Image, ImageTk


def open_image_and_directory(self, image_obj, config):
    # pull up the directory where the image is located to see if there are any related
    os.startfile(os.path.join(self.photo_dir, image_obj.subdirectories))

    # open image in popup window
    image_path = image_obj.get_converted_image_path(config.get_image_base_dir())
    image = Image.open(image_path)
    window = tk.Tk()
    tk_image = ImageTk.PhotoImage(image)
    label = tk.Label(window, image=tk_image)
    label.pack()
    window.mainloop()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    config = Config()
    db_conn = MysqlConnection(config)
    tumblr_conn = TumblrConnection(config, db_conn)

    loop = True
    while loop is True:
        # pick an image id at random
        latest_image_records = db_conn.execute_sql_query(get_recently_posted_images_query(10))
        if latest_image_records is not None and len(latest_image_records) > 0:
            latest_subdirectories = list(set([x['subdirectories'] for x in latest_image_records]))
            random_image_query = get_random_fresh_image_query(latest_subdirectories)
        else:
            random_image_query = get_random_fresh_image_query()

        logging.debug("Random image query: {0}".format(random_image_query))
        random_image_record = db_conn.execute_sql_query(random_image_query)

        if random_image_record is None:
            print("No images to post! Either something went wrong or you finally posted them all. "
                  "Double check and rerun the program.")
            exit(53)

        # create object from random image record
        image = ClipartImage(**random_image_record[0])
        logging.debug("Image object: {0}".format(image))

        # open image and directory in a new thread
        image_thread = threading.Thread(target=open_image_and_directory, args=(image,))
        image_thread.start()

        # ask if the image should be posted and loop until an appropriate answer is received
        should_post = input('Do you want to post this image? (y/n)')
        while should_post.lower() not in ['y', 'n']:
            should_post = input('Response {0} is not valid!\n\nDo you want to post this image? (y/n)').format(
                should_post)

        # if user input is no, mark image as skipped so it won't attempt to post again
        if should_post.lower() == 'n':
            logging.info("Not posting image.")
            db_conn.execute_sql_statement(image.get_update_image_mark_skipped_statement())

        # otherwise, post the image
        else:
            logging.info("Posting image...")
            post = TumblrPost(image, config)
            additional_image_string = input("Are there any additional images you want to post with this one? "
                                            "If so, enter their names as a comma separated list. "
                                            "Leave blank for none.")
            additional_images = [x.strip() for x in additional_image_string.split(',')]
            for image_filename in additional_images:
                image_record = db_conn.execute_sql_query(get_image_by_file_data_query(image_filename, image.origin_cd,
                                                                                      image.subdirectories))
                if image_record is None or len(image_record) == 0:
                    logging.error("Could not find image {0} in the database!".format(image_filename))
                    # for now just going to fail and skip; worst case can just restart the post creation flow.
                else:
                    try:
                        post.add_image_from_record(image_record[0])
                    except Exception as e:
                        logging.error("Could not add image {0} to post!".format(image_filename))
                        logging.error(e)
                        # might throw error in validation if the image is on a different disk or subdirectory, and again
                        # we will just log and skip.

            response = tumblr_conn.send_post(post)
            logging.info(response.json())

            for image in post.images:
                db_conn.execute_sql_statement(image.get_update_image_mark_posted_statement())

        # rejoin opened image thread
        print("Close the image to continue.")
        image_thread.join()

        # keep looping and creating posts until the user quits=
        keep_going = input("Press enter to post another image, or type 'x' to quit.")
        while keep_going.lower() not in ['', 'x']:
            keep_going = input("Response '{0}' is not valid!\nPress enter to post another image, or type 'x' to quit.") \
                .format(keep_going)
        if keep_going.lower() == 'x':
            loop = False
