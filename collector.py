import os
import platform
import socket
import sys
import psutil
import winreg
import subprocess
import getpass
import json
from datetime import datetime


# ---- 分步采集日志：卡住时可在“采集步骤.log”看到卡在哪一步 ----
_STEP_LOG = None


def set_step_log(path):
    """设置分步日志文件路径（传入 None 可关闭）"""
    global _STEP_LOG
    _STEP_LOG = path
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")  # 清空旧日志
        except Exception:
            pass


def log_step(msg):
    if not _STEP_LOG:
        return
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        with open(_STEP_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def get_base_dir():
    """统一获取程序根目录的唯一方法"""
    try:
        # 如果是 PyInstaller 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            # sys.executable 是 exe 的路径
            return os.path.dirname(os.path.abspath(sys.executable))

        # 如果是源码运行环境
        # sys.argv[0] 是启动脚本的路径
        curr_path = os.path.abspath(sys.argv[0])
        return os.path.dirname(curr_path)
    except Exception as e:
        print(f"获取路径失败，回退到当前工作目录: {e}")
        return os.getcwd()
def get_data_file_path(filename):
    """
        统一的存储位置获取函数：所有文件都存放在“数据存储”文件夹下
        用法：get_data_file_path("brands.json")
        """
    base = get_base_dir()
    data_dir = os.path.join(base, "数据存储")

    # 自动创建“数据存储”文件夹
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    return os.path.join(data_dir, filename)


def is_temp_directory(path):
    """判断是否为临时目录，防止数据写到 C 盘临时文件夹里"""
    path_lower = path.lower()
    temp_keywords = ['temp', 'tmp', 'appdata', 'local\\temp', 'onedrive', '~', '用户\\', 'users\\']
    for keyword in temp_keywords:
        if keyword in path_lower:
            return True
    return False


def get_ip_and_mac():
    """
    获取当前主要网络接口的 IPv4 地址和 MAC 地址
    - 主要网卡：优先使用默认路由所使用的 IP
    - 如果有多个 IP 绑定在同一网卡上，会全部列出
    返回: (ip_display, mac_address)
    """
    primary_ip = None

    # 方法1：通过与公网地址建立 UDP 连接，获取本机对外 IPv4（最快、最稳）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
        if primary_ip and primary_ip.startswith("169.254."):
            primary_ip = None
    except Exception:
        primary_ip = None

    # 方法2：PowerShell 获取带默认网关的 IPv4
    if primary_ip is None and os.name == "nt":
        try:
            cmd = (
                'powershell -Command '
                '"(Get-NetIPConfiguration | '
                'Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress"'
            )
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                encoding="utf-8",
                timeout=15,
            )
            if result.returncode == 0:
                text = result.stdout.strip()
                # 可能有多行，优先第一行
                for line in text.splitlines():
                    ip = line.strip()
                    if ip and not ip.startswith("169.254."):
                        primary_ip = ip
                        break
        except Exception:
            pass

    # 方法3：主机名解析兜底
    if primary_ip is None:
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if (
                    ip
                    and not ip.startswith("127.")
                    and not ip.startswith("169.254.")
                    and not ip.startswith("172.17.")
                ):
                    primary_ip = ip
                    break
        except Exception:
            pass

    # 使用 psutil 将 IP 绑定到具体网卡，并拿到对应 MAC
    try:
        nic_addrs = psutil.net_if_addrs()
    except Exception:
        nic_addrs = {}

    chosen_nic = None
    all_addrs_on_nic = []
    mac_addr = None

    if nic_addrs:
        # 先根据 primary_ip 找到对应网卡
        for nic, addrs in nic_addrs.items():
            ipv4_list = [
                a.address
                for a in addrs
                if getattr(a, "family", None) == socket.AF_INET
                and not a.address.startswith("169.254.")
            ]
            if primary_ip and primary_ip in ipv4_list:
                chosen_nic = nic
                all_addrs_on_nic = ipv4_list
                break

        # 如果没找到 primary_ip 对应的网卡，就选第一个有正常 IPv4 的网卡
        if chosen_nic is None:
            for nic, addrs in nic_addrs.items():
                ipv4_list = [
                    a.address
                    for a in addrs
                    if getattr(a, "family", None) == socket.AF_INET
                    and not a.address.startswith("169.254.")
                    and not a.address.startswith("127.")
                ]
                if ipv4_list:
                    chosen_nic = nic
                    all_addrs_on_nic = ipv4_list
                    if primary_ip is None:
                        primary_ip = ipv4_list[0]
                    break

        # 拿到这个网卡的 MAC
        if chosen_nic is not None:
            addrs = nic_addrs.get(chosen_nic, [])
            for a in addrs:
                # Windows 下 psutil 会把 MAC 放在 AF_LINK
                if str(getattr(a, "family", "")) in ("AddressFamily.AF_LINK", "17") or getattr(
                    a, "family", None
                ) == getattr(psutil, "AF_LINK", None):
                    if a.address and a.address != "00:00:00:00:00:00":
                        mac_addr = a.address
                        break

    # 组合展示字符串：同一网卡上的多个 IPv4 一起展示
    if all_addrs_on_nic:
        ip_display = ", ".join(all_addrs_on_nic)
    elif primary_ip:
        ip_display = primary_ip
    else:
        ip_display = "未知"

    if not mac_addr:
        mac_addr = "未知"

    return ip_display, mac_addr


# ============================================================
# 硬盘识别（统一模块级函数，避免多数据源不一致）
# ============================================================

