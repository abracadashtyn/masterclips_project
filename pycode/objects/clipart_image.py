import datetime as dt
import os.path

# various statements and queries associated with the Image Record class but kept outside of it so we can use them
# without instantiating a record first.
table_name = "clipart"
create_image_table_statement = "CREATE TABLE IF NOT EXISTS {0} (id INT AUTO_INCREMENT PRIMARY KEY," \
                               "filename VARCHAR(255) NOT NULL," \
                               "origin_cd INT NOT NULL, " \
                               "subdirectories VARCHAR(100), " \
                               "original_file_extension VARCHAR(5), " \
                               "failed_to_save BOOLEAN, " \
                               "posted_on DATETIME);".format(table_name)


# parameters in the methods below are to force user to be aware that values also have to be provided with these queries
def get_recently_posted_images_query(limit):
    recently_posted_images_query = f"SELECT * FROM {table_name} WHERE posted_on IS NOT NULL ORDER BY posted_on DESC LIMIT %s;"
    return recently_posted_images_query, (limit,)


def get_image_by_file_data_query(filename, origin_cd, subdirectories):
    image_by_file_data_query = f"SELECT * FROM {table_name} WHERE filename = %s AND origin_cd = %s and subdirectories = %s;"
    return image_by_file_data_query, (filename, origin_cd, subdirectories)


def get_image_by_id_query(id):
    image_by_id_query = f"SELECT * FROM {table_name} WHERE id = %s;"
    return image_by_id_query, (id,)


# gets a random image from the database that has not been posted yet, and optionally allows the user to provide
# subdirectories to exclude - like, for instance, the last N subdirectories that posts came from, to avoid
# repetitiveness
# TODO maybe modify this to just directly query the last N posts rather than asking the user to provide them
def get_random_fresh_image_query(skip_subdirectories=None):
    select_statement = f"SELECT * FROM {table_name} "

    where_clauses = ["posted_on IS NULL", "failed_to_save != 1"]
    if skip_subdirectories is not None and len(skip_subdirectories) > 0:
        where_clauses.append(
            "subdirectories NOT IN ({0})".format(",".join(["'{0}'".format(x) for x in skip_subdirectories])))

    select_statement += "WHERE {0} ORDER BY RAND() LIMIT 1;".format(" AND ".join(where_clauses))
    return select_statement


class ClipartImage:
    def __init__(self, id=None, filename=None, origin_cd=None, subdirectories=None, original_file_extension=None,
                 failed_to_save=False, posted_on=None):
        self.id = id
        self.filename = filename
        self.origin_cd = origin_cd
        self.subdirectories = subdirectories
        self.original_file_extension = original_file_extension
        self.failed_to_save = failed_to_save
        self.posted_on = posted_on

        # fields only used when actively posting to tumblr; do not need to persist this data in the db
        self.mimetype = self.convert_file_extension_to_mimetype()
        self.original_filename = '{0}.{1}'.format(os.path.splitext(self.filename)[0],
                                                  self.original_file_extension.lower())
        self.alt_text = None

        # workaround to avoid garbage collection when displaying images in GUI app. This will be set when the image is
        # loaded into a tk.PhotoImage object by the PostingApplication class.
        # See that class for more details on this workaround.
        self.current_tk_pic = None

    def __repr__(self):
        return f"ClipartImage(id={self.id}, filename={self.filename}, origin_cd={self.origin_cd}, " \
               f"subdirectories={self.subdirectories}, original_file_extension={self.original_file_extension}, " \
               f"failed_to_save={self.failed_to_save}, posted_on={self.posted_on})"

    def get_insert_statement(self):
        columns = ['filename', 'origin_cd', 'subdirectories', 'original_file_extension', 'failed_to_save']
        values = [self.filename, self.origin_cd, self.subdirectories, self.original_file_extension, self.failed_to_save]
        if self.posted_on is not None:
            columns.append('posted_on')
            values.append(self.posted_on)

        insert_statement = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))});"
        return insert_statement, values

    def get_update_image_mark_corrupted_statement(self):
        update_statement = f"UPDATE {table_name} SET failed_to_save = TRUE WHERE id = %s;"
        return update_statement, (self.id,)

    def get_update_image_mark_posted_statement(self):
        update_statement = f"UPDATE {table_name} SET posted_on = NOW() WHERE id = %s;"
        return update_statement, (self.id,)

    def get_update_image_mark_skipped_statement(self):
        beginning_of_time = dt.datetime.utcfromtimestamp(0)
        update_statement = f"UPDATE {table_name} SET posted_on = %s WHERE id = %s;"
        return update_statement, (beginning_of_time.isoformat(), self.id)

    def convert_file_extension_to_mimetype(self):
        # TODO implement for all file extensions
        name, extension = os.path.splitext(self.filename)
        extension = extension.lower()
        if extension == ".jpg" or extension == ".png":
            return "image/jpeg"
        else:
            raise ValueError(f"Unknown file extension '{extension}' for file {self.filename}")

    def get_converted_image_path(self, main_photo_dir):
        return os.path.join(main_photo_dir, self.subdirectories, self.filename)

    def get_nearby_files(self, main_photo_dir):
        image_path = self.get_converted_image_path(main_photo_dir)
        directory, filename = os.path.split(image_path)
        dir_content = os.listdir(directory)
        file_index = None
        for index, fq_filepath in enumerate(dir_content):
            if fq_filepath == filename:
                file_index = index
                break

        if file_index is None:
            raise ValueError(f"Could not find file {filename} in directory {directory}")

        lower_bound = max(0, file_index - 20)
        upper_bound = min(len(dir_content), file_index + 21)
        return dir_content[lower_bound:file_index] + dir_content[file_index + 1:upper_bound]
