import json
import tkinter as tk

from pycode.objects.clipart_image import ClipartImage


class TumblrPost:
    def __init__(self, images, config):
        if isinstance(images, ClipartImage):
            self.images = [images]
        elif (isinstance(images, list) or isinstance(images, tuple)) and \
                all(isinstance(x, ClipartImage) for x in images):
            self.images = list(images)
        else:
            raise ValueError("'images' param must be a ClipartImage or list of ClipartImages")
        self.attribution = config.get_standard_attribution()
        self.image_base_location = config.get_image_base_dir()
        self.publish_state = config.get_default_post_state()

        # these vars are set in the GUI, so they're stored in tkinter variables for easier access, but are still used
        # in the command line version
        self.title = tk.StringVar()
        self.caption = tk.StringVar()
        self.tags = tk.StringVar()
        self.tags.set(','.join(config.get_standard_tags()))  # pre-populate with default tags

        self.validate()

    def set_tags(self, tags):
        if isinstance(tags, list) or isinstance(tags, tuple):
            tags = ','.join(tags)
        self.tags.set(self.tags.get() + ',' + tags)

    def validate(self):
        if len(self.images) == 0:
            raise Exception("No images to post!")
        elif len(self.images) > 1:
            origin_cd = self.images[0].origin_cd
            subdirectories = self.images[0].subdirectories
            for image in self.images[1:]:
                if image.origin_cd != origin_cd or image.subdirectories != subdirectories:
                    raise Exception("Images must be from the same CD and directory")

    def get_formatted(self):
        post_data = {}
        content = []
        for image in self.images:
            image_identifier = f"image_{image.id}"
            post_data[image_identifier] = (image_identifier,
                                           open(image.get_converted_image_path(self.image_base_location), 'rb'),
                                           image.mimetype,
                                           {'Expires': '0'})
            content.append({
                "type": "image",
                "media": [{"type": image.mimetype, "identifier": image_identifier}],
                "alt_text": image.alt_text.get(),
                "caption": image.original_filename
            })

        commentary_string = f"\nFrom Disc #{self.images[0].origin_cd}, '{self.images[0].subdirectories}' directory"

        if self.caption.get() != '':
            commentary_string += "\n" + self.caption.get()

        content.append({
            "type": "text",
            "text": commentary_string
        })

        content.append({
            "type": "text",
            "text": self.attribution,
            "formatting": [
                {
                    "start": 0,
                    "end": len(self.attribution),
                    "type": "small"
                }
            ]
        })

        layout = {
            "type": "rows",
            "display": [
                {"blocks": [x for x in range(len(self.images))]},  # images
                {"blocks": [len(self.images)]},  # description
                {"blocks": [len(self.images) + 1]}  # attribution
            ]
        }
        print(layout)

        blob = {
            'state': self.publish_state,
            'tags': self.tags.get(),
            "content": content,
            "layout": [layout]
        }
        print(json.dumps(blob, separators=(',', ':'), indent=4))
        post_data['json'] = (None, json.dumps(blob, separators=(',', ':')), 'application/json')

        return post_data

    def add_image_from_record(self, db_record):
        image_obj = ClipartImage(*db_record)
        self.images.append(image_obj)
        self.validate()