def _format_disk_size(size_bytes):
    """
    将原始字节数转换为贴近厂商标称的容量档位。
    关键改进：改用十进制(1GB=10^9)而非二进制(1GiB=1024^3)，
    使结果对齐包装盒上的“512G / 1T”等标称值，而不是显示 476G、931G。
    """
    if not size_bytes or size_bytes <= 0:
        return ""

    gb = size_bytes / 1_000_000_000  # 十进制 GB

    if gb >= 1000:
        tb = gb / 1000.0
        tiers = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20]
        best = min(tiers, key=lambda t: abs(t - tb))
        if abs(best - tb) <= 0.25:
            return f"{best}T".replace(".0T", "T")
        return f"{round(tb, 1)}T"

    tiers = [120, 128, 160, 180, 200, 240, 250, 256, 320,
             360, 400, 480, 500, 512, 600, 640, 750, 800, 960, 1000]
    best = min(tiers, key=lambda g: abs(g - gb))
    if abs(best - gb) <= 0.12 * best + 5:
        return f"{best}G"
    return f"{round(gb)}G"


def _detect_disk_vendor(model):
    """根据硬盘型号文本推断厂商（中文优先）"""
    m = (model or "").upper()
    table = [
        ("三星", ["SAMSUNG"]),
        ("西数", ["WDC", "WD", "WESTERN DIGITAL"]),
        ("希捷", ["SEAGATE", "ST"]),
        ("东芝", ["TOSHIBA"]),
        ("金士顿", ["KINGSTON"]),
        ("英睿达", ["CRUCIAL", "CT"]),
        ("英特尔", ["INTEL"]),
        ("闪迪", ["SANDISK"]),
        ("镁光", ["MICRON"]),
        ("海力士", ["SK HYNIX", "HYNIX"]),
        ("铠侠", ["KIOXIA"]),
        ("长江存储", ["YMTC"]),
        ("朗科", ["NETAC"]),
        ("江波龙", ["FORESEE", "LONG SYS", "LONGsys"]),
        ("雷克沙", ["LEXAR"]),
        ("七彩虹", ["COLORFUL"]),
        ("影驰", ["GALAX"]),
        ("威刚", ["ADATA"]),
        ("宇瞻", ["APACER"]),
        ("金泰克", ["TIGO"]),
        ("浦科特", ["PLEXTOR"]),
        ("致态", ["ZHITAI"]),
        ("海康威视", ["HIKVISION"]),
        ("联想", ["LENOVO"]),
        ("光威", ["GLOWAY", "GW-"]),
    ]
    for cn, keys in table:
        for k in keys:
            if k in m:
                return cn
    return ""


def _classify_disk_type(media, bus, model):
    """
    综合 MediaType / BusType / 型号关键字 判定磁盘类型。
    改进点：
      - NVMe 总线一律视为 SSD（很多 NVMe 在 MediaType 上被标成 Unspecified）；
      - MediaType=Unspecified 不再粗暴归为机械盘，而是结合总线与型号关键字判断；
      - 返回 (类型代码, 展示标签)。
    """
    media = (media or "").upper()
    bus = (bus or "").upper()
    m = (model or "").lower()

    if media == "SSD" or bus == "NVME":
        dtype = "SSD"
    elif media == "HDD":
        dtype = "HDD"
    else:
        # Unspecified / SCM 等：进一步推断
        if bus == "NVME" or "nvme" in m or "ssd" in m or "m.2" in m:
            dtype = "SSD"
        else:
            dtype = "HDD"

    if dtype == "SSD":
        type_label = "SSD(NVMe)" if bus == "NVME" else "SSD"
    else:
        type_label = "机械HDD"
    return dtype, type_label


def _normalize_physical_disk(d):
    """把 Get-PhysicalDisk 的单条记录整理成统一结构"""
    media = d.get("MediaType")
    bus = d.get("BusType")
    size_bytes = int(d.get("Size") or 0)
    model = str(d.get("FriendlyName") or d.get("Model") or "未知型号").strip()

    _, type_label = _classify_disk_type(media, bus, model)
    size_label = _format_disk_size(size_bytes) if size_bytes else ""
    vendor = _detect_disk_vendor(model)
    return {
        "type_label": type_label,
        "model": model,
        "vendor": vendor,
        "size_bytes": size_bytes,
        "size_label": size_label,
    }


def _normalize_wmic_disk(model, size_bytes, media):
    """WMIC 降级方案：MediaType 基本无法区分 SSD/HDD，标记为待确认"""
    media_u = (media or "").upper()
    _, type_label = _classify_disk_type(media_u, "", model)
    # WMIC 无法可靠区分 SSD/HDD，未明确报 SSD/HDD 时标记为“磁盘”以示待确认
    if media_u not in ("SSD", "HDD"):
        type_label = "磁盘"
    size_label = _format_disk_size(size_bytes) if size_bytes else ""
    vendor = _detect_disk_vendor(model)
    return {
        "type_label": type_label,
        "model": model or "未知型号",
        "vendor": vendor,
        "size_bytes": size_bytes,
        "size_label": size_label,
    }


