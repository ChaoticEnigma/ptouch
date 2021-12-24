
import os
import math
import logging

import qrcode
from PIL import Image, ImageFont, ImageDraw

log = logging.getLogger(__name__)


def rendertext(text, size, font="RobotoCondensed-Bold.ttf"):
    fpath = os.path.dirname(__file__) + "/../font/" + font
    log.debug(f"Load font from {fpath}")
    font = ImageFont.truetype(fpath, size=size)
    text_size = font.getsize(text)
    # print("Text dim: %d x %d" % text_size)

    img_size = (text_size[0], text_size[1])
    img = Image.new("1", img_size, "white")

    button_draw = ImageDraw.Draw(img)
    button_draw.text((0, 0), text, font=font, fill="black")
    # img.show()

    # ImageFont.getsize is wrong a lot, so we have to crop
    non_empty_rows = []
    for y in range(img.height):
        for x in range(img.width):
            if img.getpixel((x, y)) == 0:
                non_empty_rows += [y]
                break
    non_empty_columns = []
    for x in range(img.width):
        for y in range(img.height):
            if img.getpixel((x, y)) == 0:
                non_empty_columns += [x]
                break

    imageBox = (min(non_empty_columns), min(non_empty_rows), max(non_empty_columns)+1, max(non_empty_rows)+1)
    cropped = img.crop(imageBox)
    return cropped


class Label:
    def __init__(self, title : str, subtitle : str, id : str, qrdata : str, height : int = 128, subtitle_ratio : float = 1):
        self.title = title
        self.subtitle = subtitle
        self.total_font_size = 120
        self.subtitle_ratio = subtitle_ratio
        self.id = id
        self.qrdata = qrdata
        self.height = height
        self.hspacing = 20
        self.vspacing = 10
        self.padding = 10
        self.max_height = 128

    def title_img(self):
        font_size = min(80, (self.total_font_size / 2) + ((1 - self.subtitle_ratio) * self.total_font_size / 2))
        return rendertext(self.title, math.floor(font_size * (self.height / self.max_height)), "RobotoCondensed-Bold.ttf")

    def subtitle_img(self):
        font_size = (self.total_font_size / 2) * self.subtitle_ratio
        if font_size >= 50:
            return rendertext(self.subtitle, math.floor(font_size * (self.height / self.max_height)), "RobotoCondensed-Bold.ttf")
        else:
            return rendertext(self.subtitle, math.floor(font_size * (self.height / self.max_height)), "RobotoCondensed-Regular.ttf")

    def id_img(self):
        img = rendertext(self.id, math.floor(24 * (self.height / self.max_height)), "Roboto-Regular.ttf")
        rot = img.transpose(Image.ROTATE_90)
        return rot

    def qr_img(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=0,
        )
        qr.add_data(self.qrdata)
        qr.make(fit=True)

        img = qr.make_image()

        # scale QR to fit label height
        scale = self.height // img.size[1]
        nimg = img.resize((img.size[0]*scale, img.size[1]*scale), resample=Image.NEAREST)

        return nimg

    def render(self):
        title = self.title_img()
        title_x = self.padding
        subtitle_x = self.padding
        title_h = title.height

        if self.subtitle:
            subtitle = self.subtitle_img()
            title_w = max(title.width, subtitle.width)
            title_x += (title_w // 2) - (title.width // 2)
            subtitle_x += (title_w // 2) - (subtitle.width // 2)
            title_h += subtitle.height + self.vspacing
        else:
            title_w = title.width

        qr_x = title_w + self.padding
        qr_w = 0

        if self.qrdata:
            qr = self.qr_img()
            qr_x += self.hspacing
            qr_w = qr.width

        id_x = qr_x + qr_w
        id_w = 0

        if self.id:
            id = self.id_img()
            if not self.qrdata:
                id_x += self.hspacing
            else:
                id_x += self.vspacing
            id_w = id.width

        total_w = id_x + id_w + self.padding

        img = Image.new("1", (total_w, self.height), "white")
        img.paste(title, (title_x, (self.height - title_h) // 2))

        if self.subtitle:
            img.paste(subtitle, (subtitle_x, (self.height - title_h) // 2 + (title_h - subtitle.height)))

        if self.qrdata:
            img.paste(qr, (qr_x, (self.height - qr.height) // 2))

        if self.id:
            img.paste(id, (id_x, (self.height - id.height) // 2))

        return img
