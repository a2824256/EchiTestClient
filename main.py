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
import PySide2

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

CLASSES_MAPPER_CONFIG = {
    0: ['CL', (0, 255, 0)],
    1: ['CE1', (255, 0, 0)],
    2: ['CE2', (0, 0, 255)],
    3: ['CE3', (0, 255, 255)],
    4: ['CE4', (46, 139, 87)],
    5: ['CE5', (218, 165, 32)],
    6: ['AE1', (255, 140, 0)],
    7: ['AE2', (255, 99, 71)],
    8: ['AE3', (255, 0, 255)]
}

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
        self.label_path = ""
        self.use_label = False
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
        self.ui.clean_area_button.clicked.connect(self.clear_ultrasonic_area)
        self.img_signal.connect(self.update_label)
        self.ui.select_file_button.clicked.connect(self.select_label_file)


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

    def select_label_file(self):
        filename = QFileDialog.getOpenFileName(self, "选取文件")[0]
        self.label_path = filename
        self.ui.label_file_path.setText(filename)
        self.use_label = True

    def clear_ultrasonic_area(self):
        self.ui.xMinBox.setText('')
        self.ui.yMinBox.setText('')
        self.ui.xMaxBox.setText('')
        self.ui.yMaxBox.setText('')

    def label_format_mapper(self, index, path, key):
        res = None
        if index == 0:
            res = self.load_echi_format(path, key)
        return res

    # TODO 有多个label
    def load_echi_format(self, path, key):
        bbox = []
        for line in open(path, "r", encoding="utf-8"):
            if key in line:
                arr = line[:-1].split(" ")
                bbox.append(arr)
        return bbox


    def slot_item_clicked(self):
        mode = self.ui.comboBox.currentIndex()
        file_name = self.ui.img_list.currentItem().text()
        img_path = os.path.join(self.selected_directory, file_name)
        x_min = self.ui.xMinBox.toPlainText()
        y_min = self.ui.yMinBox.toPlainText()
        x_max = self.ui.xMaxBox.toPlainText()
        y_max = self.ui.yMaxBox.toPlainText()
        files = {}
        data = {}
        res = None
        url = HOST + REST[mode]
        if x_min != '' and y_min != '' and x_max != '' and y_max != '':
            pointPairList_json = '{"pointPair":[{"minPoint":{"x":' + str(x_min) + ',"y":' + str(y_min) + '},"maxPoint":{"x":' + str(x_max) + ',"y":' + str(y_max) + '}}]}'
            data = {'files': open(img_path, 'rb')}
            files = {'pointPairList': pointPairList_json}
            res = requests.post(url, files=files, data=data)
        else:
            files = {'files': open(img_path, 'rb')}
            res = requests.post(url, files=files)
        self.ui.outputBox.setText(res.text)
        res_json = json.loads(res.text)
        images = res_json['data']['images']
        img = cv2.imread(img_path)
        if self.use_label:
            label_type = self.ui.dataTypeComboBox.currentIndex()
            arr = file_name.split(" ")
            bbox_arr = self.label_format_mapper(label_type, self.label_path, arr[0])
            for bbox in bbox_arr:
                cv2.rectangle(img=img, pt1=(int(bbox[2]), int(bbox[3])), pt2=(int(bbox[4]), int(bbox[5])), color=(0, 0, 255), thickness=2)
                cv2.putText(img, bbox[1], (int(bbox[2]), int(bbox[3])-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        if len(img.shape) == 3:
            channel = img.shape[2]
            self.ui.channelBox.setText(str(channel) + '通道')
        elif len(img.shape) == 2:
            self.ui.channelBox.setText('单通道')
        else:
            self.ui.channelBox.setText('未知')
        height = img.shape[0]
        width = img.shape[1]
        self.ui.widthBox.setText(str(width))
        self.ui.heightBox.setText(str(height))
        for image in images:
            for lesion in image['lesions']:
                x_min = int(lesion['bbox'][0])
                y_min = int(lesion['bbox'][1])
                x_max = int(lesion['bbox'][2])
                y_max = int(lesion['bbox'][3])
                class_id = int(lesion['class'])
                class_name = CLASSES_MAPPER_CONFIG[class_id][0]
                class_color = CLASSES_MAPPER_CONFIG[class_id][1]
                conf = str(lesion['conf'])
                text = class_name + ':' + conf
                cv2.rectangle(img=img, pt1=(x_min, y_min), pt2=(x_max, y_max), color=class_color, thickness=2)
                cv2.putText(img, text, (x_min, y_min-5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, class_color, 2)
        self.img_signal.emit(img)

    def update_label(self, img_nd):
        img = cv2.cvtColor(img_nd, cv2.COLOR_BGR2RGB)
        height, width, bytesPerComponent = img.shape
        bytesPerLine = bytesPerComponent * width
        image = QImage(img.data, width, height, bytesPerLine, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        pixmap = pixmap.scaled(861, 701, PySide2.QtCore.Qt.KeepAspectRatio, PySide2.QtCore.Qt.SmoothTransformation)
        self.ui.img_label.setPixmap(pixmap)


if __name__ == "__main__":
    app = QApplication([])
    widget = Main()
    widget.setWindowTitle("AI预测测试客户端")
    widget.widget_setting()
    widget.show()
    sys.exit(app.exec_())