def _query_physical_disks():
    """
    统一抓取物理磁盘列表（类型/容量/型号/厂商）。
    优先 PowerShell Get-PhysicalDisk(输出 JSON，解析稳定)，
    失败再降级到 WMIC diskdrive。
    """
    disks = []

    # ---- 主方案：PowerShell -> JSON（解析稳定，不依赖表格列对齐）----
    try:
        ps = (
            "powershell -NoProfile -Command "
            "\"@(Get-PhysicalDisk | Select-Object MediaType,BusType,Size,FriendlyName) "
            "| ConvertTo-Json -Compress\""
        )
        res = subprocess.run(
            ps,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True,
            shell=True,
            encoding="gbk",
            timeout=15,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            # 单块硬盘时 ConvertTo-Json 返回的是对象而非数组，统一成列表
            if isinstance(data, dict):
                data = [data]
            for d in data:
                disks.append(_normalize_physical_disk(d))
    except Exception:
        disks = []

    if disks:
        return disks

    # ---- 降级方案：WMIC diskdrive /value ----
    try:
        cmd = "wmic diskdrive get Model,Size,MediaType /value"
        res = subprocess.run(
            cmd,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True,
            shell=True,
            encoding="gbk",
            timeout=15,
        )
        if res.returncode == 0:
            for blk in res.stdout.strip().split("\n\n"):
                model = size = media = None
                for line in blk.splitlines():
                    line = line.strip()
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "model":
                        model = v
                    elif k == "size":
                        size = v
                    elif k == "mediatype":
                        media = v
                if not model:
                    continue
                size_bytes = int(size) if (size and size.isdigit()) else 0
                disks.append(_normalize_wmic_disk(model, size_bytes, media))
    except Exception:
        pass

    return disks


def _query_disk_health():
    """
    抓取每块物理盘的 S.M.A.R.T. 健康信息：
      - OperationalStatus / HealthStatus（Win 自带，稳）
      - Get-StorageReliabilityCounter：通电时长(PowerOnHours)、温度(Temperature)、磨损(Wear)
    返回 dict：key = 复合键(FriendlyName|Size)，value = 健康字典。
    用 model+size 做合并键，这样即使与 _query_physical_disks 顺序不同也能正确合并。
    """
    import tempfile
    health_map = {}
    ps = (
        "$ErrorActionPreference = 'SilentlyContinue'\n"
        "$pds = @(Get-PhysicalDisk)\n"
        "$out = foreach ($pd in $pds) {\n"
        "    $c = $pd | Get-StorageReliabilityCounter\n"
        "    $temp = if ($c -and $c.Temperature) { $c.Temperature } else { $null }\n"
        "    $poh  = if ($c -and $c.PowerOnHours) { $c.PowerOnHours } else { $null }\n"
        "    $wear = if ($c -and $c.Wear) { $c.Wear } else { $null }\n"
        "    [PSCustomObject]@{\n"
        "        FriendlyName = $pd.FriendlyName\n"
        "        Size = $pd.Size\n"
        "        OperationalStatus = ($pd.OperationalStatus -join ';')\n"
        "        HealthStatus = $pd.HealthStatus\n"
        "        Temperature = $temp\n"
        "        PowerOnHours = $poh\n"
        "        Wear = $wear\n"
        "    }\n"
        "}\n"
        "$out | ConvertTo-Json -Compress\n"
    )
    fd, path = tempfile.mkstemp(suffix=".ps1")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(ps)
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True,
            encoding="gbk",
            timeout=30,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip())
            if isinstance(data, dict):
                data = [data]
            for d in data:
                fn = str(d.get("FriendlyName") or "")
                sz = str(d.get("Size") or "")
                health_map[f"{fn}|{sz}"] = d
    except Exception:
        pass
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
    return health_map


def _merge_disk_health(disks, health_map):
    """把健康信息合并进硬盘字典，新增 health_label / health_detail 字段"""
    for d in disks:
        key = f"{d.get('model', '')}|{d.get('size_bytes', '')}"
        h = health_map.get(key)
        if not h:
            # 退化匹配：仅按 model 前缀（应对 size 取整差异）
            for k, v in health_map.items():
                if k.startswith(f"{d.get('model', '')}|"):
                    h = v
                    break
        if not h:
            d["health_label"] = "未知"
            d["health_detail"] = ""
            continue

        op_u = str(h.get("OperationalStatus") or "").upper()
        hs_u = str(h.get("HealthStatus") or "").upper()
        if "UNHEALTHY" in hs_u or "FAILED" in op_u or "PREDICTIVE" in op_u:
            label = "故障/预警"
        elif "WARNING" in hs_u or "WARNING" in op_u or "DEGRADED" in op_u:
            label = "警告"
        elif hs_u == "HEALTHY" or "OK" in op_u or op_u == "":
            label = "健康"
        else:
            label = "未知"

        parts = []
        temp = h.get("Temperature")
        if temp is not None:
            try:
                t = float(temp)
                if t > 200:  # Windows 有时以开尔文返回
                    t = t - 273.15
                parts.append(f"温度{round(t)}°C")
            except Exception:
                pass
        poh = h.get("PowerOnHours")
        if poh is not None:
            try:
                hours = float(poh)
                if hours >= 24:
                    parts.append(f"通电{round(hours / 24)}天")
                elif hours > 0:
                    parts.append(f"通电{round(hours)}小时")
            except Exception:
                pass
        wear = h.get("Wear")
        if wear is not None:
            try:
                w = float(wear)
                if w > 0:
                    parts.append(f"磨损{round(w)}%")
            except Exception:
                pass
        d["health_label"] = label
        d["health_detail"] = "，".join(parts)
    return disks


def _summarize_disks(disks):
    """生成“硬盘”字段：SSD:512G + 机械HDD:1T"""
    if not disks:
        return "未知硬盘"
    parts = []
    for d in disks:
        if d["size_label"]:
            parts.append(f"{d['type_label']}:{d['size_label']}")
        else:
            parts.append(d["type_label"])
    return " + ".join(parts)


