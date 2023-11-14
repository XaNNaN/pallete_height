# Чтение и обработка таблицы с типами коробок
import pandas as pd

# Библиотека для размещения прямоугольников
from rectpack import *


# Для разделения коробок на группы по высоте
from itertools import groupby

# Отладка принтами на максималке
from icecream import ic
ic.disable()

# Параметры самого поддона
HEIGHT = 150
LENGTH = 1200
WIDTH = 800


class Box:
    def __init__(self, length: float, width: float, height: float, packs_in_row: int, pack_type='Unknown'):
        self.length = int(length)
        self.width = int(width)
        self.height = int(height)
        self.area = self.rectangle_area(length, width)
        self.packs_in_row = packs_in_row
        self.volume = self.parallelepiped_volume(length, width, height)
        self.pack_type = pack_type

    @staticmethod
    def rectangle_area(length: float, width: float) -> float:
        return length * width

    @staticmethod
    def parallelepiped_volume(length: float, width: float, height: float) -> float:
        return length * width * height

    def __repr__(self):
        return f'  Pack_type:\t{self.pack_type}  {self.height}'
    #     return f'\nBox\n' \
    #            f'  Pack type:\t{self.pack_type}\n' \
    #            f'  Length:\t{self.length}\n' \
    #            f'  Width:\t{self.width}\n' \
    #            f'  Height:\t{self.height}\n' \
    #            f'  Area:     {self.area}\n' \
    #            f'  Volume:\t{self.volume}\n'

    def __getitem__(self, item):
        #  Да, да. Да, да...
        return self.pack_type


