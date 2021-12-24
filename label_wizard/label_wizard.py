
import os
import sys
import logging

from PySide2.QtCore import QObject, QThread, Signal, Slot
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import QApplication, QLineEdit, QPushButton, QStatusBar, QLabel, QRadioButton
from PySide2.QtUiTools import QUiLoader

from PIL import Image, ImageQt
import usb1

from ptouch.label import Label
from ptouch.ptd600 import PTD600

log = logging.getLogger(__name__)


def get_children(widget):
    for obj in widget.children():
        name = obj.objectName()
        classname = obj.metaObject().className()
        # Get all named children
        if len(name):
            try:
                # Ignore children with unknown (Qt internal) types
                typ = getattr(sys.modules[__name__], classname)
                yield (typ, name)
            except AttributeError:
                # print("Unknown Widget Type: %s" % classname)
                pass
        yield from get_children(obj)


class Worker(QObject):
    gui_status = Signal(str)

    def __init__(self, parent):
        # QObject must not have a parent on the main thread, or
        # the object cannot be moved to the worker thread
        super(Worker, self).__init__(None)
        self.app = parent

        self.gui_status.connect(self.app.status)

    @Slot(Image.Image)
    def print(self, img):
        try:
            log.info("Open PTouch...")
            with PTD600.open() as ptouch:
                ptouch.log_info()

                if ptouch.tape_px != img.height:
                    raise Exception("Incorrect Tape Size")

                log.info("Printing Label..")
                self.gui_status.emit("Printing Label..")
                ptouch.print_img(img)
                log.info("Done")
                self.gui_status.emit("Done")

        except Exception as e:
            log.exception("Error")
            self.gui_status.emit(str(e))


class App(QApplication):
    worker_print = Signal(Image.Image)

    def __init__(self, argv):
        super(App, self).__init__(argv)

        # Load UI
        loader = QUiLoader()
        self.window = loader.load(os.path.dirname(__file__) + "/label_wizard.ui")

        # Find widgets
        for w in get_children(self.window):
            setattr(self, w[1], self.window.findChild(w[0], w[1]))

        self.thread = QThread()
        self.worker = Worker(self)
        self.worker.moveToThread(self.thread)
        self.thread.start()

        self.update()

        self.titleEdit.textChanged.connect(self.update)
        self.subtitleEdit.textChanged.connect(self.update)
        self.idEdit.textChanged.connect(self.update)
        self.qrEdit.textChanged.connect(self.update)
        self.tape24mm.toggled.connect(self.update)

        self.printButton.pressed.connect(self.print)
        self.worker_print.connect(self.worker.print)

    def render(self):
        title = self.titleEdit.text()
        subtitle = self.subtitleEdit.text()
        id = self.idEdit.text()
        qr = self.qrEdit.text()
        size = self.tape24mm.isChecked()
        height = (128 if size else 76)

        label = Label(title, subtitle, id, qr, height=height)
        return label.render()

    def update(self):
        img = self.render()
        qimg = ImageQt.ImageQt(img)
        self.imageLabel.setPixmap(QPixmap.fromImage(qimg))

    def print(self):
        img = self.render()
        self.worker_print.emit(img)

    @Slot(str)
    def status(self, text):
        self.statusBar.showMessage(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s - %(message)s", stream=sys.stdout)

    app = App(sys.argv)
    app.window.show()
    ret = app.exec_()