def _detail_disks(disks):
    """生成“硬盘详情”字段：厂商 型号 (类型:容量)"""
    if not disks:
        return "未知"
    parts = []
    for d in disks:
        name = (d["vendor"] + " " + d["model"]).strip() if d["vendor"] else d["model"]
        if d["size_label"]:
            parts.append(f"{name} ({d['type_label']}:{d['size_label']})")
        else:
            parts.append(f"{name} ({d['type_label']})")
    return " + ".join(parts)


# ============================================================
# 设备身份识别（制造商 / 型号 / 序列号 / UUID / 品牌）
# 关键改进：不再只看 computersystem.Model，而是综合
#   制造商(Manufacturer) + 产品厂商(Vendor) + 主板厂商 + BIOS厂商 + 型号
# 用关键字表做智能品牌识别，彻底解决“小米(TIMI)被识别成组装机”的问题。
# ============================================================

# 无效型号/制造商占位符，等于没查到
_INVALID_TOKENS = {
    "", "system product name", "to be filled by o.e.m.",
    "to be filled by o.e.m", "default string", "unknown",
    "none", "not specified", "not applicable", "n/a",
    "system manufacturer", "system version", "oem", "o.e.m.",
    "chassis manufacture", "type1productconfigid", "standard",
}

# 品牌关键字表：命中任一关键字即判定为对应中文品牌。
# 顺序有讲究——把更“专有”的关键字放前面（如 ALIENWARE 先于 DELL 无所谓，因为都归戴尔；
# 但 TIMI/REDMI 必须能命中小米，HONOR 要先于华为避免误判）。
_BRAND_KEYWORDS = [
    # 品牌中文名, [大写关键字列表]
    ("小米", ["XIAOMI", "TIMI", "REDMI", "REDMIBOOK", "MI NOTEBOOK", "MIBOOK", "天米"]),
    ("荣耀", ["HONOR", "MAGICBOOK", "HLY-", "BRK-", "NBR-", "GLO-", "FRI-"]),
    ("华为", ["HUAWEI", "MATEBOOK", "MATESTATION", "KLVL", "KLVD", "BOHK", "NBLK", "HKD-", "WRT-", "WAH9", "WAG9"]),
    ("联想", ["LENOVO", "THINKPAD", "THINKBOOK", "THINKCENTRE", "THINKSTATION",
              "IDEAPAD", "IDEACENTRE", "YOGA", "LEGION", "XIAOXIN", "YANGTIAN",
              "QITIANTIAN", "SAVIOR", "GEEKPRO", "ZHAOYANG"]),
    ("外星人", ["ALIENWARE", "AREA-51", "AREA51", "AURORA", "外星人"]),
    ("戴尔", ["DELL", "OPTIPLEX", "LATITUDE", "INSPIRON",
              "PRECISION", "VOSTRO", "XPS", "VICTUS", "OMNIBOOK"]),
    ("惠普", ["HP", "HEWLETT-PACKARD", "HEWLETT PACKARD", "COMPAQ", "ELITEBOOK",
              "PROBOOK", "PAVILION", "SPECTRE", "ENVY", "OMEN", "ELITEDESK",
              "PRODESK", "ZBOOK", "VICTUS"]),
    ("华硕", ["ASUS", "ASUSTEK", "ROG", "TUF", "VIVOBOOK", "ZENBOOK", "PROART",
              "EXPERTBOOK", "TIANXUAN", "LINGYAO", "WUWEI", "ADOL", "POXIAO"]),
    ("宏碁", ["ACER", "ASPIRE", "PREDATOR", "NITRO", "SWIFT", "TRAVELMATE",
              "CONCEPTD", "VERITON", "GATEWAY"]),
    ("微星", ["MSI", "MICRO-STAR", "MICRO STAR", "MEGABOOK", "MODERN",
              "PRESTIGE", "STEALTH", "RAIDER", "KATANA", "CROSSHAIR", "CYBORG"]),
    ("技嘉", ["GIGABYTE", "AORUS", "AERO"]),
    ("华擎", ["ASROCK"]),
    ("微软", ["MICROSOFT", "SURFACE"]),
    ("苹果", ["APPLE", "MACBOOK", "IMAC", "MACMINI", "MAC PRO", "MACSTUDIO"]),
    ("三星", ["SAMSUNG", "GALAXY BOOK", "GALAXYBOOK"]),
    ("LG", ["LG ELECTRONICS", "LGE ", "GRAM"]),
    ("雷蛇", ["RAZER", "BLADE"]),
    ("机械革命", ["MECHREVO", "机械革命", "JIGUANG", "KUANGSHI", "JIAOLONG", "WUJIE"]),
    ("神舟", ["HASEE", "神舟", "ZHANSHEN", "YOUYA", "JINGDUN"]),
    ("雷神", ["THUNDEROBOT", "雷神"]),
    ("机械师", ["MACHENIKE", "机械师"]),
    ("七彩虹", ["COLORFUL"]),
    ("索尼", ["SONY", "VAIO"]),
    ("富士通", ["FUJITSU"]),
    ("松下", ["PANASONIC"]),
    ("火影", ["HOTWAVE", "火影"]),
    ("吾空", ["WOOKONG", "吾空"]),
    ("玄派", ["XUANPAI", "玄派"]),
    ("京天", ["KOTIN", "京天"]),
    ("同方", ["TONGFANG", "清华同方", "TSINGHUA"]),
    ("攀升", ["IPASON", "攀升"]),
    ("宁美", ["NINGMEI", "宁美"]),
    ("名龙堂", ["名龙堂"]),
    ("海尔", ["HAIER", "海尔"]),
    ("方正", ["FOUNDER", "方正"]),
    ("GPD", ["GPD"]),
    ("零刻", ["BEELINK", "零刻"]),
    ("英特尔", ["INTEL", "NUC"]),
    ("VMware虚拟机", ["VMWARE"]),
    ("VirtualBox虚拟机", ["VIRTUALBOX", "INNOTEK"]),
    ("Hyper-V虚拟机", ["MICROSOFT CORPORATION VIRTUAL", "VIRTUAL MACHINE"]),
    ("QEMU虚拟机", ["QEMU", "BOCHS"]),
]