class Pallet:
    def __init__(self, length: float, width: float, boxes: list, pack_counter: list):
        self.length = length
        self.width = width
        self.area = self.rectangle_area(length, width)
        self.boxes = sorted(boxes, key=self.sort_by_height)
        self.lines = []
        self.total_height = HEIGHT
        self.box_counter = pack_counter
        self.total_boxes = sum(pack_counter)

    @staticmethod
    def rectangle_area(length: float, width: float) -> float:
        return length * width

    @staticmethod
    def sort_by_height(box: list) -> float:
        return box.height

    def __repr__(self):
        return f'Pallet\n' \
               f'  Length:\t{self.length}\n' \
               f'  Width:\t{self.width}\n' \
               f'  Boxes:\t{self.boxes}\n'

    def build_pallet(self) -> float:
        self._build_full_lines()
        print(f"Prebuilded height: {self.total_height}")
        while self.total_boxes > 0:
            self._build_line()
        print(f"Pallet height: {self.total_height}")

        return self.total_height

    def _build_full_lines(self):
        for idx, box in enumerate(self.boxes):
            if self.box_counter[idx] >= box.packs_in_row:
                full_lines = int(self.box_counter[idx]) // int(box.packs_in_row)
                self.total_height += full_lines * box.height
                self.box_counter[idx] -= full_lines * int(box.packs_in_row)
                self.total_boxes -= full_lines * int(box.packs_in_row)

    def _build_line(self):
        cur_line_boxes, line_height = self._fill_line()
        self.total_height += line_height
        self.lines.append(cur_line_boxes)
        self.total_boxes = sum(self.box_counter)

    def _fill_line(self):
        def nearest_value(values: set, one: int) -> int:
            return min(values, key=lambda n: (abs(one - n), n))

        # Разделим коробки по высоте при помощи groupby.
        def key_func(box):
            """
            Separator function for itertools.groupby.
            Returns the decimal representation of box.height with the three least significant bits zeroed out.
            Which allows you to divide the height packages into 7 mm ranges.

            :param box: An object of the Box class for which a group is required to be defined.
            :return: Decimal representation of box.height with the three least significant bits zeroed out.
            """
            return 2 ** 32 - 1 << 3 & int(box.height)

        groups = []
        unique_keys = []
        boxes = [box for box, b_count in zip(self.boxes, self.box_counter) if b_count > 0]
        for k, g in groupby(boxes, key=key_func):
            groups.append(list(g))
            unique_keys.append(k)

        # Теперь создадим набор прямоугольников из первой группы.
        # Для нахождения объекта коробки(Box) и количества таких коробок на паллете будем хранить их общий индекс \
        # В словаре soup_dict.
        # WARNING! Возможна коллизия по индексу, если у разных коробок одинаковые ширина и длина + они в одной группе
        packs_idx = []
        rectangles = []
        soup_dict = {}
        total_area = 0
        soup_list = []
        for pack in groups[0]:
            pack_idx = self.boxes.index(pack)
            if self.box_counter[pack_idx] > 0:
                total_area += self.boxes[pack_idx].area * self.box_counter[pack_idx]
                packs_idx.append(pack_idx)
                soup_dict[(pack.length, pack.width)] = pack_idx
                for _ in range(self.box_counter[pack_idx]):
                    soup_list.append(pack_idx)
                    rectangles.append((pack.length, pack.width))
        # А также создадим набор из прямоугольников, в которые нужно вписать остальные.
        n_bins = int(total_area / self.area)
        if total_area % self.area != 0:
            n_bins += 1
        bin = [(self.length, self.width) for _ in range(n_bins)]
        #  Костыль для размещения однотипных прямоугольников
        if len(groups[0]) == 1 and groups[0][0].area * self.box_counter[soup_list[0]] / self.area >= 0.80:
            self.box_counter[soup_list[0]] = 0
            line_height = groups[0][0].height
            return groups[0], line_height

        bin_algo = PackingBin.BFF
        pack_algo = MaxRectsBlsf
        packer = newPacker(bin_algo=bin_algo, pack_algo=pack_algo, rotation=True)

        # Add the rectangles to packing queue
        for r, box_index in zip(rectangles, soup_list):
            packer.add_rect(*r, rid=box_index)
            # packer.add_rect(*r)

        # Add the bins where the rectangles will be placed
        for b in bin:
            packer.add_bin(*b)

        # Start packing
        packer.pack()

        # После размещения посмотрим на "плотность" каждого слоя.
        area = 0
        lines_density = []
        for line in packer:
            counter = 0
            for rect in line:
                area += rect.width * rect.height
                counter += 1
            lines_density.append(area / self.area)
            # print(f"Density: {area / self.area}")
            # print(f"Rectcount in line: {counter}")
            area = 0

        area_last = 0
        # Считаем площадь занимаюмаю всеми прямоугольниками в последнем бине.
        for rect in packer[-1]:
            area_last += rect.width * rect.height
        # Если последний слой заполнен недостаточно плотно, то прямоугольники в нём должны быть добавлены в другю группу

        packer_rect_sum = 0
        for bin in packer:
            packer_rect_sum += len(bin)

        while packer_rect_sum != len(rectangles):
            packer_rect_sum = 0
            # Увеличение количества слоёв на один
            n_bins += 1
            bin = [(self.length, self.width) for _ in range(n_bins)]

            packer = newPacker(bin_algo=bin_algo, pack_algo=pack_algo, rotation=True)

            # Add the rectangles to packing queue
            for r, box_index in zip(rectangles, soup_list):
                packer.add_rect(*r, rid=box_index)
                # packer.add_rect(*r)

            # Add the bins where the rectangles will be placed
            for b in bin:
                packer.add_bin(*b)

            # Start packing
            packer.pack()

            for bin in packer:
                packer_rect_sum += len(bin)

        # После размещения посмотрим на "плотность" каждого слоя.
        area = 0
        lines_density = []
        for line in packer:
            counter = 0
            for rect in line:
                area += rect.width * rect.height
                counter += 1
            lines_density.append(area / self.area)
            # print(f"Density: {area / self.area}")
            # print(f"Rectcount in line: {counter}")
            area = 0

        packer_0_len = len(packer[0])
        if area_last / self.area < 0.70 and len(packer[0]) != self.total_boxes:
            # print(f"Last line area is small, density: {area / self.area}")
            line_height = (len(packer) - 1) * groups[0][0].height
            idxs = []
            for rect in packer[-1]:
                # if (rect.height, rect.width) in soup_dict.keys():
                #     idx = soup_dict[(rect.height, rect.width)]
                # else:
                #     idx = soup_dict[(rect.width, rect.height)]
                idx = rect.rid
                idxs.append(idx)
                self.box_counter[idx] -= 1
            for idx in set(idxs):
                heights = set([i.height for i in self.boxes if i.height != self.boxes[idx].height])
                if heights == set():
                    line_height = groups[0][0].height
                else:
                    nearest_height = nearest_value(heights, self.boxes[idx].height)
                    self.boxes[idx].height = nearest_height
        else:
            line_height = len(packer) * groups[0][0].height
            for i in packs_idx:
                self.box_counter[i] = 0

        return groups[0], line_height


pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
# ic.disable()

# # Чтение чтение таблицы.
# box_types_df = pd.read_excel('package_types.xls', index_col=0)
# # Дроп столбцов 'ROWS_NUMBER', 'ICOMMENT'.
# box_types_df = box_types_df[['PACK_TYPE', 'LENGTH', 'WIDTH', 'HEIGHT', 'PACKS_IN_ROW']]
# # Удаление строк с отсутствующими данными.
# box_types_df = box_types_df.dropna()
#
# # Создание и заполнение уже словаря типов коробок по датафрейму.
# # box_types_dict = {}
# # for index, row in box_types_df.iterrows():
# #     box_types_dict[row[0]] = [row[1], row[2], row[3], row[4]]
#
#
# # Чтение файла поставки:
# # +-------------+---------+
# # | Column Name | Type    |
# # +-------------+---------+
# # | PALLET_ID   | int     | ID паллеты для этих коробок
# # | PACK_ID     | varchar | ID упаковки из таблицы с упаковками
# # | PACK_NUM    | varchar | Количество упаковок с данным ID на паллете
# # +-------------+---------+
# delivery_df = pd.read_excel('delivery.xls', index_col=0)
# # Проверка нахождения упаковок поставки в словаре
# del_index = []
# # Индексы сохранились после удаления строк, поскольку не было reset_index()
# pack_ids = frozenset(box_types_df.index.values)
# for index, row in delivery_df.iterrows():
#     if row[1] not in pack_ids:
#         print(f'Упаковка с индексом {row[1]} отсутсвует в таблице либо данные о ней недостаточны.')
#         print(f'Попробуйте задать PACKS_IN_ROW, равным очень большому числу, например 10 000.')
#         del_index.append(index)
# delivery_df.drop(del_index)
# delivery_df = delivery_df.sort_values(by=['PALLET_ID'])
#
#
# # INNER JOIN
# new_df = delivery_df.merge(box_types_df, left_on='PACK_ID', right_index=True)
# print(new_df)
#
# pallet_ids = new_df["PALLET_ID"].unique()
# print(pallet_ids)

invoices_df = pd.read_excel("ready_data.xlsx", index_col=0)

output = pd.DataFrame(columns=["INVOICE_ID", "PALLET_NO", "PALLET_HEIGHT"])

invoices_id = invoices_df["INVOICE_ID"].unique()
ic(invoices_id[:5])
column_invoice_id = []
column_pallet_no = []
column_pallet_height = []
for invoice_id in invoices_id:
    ic(invoice_id)
    pallets = invoices_df[invoices_df['INVOICE_ID'] == invoice_id]["PALLET_NO"].unique()
    for pallet in pallets:
        column_invoice_id.append(invoice_id)
        column_pallet_no.append(pallet)
        ic(pallet)
        boxes_df = invoices_df[(invoices_df['INVOICE_ID'] == invoice_id) & (invoices_df['PALLET_NO'] == pallet)]
        box_count = []
        boxes = []
        for index, box in boxes_df.iterrows():
            boxes.append(Box(box[3], box[4], box[5], box[6], pack_type=box[2]))
            box_count.append(box[7])
        ic(boxes)
        ic(box_count)
        pallet_object = Pallet(LENGTH, WIDTH, boxes, box_count)
        pallet_object.build_pallet()
        column_pallet_height.append(pallet_object.total_height)

output["INVOICE_ID"] = column_invoice_id
output["PALLET_NO"] = column_pallet_no
output["PALLET_HEIGHT"] = column_pallet_height
ic(output.head())
output.to_excel("output_low_density_straight_sort.xlsx")
# boxes = []
# box_count = []
# for i in pallet_ids:
#     pallet_ = new_df[new_df['PALLET_ID'] == i]
#     for index, box in pallet_.iterrows():
#         boxes.append(Box(box[4], box[5], box[6], box[7], pack_type=box[3]))
#         box_count.append(box[2])
#     pallet_obj = Pallet(LENGTH, WIDTH, boxes, box_count)
#     pallet_obj.build_pallet()