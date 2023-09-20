import json

from pycode.objects.clipart_image import ClipartImage


class TumblrPost:
    def __init__(self, images, config):
        if isinstance(images, ClipartImage):
            self.images = [images]
        elif (isinstance(images, list) or isinstance(images, tuple)) and \
                all(isinstance(x, ClipartImage) for x in images):
            self.images = images
        else:
            raise ValueError("'images' param must be a ClipartImage or list of ClipartImages")
        self.images = images
        self.attribution = config.get_standard_attribution()
        self.caption = ""
        self.tags = config.get_standard_tags()
        self.publish_state = config.get_default_post_state()
        self.validate()

    def add_user_input(self):
        self.caption = input("What should the caption be for this post? (Leave blank for none)")
        tag_input = input("Enter any additional tags beyond the standard set that you want to add to this post. "
                          "Leave blank for none.")
        if tag_input != '':
            self.tags += "," + ",".join([x.strip() for x in tag_input.split(',')])

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
            post_data[image_identifier] = (image_identifier, open(image.get_converted_image_path(), 'rb'),
                                              image.mimetype, {'Expires': '0'})
            content.append({
                "type": "image",
                "media": [{"type": image.mimetype, "identifier": image_identifier}],
                "alt_text": image.alt_text
            })
            content.append({
                "type": "text",
                "text": image.original_filename
            })

        content.append({
            "type": "text",
            "text": f"From Disc #{self.images[0].origin_cd}, '{self.images[0].subdirectories}' directory"
        })
        if self.caption != '':
            content.append({
                "type": "text",
                "text": self.caption
            })
        content.append({
            "type": "text",
            "text": self.attribution
        })

        post_data['json'] = (None, json.dumps({
            "state": self.publish_state,
            "tags": self.tags,
            "content": content,
            "source_url": "https://archive.org/details/masterclips-cd-pack",
        }, separators=(',', ':')), 'application/json')

        return post_data

    def add_image_from_record(self, db_record):
        image_obj = ClipartImage(**db_record)
        self.images += image_obj
        self.validate()
