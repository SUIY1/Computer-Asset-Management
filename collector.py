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


def get_ip_address():
    """获取本机 IP 地址"""
    # 方法1：尝试 socket 连接（最快）
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        print(ip_address)
        s.close()
        if ip_address and not ip_address.startswith('169.254.'):
            return ip_address
    except:
        pass
    # 方法2：使用系统命令
    try:
        # Windows 系统
        if os.name == 'nt':
            cmd = 'powershell -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress"'
            result = subprocess.run(cmd, capture_output=True,
    creationflags=subprocess.CREATE_NO_WINDOW,   text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
    except:
        return "windows识别未知"
    # 方法3：通过主机名获取
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith('127.') and not ip.startswith('169.254.') and not ip.startswith('172.17.'):
                print(socket.gethostbyname_ex(hostname)[2])
                return ip
    except:
        pass

    return "未知"


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

        # 4. 获取内存 (转换成 GB)
        mem_info = psutil.virtual_memory()
        memory = f"{round(mem_info.total / (1024 ** 3))}GB"

        # 5. 获取硬盘 (识别 SSD/HDD)
        disk = HardwareCollector._get_disk_info()

        # 获取操作系统信息
        os_info = f"{platform.system()} {platform.release()}"

        # 获取计算机名
        computer_name = platform.node()

        # 获取当前用户
        try:
            current_user = getpass.getuser()
        except:
            current_user = os.environ.get('USERNAME', '未知用户')

        ip= get_ip_address()


        return {
            "当前用户":current_user,
            "计算机名称": computer_name,
            "型号": model,
            "品牌": brand,
            "CPU": cpu,
            "内存": memory,
            "硬盘": disk,
            "操作系统": os_info,
            "ip地址": ip
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

