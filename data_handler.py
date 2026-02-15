# data_handler.py
import os
import json
from openpyxl import Workbook
from datetime import datetime
from collector import get_data_file_path, HardwareCollector



class DataHandler:
    def __init__(self):

        self.data_dir = os.path.join("数据存储")
        self.json_path = get_data_file_path("computer_assets.json")


        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)

        # 这里的名称必须和 get_hardware_info 返回的 return {} 完全一致
        self.column_order = [
            "计算机名称", "ip地址", "当前用户", "型号", "品牌",
            "CPU", "内存", "硬盘", "操作系统", "部门", "现使用人", "收集时间"
        ]

    def load_data(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_data(self, data_list):
        try:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(data_list, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

    def export_to_excel(self, data):
        try:
            if not data: return False, "数据为空"

            wb = Workbook()
            ws = wb.active
            ws.title = "硬件资产清单"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 1. 自动提取表头
            headers = list(data[0].keys())
            ws.append(headers)

            # 2. 逐行写入数据
            for item in data:
                row = [str(item.get(h, "")) for h in headers]
                ws.append(row)

            export_path = f"资产清单导出{timestamp}.xlsx"
            wb.save(export_path)
            return True, export_path
        except Exception as e:
            return False, str(e)