# Win32_SystemEnclosure ChassisTypes 代码 → 设备类型
_CHASSIS_MAP = {
    "1": "其他", "2": "未知", "3": "台式机", "4": "低矮台式机", "5": "披萨盒台式机",
    "6": "小型立式机", "7": "塔式机", "8": "便携设备", "9": "笔记本",
    "10": "笔记本", "11": "手持设备", "12": "扩展坞笔记本", "13": "一体机",
    "14": "子笔记本", "15": "紧凑台式机", "16": "小型台式机", "17": "服务器塔",
    "18": "扩展机箱", "21": "外接键盘设备", "22": "微型电脑", "23": "机架服务器",
    "24": "密封台式机", "30": "平板", "31": "笔记本", "32": "可拆卸平板",
    "34": "嵌入式", "35": "微型台式机", "36": "存根PC",
}

# 采集缓存：一次运行内只查询一次，避免多次 PowerShell 调用拖慢速度
_SYSTEM_IDENTITY_CACHE = None


def _clean_token(v):
    """清洗单个字段值，无效占位符统一转成空字符串"""
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in _INVALID_TOKENS:
        return ""
    return s


def _query_system_identity(force=False):
    """
    一次性抓取设备身份信息（制造商/型号/序列号/UUID/主板/BIOS/机箱类型）。
    优先 PowerShell CIM(JSON，稳定)，失败降级到 WMIC。结果缓存。
    """
    global _SYSTEM_IDENTITY_CACHE
    if _SYSTEM_IDENTITY_CACHE is not None and not force:
        return _SYSTEM_IDENTITY_CACHE

    info = {
        "cs_manufacturer": "", "cs_model": "", "cs_sku": "",
        "vendor": "", "product_name": "", "uuid": "", "sn": "", "version": "",
        "bios_manufacturer": "", "bios_serial": "", "bios_version": "",
        "board_manufacturer": "", "board_product": "", "board_serial": "",
        "chassis": "",
    }

    # ---- 主方案：PowerShell CIM -> JSON ----
    try:
        ps = (
            "powershell -NoProfile -Command "
            "\"$cs=Get-CimInstance Win32_ComputerSystem;"
            "$p=Get-CimInstance Win32_ComputerSystemProduct;"
            "$b=Get-CimInstance Win32_BIOS;"
            "$bb=Get-CimInstance Win32_BaseBoard;"
            "$e=Get-CimInstance Win32_SystemEnclosure;"
            "[PSCustomObject]@{"
            "csm=$cs.Manufacturer;csmodel=$cs.Model;sku=$cs.SystemSKUNumber;"
            "vendor=$p.Vendor;pname=$p.Name;uuid=$p.UUID;sn=$p.IdentifyingNumber;ver=$p.Version;"
            "biosm=$b.Manufacturer;biossn=$b.SerialNumber;biosver=$b.SMBIOSBIOSVersion;"
            "bbm=$bb.Manufacturer;bbp=$bb.Product;bbsn=$bb.SerialNumber;"
            "chassis=($e.ChassisTypes -join ',')"
            "} | ConvertTo-Json -Compress\""
        )
        res = subprocess.run(
            ps, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
            text=True, shell=True, encoding="gbk",
            timeout=20,
        )
        if res.returncode == 0 and res.stdout.strip():
            d = json.loads(res.stdout.strip())
            info["cs_manufacturer"] = _clean_token(d.get("csm"))
            info["cs_model"] = _clean_token(d.get("csmodel"))
            info["cs_sku"] = _clean_token(d.get("sku"))
            info["vendor"] = _clean_token(d.get("vendor"))
            info["product_name"] = _clean_token(d.get("pname"))
            info["uuid"] = _clean_token(d.get("uuid"))
            info["sn"] = _clean_token(d.get("sn"))
            info["version"] = _clean_token(d.get("ver"))
            info["bios_manufacturer"] = _clean_token(d.get("biosm"))
            info["bios_serial"] = _clean_token(d.get("biossn"))
            info["bios_version"] = _clean_token(d.get("biosver"))
            info["board_manufacturer"] = _clean_token(d.get("bbm"))
            info["board_product"] = _clean_token(d.get("bbp"))
            info["board_serial"] = _clean_token(d.get("bbsn"))
            info["chassis"] = _clean_token(d.get("chassis"))
    except Exception:
        pass

    # ---- 降级方案：WMIC 补齐仍为空的关键字段 ----
    if not info["cs_manufacturer"] or not info["cs_model"]:
        try:
            res = subprocess.run(
                "wmic computersystem get Manufacturer,Model /value",
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                text=True, shell=True, encoding="gbk",
                timeout=15,
            )
            for line in res.stdout.splitlines():
                line = line.strip()
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().lower()
                if k == "manufacturer" and not info["cs_manufacturer"]:
                    info["cs_manufacturer"] = _clean_token(v)
                elif k == "model" and not info["cs_model"]:
                    info["cs_model"] = _clean_token(v)
        except Exception:
            pass

    if not info["bios_serial"]:
        try:
            res = subprocess.run(
                "wmic bios get SerialNumber /value",
                capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
                text=True, shell=True, encoding="gbk",
                timeout=15,
            )
            for line in res.stdout.splitlines():
                if "serialnumber=" in line.lower():
                    info["bios_serial"] = _clean_token(line.split("=", 1)[1])
        except Exception:
            pass

    _SYSTEM_IDENTITY_CACHE = info
    return info


