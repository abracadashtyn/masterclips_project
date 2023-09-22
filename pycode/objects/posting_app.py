import logging
import os
import tkinter as tk
import tkinter.font as tkFont
import webbrowser

from tkinter import ttk
from PIL import Image, ImageTk
from pycode.objects.clipart_image import get_random_fresh_image_query, get_recently_posted_images_query, ClipartImage, \
    get_image_by_file_data_query
from pycode.objects.mysql_connection import MysqlConnection
from pycode.objects.tumblr_connection import TumblrConnection
from pycode.objects.tumblr_post import TumblrPost


class PostingApp(tk.Frame):
    def __init__(self, root, config):
        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
        self.image_labeling_batch_size = 4
        self.config = config
        self.db_conn = MysqlConnection(self.config)
        self.tumblr_conn = TumblrConnection(self.config, self.db_conn)

        # these variables capture some values that we want to persist between methods and/or so they don't get garbage
        # collected. See below for examples of why this is needed
        # https://stackoverflow.com/questions/43030219/tkk-checkbutton-appears-when-loaded-up-with-black-box-in-it
        # https://stackoverflow.com/questions/74857162/avoiding-garbage-collection-for-tkinter-photoimage-python
        self.auth_redirect_url = tk.StringVar()
        self.current_image = None
        self.related_image_variables = []
        self.other_images_to_add = tk.StringVar()
        self.post = None

        # GUI application setup
        self.gui_root = root
        tk.Frame.__init__(self, self.gui_root)
        self.configure_gui()

        # determine if we need to tumblr auth or if we can just start the app
        authenticated = self.tumblr_conn.auth_if_token_present()
        if authenticated is False:
            self.authenticate()
        else:
            self.display_random_image()

    def configure_gui(self):
        self.gui_root.title("Posting App")
        self.gui_root.minsize(1500, 1000)
        default_font = tkFont.nametofont("TkDefaultFont")
        default_font.configure(size=14)

    def authenticate(self):
        auth_url = self.tumblr_conn.get_auth_url()

        self.clear_current_display()
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()
        ttk.Label(content_frame, text="Click the link below to authenticate. Once you have, paste the URL you're "
                                      "redirected to in the box below:").grid(column=0, row=0, columnspan=2)
        ttk.Button(content_frame, text="CLICK ME", command=lambda: webbrowser.open_new(auth_url)).grid(column=0, row=1,
                                                                                                       columnspan=2)
        ttk.Entry(content_frame, textvariable=self.auth_redirect_url).grid(column=0, row=2, columnspan=2)
        ttk.Button(content_frame, text="Authenticate", command=self.check_auth_response).grid(column=1, row=3)
        ttk.Button(content_frame, text="Exit", command=self.gui_root.quit).grid(column=0, row=3)

    def check_auth_response(self):
        self.tumblr_conn.token_from_redirect_response(self.auth_redirect_url.get())
        if self.tumblr_conn.token_obj is not None:
            self.display_random_image()
        else:
            logging.error("Authentication failed. Please try again.")
            self.authenticate()

    def clear_current_display(self):
        for widget in self.gui_root.winfo_children():
            widget.destroy()

    def display_random_image(self):
        self.clear_current_display()
        # frame with all content is fit inside of root window
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()

        # get a random image from the database
        latest_image_records = self.db_conn.execute_sql_query(*get_recently_posted_images_query(10))
        if latest_image_records is not None and len(latest_image_records) > 0:
            latest_subdirectories = list(set([x[3] for x in latest_image_records]))
            random_image_query = get_random_fresh_image_query(latest_subdirectories)
        else:
            random_image_query = get_random_fresh_image_query()
        random_image_record = self.db_conn.execute_sql_query(random_image_query)

        if random_image_record is None:
            logging.error("No images to post! Either something went wrong or you finally posted them all. "
                          "Double check and rerun the program.")
            exit(53)

        # create object from random image record
        self.current_image = ClipartImage(*random_image_record[0])
        self.current_image.alt_text = tk.StringVar()
        current_image_path = self.current_image.get_converted_image_path(self.config.get_image_base_dir())

        # have to set as class variable so garbage collector doesn't dump the image data before it can be displayed
        self.current_image.current_tk_pic = ImageTk.PhotoImage(Image.open(current_image_path))

        ttk.Label(content_frame, image=self.current_image.current_tk_pic).grid(column=0, row=0, columnspan=3)
        ttk.Label(content_frame, text=f"id{self.current_image.id}, filename {self.current_image.filename}") \
            .grid(column=0, row=1, columnspan=3)
        ttk.Label(content_frame,
                  text=f"From disc {self.current_image.origin_cd}, subdirectory {self.current_image.subdirectories}") \
            .grid(column=0, row=2, columnspan=3)
        ttk.Label(content_frame, text="Do you want to post this image?").grid(column=0, row=3, columnspan=3)
        ttk.Button(content_frame, text="Yes", command=self.choose_related).grid(column=0, row=4)
        ttk.Button(content_frame, text="Skip for now", command=self.display_random_image).grid(column=1, row=4)
        ttk.Button(content_frame, text="Skip Forever", command=self.mark_skipped).grid(column=2, row=4)
        ttk.Button(content_frame, text="Quit Program", command=self.gui_root.destroy).grid(column=2, row=5)

    def mark_skipped(self):
        self.db_conn.execute_sql_statement(*self.current_image.get_update_image_mark_skipped_statement())
        self.display_random_image()

    def choose_related(self):
        self.clear_current_display()
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()

        related_images = self.current_image.get_nearby_files(self.config.get_image_base_dir())
        self.related_image_variables = [tk.StringVar() for x in related_images]
        column_count = 0
        for index, filename in enumerate(related_images):
            # 20 per column
            column_count = 1 + (index // 20)
            row_count = index - ((column_count - 1) * 20)
            ttk.Checkbutton(content_frame, text=filename, variable=self.related_image_variables[index],
                            onvalue=filename, offvalue="") \
                .grid(column=column_count, row=row_count)
            self.related_image_variables[index].set("")

        ttk.Label(content_frame, image=self.current_image.current_tk_pic).grid(column=0, row=0, rowspan=19)
        ttk.Label(content_frame, text=f"id{self.current_image.id}, filename {self.current_image.filename}").grid(
            column=0, row=20)

        # TODO implement some way of checking that these are valid filenames before using
        '''ttk.Label(content_frame,
                  text="Or, you can specify any other image in this directory by typing their IDs below:").grid(column=0, row=21, columnspan=column_count)
        ttk.Entry(content_frame, textvariable=self.other_images_to_add).grid(column=0, row=22, columnspan=column_count)'''

        ttk.Button(content_frame, text="Done", command=self.start_post).grid(column=column_count, row=23)

        # pull up the directory where the image is located in a separate window - seeing the image previews there is
        # more efficient than loading in and displaying hundreds of images in the GUI, especially since most will be
        # discarded. And it's easier to drop into a reverse image search from there.
        os.startfile(os.path.join(self.config.get_image_base_dir(), self.current_image.subdirectories))

    def start_post(self):
        self.post = TumblrPost(self.current_image, self.config)
        image_directory = os.path.join(self.config.get_image_base_dir(), self.current_image.subdirectories)
        for s in self.related_image_variables:
            if s.get() != "":
                print(s.get())
                db_record = self.db_conn.execute_sql_query(*get_image_by_file_data_query(
                    s.get(), self.current_image.origin_cd, self.current_image.subdirectories))
                if db_record is not None and len(db_record) == 1:
                    self.post.add_image_from_record(db_record[0])
                    self.post.images[-1].current_tk_pic = ImageTk.PhotoImage(
                        Image.open(os.path.join(image_directory, s.get())))
                    self.post.images[-1].alt_text = tk.StringVar()
                else:
                    logging.error(f"Could not find image {s.get()} in database, skipping!")

        # alt text is added to images in batches, since if there's like 20 selected they'll overwhelm the whole screen
        self.add_alt_text(0, self.image_labeling_batch_size)

    def add_alt_text(self, lower_bound, upper_bound, is_final=False):
        self.clear_current_display()
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()

        # display batch of images with alt text entry
        for index, image in enumerate(self.post.images[lower_bound:upper_bound]):
            ttk.Label(content_frame, image=image.current_tk_pic).grid(column=index, row=0)
            ttk.Label(content_frame, text=f"Alt text for {image.filename}").grid(column=index, row=1)
            ttk.Entry(content_frame, textvariable=image.alt_text).grid(column=index, row=2)

        next_lower_bound = upper_bound + 1
        next_upper_bound = next_lower_bound + self.image_labeling_batch_size

        # if the next lower bound is >= the number of images total, this was the last batch of images to add alt text.
        # move onto the next step
        if next_lower_bound >= len(self.post.images):
            ttk.Button(content_frame, text="Continue", command=self.add_post_data).grid(
                column=self.image_labeling_batch_size, row=3)

        # if the next upper bound is >= the number of images total, the next batch will be the last.
        # Indicate that when calling the method again.
        elif next_upper_bound >= len(self.post.images):
            ttk.Button(content_frame, text="Label next batch", command=lambda: self.add_alt_text(
                next_lower_bound, len(self.post.images), True)).grid(column=self.image_labeling_batch_size, row=3)

        # if we indicated this is the last batch in the previous call, the button should move onto the next step
        elif is_final:
            ttk.Button(content_frame, text="Continue", command=self.add_post_data).grid(
                column=self.image_labeling_batch_size, row=3)

        # otherwise, just call the method again with the next batch
        else:
            ttk.Button(content_frame, text="Label next batch", command=lambda: self.add_alt_text(
                next_lower_bound, next_upper_bound)).grid(column=self.image_labeling_batch_size, row=3)

    def add_post_data(self):
        self.clear_current_display()
        for image in self.post.images:
            print(f"image {image.filename} alt text now set to {image.alt_text.get()}")
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()
        ttk.Label(content_frame, text="Title:").grid(column=0, row=0)
        ttk.Entry(content_frame, width=100, textvariable=self.post.title).grid(column=1, row=0, columnspan=2)
        ttk.Label(content_frame, text="Tags:").grid(column=0, row=1)
        ttk.Entry(content_frame, width=100, textvariable=self.post.tags).grid(column=1, row=1, columnspan=2)
        ttk.Label(content_frame, text="Caption:").grid(column=0, row=2)
        ttk.Entry(content_frame, width=100, textvariable=self.post.caption).grid(column=1, row=2, columnspan=2)
        ttk.Button(content_frame, text="Review Post", command=self.post_image).grid(column=2, row=3)

    def post_image(self):
        print(f"posting image {self.post.images[0].filename}")
        self.clear_current_display()
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()
        ttk.Label(content_frame, text="Waiting for post to be submitted...").grid(column=0, row=0)
        response = self.tumblr_conn.send_post(self.post)
        self.clear_current_display()
        content_frame = ttk.Frame(self.gui_root, padding=25)
        content_frame.grid()
        if response is None:
            ttk.Label(content_frame, text="Posting failed with no HTTP response!").grid(column=0, row=0, columnspan=2)
            ttk.Label(content_frame, text="Check the logs for more information.").grid(column=0, row=1, columnspan=2)

        else:
            if response.status_code != 201:
                ttk.Label(content_frame, text="Post failed!").grid(column=0, row=0, columnspan=2)
                ttk.Label(content_frame, text=f"Response: {response}").grid(column=0, row=1, columnspan=2)
            else:
                ttk.Label(content_frame, text="Post successfully sent!").grid(column=0, row=0, columnspan=2)

        ttk.Label(content_frame, text="What would you like to do next?").grid(column=0, row=2, columnspan=2)
        ttk.Button(content_frame, text="Post another image", command=self.start_post).grid(column=1, row=3)
        ttk.Button(content_frame, text="Exit", command=self.gui_root.destroy).grid(column=0, row=3)
