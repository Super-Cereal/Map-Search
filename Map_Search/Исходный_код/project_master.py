import sys
import os
import requests
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QByteArray
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from data.project_interface import Ui_MainWindow


def resource_path(relative_path):
    # первый return - для запуска в idle
    # второй return - для сборки .exe файла
    return os.path.join('data', relative_path)
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


class Interface(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon(resource_path('project.ico')))
        self.map_edit.setChecked(True)
        self.image.setPixmap(QPixmap(resource_path('karina.jpeg')))
        self.find_by_coords_btn.clicked.connect(self.update_params_by_coords)
        self.find_by_name_btn.clicked.connect(self.update_params_by_name)
        self.show_address_edit.clicked.connect(self.update_adress)
        self.show_postal_code_edit.clicked.connect(self.update_adress)
        self.map_edit.clicked.connect(self.update_map_type)
        self.sat_edit.clicked.connect(self.update_map_type)
        self.trf_edit.clicked.connect(self.update_map_type)
        self.skl_edit.clicked.connect(self.update_map_type)
        self.clear_all_btn.clicked.connect(self.clear_all)

        self.current_toponym = None
        self.map_params = {
            "ll": None,
            "l": 'map',
            "spn": '0.002,0.002',
            "size": '450,450',
            "pt": ''
        }

    def show_map(self):
        if self.map_params['ll'] is None:
            return
        response = requests.get(static_map_api_server, params=self.map_params)
        if not response:
            QMessageBox.about(self, 'Error', '''Ошибка выполнения запроса:\n{}\nHttp статус: {} ({})'''.format(response.url, response.status_code, response.reason))
            self.map_params['ll'] = None
            self.image.setPixmap(QPixmap(resource_path('karina.jpeg')))
        else:
            pix = QPixmap()
            pix.loadFromData(QByteArray(response.content))
            self.image.setPixmap(pix)

    def update_params_by_coords(self):
        try:
            self.map_params['ll'] = self.map_params['pt'] = f'{float(self.long_edit.text())},{float(self.lat_edit.text())}'
        except Exception:
            QMessageBox.about(self, 'Error', 'Неправильный формат записи координат')
            return
        self.current_toponym = None
        self.map_params['spn'] = '0.002,0.002'
        self.update_adress()
        self.show_map()

    def update_params_by_name(self):
        if not self.name_edit.text():
            QMessageBox.about(self, 'Error', 'Вы ничего не ввели')
            return
        elem = self.take_geocode_request(self.name_edit.text())
        if elem:
            self.current_toponym = elem
            self.map_params['ll'] = self.map_params['pt'] = ','.join(elem['Point']['pos'].split())
            self.map_params['spn'] = '0.002,0.002'
            self.update_adress()
            self.show_map()

    def update_map_type(self):
        res = []
        if self.sat_edit.isChecked():
            res.append('sat')
        if self.map_edit.isChecked():
            res.append('map')
        if self.trf_edit.isChecked():
            res.append('trf')
        if self.skl_edit.isChecked():
            res.append('skl')
        self.map_params['l'] = ','.join(res)
        self.show_map()

    def update_adress(self):
        if not self.show_address_edit.isChecked():
            self.address_text.clear()
            return
        if self.current_toponym is None:
            if not self.map_params['pt']:
                return
            response = self.take_geocode_request(self.map_params['pt'])
            if not response:
                self.address_text.setText('Ошибка')
                return
            else:
                self.current_toponym = response
        elem = self.current_toponym
        text = elem['metaDataProperty']['GeocoderMetaData']['Address']['formatted']
        if self.show_postal_code_edit.isChecked():
            try:
                text += '\n\nПочтовый индекс: ' + elem['metaDataProperty']['GeocoderMetaData']['Address']['postal_code']
            except KeyError:
                text += '\n\nПочтовый индекс: не существует'
        self.address_text.setText(text)

    def clear_all(self):
        self.map_params['ll'] = None
        self.map_params['l'] = 'map',
        self.map_params['pt'] = ''
        self.map_params['spn'] = '0.002,0.002'
        self.current_toponym = None
        self.image.setPixmap(QPixmap(resource_path('karina.jpeg')))
        self.long_edit.clear()
        self.lat_edit.clear()
        self.name_edit.clear()
        self.show_address_edit.setChecked(False)
        self.show_postal_code_edit.setChecked(False)
        self.address_text.clear()
        self.sat_edit.setChecked(False)
        self.map_edit.setChecked(True)
        self.skl_edit.setChecked(False)
        self.trf_edit.setChecked(False)

    def move(self, direct):
        ll0, ll1 = map(float, self.map_params['ll'].split(','))
        spn = float(self.map_params['spn'].split(',')[0])
        if direct == 'l':
            ll0 -= spn
        elif direct == 'r':
            ll0 += spn
        elif direct == 'u':
            ll1 += spn / 2
        elif direct == 'd':
            ll1 -= spn / 2
        self.map_params['ll'] = f'{ll0},{ll1}'
        self.show_map()

    def scale(self, direct):
        spn = float(self.map_params['spn'].split(',')[0])
        if direct == 'u':
            spn /= 2
        elif direct == 'd':
            spn *= 2
        if 0.0003 < spn < 100:
            self.map_params['spn'] = f'{spn},{spn}'
            self.show_map()

    def take_geocode_request(self, text):
        geocode_params = {
            'geocode': text,
            'apikey': geocoder_apikey,
            'format': 'json'
        }
        response = requests.get(geocoder_api_server, geocode_params)
        if not response:
            QMessageBox.about(self, 'Error', '''Ошибка выполнения запроса:\n{}\nHttp статус: {} ({})'''.format(response.url, response.status_code, response.reason))
            return False
        else:
            try:
                return response.json()['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']
            except IndexError:
                QMessageBox.about(self, 'Error', 'Такого адреса не существует')
                return False

    def keyPressEvent(self, e):
        if self.map_params['ll'] is None:
            return
        if e.key() == 16777238:
            self.scale('u')
        elif e.key() == 16777239:
            self.scale('d')
        elif e.key() == 16777234:
            self.move('l')
        elif e.key() == 16777235:
            self.move('u')
        elif e.key() == 16777236:
            self.move('r')
        elif e.key() == 16777237:
            self.move('d')


geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"
static_map_api_server = "http://static-maps.yandex.ru/1.x/"
search_api_server = "http://search-maps.yandex.ru/v1/"
geocoder_apikey = "40d1649f-0493-4b70-98ba-98533de7710b"
search_apikey = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

if __name__ == "__main__":
    if True:
        app = QApplication(sys.argv)
        interface = Interface()
        interface.show()
        sys.exit(app.exec())
