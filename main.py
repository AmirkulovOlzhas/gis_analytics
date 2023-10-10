# import typing
from PyQt5.QtWidgets import QApplication, QMainWindow, \
                            QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QObject, Qt, qInstallMessageHandler, QtMsgType

from ui import Ui_MainWindow
from osmnx_data import show_map
from h3_to_map import gen_hexagons

from multi_thread import Check_City_Thread, Search_City_Thread, Progress_Bar_Thread
import sys, os, io


def custom_message_handler(type, context, message):
    if context.category == QtMsgType.QtWarningMsg and context.object and isinstance(context.object, QObject):
        return  # Игнориовать предупреждения от объектов QObject
    else:
        # Вывести остальные сообщения в терминал
        sys.stderr.write(f'{type} {context.file} {context.line} {context.function} {message}\n')


# обработчик исключений для отображения ошибок
def show_exepction(self=None, e=None, text=None):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    if self is None:
        print(f'Ошибка {exc_type}, {fname}, {exc_tb.tb_lineno}, {e} \n {text}')
    else:
        QMessageBox.warning(self, 'Ошибка', f'{exc_type}, {fname}, {exc_tb.tb_lineno}, {e} \n {text}')


class myWindow(QMainWindow):
    def __init__(self):
        super(myWindow, self).__init__()

        self.city_name = ''
        self.region_name = ''
        self.map_window = None
        self.polygon_krd = None
        self.data_poi = None
        self.score = 0

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_UI()

    def init_UI(self):
        # Титулка
        self.setWindowTitle('GIS Аналитик')
        # Поисковая строка
        self.ui.lineEdit.setPlaceholderText('Қала атауын жазыңыз')

        # кнопка нажатия поиска
        self.ui.pushButton_search.clicked.connect(self.start_city_search)
        self.search_city_thread = Search_City_Thread(window=self)

        # поиск при нажатий Enter
        self.ui.lineEdit.returnPressed.connect(self.activate_button)

        # кнопка открытия карты
        self.ui.pushButton_openmap.clicked.connect(self.open_map)
        # таблица с объектами
        self.ui.tableWidget_city_objects.cellClicked.connect(self.cell_clicked_handler)

        # кнопка для вывода данных города в таблицу
        self.ui.pushButton_check_city.clicked.connect(self.start_check_city)
        self.check_city_thread = Check_City_Thread(window=self)

        self.ui.progressBar.setValue(0)
        self.progress_bar_thread = Progress_Bar_Thread(window=self)


    # Активация кнопки Поиск через enter
    def activate_button(self):
        self.ui.pushButton_search.click()  # Активируем кнопку при нажатии Enter
        

    # Нажатие кнопки Поиск
    def start_city_search(self):
        self.search_city_thread.window = self
        self.search_city_thread.start()

    # Запуск потока для вывода данных города в таблицу
    def start_check_city(self):
        self.check_city_thread.window = self
        self.check_city_thread.start()

    #  открывает карту в новом окне
    def open_map(self, m=None):
        try:
            selected_region = self.ui.listWidget_city.currentItem().text()
            self.map_window = MapWindowWhithMap(self.city_name, selected_region, m)
            self.map_window.show()
        except Exception as e:
            show_exepction(self, e)
    

    # обработчик нажатия на ячейку таблицы
    def cell_clicked_handler(self, row, column):
        item = self.ui.tableWidget_city_objects.item(row, 0)
        if item is not None:
            try:            
                cell_value = item.text()
                # print(f"Выделена ячейка: {cell_value}, {self.region_name}")
                polygon_krd = self.polygon_krd[(self.polygon_krd['name'] == self.region_name)]
                # print(type(polygon_krd))
                # print(polygon_krd)
                self.open_map(gen_hexagons(polygon_krd, self.city_name, cell_value, self.data_poi))
            except Exception as e:
                show_exepction(self, e)
    
        

class MapWindowWhithMap(QWidget):
    def __init__(self, city_name, region_name, m=None):
        print('- - - '*10)
        print(f'MapWindowWhithMap init \nm is {m}\ncity_name is {city_name}\nregion_name is {region_name}')
        print('- - - '*10)
        super().__init__()

        self.setWindowTitle("Карта")
        self.setGeometry(200, 200, 800, 600)
        try:
            if m is None or m is False:
                m = show_map(city_name, region_name)

            layout = QVBoxLayout()
            self.setLayout(layout)

            data = io.BytesIO()
            m.save(data, close_file=False)

            map_widget = QWebEngineView()
            map_widget.setHtml(data.getvalue().decode())

            layout.addWidget(map_widget)
        except Exception as e:
            show_exepction(self=None, e=e)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    qInstallMessageHandler(custom_message_handler)
    application = myWindow()
    application.setFixedSize(800, 600)
    application.show()
    app.exec()

