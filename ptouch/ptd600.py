
import time
import struct
import logging
from typing import NamedTuple

import usb1
from PIL import Image

log = logging.getLogger(__name__)

tape_sizes = {
    6:  (32, 48+6),
    9:  (52, 38+6),
    12: (76, 26+5),
    18: (120, 4+6),
    24: (128, 0),
}


class ptouch_status(NamedTuple):
    printheadmark: int  # 0x80
    size: int           # 0x20
    brother_code: int   # "B"
    series_code: int    # "0"
    model: int
    country: int        # "0"
    reserved_1: int
    error: int          # table 1 and 2
    media_width: int    # tape width in mm
    media_type: int     # table 4
    ncol: int           # 0
    fonts: int          # 0
    jp_fonts: int       # 0
    mode: int
    density: int        # 0
    media_len: int      # table length, always 0
    status_type: int    # table 5
    phase_type: int
    phase_number: int   # table 6
    notif_number: int
    exp: int            # 0
    tape_color: int     # table 8
    text_color: int     # table 9
    hw_setting: int


class PTD600:
    VID = 0x04f9
    PID = 0x2074
    INTF = 0
    SEND_EP = 0x02
    RECV_EP = 0x81

    def __init__(self, handle : usb1.USBDeviceHandle):
        self.handle = handle
        self.status = None
        self.max_px = 128
        self.tape_px = 0
        self.tape_offset = 0

        self.init()
        self.getstatus()

    def init(self):
        cmd = b'\x1b\x40' # 1B 40 = ESC @ = INIT
        self.handle.bulkWrite(self.SEND_EP, cmd)

    def getstatus(self):
        # 1B 69 53 = ESC i S = Status info request
        self.handle.bulkWrite(self.SEND_EP, b'\x1biS')
        time.sleep(0.1)
        buf = self.handle.bulkRead(self.RECV_EP, 32)
        assert len(buf) == 32
        # print(buf.hex())
        assert buf[0] == 0x80 and buf[1] == 0x20
        self.status = ptouch_status(*struct.unpack("BBBBBBHHBBBBBBBBBBHBBBBI", buf))
        self.tape_px, self.tape_offset = tape_sizes[self.status.media_width]

    def log_info(self):
        log.info("Tape: %dmm, %dpx" % (self.status.media_width, self.tape_px))
        colors = {
            1: "White",
            8: "Black",
        }
        log.info("Color: %d, %d" % (self.status.tape_color, self.status.text_color))

    def make_rasterlines(self, img : Image):
        assert img.height == self.tape_px
        assert img.mode == "1"


        for x in range(img.width):
            rasterline = bytearray([0x00] * (self.max_px // 8))

            # pack pixels into raster bits
            for y in range(img.height):
                # val = img.getpixel((x, img.height - 1 - y))
                # if val == 0:
                #     rasterline[(len(rasterline)-1) - (y//8)] |= (1 << (y%8))

                val = img.getpixel((x, y))
                sy = y + self.tape_offset
                if val == 0:
                    rasterline[(sy//8)] |= (1 << (7-(sy%8)))

            yield bytes(rasterline)

    def print_img(self, img : Image.Image):
        assert img.height == self.tape_px
        assert img.mode == "1"

        # 4D 00 = disable compression
        # 4D 02 = enable packbits compression mode
        self.handle.bulkWrite(self.SEND_EP, b'M\x02')

        # 1B 69 52 01 = ESC i R 01 = Select graphics transfer mode = Raster
        self.handle.bulkWrite(self.SEND_EP, b'\x1biR\x01')

        for rasterline in self.make_rasterlines(img):
            # 47 = send raster line
            cmd = b'\x47' + bytes([len(rasterline) + 1, 0x00, len(rasterline) - 1]) + rasterline
            self.handle.bulkWrite(self.SEND_EP, cmd)

        # 1A = eject and cut tape
        self.handle.bulkWrite(self.SEND_EP, b'\x1a')


if __name__ == "__main__":
    # img = Image.open("test_76.png")
    img = Image.open("test_128.png")
    img = img.convert("1")
    # img.show()

    pimg = Image.new("1", (img.width + 40, img.height), "white")
    pimg.paste(img, (20, 0))

    with usb1.USBContext() as context:
        handle = context.openByVendorIDAndProductID(PTD600.VID, PTD600.PID)
        if handle is None:
            # Device not present, or user is not allowed to access device.
            print("Unable to open PTD600")
        else:
            try:
                handle.detachKernelDriver(PTD600.INTF)
            except:
                pass

            with handle.claimInterface(PTD600.INTF):
                # Do stuff with endpoints on claimed interface.
                print("Opened PTD600")

                ptouch = PTD600(handle)
                ptouch.log_info()

                ptouch.print_img(pimg)
