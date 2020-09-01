
import argparse

import usb1
from ptd600 import PTD600
from label import Label


parser = argparse.ArgumentParser()
parser.add_argument("title")
parser.add_argument("qr", nargs="?", type=str, default="")
parser.add_argument("-S", "--subtitle", type=str, default="")
parser.add_argument("-I", "--id", type=str, default="")
parser.add_argument("-H", "--height", type=int, default=128)
parser.add_argument("-p", "--print", action="store_true")
parser.add_argument("-n", "--no-print", action="store_true")
args = parser.parse_args()

print("Title: %s" % args.title)
print("Subtitle: %s" % args.subtitle)
print("ID: %s" % args.id)
print("QR: %s" % args.qr)

if args.print or args.no_print:
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
                ptouch.info()
                if not args.no_print:
                    print("Printing Label..")
                    label = Label(args.title, args.subtitle, args.id, args.qr, height=ptouch.tape_px)
                    img = label.render()
                    ptouch.print_img(img)

else:
    print("Preview Label...")
    label = Label(args.title, args.subtitle, args.id, args.qr, height=args.height)
    # label = Label("Test Label", "Test Subtitle", "TESTLABL", "https://www.google.com")
    # label = Label("Test Label", "", "", "https://www.google.com")
    img = label.render()
    img.show()