def _match_brand_keyword(text):
    """在给定文本中查找品牌关键字，命中返回中文品牌名，否则空串"""
    if not text:
        return ""
    t = text.upper()
    for cn, keys in _BRAND_KEYWORDS:
        for k in keys:
            if k in t:
                return cn
    return ""


def _detect_brand_smart(identity, brands_db=None):
    """
    智能品牌识别：按可靠性排序综合多个数据源。
      1) 制造商 Manufacturer（最可靠，小米=TIMI 在这里命中）
      2) 产品厂商 Vendor / BIOS 厂商
      3) 用户自建型号库（brands.json，覆盖冷门/自定义机型）
      4) 型号名 / SKU / 产品名 关键字
      5) 主板厂商关键字（组装机常用主板品牌兜底）
    全部未命中才返回“组装机”。
    """
    # 1. 制造商
    b = _match_brand_keyword(identity.get("cs_manufacturer"))
    if b:
        return b

    # 2. 产品厂商 / BIOS 厂商
    b = _match_brand_keyword(identity.get("vendor")) or \
        _match_brand_keyword(identity.get("bios_manufacturer"))
    if b:
        return b

    # 3. 用户自建型号库（把 组装机/未知 视为“没查到”）
    if brands_db is not None:
        for cand in (identity.get("cs_model"), identity.get("product_name"),
                     identity.get("board_product")):
            if not cand:
                continue
            try:
                r = brands_db.detect_brand_from_model(cand)
            except Exception:
                r = None
            if r and r not in ("组装机", "未知", "其他"):
                return r

    # 4. 型号 / SKU / 产品名 关键字
    for cand in (identity.get("cs_model"), identity.get("product_name"),
                 identity.get("cs_sku"), identity.get("version")):
        b = _match_brand_keyword(cand)
        if b:
            return b

    # 5. 主板厂商 / 主板型号（组装机白牌兜底）
    b = _match_brand_keyword(identity.get("board_manufacturer")) or \
        _match_brand_keyword(identity.get("board_product"))
    if b:
        return b

    return "组装机"


def _detect_device_type(identity):
    """根据机箱类型代码判定设备类型（笔记本/台式机/一体机等）"""
    chassis = identity.get("chassis") or ""
    for code in chassis.split(","):
        code = code.strip()
        if code in _CHASSIS_MAP:
            label = _CHASSIS_MAP[code]
            if label not in ("其他", "未知"):
                return label
    return "未知"


def _build_model_string(identity, brand):
    """
    组装一个清晰的“型号”展示字符串：
      - 优先用 computersystem.Model；
      - 若是 TM2107 这类裸代号或缺失，则结合产品名/主板型号补全；
      - 尽量带上品牌，避免只显示一串代号看不懂。
    """
    model = identity.get("cs_model") or identity.get("product_name") or ""
    # computersystem.Model 无效时，用主板型号兜底
    if not model:
        board = identity.get("board_product")
        if board:
            model = f"主板:{board}"

    if not model:
        # 实在没有型号，用设备类型+架构给个可读兜底
        dtype = _detect_device_type(identity)
        arch = platform.machine()
        base = dtype if dtype != "未知" else "组装机"
        return f"{base} (架构:{arch})"

    # 如果型号里不含品牌词，且品牌已知且不是组装机，则前缀品牌，便于人读
    if brand and brand not in ("组装机", "未知", "其他"):
        if brand.upper() not in model.upper() and \
           not _match_brand_keyword(model):
            return f"{brand} {model}"
    return model


