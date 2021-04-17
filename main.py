 # This Python file uses the following encoding: utf-8
import sys
import os
import requests
import json
import cv2
from PySide2.QtWidgets import QApplication, QWidget, QFileDialog, QLabel, QListWidgetItem
from PySide2.QtCore import QFile, Signal
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QPixmap, QImage
from numpy import ndarray

HOST = ""
REST = [
    "/infer/images",
    "/infer/video",
    "/infer/dicom"
]

FILE_FILTER = [
    {".jpg", ".png", ".bmp"},
    {".jpg", ".png", ".bmp"},
    {".dicom"}
]

def filter_check(string, filter_index):
    for keyword in FILE_FILTER[filter_index]:
        if keyword in string:
            return True
    return False


class Main(QWidget):
    img_signal = Signal(ndarray)
    def __init__(self):
        super(Main, self).__init__()
        self.selected_directory = ""
        self.load_ui()


    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()


    def widget_setting(self):
        self.ui.select_button.clicked.connect(self.slot_select)
        self.ui.img_list.itemActivated.connect(self.slot_item_clicked)
        self.img_signal.connect(self.update_label)


    def slot_select(self):
        self.ui.img_list.clear()
        mode = self.ui.comboBox.currentIndex()
        self.selected_directory = QFileDialog.getExistingDirectory(self, "选择文件所在目录", "")
        for root, dirs, files in os.walk(self.selected_directory):
            for file in files:
                qlwi = QListWidgetItem(file)
                if filter_check(file, mode):
                    self.ui.img_list.addItem(qlwi)
        self.ui.textEdit.setText(self.selected_directory)


    def slot_item_clicked(self):
        mode = self.ui.comboBox.currentIndex()
        file_name = self.ui.img_list.currentItem().text()
        img_path = os.path.join(self.selected_directory, file_name)
        data = {'files': open(img_path, 'rb')}
        url = HOST + REST[mode]
        res = requests.post(url, files=data)
        res_json = json.loads(res.text)
        images = res_json['data']['images']
        img = cv2.imread(img_path)
        for image in images:
            for lesion in image['lesions']:
                x_min = int(lesion['bbox'][0])
                y_min = int(lesion['bbox'][1])
                x_max = int(lesion['bbox'][2])
                y_max = int(lesion['bbox'][3])
                cv2.rectangle(img=img, pt1=(x_min, y_min), pt2=(x_max, y_max), color=(0, 255, 0), thickness=2)
        self.img_signal.emit(img)

    def update_label(self, img_nd):
        img = cv2.cvtColor(img_nd, cv2.COLOR_BGR2RGB)
        image = QImage(img)
        pixmap = QPixmap.fromImage(image)
        self.ui.img_label.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication([])
    widget = Main()
    widget.setWindowTitle("AI预测测试客户端")
    widget.widget_setting()
    widget.show()
    sys.exit(app.exec_())
