import os
import platform
import socket
import sys
import psutil
import winreg
import subprocess
import getpass


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


def _format_disk_size( gb_raw):
        """将不规则的原始容量归类为标准档位"""
        val = float(gb_raw)

        # 1. 处理 T 级硬盘 (大于 700G 统一往 1T 以上靠)
        if val >= 700:
            tb_val = round(val / 1024)
            return f"{tb_val if tb_val > 0 else 1}T"

        # 2. 处理 G 级硬盘 (模糊匹配常见档位)
        if val < 180:
            return "120G"  # 涵盖 110G-128G
        elif 180 <= val < 380:
            return "256G"  # 涵盖 220G-256G
        elif 380 <= val < 700:
            return "500G"  # 涵盖 440G-512G
        else:
            return f"{round(val)}G"  # 其他非常规容量原样显示



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
        # 1. 获取型号
        model = HardwareCollector._get_model()

        # 2. 识别品牌
        brand = bar.detect_brand_from_model(model)

        # 3. 获取 CPU
        cpu = HardwareCollector._get_cpu()

        # 4. 获取内存 (总容量 + 详细信息)
        mem_info = psutil.virtual_memory()
        total_gb = mem_info.total / (1024 ** 3)
        memory = HardwareCollector._format_memory_total(total_gb)
        memory_detail = HardwareCollector._get_memory_detail()

        # 5. 获取硬盘 (识别 SSD/HDD)
        disk = HardwareCollector._get_disk_info()
        disk_detail = HardwareCollector._get_disk_model_info()

        # 获取操作系统信息（使用 WMIC 兜底，尽量显示完整版本）
        os_info = HardwareCollector._get_os_info()

        # 获取计算机名
        computer_name = platform.node()

        # 获取当前用户
        try:
            current_user = getpass.getuser()
        except:
            current_user = os.environ.get('USERNAME', '未知用户')

        # 网络信息：IP + MAC（同一网卡）
        ip, mac = get_ip_and_mac()

        # 显卡 / 主板信息
        gpu = HardwareCollector._get_gpu_info()
        mainboard = HardwareCollector._get_baseboard_info()


        return {
            "当前用户":current_user,
            "计算机名称": computer_name,
            "型号": model,
            "品牌": brand,
            "CPU": cpu,
            "内存": memory,
            "内存详情": memory_detail,
            "硬盘": disk,
            "硬盘详情": disk_detail,
            "操作系统": os_info,
            "ip地址": ip,
            "MAC地址": mac,
            "显卡": gpu,
            "主板信息": mainboard,
        }

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
                                    creationflags=subprocess.CREATE_NO_WINDOW, text=True, shell=True, encoding='gbk')
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
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True, shell=True, encoding='gbk')
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
                                    creationflags=subprocess.CREATE_NO_WINDOW, text=True, shell=True, encoding='gbk')
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
        """增强版型号探测：五级尝试逻辑"""

        # 排除名单：这些字符串等于没查到
        invalid_models = ['System Product Name', 'To be filled by O.E.M.', 'Default string', 'Unknown', 'None', '']

        # --- 第一级：标准 WMIC 查询 ---
        try:
            res = subprocess.run(['wmic', 'computersystem', 'get', 'model'], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True,
                                 encoding='gbk')
            model = res.stdout.strip().split('\n')[-1].strip()
            if model and model not in invalid_models:
                return model
        except:
            pass

        # --- 第二级：PowerShell CIM 探测 (针对现代系统更底层) ---
        try:
            cmd = 'Get-CimInstance Win32_ComputerSystemProduct | Select-Object -ExpandProperty Name'
            res = subprocess.run(['powershell', '-Command', cmd], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True, encoding='gbk')
            ps_model = res.stdout.strip()
            if ps_model and ps_model not in invalid_models:
                return ps_model
        except:
            pass

        # --- 第三级：主板探测 (组装机/白牌机神器) ---
        try:
            res = subprocess.run(['wmic', 'baseboard', 'get', 'product'], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True,
                                 encoding='gbk')
            board = res.stdout.strip().split('\n')[-1].strip()
            if board and board not in invalid_models:
                return f"主板:{board}"
        except:
            pass

        # --- 第四级：注册表硬路径 ---
        import winreg
        try:
            path = r"HARDWARE\DESCRIPTION\System\BIOS"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            reg_model, _ = winreg.QueryValueEx(key, "SystemProductName")
            if reg_model and reg_model not in invalid_models:
                return str(reg_model).strip()
        except:
            pass

        # --- 第五级：最终保底 (硬件指纹拼凑) ---
        # 如果实在查不到名字，我们就用 CPU 型号告诉管理员这是台什么性能的机器
        cpu_simple = platform.processor().split(',')[0]  # 拿到类似 Intel64 Family...
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
        """获取极简硬盘信息：类型+容量"""
        disks_summary = []
        try:
            # 1. 使用 PowerShell 获取媒体类型和物理大小
            cmd = 'Get-PhysicalDisk | Select-Object MediaType, Size'
            res = subprocess.run(['powershell', '-Command', cmd], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True, encoding='gbk')

            if res.returncode == 0:
                lines = res.stdout.strip().split('\n')
                # 跳过表头和横线（前两行）
                for line in lines[2:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        raw_type = parts[0].upper()  # 拿到 SSD 或 HDD
                        raw_size = int(parts[1])

                        # 容量转换逻辑 (GB/TB)
                        gb_size = raw_size / (1024 ** 3)
                        size_label = _format_disk_size(gb_size)
                        # if gb_size >= 900:  # 大于 900G 自动显示为 T
                        #     size_str = f"{round(gb_size / 1024, 1)}T"
                        # else:
                        #     size_str = f"{round(gb_size)}G"

                        # 类型转换
                        type_label = "SSD" if "SSD" in raw_type else "机械"
                        disks_summary.append(f"{type_label}:{size_label}")
        except:
            pass

        # 2. 如果 PowerShell 失败（旧系统），则使用 WMIC 兜底（WMIC 很难分 SSD/HDD，默认标为“磁盘”）
        if not disks_summary:
            try:
                res = subprocess.run(['wmic', 'diskdrive', 'get', 'size'], capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True)
                sizes = [line.strip() for line in res.stdout.split('\n') if line.strip().isdigit()]
                for s in sizes:
                    gb = round(int(s) / (1024 ** 3))
                    disks_summary.append(f"磁盘:{gb}G")
            except:
                pass

        # 3. 最终组合输出
        if disks_summary:
            # 如果有多个硬盘，用加号连接：SSD:512G + 机械:1T
            return " + ".join(disks_summary)
        else:
            return "未知硬盘"

    @staticmethod
    def _get_disk_model_info():
        """
        获取硬盘品牌 / 型号 等更详细信息
        例如：Samsung SSD 980 1TB (SSD:512G) + WDC WD10EZEX (机械:1T)
        这里只关注型号文本，容量仍以 _get_disk_size 结果为准
        """
        disks = []
        try:
            cmd = "wmic diskdrive get Model,Size"
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                text=True,
                shell=True,
                encoding="gbk",
            )
            if res.returncode != 0:
                return "未知"

            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            # 跳过表头
            for line in lines[1:]:
                # WMIC 输出类似：ModelText        512110190592
                parts = line.split()
                if len(parts) < 2:
                    continue
                # 最后一个通常是 Size
                size_part = parts[-1]
                model_text = " ".join(parts[:-1])
                size_label = ""
                if size_part.isdigit():
                    try:
                        gb = int(size_part) / (1024 ** 3)
                        size_label = _format_disk_size(gb)
                    except Exception:
                        size_label = ""

                if size_label:
                    disks.append(f"{model_text} ({size_label})")
                else:
                    disks.append(model_text)
        except Exception:
            return "未知"

        if not disks:
            return "未知"
        return " + ".join(disks)

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

                    m_upper = manufacturer_raw.upper()
                    # 常见主板厂商到中文品牌的映射
                    if "ASUS" in m_upper or "ASUSTEK" in m_upper:
                        brand_cn = "华硕"
                    elif "GIGABYTE" in m_upper or "TECHNOLOGYCO" in m_upper:
                        brand_cn = "技嘉"
                    elif "MSI" in m_upper or "MICRO-STAR" in m_upper:
                        brand_cn = "微星"
                    elif "ASROCK" in m_upper:
                        brand_cn = "华擎"
                    elif "LENOVO" in m_upper:
                        brand_cn = "联想"
                    elif "DELL" in m_upper:
                        brand_cn = "戴尔"
                    elif "HP" in m_upper or "HEWLETT-PACKARD" in m_upper:
                        brand_cn = "惠普"
                    elif "HUAWEI" in m_upper:
                        brand_cn = "华为"
                    else:
                        brand_cn = None

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

