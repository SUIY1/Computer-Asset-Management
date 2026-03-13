# test_data_handler.py
import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Mock Windows-specific modules before importing data_handler
import sys

# 创建更完整的 winreg mock
winreg_mock = MagicMock()
winreg_mock.QueryValueEx.return_value = ("test_value", 1)  # 返回元组
sys.modules['winreg'] = winreg_mock

# 创建 psutil mock
psutil_mock = MagicMock()
psutil_mock.virtual_memory.return_value.total = 16 * (1024 ** 3)
sys.modules['psutil'] = psutil_mock

# Mock collector 模块
collector_mock = MagicMock()
collector_mock.get_data_file_path.return_value = "/tmp/test_computer_assets.json"
sys.modules['collector'] = collector_mock

# 需要测试的模块
from data_handler import DataHandler


class TestDataHandler(unittest.TestCase):
    """DataHandler 类的单元测试"""

    def setUp(self):
        """每个测试前的准备工作"""
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.test_json_path = os.path.join(self.test_dir, "test_computer_assets.json")
        
        # 模拟数据
        self.sample_data = [
            {
                "计算机名称": "PC001",
                "ip 地址": "192.168.1.100",
                "当前用户": "zhangsan",
                "型号": "ThinkPad T14",
                "品牌": "联想",
                "CPU": "Intel i7-1165G7",
                "内存": "16GB",
                "硬盘": "SSD:512G",
                "操作系统": "Windows 10",
                "部门": "IT 部",
                "现使用人": "张三",
                "收集时间": "2024-01-01 10:00:00"
            },
            {
                "计算机名称": "PC002",
                "ip 地址": "192.168.1.101",
                "当前用户": "lisi",
                "型号": "XPS 13",
                "品牌": "戴尔",
                "CPU": "Intel i5-1135G7",
                "内存": "8GB",
                "硬盘": "SSD:256G",
                "操作系统": "Windows 11",
                "部门": "财务部",
                "现使用人": "李四",
                "收集时间": "2024-01-02 11:00:00"
            }
        ]

    def tearDown(self):
        """每个测试后的清理工作"""
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('data_handler.get_data_file_path')
    def test_init_creates_data_dir(self, mock_get_path):
        """测试初始化时自动创建数据目录"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        
        # 验证数据目录存在
        self.assertTrue(os.path.exists(handler.data_dir))
        mock_get_path.assert_called_once_with("computer_assets.json")

    @patch('data_handler.get_data_file_path')
    def test_load_data_from_existing_file(self, mock_get_path):
        """测试从现有文件加载数据"""
        mock_get_path.return_value = self.test_json_path
        
        # 先创建测试文件
        with open(self.test_json_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_data, f, ensure_ascii=False)
        
        handler = DataHandler()
        loaded_data = handler.load_data()
        
        self.assertEqual(len(loaded_data), 2)
        self.assertEqual(loaded_data[0]["计算机名称"], "PC001")
        self.assertEqual(loaded_data[1]["品牌"], "戴尔")

    @patch('data_handler.get_data_file_path')
    def test_load_data_from_nonexistent_file(self, mock_get_path):
        """测试从不存在的文件加载数据返回空列表"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        loaded_data = handler.load_data()
        
        self.assertEqual(loaded_data, [])

    @patch('data_handler.get_data_file_path')
    def test_save_data_success(self, mock_get_path):
        """测试保存数据成功"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        result = handler.save_data(self.sample_data)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.test_json_path))
        
        # 验证保存的内容
        with open(self.test_json_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        self.assertEqual(len(saved_data), 2)
        self.assertEqual(saved_data[0]["当前用户"], "zhangsan")

    @patch('data_handler.get_data_file_path')
    def test_export_to_excel_success(self, mock_get_path):
        """测试导出 Excel 成功"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        success, result = handler.export_to_excel(self.sample_data)
        
        self.assertTrue(success)
        self.assertTrue(result.endswith('.xlsx'))
        self.assertTrue(os.path.exists(result))
        
        # 清理生成的 Excel 文件
        if os.path.exists(result):
            os.remove(result)

    @patch('data_handler.get_data_file_path')
    def test_export_to_excel_empty_data(self, mock_get_path):
        """测试导出空数据"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        success, message = handler.export_to_excel([])
        
        self.assertFalse(success)
        self.assertEqual(message, "数据为空")

    @patch('data_handler.get_data_file_path')
    def test_export_to_excel_none_data(self, mock_get_path):
        """测试导出 None 数据"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        success, message = handler.export_to_excel(None)
        
        self.assertFalse(success)
        self.assertEqual(message, "数据为空")

    @patch('data_handler.get_data_file_path')
    def test_column_order(self, mock_get_path):
        """测试列顺序定义正确"""
        mock_get_path.return_value = self.test_json_path
        
        handler = DataHandler()
        
        expected_columns = [
            "计算机名称", "ip 地址", "当前用户", "型号", "品牌",
            "CPU", "内存", "硬盘", "操作系统", "部门", "现使用人", "收集时间"
        ]
        
        self.assertEqual(handler.column_order, expected_columns)


if __name__ == '__main__':
    unittest.main()
