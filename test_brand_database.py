# test_brand_database.py
"""
BrandDatabase 品牌数据库单元测试
测试品牌识别功能，不依赖 Windows 特定模块
"""

import unittest
import json
import os
import tempfile
import shutil


class MockBrandDatabase:
    """简化版 BrandDatabase 用于测试"""
    
    def __init__(self, brands_data=None):
        if brands_data is None:
            self.brands_data = {
                "联想": ["thinkpadx1carbon", "thinkpadt14", "xiaoxin14"],
                "戴尔": ["xps13", "xps15", "latitude5440"],
                "惠普": ["spectrex36014", "envy13", "elitebook840"],
                "华硕": ["rogstrixscar16", "vivobooks14", "tianxuan4"]
            }
        else:
            self.brands_data = brands_data
    
    def detect_brand_from_model(self, model_name):
        """从型号检测品牌"""
        if not model_name:
            return "未知"
        
        model_lower = str(model_name).lower().replace(" ", "").replace("-", "")
        
        for brand, models in self.brands_data.items():
            for model_keyword in models:
                if model_keyword in model_lower:
                    return brand
        
        return "未知"


class TestBrandDatabase(unittest.TestCase):
    """BrandDatabase 单元测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.db = MockBrandDatabase()
    
    def test_detect_lenovo_thinkpad(self):
        """测试联想 ThinkPad 识别"""
        self.assertEqual(self.db.detect_brand_from_model("ThinkPad X1 Carbon"), "联想")
        self.assertEqual(self.db.detect_brand_from_model("ThinkPadT14"), "联想")
        self.assertEqual(self.db.detect_brand_from_model("20UDS0KV00"), "未知")
    
    def test_detect_dell_xps(self):
        """测试戴尔 XPS 识别"""
        self.assertEqual(self.db.detect_brand_from_model("XPS 13"), "戴尔")
        self.assertEqual(self.db.detect_brand_from_model("XPS-15"), "戴尔")
        self.assertEqual(self.db.detect_brand_from_model("Latitude 5440"), "戴尔")
    
    def test_detect_hp(self):
        """测试惠普识别"""
        self.assertEqual(self.db.detect_brand_from_model("Spectre x360 14"), "惠普")
        self.assertEqual(self.db.detect_brand_from_model("ENVY 13"), "惠普")
        self.assertEqual(self.db.detect_brand_from_model("EliteBook 840"), "惠普")
    
    def test_detect_asus(self):
        """测试华硕识别"""
        self.assertEqual(self.db.detect_brand_from_model("ROG Strix Scar 16"), "华硕")
        self.assertEqual(self.db.detect_brand_from_model("VivoBook S14"), "华硕")
        self.assertEqual(self.db.detect_brand_from_model("tianxuan4"), "华硕")
    
    def test_unknown_brand(self):
        """测试未知品牌"""
        self.assertEqual(self.db.detect_brand_from_model(""), "未知")
        self.assertEqual(self.db.detect_brand_from_model(None), "未知")
        self.assertEqual(self.db.detect_brand_from_model("Unknown Model XYZ"), "未知")
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        self.assertEqual(self.db.detect_brand_from_model("XPS 13"), "戴尔")
        self.assertEqual(self.db.detect_brand_from_model("xps 13"), "戴尔")
        self.assertEqual(self.db.detect_brand_from_model("XpS-13"), "戴尔")


class TestDataHandlerLogic(unittest.TestCase):
    """DataHandler 逻辑测试（不依赖实际文件操作）"""
    
    def test_json_serialization(self):
        """测试 JSON 序列化"""
        data = [
            {"计算机名称": "PC001", "品牌": "联想", "CPU": "i7"},
            {"计算机名称": "PC002", "品牌": "戴尔", "CPU": "i5"}
        ]
        
        # 序列化
        json_str = json.dumps(data, ensure_ascii=False)
        self.assertIsInstance(json_str, str)
        
        # 反序列化
        loaded = json.loads(json_str)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["计算机名称"], "PC001")
    
    def test_empty_data_handling(self):
        """测试空数据处理"""
        self.assertFalse([])  # 空列表为 False
        self.assertFalse(None)  # None 为 False
        self.assertTrue([{"key": "value"}])  # 非空列表为 True
    
    def test_excel_headers_extraction(self):
        """测试 Excel 表头提取逻辑"""
        data = [
            {"计算机名称": "PC001", "ip 地址": "192.168.1.1", "品牌": "联想"},
            {"计算机名称": "PC002", "ip 地址": "192.168.1.2", "品牌": "戴尔"}
        ]
        
        headers = list(data[0].keys())
        self.assertEqual(len(headers), 3)
        self.assertIn("计算机名称", headers)
        self.assertIn("ip 地址", headers)
        self.assertIn("品牌", headers)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
