
import os
import sys
import logging
import csv

from PySide2.QtCore import QObject, QThread, Signal, Slot
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import QApplication, QLineEdit, QPushButton, QStatusBar, QLabel, QRadioButton, QComboBox
from PySide2.QtUiTools import QUiLoader

from PIL import Image, ImageQt

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
        self.window = loader.load(os.path.dirname(__file__) + "/item_wizard.ui")

        # Find widgets
        for w in get_children(self.window):
            setattr(self, w[1], self.window.findChild(w[0], w[1]))

        # self.thread = QThread()
        # self.worker = Worker(self)
        # self.worker.moveToThread(self.thread)
        # self.thread.start()

        self.data = {}

        try:
            with open("items.csv", "r", newline="") as f:
                csvreader = csv.reader(f)
                for line in csvreader:
                    id, title, subtitle = line
                    id = int(id)
                    self.data[id] = (title, subtitle)
        except:
            pass

        if len(self.data):
            self.next_id = max(self.data.keys()) + 1
        else:
            self.next_id = 1
        self.idEdit.setText(f"{self.next_id:05d}")

        self.comboBox.addItem("New...", None)
        for id, (title, subtitle) in self.data.items():
            print(f"{id} - {title} - {subtitle}")
            self.comboBox.addItem(f"{id:05d}: {title}", id)

        self.update()

        self.titleEdit.textChanged.connect(self.update)
        self.title2Edit.textChanged.connect(self.update)
        self.subtitleEdit.textChanged.connect(self.update)
        self.idEdit.textChanged.connect(self.update)
        self.qrEdit.textChanged.connect(self.update)
        self.tape24mm.toggled.connect(self.update)
        self.radioButton.toggled.connect(self.update)
        self.radioButton_2.toggled.connect(self.update)

        self.comboBox.activated.connect(self.select)
        self.printButton.pressed.connect(self.print)
        # self.worker_print.connect(self.worker.print)

    @Slot(int)
    def select(self, index):
        id = self.comboBox.itemData(index)
        if id is not None:
            title, subtitle = self.data[id]
            self.titleEdit.setText(title)
            self.title2Edit.setText(subtitle)
            self.subtitleEdit.setText(subtitle)
            self.idEdit.setText(f"{id:05d}")
            self.qrEdit.setText(f"https://znnxs.com/item/{id:05d}")

    def params(self):
        title = self.titleEdit.text()
        if self.subtitleEdit.isEnabled():
            subtitle = self.subtitleEdit.text()
            ratio = 0.7
        else:
            subtitle = self.title2Edit.text()
            ratio = 0.5
        id = self.idEdit.text()
        qr = self.qrEdit.text()

        return title, subtitle, id, qr, ratio

    def save(self):
        title, subtitle, id, qr, ratio = self.params()
        id = int(id)
        self.data[id] = (title, subtitle)
        with open("items.csv", "a", newline="") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow([ id, title, subtitle ])
        self.comboBox.addItem(f"{id:05d}: {title}", id)
        self.next_id = id + 1
        self.idEdit.setText(f"{self.next_id:05d}")

    def render(self):
        title, subtitle, id, qr, ratio = self.params()
        size = self.tape24mm.isChecked()
        height = (128 if size else 76)

        label = Label(title, subtitle, id, qr, height=height, title_ratio=ratio)
        return label.render()

    @Slot()
    def update(self):
        img = self.render()
        qimg = ImageQt.ImageQt(img)
        self.imageLabel.setPixmap(QPixmap.fromImage(qimg))

    @Slot()
    def print(self):
        img = self.render()
        self.save()
        # self.worker_print.emit(img)

        try:
            log.info("Open PTouch...")
            with PTD600.open() as ptouch:
                ptouch.log_info()

                if ptouch.tape_px != img.height:
                    raise Exception("Incorrect Tape Size")

                log.info("Printing Label..")
                self.status("Printing Label..")
                ptouch.print_img(img)
                log.info("Done")
                self.status("Done")

        except Exception as e:
            log.exception("Error")
            self.status(str(e))

    @Slot(str)
    def status(self, text):
        self.statusBar.showMessage(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s - %(message)s", stream=sys.stdout)

    app = App(sys.argv)
    app.window.show()
    ret = app.exec_()
