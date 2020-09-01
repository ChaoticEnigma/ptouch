
import math

import qrcode
from PIL import Image, ImageFont, ImageDraw


def rendertext(text, size, font="RobotoCondensed-Bold.ttf"):
    font = ImageFont.truetype(font, size=size)
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
    def __init__(self, title : str, subtitle : str, id : str, qrdata : str, height=128):
        self.title = title
        self.subtitle = subtitle
        self.id = id
        self.qrdata = qrdata
        self.height = height
        self.hspacing = 20
        self.vspacing = 10
        self.padding = 20

    def title_img(self):
        return rendertext(self.title, math.floor(80 * (self.height / 128)), "RobotoCondensed-Bold.ttf")

    def subtitle_img(self):
        return rendertext(self.subtitle, math.floor(36 * (self.height / 128)), "RobotoCondensed-Regular.ttf")

    def id_img(self):
        img = rendertext(self.id, math.floor(24 * (self.height / 128)), "Roboto-Regular.ttf")
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
        assert self.height <= self.height

        # scale QR to fit label height
        scale = self.height // img.size[1]
        nimg = img.resize((img.size[0]*scale, img.size[1]*scale), resample=Image.NEAREST)

        return nimg

    def render(self):
        title = self.title_img()
        title_x = 0
        title_h = title.height

        if self.subtitle:
            subtitle = self.subtitle_img()
            title_w = max(title.width, subtitle.width)
            title_x = (title_w - title.width) // 2
            subtitle_x = (title_w - subtitle.width) // 2
            title_h += subtitle.height + self.vspacing
        else:
            title_w = title.width

        qr_x = title_x + title_w
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
