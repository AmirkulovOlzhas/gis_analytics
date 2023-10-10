from PyQt5.QtWidgets import QTableWidgetItem as qtwi, QMessageBox
from PyQt5.QtCore import QThread, Qt

from h3_to_map import get_data_poi, gen_hexagons
from osmnx_data import get_regions, show_map


import sys, os

def show_exepction(self=None, e=None, text=None):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    if self is None:
        print(f'Ошибка {exc_type}, {fname}, {exc_tb.tb_lineno}, {e} \n {text}')
    else:
        QMessageBox.warning(self, 'Ошибка', f'{exc_type}, {fname}, {exc_tb.tb_lineno}, {e} \n {text}')


class Progress_Bar_Thread(QThread):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.i = 0

    def set_i(self, i):
        self.i = i

    def run(self):
        self.window.ui.progressBar.setValue(self.i)



# Нажатие кнопки Поиск
class Search_City_Thread(QThread):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def run(self):
        self.window.city_name = str(self.window.ui.lineEdit.text())
        try:
            regions, self.window.polygon_krd = get_regions(self.window.city_name)

            self.window.ui.listWidget_city.clear()

            for region in regions:
                self.window.ui.listWidget_city.addItem(region)
        except Exception as e:
            show_exepction(self.window, e, 'Қала атауы дұрыс емес')


# Класс для вывода данных о городе в таблицу в отдельном потоке
class Check_City_Thread(QThread):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def run(self):
        try:
            selected_region = qtwi(self.window.ui.listWidget_city.currentItem().text())

            self.window.ui.tableWidget_city_objects.clear()
            # self.ui.tableWidget_city_objects.setHorizontalHeaderLabels(['Тип', 'Количество'])
            if selected_region is not None:
                self.window.region_name = selected_region.text()
                self.window.data_poi = get_data_poi(self.window.city_name, self.window)
                pd_table = self.window.data_poi.groupby(['type'], as_index = False).agg({'geometry':'count'})

                houses_sum = 0
                other_buildings_sum = 0
                try:
                    houses_sum  += pd_table[pd_table['type'] == 'apartments'] ['geometry'].iloc[0]
                    houses_sum  += pd_table[pd_table['type'] == 'house'] ['geometry'].iloc[0]
                except Exception as e:
                    show_exepction(self=None, e=e)

                
                self.window.ui.tableWidget_city_objects.setRowCount(pd_table.shape[0])
                self.window.ui.tableWidget_city_objects.setColumnCount(pd_table.shape[1])

                for row in range(pd_table.shape[0]):
                    for col in range(pd_table.shape[1]):
                        if col == 1:
                            try:
                                other_buildings_sum += pd_table.iloc[row, col]
                            except:
                                print(col, ' - ', str(pd_table.iloc[row, col]))
                        item = qtwi(str(pd_table.iloc[row, col]))
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)     # неизменяемые ячейки
                        self.window.ui.tableWidget_city_objects.setItem(row, col, item)
                n = houses_sum/(other_buildings_sum-houses_sum)
                if n > 3:
                    n=3
                self.window.score = ((houses_sum / other_buildings_sum)/n)*100
                self.window.ui.result_label.setText(f'Қала үшін балл: {int(self.window.score)}')
                print(f'дома {houses_sum}')
                print(f'другие здания {other_buildings_sum}')
        except:
            show_exepction(self=self.window, text='выберите регион')