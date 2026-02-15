# config/brand_database.py

import json
import os
from collector import get_data_file_path # 引用统一方法


class BrandDatabase:

    def __init__(self):
        """
        初始化品牌数据库
        :param data_dir: 数据目录路径
        """
        self.db_file = get_data_file_path("brands.json")
        print(f"--- 数据库当前加载路径: {os.path.abspath(self.db_file)} ---")  # 加这行
        self.brands_data = self._load_database()



    def _load_database(self):
        """加载品牌数据库"""
        # 1. 如果文件已经存在，直接读取并返回，不再看 default_data

        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:  # 确保文件不是空的
                        return data
            except Exception as e:
                print(f"读取JSON失败: {e}")

        # 2. 只有当文件不存在或读取失败时，才使用代码里的默认数据
        print("未检测到数据库文件，正在初始化默认数据...")

        # 巨大的字典
        default_data = {

            "联想": [
                "thinkpadx1carbon",
                "thinkpadx1yoga",
                "thinkpadx1nano",
                "thinkpadx1fold",
                "thinkpadt14",
                "thinkpadt14s",
                "thinkpadt16",
                "thinkpadt480",
                "thinkpadt580",
                "thinke14",
                "thinke16",
                "thinkpadl13",
                "thinkpadl14",
                "thinkpadl15",
                "thinkpadp1",
                "thinkpadp16",
                "thinkpadp16s",
                "thinkpadp14s",
                "thinkpadz13",
                "thinkpadz16",
                "xiaoxin14",
                "xiaoxin16",
                "xiaoxinpro14",
                "xiaoxinpro16",
                "xiaoxinduet",
                "saviorr7000",
                "saviorr7000p",
                "saviorr9000p",
                "saviorr9000k",
                "saviory7000",
                "saviory7000p",
                "saviory9000p",
                "saviory9000k",
                "saviorr720",
                "saviorr920",
                "yoga7i",
                "yoga9i",
                "yogaslim7",
                "yogabook9i",
                "yoga920",
                "yoga730",
                "yoga6",
                "yoga5i",
                "legion5",
                "legion5i",
                "legion5pro",
                "legion7",
                "legion7i",
                "legion9i",
                "legionslim5",
                "legionslim7",
                "ideapadslim3",
                "ideapadslim5",
                "ideapadgaming3",
                "thinkbook14",
                "thinkbook14s",
                "thinkbook16",
                "thinkbookplus",
                "thinkbook13x",
                "thinkcentrem70t",
                "thinkcentrem70s",
                "thinkcentrem70q",
                "thinkcentrem80t",
                "thinkcentrem80s",
                "thinkcentrem80q",
                "thinkcentrem90t",
                "thinkcentrem90s",
                "thinkcentrem90q",
                "thinkcentrem720q",
                "thinkcentrem720s",
                "thinkcentrem920q",
                "thinkcentrem920t",
                "thinkcentreneos50s",
                "thinkcentreneos50t",
                "legiont5",
                "legiont7",
                "legiontower5i",
                "legiontower7i",
                "ideacentre3",
                "ideacentre5",
                "ideacentregaming5",
                "ideacentremini5",
                "geekprog5000",
                "geekpro2023",
                "geekpro2024",
                "blade7000k",
                "blade9000k",
                "blade9000",
                "blade7000",
                "yangtianm400",
                "yangtianm460",
                "yangtiant4900",
                "qitiantianm430",
                "qitiantianm450",
                "qitiantianm455"
            ],
            "戴尔": [
                "xps13",
                "xps13plus",
                "xps14",
                "xps15",
                "xps17",
                "xps132in1",
                "xps152in1",
                "latitude3440",
                "latitude5440",
                "latitude5540",
                "latitude7440",
                "latitude7640",
                "latitude9440",
                "latitude7350",
                "latitude7450",
                "inspiron14",
                "inspiron15",
                "inspiron16",
                "inspiron142in1",
                "inspiron16plus",
                "precision3480",
                "precision3580",
                "precision3581",
                "precision5490",
                "precision5690",
                "precision7780",
                "precision3431",
                "precision3440",
                "precision3630",
                "alienwarex14r2",
                "alienwarex15r2",
                "alienwarex16r1",
                "alienwarex16r2",
                "alienwarem15r7",
                "alienwarem16r1",
                "alienwarem16r2",
                "alienwarem17r5",
                "alienwarem18r1",
                "alienwarem18r2",
                "alienware16area51",
                "alienware18area51",
                "alienware16aurora",
                "alienware16xaurora",
                "g15",
                "g16",
                "optiplex3000micro",
                "optiplex3000sff",
                "optiplex3000tower",
                "optiplex5000micro",
                "optiplex5000sff",
                "optiplex5000tower",
                "optiplex7000micro",
                "optiplex7000sff",
                "optiplex7000tower",
                "optiplex7010micro",
                "optiplex7010sff",
                "optiplex7010tower",
                "optiplex3060micro",
                "optiplex3060sff",
                "optiplex3060tower",
                "optiplex3070micro",
                "optiplex3070sff",
                "optiplex3070tower",
                "optiplex5060sff",
                "optiplex5060tower",
                "optiplex5070micro",
                "optiplex5070sff",
                "optiplex7060micro",
                "optiplex7060sff",
                "optiplex7060tower",
                "optiplex7070micro",
                "optiplex7070sff",
                "optiplex7070tower",
                "optiplex7080sff",
                "optiplex7080tower",
                "optiplex7090micro",
                "optiplex7400allinone",
                "precision3431sff",
                "precision3440sff",
                "precision3450",
                "precision3460",
                "precision3630tower",
                "precision3640tower",
                "precision3660tower",
                "precision5820tower",
                "precision7820tower",
                "precision7920tower",
                "precision3280cff",
                "alienwarearea51intel",
                "alienwarearea51amd",
                "alienwareaurora",
                "alienwareaurorar15",
                "alienwareaurorar16",
                "xps8960desktop",
                "xps8950",
                "xps8940",
                "inspirondesktop",
                "inspironsmalldesktop",
                "inspiron24allinone",
                "inspiron27allinone"
            ],
            "惠普": [
                "spectrex36013",
                "spectrex36014",
                "spectrex36016",
                "spectrex360134000",
                "spectrex36015bl000",
                "spectrex36015bl100",
                "envy13",
                "envy14",
                "envy15",
                "envy17",
                "envyx36013",
                "envyx36015",
                "envyx36016",
                "envytouchsmart15",
                "envytouchsmart17",
                "pavilion14",
                "pavilion15",
                "pavilion16",
                "pavilion17",
                "pavilionx36014",
                "pavilionx36015",
                "paviliongaming15",
                "paviliongaming16",
                "pavilion14al000",
                "pavilion15ab",
                "pavilion15au",
                "pavilion17g",
                "elitebook640",
                "elitebook660",
                "elitebook840",
                "elitebook860",
                "elitebook1040",
                "elitebook820g2",
                "elitebook840g2",
                "elitebook850g2",
                "elitebook1040g3",
                "probook440",
                "probook450",
                "probook460",
                "probook440g2",
                "probook450g2",
                "probook455g2",
                "probook470g2",
                "omen15",
                "omen16",
                "omen17",
                "omen15ax",
                "omen15tax000",
                "omen15tce000",
                "omen15tdc000",
                "zbookfirefly",
                "zbookpower",
                "zbookfury",
                "zbookstudio",
                "stream11",
                "stream13",
                "stream14",
                "chromebook14g4",
                "elitedesk800g6micro",
                "elitedesk800g6sff",
                "elitedesk800g4micro",
                "elitedesk800g4sff",
                "elitedesk600g4micro",
                "elitedesk600g4sff",
                "elitedesk600g6micro",
                "elitedesk600g6sff",
                "prodesk400g7",
                "prodesk400g9",
                "prodesk600g4micro",
                "prodesk600g4sff",
                "prodesk600g6micro",
                "paviliondesktop",
                "paviliongamingdesktop",
                "pavilion24allinone",
                "pavilion27allinone",
                "omen25l",
                "omen30l",
                "omen35l",
                "omen45l",
                "envydesktop",
                "envy34allinone",
                "envy32allinone",
                "z2mini",
                "z2sff",
                "z2tower",
                "z4tower",
                "z6tower",
                "z8tower"
            ],
            "华硕": [
                "rogstrixscar16",
                "rogstrixscar18",
                "rogstrixg16",
                "rogstrixg18",
                "rogzephyrusg14",
                "rogzephyrusg16",
                "rogzephyrusm16",
                "rogzephyrusduo16",
                "rogflowx13",
                "rogflowz13",
                "rogflowx16",
                "rogstrix",
                "rogzephyrus",
                "tianxuan4",
                "tianxuan5",
                "tianxuan5pro",
                "tianxuan6",
                "tianxuan6pro",
                "tianxuanair",
                "tianxuanplus",
                "lingyao14",
                "lingyao16",
                "lingyaoxshuangping",
                "lingyaoxfold",
                "lingyaox14",
                "lingyaopro14",
                "lingyaopro16",
                "lingyao142025",
                "lingyaoxultra",
                "wuwei14",
                "wuwei15",
                "wuwei16",
                "wuweipro14",
                "wuweipro15",
                "wuweipro16",
                "wuweipro162025",
                "adou14",
                "adou14pro",
                "adouair",
                "poxiaopro",
                "poxiaoair",
                "expertbookb9",
                "expertbookb5",
                "expertbookp5",
                "tufgaminga15",
                "tufgaminga16",
                "tufgamingf15",
                "tufgamingf17",
                "vivobooks14",
                "vivobooks15",
                "vivobooks16",
                "vivobookpro",
                "rogstrixga15",
                "rogstrixga35",
                "rogstrixg10ce",
                "rogstrixg15ce",
                "roghuracan",
                "roggt51ca",
                "tufgaminggt301",
                "tufgaminggt501",
                "tufgaminggt15",
                "tufgaminggt30",
                "proartstationpd5",
                "proartstationpa90",
                "expertcenterd7sff",
                "expertcenterd9tower",
                "expertcentere5aio",
                "primeb450",
                "primeh510",
                "primez690"
            ],
            "苹果": [
                "macbookair13m1",
                "macbookair13m2",
                "macbookair13m3",
                "macbookair15m2",
                "macbookair15m3",
                "macbookpro14m3",
                "macbookpro14m3pro",
                "macbookpro14m3max",
                "macbookpro16m3pro",
                "macbookpro16m3max",
                "macbookpro13m2",
                "macbookpro14m2pro",
                "macbookpro16m2max",
                "macbook12retina",
                "macstudiom1max",
                "macstudiom1ultra",
                "macstudiom2max",
                "macstudiom2ultra",
                "macpro2019",
                "macpro2023m2ultra",
                "imac24m1",
                "imac24m3",
                "macminim1",
                "macminim2",
                "macminim2pro",
                "macminim4",
                "macminim4pro"
            ],
            "宏碁": [
                "swift3",
                "swift5",
                "swift7",
                "swiftgo14",
                "swiftgo16",
                "swift14ai",
                "swift16ai",
                "swiftedge14",
                "swiftedge16",
                "aspire3",
                "aspire5",
                "aspire7",
                "aspire14ai",
                "aspire16ai",
                "aspirevero",
                "predatorhelios16",
                "predatorhelios18",
                "predatorheliosneo16",
                "predatorheliosneo16s",
                "predatortriton14",
                "predatortriton16",
                "predatortriton17x",
                "predatorhelios300",
                "predatorhelios500",
                "nitro5",
                "nitro16",
                "nitro17",
                "nitrov16",
                "nitrov16s",
                "travelmatep2",
                "travelmatep4",
                "travelmatep6",
                "chromebookspin",
                "chromebook314",
                "chromebook514"
            ],
            "微星": [
                "titan18hx",
                "titangt77hx",
                "raiderge78hx",
                "raiderge68hx",
                "stealth18",
                "stealth16",
                "stealth14",
                "stealthgs77",
                "vector16hx",
                "vectorgp77",
                "crosshair16",
                "crosshair17",
                "pulse15",
                "pulse17",
                "katana15",
                "katana17",
                "cyborg15",
                "cyborg14",
                "creatorz17hx",
                "creatorz16p",
                "creatorm16",
                "bravo15",
                "bravo17",
                "alpha15",
                "alpha17",
                "modern14",
                "modern15",
                "summite16flip",
                "summite14flip",
                "prestige16",
                "prestige14",
                "prestige13",
                "infinites",
                "infinitex",
                "infinitea",
                "trident3",
                "tridentx",
                "tridenta",
                "codexr",
                "codexx",
                "codexs",
                "aegisr",
                "aegisrs",
                "aegisti5",
                "aegisti512th",
                "mpgtridentas",
                "mpgininutex2",
                "megtridentx2",
                "megaegisti5"
            ],
            "华为": [
                "matebookx",
                "matebookx2020",
                "matebookx2021",
                "matebookxpro",
                "matebookxpro2019",
                "matebookxpro2020",
                "matebookxpro2021",
                "matebookxprocoreultra",
                "matebook13",
                "matebook14",
                "matebook14coreultra",
                "matebook14linux",
                "matebook16",
                "matebook16s",
                "matebook14s",
                "matebookd14",
                "matebookd15",
                "matebookd16",
                "matebookd14ryzen",
                "matebookd15ryzen",
                "matebooke",
                "matebookego",
                "matebookegoseries",
                "matebookgt14",
                "matebookpro",
                "matebookfold",
                "matebookb3410",
                "matebookb3420",
                "matebookb3430",
                "matebookb3510",
                "matebookb3520",
                "matebookb5420",
                "matebookb5430",
                "matebookb7410",
                "matestationx",
                "matestations",
                "matestationb515",
                "matestationb520"
            ],
            "小米": [
                "mibookair12.5",
                "mibookair13.3",
                "mibookpro15",
                "mibookprox",
                "mibookpro14",
                "mibookpro16",
                "redmibook14",
                "redmibook15",
                "redmibook16",
                "redmibookair13",
                "redmibookair14",
                "redmibookpro14",
                "redmibookpro15",
                "redmibookpro16",
                "redmibookpro142024",
                "redmibookpro162024",
                "redmibookpro142025",
                "redmibookpro162025",
                "redmig2021",
                "redmig2022",
                "redmigpro",
                "xiaomibookair13",
                "xiaomibookpro14",
                "xiaomibookpro16",
                "xiaomiminihost",
                "xiaomihost2023",
                "xiaomihost2024"
            ],
            "三星": [
                "galaxybook5pro360",
                "galaxybook5pro",
                "galaxybook5360",
                "galaxybook5",
                "galaxybook4ultra",
                "galaxybook4pro360",
                "galaxybook4pro",
                "galaxybook4360",
                "galaxybook4edge",
                "galaxybook6ultra",
                "galaxybook6pro360",
                "galaxybook6pro"
            ],
            "lg": [
                "gram14",
                "gram15",
                "gram16",
                "gram17",
                "grampro16",
                "grampro17",
                "grampro16z90u",
                "grampro17z90ur",
                "gramstyle",
                "gramsuperslim"
            ],
            "雷蛇": [
                "blade14",
                "blade15",
                "blade16",
                "blade17",
                "blade18",
                "bladestealth13"
            ],
            "技嘉": [
                "aorusmaster16",
                "aorusmaster18",
                "aoruselite16",
                "aorus16x",
                "aorus17x",
                "aorus17",
                "aorus15",
                "aerox16",
                "aero16",
                "aero14",
                "gaminga18pro"
            ],
            "微软": [
                "surfacelaptop7",
                "surfacelaptop6",
                "surfacelaptop5",
                "surfacelaptopstudio2",
                "surfacelaptopstudio",
                "surfacepro11",
                "surfacepro10",
                "surfacepro9",
                "surfacebook3",
                "surfacego4",
                "surfacelaptopgo3",
                "surfacelaptopgo2"
            ],
            "荣耀": [
                "magicbook14",
                "magicbook15",
                "magicbook16",
                "magicbookpro",
                "magicbookv14",
                "magicbookart14"
            ],
            "机械革命": [
                "jiguangpro",
                "jiguange",
                "jiguangair",
                "kuangshix",
                "kuangshig16",
                "kuangshi16pro",
                "jiaolong16",
                "jiaolong16pro",
                "jiaolong17",
                "jiaolong17pro",
                "wujie14",
                "wujie14pro",
                "wujie16",
                "wujiem5",
                "wujiem7"
            ],
            "神舟": [
                "zhanshenz7",
                "zhanshenz8",
                "zhanshenz9",
                "zhanshent7",
                "zhanshent8",
                "zhanshentx8",
                "zhanshentx9",
                "youyax4",
                "youyax5",
                "youyax6",
                "jingdunu45",
                "jingdunx55",
                "jingdunx57"
            ],
            "雷神": [
                "911air",
                "911plus",
                "911pro",
                "911mt",
                "911zero",
                "911p1",
                "lielie15",
                "lielie16",
                "zero2023",
                "zero2024",
                "zeropro",
                "tbook14",
                "tbook16"
            ],
            "机械师": [
                "shuguang15",
                "shuguang16",
                "shuguang16pro",
                "shuguang18",
                "xingchen15",
                "xingchen17",
                "chuangwuzhex14",
                "chuangwuzhex16",
                "chuangwuzhem",
                "chuangwuzhemini"
            ],
            "外星人": [
                "area51intelcoreultra",
                "area51amdryzen",
                "aurorar13",
                "aurorar14",
                "aurorar15",
                "aurorar16"
            ],
            "华擎": [
                "deskminix300",
                "deskminib660",
                "deskminih470",
                "deskminigtx",
                "marsucff"
            ],
            "英特尔": [
                "nuc13pro",
                "nuc13extreme",
                "nuc12pro",
                "nuc12enthusiast",
                "nuc11performance",
                "nuc11pro",
                "nuc11essential",
                "nuc10performance",
                "nuc9extreme"
            ], "其他": []  # 保留"其他"类别

        }

        # 3. 初始化时顺手把这些数据存进文件，下次运行就走步骤 1 了
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
        except:
            pass

        return default_data


    def save_database(self):
        """保存品牌数据库"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.brands_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存品牌数据库失败: {e}")
            return False

    def detect_brand_from_model(self, model):
        """
        根据型号字符串识别品牌
        :param model: 型号字符串
        :return: 品牌名称或"未知"
        """
        # 1. 基础校验
        if not model or str(model).strip() == '未知' or not isinstance(model, (str, bytes)):
            return '未知'

        # 2. 预处理：转小写，并去掉所有空格和特殊字符
        # 这样 "TUF GAMING" 就会变成 "tufgaming"
        m_raw = str(model).lower().strip()
        m_compact = m_raw.replace(" ", "").replace("-", "").replace("_", "")

        # 3. 优先匹配：品牌名本身就在型号里
        for brand in self.brands_data.keys():
            # 跳过 JSON 里的特殊字段（如之前建议的 pure_brands 列表）
            if brand == "pure_brands": continue

            brand_clean = brand.lower().strip()
            if brand_clean in m_raw or brand_clean in m_compact:
                return brand

        # 4. 次优先：遍历所有品牌下的型号列表
        for brand, models in self.brands_data.items():
            if not isinstance(models, list): continue

            for target_m in models:
                # 处理库里的型号：转小写，去空格
                t_clean = str(target_m).lower().strip()
                t_compact = t_clean.replace(" ", "").replace("-", "").replace("_", "")

                # 核心修正：双向包含判断
                # 如果主板型号里包含库型号，或者库型号包含主板型号，则匹配成功
                if t_compact and (t_compact in m_compact or m_compact in t_compact):
                    return brand

        # 5. 最后一道防线：返回值改为“未知”，让 collector.py 的硬编码逻辑继续判断
        # 只有当 collector 也识别不出时，才在 GUI 界面显示为“组装机/未知”
        return '组装机'

    def get_all_brands(self):
        """获取所有品牌"""
        return list(self.brands_data.keys())

    def get_brand_models(self, brand_name):
        """获取指定品牌的所有型号"""
        return self.brands_data.get(brand_name, [])

    def add_brand(self, brand_name):
        """添加新品牌"""
        if brand_name in self.brands_data:
            return False, "品牌已存在"

        self.brands_data[brand_name] = []

        if self.save_database():
            return True, f"品牌 '{brand_name}' 添加成功"
        else:
            return False, "保存失败"

    def add_model_to_brand(self, brand_name, model_name):
        """添加型号到指定品牌"""
        if brand_name not in self.brands_data:
            return False, "品牌不存在"

        if not model_name or not isinstance(model_name, str):
            return False, "型号名称无效"

        # 清理型号名称
        model_name = model_name.strip()

        # 检查是否已存在
        if model_name in self.brands_data[brand_name]:
            return False, "型号已存在"

        self.brands_data[brand_name].append(model_name)

        if self.save_database():
            return True, f"型号 '{model_name}' 已添加到品牌 '{brand_name}'"
        else:
            return False, "保存失败"

    def remove_brand(self, brand_name):
        """删除品牌"""
        if brand_name not in self.brands_data:
            return False, "品牌不存在"

        if brand_name == '其他':
            return False, "不能删除默认品牌 '其他'"

        del self.brands_data[brand_name]

        if self.save_database():
            return True, f"品牌 '{brand_name}' 删除成功"
        else:
            return False, "保存失败"

    def remove_model_from_brand(self, brand_name, model_name):
        """从品牌中删除型号"""
        if brand_name not in self.brands_data:
            return False, "品牌不存在"

        if model_name not in self.brands_data[brand_name]:
            return False, "型号不存在"

        self.brands_data[brand_name].remove(model_name)

        if self.save_database():
            return True, f"型号 '{model_name}' 已从品牌 '{brand_name}' 中删除"
        else:
            return False, "保存失败"

    def search_models(self, search_term):
        """搜索型号（模糊匹配）"""
        if not search_term:
            return ["传入参数为空"]

        results = []
        search_lower = search_term.lower().strip()
        brand_from_search = self.detect_brand_from_model(search_term)
        if brand_from_search != '未知':
            return brand_from_search
        else:
            for brand, models in self.brands_data.items():
                for model in models:
                    if search_lower in model.lower():
                        results.append({
                            'brand': brand,
                            'model': model
                        })
            if results:
                return results
            else:
                return "未知"

    def add_pure_brand(self, brand_name):
        """
      简单添加品牌名，不关联型号
      """

        brand_name = brand_name.strip()
        if not brand_name:
            return False, "品牌名不能为空"

        # 1. 查重：不论是作为 Key 还是在型号列表里，只要出现过就算存在
        if brand_name in self.brands_data:
            return False, f"品牌 [{brand_name}] 已存在"

        # 2. 追加数据：以品牌名为 Key，初始化一个空列表
        self.brands_data[brand_name] = []

        # 3. 立即写入文件 (self.db_file 已经是指向“数据存储/brands.json”)
        if self.save_database():
            return True, "品牌添加成功"
        else:
            return False, "文件写入失败"

    def reload(self):
        """强制重新从磁盘加载最新的数据"""
        self.brands_data = self._load_database()
