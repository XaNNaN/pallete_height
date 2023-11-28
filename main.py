# Чтение и обработка таблицы с типами коробок
import pandas as pd

# Библиотека для размещения прямоугольников
from rectpack import *

import copy

# Для разделения коробок на группы по высоте
from itertools import groupby

# Отладка принтами на максималке
from icecream import ic

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
        self.height_stable = height

    @staticmethod
    def rectangle_area(length: float, width: float) -> float:
        return length * width

    @staticmethod
    def parallelepiped_volume(length: float, width: float, height: float) -> float:
        return length * width * height

    def __repr__(self):
        return f'  Pack_type:\t{self.pack_type}  {self.height}  {self.height_stable}'
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
    def __init__(self, length: float, width: float, boxes: list, pack_counter: list, reverse=False):
        self.length = length
        self.width = width
        self.area = self.rectangle_area(length, width)
        boxes_index = [(i, item) for i, item in enumerate(boxes)]
        sorted_box_index = sorted(boxes_index, key=self.sort_by_height, reverse=reverse)
        self.boxes = [i[1] for i in sorted_box_index]
        _ = [i[0] for i in sorted_box_index]
        self.lines = []
        self.total_height = HEIGHT
        self.box_counter = [pack_counter[i] for i in _]
        self.total_boxes = sum(pack_counter)
        self.reverse = reverse
        self.box_counter_ = pack_counter.copy()
        self.boxes_ = copy.deepcopy(boxes)

    @staticmethod
    def rectangle_area(length: float, width: float) -> float:
        return length * width

    @staticmethod
    def sort_by_height(box: tuple) -> float:
        return box[1].height

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

        if not self.reverse:
            reverse_pallet = Pallet(self.length, self.width, self.boxes_, self.box_counter_, reverse=True)
            reverse_pallet.build_pallet()
            if self.total_height < reverse_pallet.total_height:
                return self.total_height
            else:
                return reverse_pallet.total_height

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

        stable_heights = [box.height_stable for box in groups[0]]
        max_height = max(stable_heights)
        for box in groups[0]:
            box.height = max_height

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
            area = 0

        area_last = 0
        for rect in packer[-1]:
            area_last += rect.width * rect.height

        packer_rect_sum = 0
        for bin in packer:
            packer_rect_sum += len(bin)

        while packer_rect_sum != len(rectangles):
            packer_rect_sum = 0
            # Увеличение количества слоёв на один
            n_bins += 1
            bin = [(self.length, self.width) for _ in range(n_bins)]
            packer = newPacker(bin_algo=bin_algo, pack_algo=pack_algo, rotation=True)

            for r, box_index in zip(rectangles, soup_list):
                packer.add_rect(*r, rid=box_index)
            for b in bin:
                packer.add_bin(*b)
            packer.pack()

            for bin in packer:
                packer_rect_sum += len(bin)


        area_last = 0
        for rect in packer[-1]:
            area_last += rect.width * rect.height

        density_list = []
        for bin in packer:
            area = 0
            for rect in bin:
                area += rect.width * rect.height
            density_list.append(area / self.area)
        print(f"Density: {density_list}, boxes: {groups[0]}")

        max_area = max([rect.width * rect.height for rect in packer[0]])
        print([rect.width * rect.height for rect in packer[0]])
        if max_area > 68000:
            high_border = 0.65
            print(f"{high_border}")
        else:
            high_border = 0.9

        cond_1 = 0.18 < area_last / self.area < high_border and len(packer[0]) != self.total_boxes and self.reverse == False
        cond_2 = area_last / self.area < high_border and len(packer[0]) != self.total_boxes and self.reverse == True

        if cond_1 or cond_2:
            packs = [pack for i, pack in enumerate(packer) if i != len(packer) - 1]
            line_height = 0
            for bin in packs:
                line_heights = []
                for rect in bin:
                    idx = rect.rid
                    line_heights.append(self.boxes[idx].height_stable)
                line_height += max(line_heights)
            # line_height = (len(packer) - 1) * groups[0][0].height
            
            idxs = []
            for pack in packs:
                for rect in pack:
                    idx = rect.rid
                    self.box_counter[idx] -= 1
            for rect in packer[-1]:
                idx = rect.rid
                idxs.append(idx)
            for idx in set(idxs):
                heights = set([i.height for i, c in zip(self.boxes, self.box_counter) if (i.height != self.boxes[idx].height and c > 0)])
                if heights == set():
                    line_height = groups[0][0].height
                else:
                    nearest_height = nearest_value(heights, self.boxes[idx].height)
                    if nearest_height > self.boxes[idx].height:
                        self.boxes[idx].height = nearest_height
                    else:
                        heights_ = [i.height for i in self.boxes]
                        i = heights_.index(nearest_height)
                        self.boxes[i].height = self.boxes[idx].height
        else:
            if area_last / self.area > 0.18 or len(packer[0]) == self.total_boxes:
                line_height = len(packer) * groups[0][0].height
            else:
                line_height = (len(packer) - 1) * groups[0][0].height
            for i in packs_idx:
                self.box_counter[i] = 0

        print(line_height)
        return groups[0], line_height


pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
ic.disable()

invoices_df = pd.read_excel("ready_fact_data_28_11.xlsx", index_col=0)

output = pd.DataFrame(columns=["INVOICE_ID", "PALLET_NO", "PALLET_HEIGHT"])

invoices_id = invoices_df["INVOICE_ID"].unique()
ic(invoices_id[:5])
column_invoice_id = []
column_pallet_no = []
column_pallet_height = []
# [True if i == 291082 else False for i in invoices_id]
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
            boxes.append(Box(box[4], box[5], box[6], box[7], pack_type=box[2]))
            box_count.append(box[9])
        ic(boxes)
        ic(box_count)
        pallet_object = Pallet(LENGTH, WIDTH, boxes, box_count)
        height = pallet_object.build_pallet()
        column_pallet_height.append(height)

output["INVOICE_ID"] = column_invoice_id
output["PALLET_NO"] = column_pallet_no
output["PALLET_HEIGHT"] = column_pallet_height
output = output.merge(invoices_df[["INVOICE_ID", "PALLET_NO", "PALLETE_HEIGHT_FACT"]], on=["INVOICE_ID", "PALLET_NO"])
output["PALLETE_HEIGHT_FACT"] = output["PALLETE_HEIGHT_FACT"] * 10
output = output.drop_duplicates()
ic(output.head())
output.to_excel("output_28_11.xlsx")