class HardwareCollector:
    def __init__(self):
        from brand_database import BrandDatabase
        # 核心：必须创建这个实例，名字必须叫 brands_db
        self.brands_db = BrandDatabase()
        self.CREATE_NO_WINDOW = 0x08000000

    """硬件采集器"""
    @staticmethod
    def get_hardware_info():
        """获取深层硬件信息（涉及 WMI 查询，稍慢）"""
        from brand_database import BrandDatabase
        bar=BrandDatabase()

        # 0. 一次性抓取设备身份（制造商/型号/序列号/UUID/主板/机箱类型），后续复用
        log_step("① 正在采集设备身份(制造商/型号/序列号/UUID)...")
        identity = _query_system_identity()
        log_step("① 设备身份采集完成")

        # 2. 智能识别品牌（综合制造商+厂商+型号库+关键字+主板，修复小米等误判）
        brand = _detect_brand_smart(identity, bar)

        # 1. 组装可读型号（结合品牌，避免只显示裸代号）
        model = _build_model_string(identity, brand)

        # 设备识别编号（资产追溯用）
        device_type = _detect_device_type(identity)
        serial = identity.get("bios_serial") or identity.get("sn") or "未知"
        system_uuid = identity.get("uuid") or "未知"
        board_serial = identity.get("board_serial") or "未知"
        bios_version = identity.get("bios_version") or "未知"

        # 3. 获取 CPU
        log_step("② 正在采集 CPU...")
        cpu = HardwareCollector._get_cpu()
        log_step("② CPU采集完成")

        # 4. 获取内存 (总容量 + 详细信息)
        mem_info = psutil.virtual_memory()
        total_gb = mem_info.total / (1024 ** 3)
        memory = HardwareCollector._format_memory_total(total_gb)
        log_step("③ 正在采集内存信息...")
        memory_detail = HardwareCollector._get_memory_detail()
        log_step("③ 内存采集完成")

        # 5. 获取硬盘 (识别 SSD/HDD) —— 一次性查询，保证“硬盘”与“硬盘详情”完全一致
        _disks = _query_physical_disks()
        # 5.1 合并 S.M.A.R.T. 健康信息（通电时长/温度/磨损/健康状态）
        try:
            _disks = _merge_disk_health(_disks, _query_disk_health())
        except Exception:
            pass
        disk = _summarize_disks(_disks)
        disk_detail = _detail_disks(_disks)

        # 5.2 硬盘健康汇总
        health_parts = []
        for d in _disks:
            short = d.get("model", "")[:20]
            label = d.get("health_label", "未知")
            detail = f"({d['health_detail']})" if d.get("health_detail") else ""
            health_parts.append(f"{short}({label}){detail}")
        disk_health = " + ".join(health_parts) if health_parts else "未知"
        log_step("④ 硬盘/健康采集完成")

        # 获取操作系统信息（使用 WMIC 兜底，尽量显示完整版本）
        log_step("⑤ 正在采集操作系统信息...")
        os_info = HardwareCollector._get_os_info()
        log_step("⑤ 系统信息采集完成")

        # 获取计算机名
        computer_name = platform.node()

        # 获取当前用户
        try:
            current_user = getpass.getuser()
        except:
            current_user = os.environ.get('USERNAME', '未知用户')

        # 网络信息：IP + MAC（同一网卡）
        log_step("⑥ 正在采集网络(IP/MAC)信息...")
        ip, mac = get_ip_and_mac()
        log_step("⑥ 网络信息采集完成")

        # 显卡 / 主板信息
        log_step("⑦ 正在采集显卡/主板信息...")
        gpu = HardwareCollector._get_gpu_info()
        mainboard = HardwareCollector._get_baseboard_info()
        log_step("⑦ 显卡/主板采集完成")


        return {
            "当前用户":current_user,
            "计算机名称": computer_name,
            "品牌": brand,
            "型号": model,
            "设备类型": device_type,
            "序列号": serial,
            "系统UUID": system_uuid,
            "主板序列号": board_serial,
            "BIOS版本": bios_version,
            "CPU": cpu,
            "内存": memory,
            "内存详情": memory_detail,
            "硬盘": disk,
            "硬盘详情": disk_detail,
            "硬盘健康": disk_health,
            "操作系统": os_info,
            "ip地址": ip,
            "MAC地址": mac,
            "显卡": gpu,
            "主板信息": mainboard,
        }
        log_step("⑧ 全部采集完成 ✓")

    def get_brand_by_model(self, model_name):
        """
        统一的品牌识别函数：优先读文件，后走硬编码逻辑
        """
        from brand_database import BrandDatabase

        # 1. 实例化数据库（它内部会自动调用 get_program_real_path 找到数据存储/brands.json）
        db = BrandDatabase()

        # 2. 核心逻辑：先去 brands.json 里查
        # 这里的 detect_brand_from_model 会遍历 {"品牌": [型号列表]}
        brand = db.detect_brand_from_model(model_name)

        if brand != "未知":
            return brand  # 只要文件里有，直接返回，不再往下走

        # 3. 如果文件里没有，再走你原来的硬编码模糊匹配
        m = str(model_name).upper()
        if "ASUSTEK" in m or "ASUS" in m: return "华硕"
        if "LENOVO" in m: return "联想"
        if "HP" in m or "HEWLETT-PACKARD" in m: return "惠普"
        if "DELL" in m: return "戴尔"

        return "未知品牌"
    @staticmethod
    def _get_model1():
        """从注册表获取型号"""
        try:
            result = subprocess.run(['wmic', 'computersystem', 'get', 'model'],
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW, text=True, shell=True, encoding='gbk',
                                    timeout=15)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    model = lines[1].strip()
                    if model and model != 'System Product Name':
                        return model
        except:
            pass
        """从WMI获取型号"""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                               r"SYSTEM\CurrentControlSet\Control\SystemInformation")
            model = winreg.QueryValueEx(key, "SystemProductName")[0]
            if model and model != 'System Product Name':
                return str(model).strip()
        except:
            pass
        """从systeminfo命令获取型号"""
        try:
            result = subprocess.run(['systeminfo'], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True, shell=True, encoding='gbk',
    timeout=30)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if '系统型号:' in line or 'System Model:' in line:
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            model = parts[1].strip()
                            if model and model != 'System Product Name':
                                return model
        except:
            pass
        try:
            result = subprocess.run(['wmic', 'computersystem', 'get', 'model'],
                                    capture_output=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW, text=True, shell=True, encoding='gbk',
                                    timeout=15)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    model = lines[1].strip()
                    if model and model != 'System Product Name':
                        return model
        except:
            pass
        return "未知"

    @staticmethod
    def _get_model():
        """
        型号探测（统一走多源身份采集 + 智能品牌逻辑）。
        与 get_hardware_info 使用完全相同的数据源，保证一致。
        """
        try:
            from brand_database import BrandDatabase
            identity = _query_system_identity()
            brand = _detect_brand_smart(identity, BrandDatabase())
            return _build_model_string(identity, brand)
        except Exception:
            return f"组装机 (架构:{platform.machine()})"
    @staticmethod
    def _get_cpu():
        """获取 CPU 完整"""
        try:
            # 从注册表获取（最准确的名称）
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            return cpu_name.strip()

        except:
            return "未知"

    @staticmethod
    def _get_disk_info():
        """获取极简硬盘信息：类型+容量（委托给统一模块函数）"""
        return _summarize_disks(_query_physical_disks())

    @staticmethod
    def _get_disk_model_info():
        """获取硬盘品牌 / 型号 / 容量详情（委托给统一模块函数）"""
        return _detail_disks(_query_physical_disks())

    @staticmethod
    def _format_memory_total(gb_raw: float) -> str:
        """
        更细粒度的内存容量归类：
        4 / 6 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 / 128 ...
        """
        if gb_raw <= 3:
            return "2GB"
        if gb_raw <= 5:
            return "4GB"
        if gb_raw <= 7:
            return "6GB"
        if gb_raw <= 10:
            return "8GB"
        if gb_raw <= 14:
            return "12GB"
        if gb_raw <= 20:
            return "16GB"
        if gb_raw <= 28:
            return "24GB"
        if gb_raw <= 40:
            return "32GB"
        if gb_raw <= 56:
            return "48GB"
        if gb_raw <= 72:
            return "64GB"
        if gb_raw <= 104:
            return "96GB"
        if gb_raw <= 136:
            return "128GB"
        return f"{round(gb_raw)}GB"

    @staticmethod
    def _get_memory_detail():
        """
        通过 WMIC 获取每条内存条的容量、频率，并粗略推断代际
        形如：8GB DDR4 3200MHz x2 + 16GB DDR4 3200MHz x1
        """
        sticks = []
        try:
            cmd = "wmic memorychip get Capacity,Speed"
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                timeout=15,
            )
            if res.returncode != 0:
                return "未知"

            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            # 跳过表头
            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue
                try:
                    capacity_raw = int(parts[0])
                except Exception:
                    continue
                speed = None
                if len(parts) >= 2 and parts[1].isdigit():
                    speed = int(parts[1])

                gb = capacity_raw / (1024 ** 3)
                gb_rounded = int(round(gb))

                # 粗略推断 DDR 代际（仅作为参考）
                if speed is None:
                    ddr = "DDR(未知代)"
                elif speed >= 4000:
                    ddr = "DDR5"
                elif speed >= 2133:
                    ddr = "DDR4"
                elif speed >= 1333:
                    ddr = "DDR3"
                else:
                    ddr = "DDR(旧代)"

                sticks.append((gb_rounded, ddr, speed))
        except Exception:
            return "未知"

        if not sticks:
            return "未知"

        # 统计相同规格的条数
        summary = {}
        for gb, ddr, speed in sticks:
            key = (gb, ddr, speed)
            summary[key] = summary.get(key, 0) + 1

        parts = []
        for (gb, ddr, speed), count in sorted(summary.items(), key=lambda x: (x[0][1], x[0][0], x[0][2] or 0)):
            speed_str = f"{speed}MHz" if speed else "未知频率"
            if count > 1:
                parts.append(f"{gb}GB {ddr} {speed_str} x{count}")
            else:
                parts.append(f"{gb}GB {ddr} {speed_str}")

        return " + ".join(parts)

    @staticmethod
    def _get_gpu_info():
        """获取显卡信息"""
        # 优先使用 WMIC，兼容性较好
        try:
            cmd = "wmic path win32_videocontroller get Name"
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                encoding="gbk",
                timeout=15,
            )
            if res.returncode == 0:
                lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
                # 跳过表头
                names = [l for l in lines[1:] if l]
                if names:
                    return " | ".join(names)
        except Exception:
            pass

        return "未知显卡"

    @staticmethod
    def _get_baseboard_info():
        """获取主板简要信息：厂商 + 型号，并尝试翻译为中文品牌"""
        try:
            cmd = "wmic baseboard get Manufacturer,Product"
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                encoding="gbk",
                timeout=15,
            )
            if res.returncode != 0:
                return "未知主板"

            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            # 跳过表头，拿第一块主板的信息
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    manufacturer_raw = parts[0]
                    product = " ".join(parts[1:])

                    # 统一复用品牌关键字表（含小米/华为/荣耀/技嘉/微星等）
                    brand_cn = _match_brand_keyword(manufacturer_raw)

                    if brand_cn:
                        return f"{brand_cn} ({manufacturer_raw}) {product}"
                    else:
                        return f"{manufacturer_raw} {product}"
        except Exception:
            pass

        return "未知主板"

    @staticmethod
    def _get_os_info():
        """
        获取更准确的操作系统信息：
        优先 WMIC Caption + Version + OSArchitecture，失败再回退到 platform
        """
        # 1. 尝试 WMIC
        try:
            cmd = "wmic os get Caption,Version,OSArchitecture /value"
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                encoding="gbk",
                timeout=15,
            )
            if res.returncode == 0 and res.stdout:
                caption = ""
                version = ""
                arch = ""
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "caption":
                        caption = v
                    elif k == "version":
                        version = v
                    elif k == "osarchitecture":
                        arch = v
                parts = [p for p in [caption, version, arch] if p]
                if parts:
                    return " ".join(parts)
        except Exception:
            pass

        # 2. 回退到 platform
        try:
            return f"{platform.system()} {platform.release()} ({platform.machine()})"
        except Exception:
            return "未知操作系统"

