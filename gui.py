# gui.py
from collector import HardwareCollector
from data_handler import DataHandler

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import os
import re
import json
import webbrowser
from datetime import datetime


def _is_lan_url(u):
    """判断一个地址是否是局域网地址（http://IP:端口）"""
    return bool(re.match(r"^https?://\d{1,3}(\.\d{1,3}){3}(:\d+)?$", u or ""))





class AssetToolGUI:
    def __init__(self, root):
        self.root = root
        # 获取 exe 所在的绝对路径，确保能读取到 brands.json
        from collector import get_data_file_path
        self.brands_path = get_data_file_path("brands.json")

        self.root.title("计算机资产管理工具 (Pro版)")
        self.root.geometry("1500x720")

        # --- 1. 样式与图标设置 ---
        self.setup_styles()


        # --- 2. 初始化核心模块 ---
        self.handler = DataHandler()
        self.collector = HardwareCollector()
        self.computers_data = self.handler.load_data()

        # --- 3. 变量初始化 ---
        self.init_variables()

        # --- 4. 构建界面 ---
        self.setup_ui()

        self.refresh_table()
        threading.Thread(target=self.auto_scan_and_prompt, daemon=True).start()
        # --- 5. 初始加载 ---
        # self.refresh_table()
        # 绑定窗口关闭协议
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动后稍微延迟一点获取基础信息，避免界面卡顿
        self.root.after(200, self.load_basic_info)

    def auto_scan_and_prompt(self):
        """后台扫描 -> 更新表格 -> 自动引导录入"""
        # 1. 先通过 after 通知主线程更新状态文字
        self.root.after(0, lambda: self.status_var.set("🚀 正在自动扫描硬件，请稍候..."))

        # 2. 执行耗时扫描 (在子线程跑，不会卡死界面)
        try:
            hardware_data = self.collector.get_hardware_info()
            # 3. 回到主线程更新 UI 和处理弹窗
            self.root.after(0, lambda: self.finish_auto_task(hardware_data))
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda m=error_msg: self.status_var.set(f"❌ 扫描出错: {m}"))



    def finish_auto_task(self, data):
        """当后台扫描任务彻底完成时调用"""
        # 1. 更新顶部 info_vars 面板（让用户看到实时数据）
        for key in self.info_vars:
            if key in data:
                self.info_vars[key].set(data[key])

        # 2. 将新扫描的数据放入内存列表
        # 这里调用写好的去重逻辑函数
        self.update_table_with_data(data)

        self.status_var.set("✅ 自动扫描完成，请补充资产归属")

        # 3. 自动引导录入
        self.prompt_user_info(data)

    def prompt_user_info(self, data):
        """自动弹窗引导用户输入部门和姓名"""
        from tkinter import simpledialog

        # 获取计算机名作为提示
        pc_name = data.get("计算机名称", "本机")

        # 弹出输入框
        dept = simpledialog.askstring("归档引导", "已完成查询，请输入所属【部门】:", parent=self.root)
        if not dept:
            self.status_var.set("⚠️ 用户取消了信息补充")
            return

        user = simpledialog.askstring("归档引导", f"请输入【现使用人】姓名:", parent=self.root)
        if not user: return

        # 1. 完善数据对象
        data["部门"] = dept if dept else "-"
        data["现使用人"] = user if user else "-"
        data["收集时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.save_to_json()
        self.refresh_table()



    def init_variables(self):
        """初始化界面显示的变量"""
        self.info_vars = {
            "计算机名称": tk.StringVar(value="-"),
            "ip地址": tk.StringVar(value="-"),
            "MAC地址": tk.StringVar(value="-"),
            "当前用户": tk.StringVar(value="-"),
            "品牌": tk.StringVar(value="-"),
            "型号": tk.StringVar(value="-"),
            "设备类型": tk.StringVar(value="-"),
            "序列号": tk.StringVar(value="-"),
            "系统UUID": tk.StringVar(value="-"),
            "主板序列号": tk.StringVar(value="-"),
            "BIOS版本": tk.StringVar(value="-"),
            "CPU": tk.StringVar(value="-"),
            "内存": tk.StringVar(value="-"),
            "内存详情": tk.StringVar(value="-"),
            "硬盘": tk.StringVar(value="-"),
            "硬盘健康": tk.StringVar(value="-"),
            "操作系统": tk.StringVar(value="-"),
            "显卡": tk.StringVar(value="-"),
            "主板信息": tk.StringVar(value="-"),
        }
        self.status_var = tk.StringVar(value="✅ 系统就绪")
        self.count_var = tk.StringVar(value="0")
        self.path_var = tk.StringVar(value=f"数据存储于: {os.path.basename(self.handler.data_dir)}")

    def update_table_with_data(self, new_item):
        """将扫描到的单条数据同步到表格中"""
        # 1. 检查数据是否完整
        if not new_item: return

        # 2. 更新本地内存数据

        self.computers_data.append(new_item)

        # 3. 真正刷新 Treeview 控件
        self.refresh_table()
    def setup_styles(self):
        """配置美化样式"""
        style = ttk.Style()
        # Windows 默认主题
        if "vista" in style.theme_names():
            style.theme_use("vista")

        # 字体配置
        base_font = ('微软雅黑', 10)
        bold_font = ('微软雅黑', 10, 'bold')

        # 按钮样式
        style.configure('Primary.TButton', font=bold_font, foreground="#005fb8")  # 蓝色重点
        style.configure('Success.TButton', font=bold_font, foreground="#2e7d32")  # 绿色导出
        style.configure('Danger.TButton', font=bold_font, foreground="#c62828")  # 红色删除
        style.configure('Normal.TButton', font=base_font)

        # 表格样式
        style.configure("Treeview.Heading", font=bold_font)
        style.configure("Treeview", font=base_font, rowheight=25)

    def setup_ui(self):
        """构建精细化布局"""
        self.status_var = tk.StringVar(value="准备就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # self.status_label.config(text="🚀 正在自动扫描硬件，请稍候...")
        # === 顶部：当前机器信息面板 ===
        info_frame = ttk.LabelFrame(self.root, text="📋 本机实时状态", padding=15)
        info_frame.pack(fill="x", padx=10, pady=5)
        # self.tree = ttk.Treeview(self.main_frame, columns=self.columns, show='headings')


        # 使用 Grid 布局模仿旧版样式的网格展示
        cols = [
            "计算机名称",
            "ip地址",
            "MAC地址",
            "当前用户",
            "品牌",
            "型号",
            "设备类型",
            "序列号",
            "系统UUID",
            "主板序列号",
            "BIOS版本",
            "操作系统",
            "CPU",
            "内存",
            "内存详情",
            "硬盘",
            "硬盘健康",
            "显卡",
            "主板信息",
        ]

        for i, key in enumerate(cols):
            row = i // 3  # 每行3个
            col = (i % 3) * 2

            # 标签名
            ttk.Label(info_frame, text=f"{key}:", font=('微软雅黑', 10, 'bold'), foreground="#555").grid(row=row,
                                                                                                         column=col,
                                                                                                         sticky="e",
                                                                                                         padx=5, pady=5)
            # 值
            ttk.Label(info_frame, textvariable=self.info_vars[key], foreground="#005fb8").grid(row=row, column=col + 1,
                                                                                               sticky="w", padx=(0, 20),
                                                                                               pady=5)

        # === 中部：功能按钮区 ===
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=10)

        # 左侧操作按钮
        ttk.Button(btn_frame, text="🔍 深度采集本机", command=self.run_scan_thread, style='Primary.TButton',
                   width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✏️ 手动录入信息", command=self.open_manual_input_window, style='Normal.TButton',
                   width=15).pack(side="left", padx=5)
        # 新增：添加品牌映射按钮
        ttk.Button(btn_frame, text="📝 录入型号", command=self.add_custom_brand_mapping).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🏷️添加品牌", command=self.add_new_brand_only).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔍 查看品牌库", command=self.show_all_brands_window, style='Normal.TButton').pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🌐 批量采集", command=self.open_batch_window, style='Primary.TButton').pack(side="left", padx=5)
        # 右侧功能按钮
        ttk.Button(btn_frame, text="📂 打开数据目录", command=self.open_data_folder, style='Normal.TButton').pack(
            side="right", padx=5)
        ttk.Button(btn_frame, text="📊 导出 Excel", command=self.export_excel, style='Success.TButton').pack(
            side="right", padx=5)
        ttk.Button(btn_frame, text="💾 保存数据", command=self.save_to_json, style='Normal.TButton').pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text="✏️ 编辑选中记录", command=self.edit_record, style='Normal.TButton').pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text="🗑 删除选中记录", command=self.delete_record, style='Danger.TButton').pack(
            side="right", padx=5
        )

        # === 底部：数据表格 ===
        table_frame = ttk.LabelFrame(self.root, text="🗄️ 资产列表", padding=5)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 定义列
        self.columns = (
            "计算机名称",
            "ip地址",
            "MAC地址",
            "当前用户",
            "品牌",
            "型号",
            "设备类型",
            "序列号",
            "系统UUID",
            "主板序列号",
            "BIOS版本",
            "CPU",
            "内存",
            "内存详情",
            "硬盘",
            "硬盘健康",
            "显卡",
            "主板信息",
            "操作系统",
            "部门",
            "现使用人",
            "收集时间",
        )
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", selectmode="extended")

        # 滚动条
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 布局表格
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # 设置表头
        col_widths = {
            "计算机名称": 120,
            "ip地址": 140,
            "MAC地址": 130,
            "当前用户": 80,
            "品牌": 80,
            "型号": 160,
            "设备类型": 80,
            "序列号": 150,
            "系统UUID": 230,
            "主板序列号": 150,
            "BIOS版本": 110,
            "CPU": 220,
            "内存": 80,
            "内存详情": 180,
            "硬盘": 220,
            "硬盘健康": 220,
            "显卡": 220,
            "主板信息": 200,
            "操作系统": 160,
            "部门": 80,
            "现使用人": 80,
            "收集时间": 150,
        }

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths.get(col, 100), anchor="center")

        # 绑定事件：右键菜单 + 双击编辑
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_row_double_click)



        # === 最底部：状态栏 ===
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill="x", side="bottom", padx=10, pady=5)

        ttk.Label(status_bar, textvariable=self.path_var, foreground="gray").pack(side="left")
        ttk.Label(status_bar, textvariable=self.status_var, foreground="#2e7d32").pack(side="right", padx=10)
        ttk.Label(status_bar, textvariable=self.count_var).pack(side="right")
        ttk.Label(status_bar, text="总记录数: ").pack(side="right")

        ttk.Button(btn_frame, text="ℹ️ 关于", command=self.show_about).pack(side="right", padx=5)


    # --- 逻辑功能 ---


    def load_basic_info(self):
        """加载基础信息显示在顶部面板"""
        info = self.collector.get_hardware_info()
        # 更新顶部面板的变量
        self.info_vars["计算机名称"].set(info.get('计算机名称', '-'))
        self.info_vars["ip地址"].set(info.get('ip地址', '-'))
        self.info_vars["MAC地址"].set(info.get('MAC地址', '-'))
        self.info_vars["当前用户"].set(info.get('当前用户', '-'))
        self.info_vars["品牌"].set(info.get('品牌', '-'))
        self.info_vars["型号"].set(info.get('型号', '-'))
        self.info_vars["设备类型"].set(info.get('设备类型', '-'))
        self.info_vars["序列号"].set(info.get('序列号', '-'))
        self.info_vars["系统UUID"].set(info.get('系统UUID', '-'))
        self.info_vars["主板序列号"].set(info.get('主板序列号', '-'))
        self.info_vars["BIOS版本"].set(info.get('BIOS版本', '-'))
        self.info_vars["CPU"].set(info.get('CPU', '-'))
        self.info_vars["内存"].set(info.get('内存', '-'))
        self.info_vars["内存详情"].set(info.get('内存详情', '-'))
        self.info_vars["硬盘"].set(info.get('硬盘', '-'))
        self.info_vars["硬盘健康"].set(info.get('硬盘健康', '-'))
        self.info_vars["显卡"].set(info.get('显卡', '-'))
        self.info_vars["主板信息"].set(info.get('主板信息', '-'))

    def run_scan_thread(self):
        """多线程执行深度扫描"""
        self.status_var.set("⏳ 正在进行深度硬件扫描...")
        t = threading.Thread(target=self._scan_logic, daemon=True)
        t.start()

    def _scan_logic(self):
        try:
            # 1. 采集
            data = self.collector.get_hardware_info()

            # 2. 补充默认空字段
            data["部门"] = "-"
            data["现使用人"] = "-"
            data["收集时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 4. 更新UI
            self.root.after(0, self.on_scan_complete, data)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

    def detect_brand(self, model):
        """简单的品牌推断逻辑"""
        model = model.lower()
        if "lenovo" in model or "think" in model: return "联想"
        if "dell" in model or "optiplex" in model: return "戴尔"
        if "hp" in model or "probook" in model: return "惠普"
        if "asus" in model: return "华硕"
        return "其他"

    def on_scan_complete(self, new_data):
        # 更新顶部面板的详细信息
        for k, v in new_data.items():
            if k in self.info_vars:
                self.info_vars[k].set(v)

        # 存入列表
        self.computers_data.append(new_data)
        self.refresh_table()
        self.status_var.set("✅ 采集成功！记得保存数据")

        # 自动弹窗询问部门
        if messagebox.askyesno("采集完成", "是否立即补充【部门】和【使用人】信息？"):
            self.tree.selection_set(self.tree.get_children()[-1])  # 选中最后一行
            self.add_manual_info()

    def open_manual_input_window(self):
        """打开手动录入窗口 (功能复刻)"""
        top = tk.Toplevel(self.root)
        top.title("手动录入资产信息")
        top.geometry("430x1040")
        top.attributes("-topmost", True)  # 1. 强制窗口显示在所有窗口的最前面
        top.grab_set()  # 2. 锁定焦点，此时用户无法点击主界面，必须先处理这个窗口
        top.focus_set()  # 3. 自动将输入焦点移动到这个新窗口
        # --- 核心改进：先抓取一次硬件信息作为底稿 ---
        try:
            base_data = self.collector.get_hardware_info()
        except:
            base_data = {}
        entries = {}
        fields = [
            ("计算机名称", base_data.get("计算机名称", "")),
            ("ip地址", base_data.get("ip地址", "")),
            ("MAC地址", base_data.get("MAC地址", "")),
            ("当前用户", base_data.get("当前用户", "")),
            ("品牌", base_data.get("品牌", "")),
            ("型号", base_data.get("型号", "")),
            ("设备类型", base_data.get("设备类型", "")),
            ("序列号", base_data.get("序列号", "")),
            ("系统UUID", base_data.get("系统UUID", "")),
            ("CPU", base_data.get("CPU", "")),
            ("内存", base_data.get("内存", "")),
            ("内存详情", base_data.get("内存详情", "")),
            ("硬盘", base_data.get("硬盘", "")),
            ("硬盘详情", base_data.get("硬盘详情", "")),
            ("显卡", base_data.get("显卡", "")),
            ("主板信息", base_data.get("主板信息", "")),
            ("部门", ""),
            ("现使用人", "")
        ]

        for i, (label_text, default_val) in enumerate(fields):
            ttk.Label(top, text=f"{label_text}:").pack(anchor="w", padx=30, pady=(10, 0))
            e = ttk.Entry(top, width=40)
            e.insert(0, str(default_val))  # 预填数据
            e.pack(padx=30, pady=5)
            entries[label_text] = e

        def submit():
            # 整合数据
            new_record = base_data.copy()  # 以硬件信息为基础
            for label_text, entry in entries.items():
                new_record[label_text] = entry.get()

            # 补全其他信息
            new_record["收集时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 确保硬件字段不会显示“手动录入”
            for col in [
                "CPU",
                "内存",
                "内存详情",
                "硬盘",
                "硬盘详情",
                "显卡",
                "主板信息",
                "操作系统",
                "MAC地址",
                "ip地址",
            ]:
                if not new_record.get(col) or new_record.get(col) == "未知":
                    new_record[col] = base_data.get(col, "采集失败")

            self.computers_data.append(new_record)
            self.refresh_table()
            top.destroy()
            messagebox.showinfo("成功", "记录已添加至列表")

        ttk.Button(top, text="确认提交", command=submit).pack(pady=25)

    def refresh_table(self):
        self.collector.brands_db.reload()
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 重新填充
        for data in self.computers_data:
            values = [data.get(col, "") for col in self.columns]
            self.tree.insert("", "end", values=values)

        self.count_var.set(str(len(self.computers_data)))

    def save_to_json(self):
        if self.handler.save_data(self.computers_data):
            self.status_var.set(f"✅ 数据已保存 ({datetime.now().strftime('%H:%M:%S')})")
            messagebox.showinfo("保存成功", "数据已成功写入 JSON 文件")
            return True
        else:
            messagebox.showerror("错误", "保存失败")
            return False

    def export_excel(self):
        success, msg = self.handler.export_to_excel(self.computers_data)
        if success:
            if messagebox.askyesno("导出成功", f"文件位于:\n{msg}\n\n是否立即打开？"):
                os.startfile(msg)
        else:
            messagebox.showerror("导出失败", msg)

    def open_data_folder(self):
        """打开数据存储文件夹"""
        path = self.handler.data_dir
        os.startfile(path)

    # --- 右键菜单功能 ---
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="✏️ 编辑该条记录", command=self.edit_record)
            menu.add_command(label="📝 修改部门/人员信息", command=self.add_manual_info)
            menu.add_separator()
            menu.add_command(label="❌ 删除该条记录", command=self.delete_record)
            menu.post(event.x_root, event.y_root)



    def add_manual_info(self):

        selected = self.tree.selection()
        if not selected: return

        dept = simpledialog.askstring("补充信息", "请输入部门名称:",parent=self.root)
        user = simpledialog.askstring("补充信息", "请输入现使用人:",parent=self.root)

        idx = self.tree.index(selected[0])
        if dept: self.computers_data[idx]["部门"] = dept
        if user: self.computers_data[idx]["现使用人"] = user
        self.refresh_table()

    def delete_record(self):
        selected = self.tree.selection()
        if selected:
            if messagebox.askyesno("确认", "确定要删除这条记录吗？"):
                idx = self.tree.index(selected[0])
                del self.computers_data[idx]
                self.refresh_table()

    def on_row_double_click(self, event):
        """双击表格行，直接进入编辑模式"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.edit_record()

    def edit_record(self):
        """编辑当前选中的整条记录（所有字段）"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先选中一条需要编辑的记录。")
            return

        idx = self.tree.index(selected[0])
        base_data = dict(self.computers_data[idx])  # 复制原始数据，避免直接修改引用

        top = tk.Toplevel(self.root)
        top.title("编辑资产记录")
        # 稍微加高一点，保证字段完整显示
        top.geometry("430x820")
        top.attributes("-topmost", True)
        top.grab_set()
        top.focus_set()

        entries = {}

        # 按列顺序展示可编辑字段
        edit_fields = [
            "计算机名称",
            "ip地址",
            "MAC地址",
            "当前用户",
            "品牌",
            "型号",
            "CPU",
            "内存",
            "硬盘",
            "显卡",
            "主板信息",
            "操作系统",
            "部门",
            "现使用人",
        ]

        for i, key in enumerate(edit_fields):
            ttk.Label(top, text=f"{key}:").pack(anchor="w", padx=30, pady=(8, 0))
            e = ttk.Entry(top, width=40)
            e.insert(0, str(base_data.get(key, "")))
            e.pack(padx=30, pady=3)
            entries[key] = e

        def submit_edit():
            # 以原始记录为基础更新
            new_record = base_data.copy()
            for key, entry in entries.items():
                new_record[key] = entry.get()

            # 写回列表并刷新
            self.computers_data[idx] = new_record
            self.refresh_table()
            top.destroy()
            messagebox.showinfo("成功", "记录已更新")

        ttk.Button(top, text="保存修改", command=submit_edit).pack(pady=20)



    def show_about(self):
        """弹出关于窗口"""
        about_win = tk.Toplevel(self.root)
        about_win.title("关于软件")
        about_win.geometry("400x250")
        about_win.resizable(False, False)

        # 强制该窗口置顶，处理完才能回主界面
        about_win.grab_set()

        # --- 1. 中间的主体文案 (左对齐，正常显示) ---
        main_text = (
            "🚀 计算机资产管理工具 Pro\n"
            "版本：v1.0.0\n\n"
            "本工具旨在帮助运维人员快速采集硬件指纹，\n"
            "支持一键导出，让资产盘点不再是苦差事.\n"
            "“代码是冷的，但解决问题的成就感是热的。”\n"
            "SUI缘儿科技:一个爱分享的小小白，你的点赞是我最大的动力"
        )
        ttk.Label(about_win, text=main_text, padding=20, justify="left").pack(fill="both", expand=True)

        # --- 2. 右下角的蓝色文字 (你的感悟和创作信息) ---
        # 创建一个容器，专门用来放右下角的字
        footer_frame = ttk.Frame(about_win)
        footer_frame.pack(side="bottom", fill="x", padx=15, pady=10)

        my_words = (
            "—— 一个异想天开的低层IT运维工程师 🛠️\n"
            "Created by [SUI缘儿科技] @ 2026"
        )

        # foreground="blue" 设置蓝色，anchor="e" 设置靠右 (East)
        personal_label = tk.Label(
            footer_frame,
            text=my_words,
            fg="#005fb8",  # 蓝色 (可以微调色号)
            font=("微软雅黑", 9, "italic"),
            justify="right"
        )
        personal_label.pack(side="right")  # 靠右排列

    # --- 批量采集（中心服务器 + 轻量 agent）---
    def _detect_lan_ip(self):
        """获取本机局域网 IP，用于局域网模式下分发给其它电脑"""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def open_batch_window(self):
        """打开批量采集中心窗口：局域网/互联网双模式、端口可配、预设地址、生成自包含部署包"""
        from server import BatchServer, list_reports

        top = tk.Toplevel(self.root)
        top.title("🌐 批量采集中心")
        top.geometry("660x640")
        top.transient(self.root)

        if not hasattr(self, "batch_server") or self.batch_server is None:
            self.batch_server = BatchServer(port=8000)
        if not hasattr(self, "batch_mode"):
            self.batch_mode = "lan"
        if not hasattr(self, "batch_port"):
            self.batch_port = "8000"
        if not hasattr(self, "saved_addresses"):
            self.saved_addresses = self._load_saved_addresses()

        lan_ip = self._detect_lan_ip()
        mode_var = tk.StringVar(value=self.batch_mode)
        port_var = tk.StringVar(value=self.batch_port)
        internet_url_var = tk.StringVar(value="")
        addr_combo_var = tk.StringVar()

        tk.Label(top, text="中心采集服务器", font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=16, pady=(14, 4))

        # 模式选择
        mode_frame = ttk.LabelFrame(top, text="采集模式")
        mode_frame.pack(fill="x", padx=16, pady=(4, 2))
        ttk.Radiobutton(mode_frame, text="局域网（服务器与目标机同一网络，零配置）",
                        variable=mode_var, value="lan", command=lambda: on_mode_or_cfg()).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(mode_frame, text="互联网（服务器有公网IP/域名，可跨网络采集）",
                        variable=mode_var, value="internet", command=lambda: on_mode_or_cfg()).pack(anchor="w", padx=8, pady=2)

        # 端口 + 互联网地址
        cfg_frame = ttk.Frame(top)
        cfg_frame.pack(fill="x", padx=16, pady=4)
        tk.Label(cfg_frame, text="服务器端口：").pack(side="left")
        port_entry = ttk.Entry(cfg_frame, textvariable=port_var, width=10)
        port_entry.pack(side="left", padx=4)
        ttk.Button(cfg_frame, text="应用端口", width=9,
                   command=lambda: (apply_port() and None, refresh_status(), refresh_preview())).pack(side="left", padx=2)
        tk.Label(cfg_frame, text="  公网/服务器地址：").pack(side="left")
        url_entry = ttk.Entry(cfg_frame, textvariable=internet_url_var, width=34)
        url_entry.pack(side="left", fill="x", expand=True)
        # 输入框改动时实时刷新预览（并清除预设选择，因为手动编辑优先）
        port_entry.bind("<KeyRelease>", lambda e: (addr_combo_var.set(""), refresh_preview()))
        url_entry.bind("<KeyRelease>", lambda e: (addr_combo_var.set(""), refresh_preview()))

        # 预设地址（可保存多个、下拉选择）
        addr_frame = ttk.Frame(top)
        addr_frame.pack(fill="x", padx=16, pady=2)
        tk.Label(addr_frame, text="预设地址：").pack(side="left")
        addr_combo = ttk.Combobox(addr_frame, textvariable=addr_combo_var, width=40,
                                  values=self.saved_addresses, state="normal")
        addr_combo.pack(side="left", padx=4)
        ttk.Button(addr_frame, text="应用选中", command=lambda: apply_preset()).pack(side="left", padx=2)
        ttk.Button(addr_frame, text="存为预设", command=lambda: save_preset()).pack(side="left", padx=2)
        ttk.Button(addr_frame, text="删除", command=lambda: del_preset()).pack(side="left", padx=2)

        url_preview_var = tk.StringVar()
        tk.Label(top, textvariable=url_preview_var, fg="#005fb8", font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=2)

        # 部署包选项（部门/使用人，可选）
        opt_frame = ttk.LabelFrame(top, text="部署包选项（部门/使用人可选）")
        opt_frame.pack(fill="x", padx=16, pady=4)
        add_meta_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opt_frame,
            text="生成部署包时填写部门/使用人（勾选后弹窗填写）",
            variable=add_meta_var,
        ).pack(side="left", padx=4)
        tk.Label(opt_frame, text="（不勾选则部署包不含部门/使用人，可之后在软件里补填）",
                 fg="#888").pack(side="left", padx=4)

        def current_server_url():
            port = port_var.get().strip() or "8000"
            if mode_var.get() == "lan":
                return f"http://{lan_ip}:{port}"
            u = internet_url_var.get().strip()
            if not u:
                return ""
            if not u.lower().startswith("http"):
                u = "http://" + u
            return u.rstrip("/")

        def get_target_url():
            """优先使用用户在“预设地址”框里直接输入/选择的地址；否则按上方端口/公网地址推导"""
            typed = (addr_combo_var.get() or "").strip()
            if typed:
                if typed.lower().startswith("http"):
                    return typed.rstrip("/")
                if re.match(r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$", typed):
                    return "http://" + typed
            return current_server_url()

        def refresh_preview():
            u = get_target_url()
            url_preview_var.set(f"目标机将上报到：{u}" if u else "请填写服务器地址（端口或公网地址）")

        def on_mode_or_cfg():
            addr_combo_var.set("")
            refresh_preview()

        def apply_preset():
            v = get_target_url()
            if not v:
                messagebox.showinfo("提示", "请先在预设地址框输入或选择，或上方填写端口/公网地址")
                return
            if _is_lan_url(v):
                mode_var.set("lan")
                m = re.search(r":(\d+)", v)
                port_var.set(m.group(1) if m else "8000")
                internet_url_var.set("")
            else:
                mode_var.set("internet")
                internet_url_var.set(v)
            addr_combo_var.set(v)
            refresh_preview()

        def save_preset():
            u = get_target_url()
            if not u:
                messagebox.showinfo("提示", "请先在预设地址框输入或选择，或上方填写端口/公网地址")
                return
            if u not in self.saved_addresses:
                self.saved_addresses.append(u)
                self._save_saved_addresses()
                addr_combo["values"] = self.saved_addresses
            addr_combo_var.set(u)
            messagebox.showinfo("已保存", f"已把以下地址加入预设：\n{u}")

        def del_preset():
            v = addr_combo_var.get().strip()
            if v in self.saved_addresses:
                self.saved_addresses.remove(v)
                self._save_saved_addresses()
                addr_combo["values"] = self.saved_addresses
                addr_combo_var.set("")
                refresh_preview()

        def apply_port():
            try:
                port = int(port_var.get().strip() or "8000")
            except ValueError:
                port = 8000
            was_running = self.batch_server.is_running()
            if was_running:
                self.batch_server.stop()
            self.batch_server = BatchServer(port=port)
            self.batch_port = str(port)
            self.batch_mode = mode_var.get()
            return was_running

        def save_settings():
            was_running = apply_port()
            if was_running:
                ok, msg = self.batch_server.start()
            else:
                msg = "已保存服务器设置（当前未启动，点『启动服务器』生效）。"
            refresh_status()
            u = current_server_url()
            messagebox.showinfo(
                "已保存",
                f"服务器设置已保存。\n端口：{self.batch_port}\n"
                f"当前服务器地址：{u or '(互联网模式需填写公网地址)'}",
            )

        # 启停服务器
        frm = ttk.Frame(top)
        frm.pack(fill="x", padx=16, pady=6)
        status_var = tk.StringVar(value="服务器未启动")
        tk.Label(frm, textvariable=status_var, fg="#555").pack(side="left")
        toggle_btn = ttk.Button(frm, text="▶ 启动服务器")

        def refresh_status():
            if self.batch_server.is_running():
                status_var.set(f"● 运行中：{self.batch_server.url()}（其它机器访问 {current_server_url()}）")
                toggle_btn.config(text="■ 停止服务器")
            else:
                status_var.set("服务器未启动")
                toggle_btn.config(text="▶ 启动服务器")

        def toggle():
            was_running = apply_port()
            if was_running:
                self.batch_server.stop()
            else:
                ok, msg = self.batch_server.start()
                status_var.set(msg)
            refresh_status()

        toggle_btn.config(command=toggle)
        toggle_btn.pack(side="right")
        ttk.Button(frm, text="💾 保存设置", command=save_settings).pack(side="right", padx=6)

        tip = ("使用方法：\n"
               "1) 选模式、填端口（互联网模式还需填服务器公网地址），点【保存设置】。\n"
               "2) 点【生成部署包】→ 得到 agent_deploy 文件夹（含编译好的 agent.exe，目标机无需装任何环境）。\n"
               "3) 把该文件夹拷到每台目标机，双击 agent.exe 即自动采集并上报。\n"
               "提示：常用地址可点『存为预设』，下次下拉选择即可，无需重复输入。\n"
               "局域网：同 WiFi/网段即可；互联网：服务器需有公网IP或域名（路由器端口映射或云服务器部署 server.py）。")
        tk.Label(top, text=tip, justify="left", wraplength=620, fg="#444",
                 font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=6)

        bf = ttk.Frame(top)
        bf.pack(fill="x", padx=16, pady=6)
        ttk.Button(bf, text="🌐 打开仪表盘", style="Primary.TButton",
                   command=lambda: webbrowser.open(self.batch_server.url())).pack(side="left", padx=4)
        ttk.Button(bf, text="📥 导入已上报数据", style="Normal.TButton",
                   command=lambda: self.import_reports(top)).pack(side="left", padx=4)
        ttk.Button(bf, text="🔄 从服务器同步", style="Normal.TButton",
                   command=lambda: self.sync_from_server(top)).pack(side="left", padx=4)
        def on_generate():
            url = get_target_url()
            if not url:
                messagebox.showerror("错误", "请先在上方设置并保存服务器地址（或在预设地址框输入），再生成部署包。")
                return
            dept = user = ""
            if add_meta_var.get():
                d = simpledialog.askstring("部门", "请输入部署包默认的【部门】：", parent=top)
                if d is None:
                    return  # 用户取消
                u = simpledialog.askstring("使用人", "请输入部署包默认的【使用人】：", parent=top)
                if u is None:
                    return
                dept, user = d.strip(), u.strip()
            # 不勾选 → 部署包不含部门/使用人，且运行 agent 时也不弹窗询问
            no_meta = not add_meta_var.get()
            self.generate_agent_package(top, url, dept, user, no_meta=no_meta)

        ttk.Button(bf, text="📦 一键生成部署包", style="Normal.TButton",
                   command=on_generate).pack(side="left", padx=4)

        cnt_var = tk.StringVar(value="已上报机器数：0")
        tk.Label(top, textvariable=cnt_var, fg="#2e7d32", font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=16, pady=6)

        def update_cnt():
            try:
                cnt_var.set(f"已上报机器数：{len(list_reports())}")
            except Exception:
                cnt_var.set("已上报机器数：?")

        refresh_preview()
        refresh_status()
        update_cnt()

        def tick():
            update_cnt()
            top.after(3000, tick)

        top.after(3000, tick)

    def import_reports(self, parent=None):
        """把服务器收到的上报数据导入到主资产列表（按计算机名称去重/更新）"""
        from server import list_reports

        try:
            reports = list_reports()
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return
        if not reports:
            messagebox.showinfo("提示", "暂无上报数据。请先启动服务器，并让其它电脑运行 agent。")
            return

        existing = {d.get("计算机名称") for d in self.computers_data}
        updated = 0
        for r in reports:
            name = r.get("计算机名称")
            if name in existing:
                for i, d in enumerate(self.computers_data):
                    if d.get("计算机名称") == name:
                        self.computers_data[i] = r
                        updated += 1
                        break
            else:
                self.computers_data.append(r)
                existing.add(name)

        self.refresh_table()
        messagebox.showinfo("完成", f"已汇总 {len(reports)} 台机器的上报数据（其中 {updated} 台为覆盖更新）。")

    def sync_from_server(self, parent=None):
        """从远程中心服务器（HTTP）拉取已上报的机器列表，合并进本机资产列表"""
        from urllib.request import urlopen, Request
        import json as _json

        default = self.batch_server.url() if (hasattr(self, "batch_server") and self.batch_server.is_running()) else ""
        url = simpledialog.askstring(
            "从服务器同步",
            "请输入中心服务器地址（含端口）：\n例如 http://192.168.1.10:8000 或 http://your.domain:8000",
            initialvalue=default, parent=parent or self.root,
        )
        if not url:
            return
        api = url.strip().rstrip("/") + "/api/machines"
        try:
            req = Request(api, headers={"Accept": "application/json"})
            with urlopen(req, timeout=15) as resp:
                machines = _json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            messagebox.showerror(
                "同步失败",
                f"无法连接服务器：\n{e}\n\n请确认：服务器已启动、地址/端口正确、防火墙已放行该端口。",
            )
            return
        if not isinstance(machines, list) or not machines:
            messagebox.showinfo("提示", "服务器暂无上报数据。")
            return
        existing = {d.get("计算机名称") for d in self.computers_data}
        added = updated = 0
        for m in machines:
            name = m.get("计算机名称")
            if not name:
                continue
            if name in existing:
                for i, d in enumerate(self.computers_data):
                    if d.get("计算机名称") == name:
                        self.computers_data[i] = m
                        updated += 1
                        break
            else:
                self.computers_data.append(m)
                existing.add(name)
                added += 1
        self.refresh_table()
        messagebox.showinfo("完成", f"已从服务器同步 {len(machines)} 台机器：\n新增 {added} 台，更新 {updated} 台。")

    def _load_saved_addresses(self):
        from collector import get_data_file_path
        p = get_data_file_path("采集地址.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [str(x) for x in data]
            except Exception:
                pass
        return []

    def _save_saved_addresses(self):
        from collector import get_data_file_path
        p = get_data_file_path("采集地址.json")
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.saved_addresses, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def generate_agent_package(self, parent=None, url="", dept="", user="", no_meta=False):
        """生成自包含部署包：编译好的 agent.exe + 配置文件（含服务器地址/部门/使用人），目标机无需安装任何环境"""
        import shutil
        import time

        if not url:
            messagebox.showerror("错误", "请先在上方设置并保存服务器地址（局域网填端口；互联网填公网地址），再生成部署包。")
            return

        base = os.path.join("agent_deploy")
        os.makedirs(base, exist_ok=True)

        proj_dir = os.path.dirname(os.path.abspath(__file__))
        exe_src = os.path.join(proj_dir, "agent.exe")
        if not os.path.exists(exe_src):
            # 没编译过则现场尝试编译（需要本机有 pyinstaller）
            ok = self._build_agent_exe(proj_dir)
            if not ok or not os.path.exists(exe_src):
                messagebox.showerror(
                    "缺少 agent.exe",
                    "未找到编译好的 agent.exe，且本机无法自动编译。\n"
                    "请在项目目录执行：pyinstaller -F agent.py\n"
                    "生成 agent.exe 后再点【一键生成部署包】。",
                )
                return

        # 拷贝 exe：先写到临时文件再原子替换；若目标 exe 正在运行被系统锁住，
        # 会重试若干次，仍失败则给出明确中文提示，避免生成“半成品”部署包。
        dst_exe = os.path.join(base, "agent.exe")
        tmp_exe = os.path.join(base, "_agent_new.tmp")
        try:
            shutil.copyfile(exe_src, tmp_exe)
        except Exception as e:
            messagebox.showerror("错误", f"读取 agent.exe 失败：{e}")
            return
        replaced = False
        last_err = None
        for _ in range(8):
            try:
                os.replace(tmp_exe, dst_exe)
                replaced = True
                break
            except PermissionError as e:
                last_err = e
                time.sleep(1)  # 等正在运行的旧 agent.exe 退出
            except Exception as e:
                last_err = e
                break
        if not replaced:
            try:
                os.remove(tmp_exe)
            except Exception:
                pass
            messagebox.showerror(
                "无法覆盖 agent.exe",
                "目标 agent_deploy/agent.exe 正在运行或被占用"
                "（很可能你刚才双击运行过它，或它仍在任务管理器里）。\n\n"
                "请先关闭正在运行的 agent.exe（任务管理器结束进程），\n"
                "再点一次【一键生成部署包】即可覆盖更新。",
            )
            return

        # 把品牌库也带过去，保证自定义机型识别可用
        brands_src = os.path.join(proj_dir, "数据存储", "brands.json")
        if os.path.exists(brands_src):
            dest_dir = os.path.join(base, "数据存储")
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.copyfile(brands_src, os.path.join(dest_dir, "brands.json"))
            except Exception:
                pass

        # 写入配置文件（agent.exe 启动即读取，无需命令行参数）
        cfg = {"server": url}
        if dept:
            cfg["department"] = dept
        if user:
            cfg["user"] = user
        if no_meta:
            # 不勾选部门/使用人 → 运行时也不弹窗询问
            cfg["no_meta"] = True
        with open(os.path.join(base, "agent_config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        if no_meta:
            meta_tip = "本次未包含部门/使用人，运行 agent 时也不会弹窗询问（如需填写，可改 agent_config.json 加上 department/user，或用命令行 --dept/--user）。"
        else:
            meta_tip = f"部门：{dept or '（未填写）'}    使用人：{user or '（未填写）'}"

        readme = (
            "计算机资产采集 Agent 部署包（自包含版）\n"
            "======================================\n\n"
            "【本包已编译为独立 exe，目标电脑【无需安装 Python / psutil 等任何环境】】\n\n"
            "【使用方法】\n"
            "1. 把整个 agent_deploy 文件夹拷到目标电脑（U盘/共享/微信都行）。\n"
            "2. 直接双击 agent.exe，自动采集并上报到：\n"
            f"    {url}\n\n"
            f"    {meta_tip}\n\n"
            "【说明】\n"
            "  - 双击 agent.exe 即可，不需要安装、不需要管理员权限。\n"
            "  - 改 agent_config.json 里的 server 可换服务器地址，无需重新生成。\n"
            "  - 也可命令行：agent.exe --server http://地址:端口 --dept 部门 --user 使用人\n"
            "  - 写共享文件夹：agent.exe --share \"\\\\\\\\服务器\\\\共享\\\\reports\"\n"
            "  - 计划任务静默：agent.exe --no-gui\n"
            "  - 运行日志见同目录 agent_log.txt，卡住时看同目录 采集步骤.log 定位卡点。\n"
        )
        with open(os.path.join(base, "README.txt"), "w", encoding="utf-8") as f:
            f.write(readme)

        msg = f"部署包已生成在：\n{base}\n\n目标机将上报到：{url}\n"
        if not no_meta and (dept or user):
            msg += f"部门：{dept or '空'} | 使用人：{user or '空'}\n"
        else:
            msg += "（未设置部门/使用人，运行时不弹窗）\n"
        msg += "\n把整个文件夹拷到每台目标电脑，双击 agent.exe 即可。\n目标电脑无需安装任何环境、无需管理员权限。"
        messagebox.showinfo("完成", msg)

    def _build_agent_exe(self, proj_dir):
        """尝试在本机用 PyInstaller 编译 agent.exe（仅当尚未编译时）"""
        import subprocess
        try:
            py = sys.executable
            subprocess.run(
                [py, "-m", "pip", "install", "--quiet", "pyinstaller"],
                capture_output=True, text=True,
            )
            r = subprocess.run(
                [py, "-m", "PyInstaller", "-F", "--noconsole",
                 "--name", "agent", "agent.py"],
                cwd=proj_dir, capture_output=True, text=True, timeout=300,
            )
            exe = os.path.join(proj_dir, "dist", "agent.exe")
            if os.path.exists(exe):
                shutil_move = os.path.join(proj_dir, "agent.exe")
                shutil.copyfile(exe, shutil_move)
                return True
            return False
        except Exception:
            return False

    def add_custom_brand_mapping(self):
        """录入品牌并存入查询使用的数据库"""
        db = self.collector.brands_db

        # 2. 获取型号输入
        model_input = simpledialog.askstring("录入", "第一步：请输入电脑型号:", parent=self.root)
        if not model_input: return
        model_key = model_input.strip()

        # 3. 【核心修正】精准查重：只检查这个型号是否已经录入过
        # 我们直接看 brands_data 的 values（所有型号列表），不走模糊匹配逻辑
        is_existed = False
        found_brand = ""
        for brand, models in db.brands_data.items():
            if model_key.lower() in [m.lower() for m in models]:
                is_existed = True
                found_brand = brand
                break

        if is_existed:
            messagebox.showinfo("提示", f"型号 [{model_key}] 已存在于品牌 [{found_brand}] 中", parent=self.root)
            return

        # 4. 获取品牌输入
        brand_input = simpledialog.askstring("录入", f"型号 [{model_key}] 对应的品牌是？", parent=self.root)
        if not brand_input: return
        brand_name = brand_input.strip()

        try:
            # 5. 使用同一个 db 对象进行保存
            success, msg = db.add_model_to_brand(brand_name, model_key)

            if success:
                # 6. 强制刷新：使用 db.reload() 即可，简洁且路径统一
                db.reload()
                messagebox.showinfo("成功", f"录入成功！\n型号: {model_key}\n品牌: {brand_name}")
            else:
                messagebox.showerror("失败", msg)

        except Exception as e:
            messagebox.showerror("错误", str(e))

    def add_new_brand_only(self):


        # 1. 弹出输入框
        new_brand = simpledialog.askstring("添加品牌", "请输入要添加的品牌名称:", parent=self.root)

        if not new_brand:
            return

        # 2. 调用数据库方法
        # 注意：这里直接通过 collector 里的 brands_db 实例操作，保证数据同步
        success, msg = self.collector.brands_db.add_pure_brand(new_brand)

        if success:
            # 3. 强制刷新内存
            self.collector.brands_db.reload()
            messagebox.showinfo("成功", f"品牌 [{new_brand}] 已加入数据文件！")
        else:
            messagebox.showwarning("提示", msg)

    def on_closing(self):
        """窗口关闭时的保存提醒"""
        # 弹出提示框：是、否、取消
        msg_box = messagebox.askyesnocancel("退出提醒", "是否保存当前资产数据后再退出？")

        if msg_box is True:  # 用户点击了“是”
            self.save_to_json()  # 调用你现有的保存函数
            self.root.destroy()
        elif msg_box is False:  # 用户点击了“否”
            self.root.destroy()
        else:  # 用户点击了“取消”或直接关闭了弹窗
            pass  # 什么都不做，留在界面上

    def show_all_brands_window(self):
        """显示所有已录入品牌的弹窗"""
        # 1. 从数据库获取所有品牌名称
        # 假设你的 brand_database 实例可以通过 self.collector.brands_db 访问
        all_brands = self.collector.brands_db.get_all_brands()

        if not all_brands:
            messagebox.showinfo("提示", "品牌库目前是空的。")
            return

        # 2. 创建弹窗
        top = tk.Toplevel(self.root)
        top.title("已录入品牌列表")
        # --- 设置窗口大小并计算居中位置 ---
        width = 350
        height = 450

        # 获取屏幕宽高
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()

        # 计算左边距和上边距
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # 应用位置：格式为 "350x450+x+y"
        top.geometry(f"{width}x{height}+{x}+{y}")
        top.transient(self.root)  # 关联主窗口
        # 保持置顶且锁定焦点（推荐，这样用户必须先看它）
        top.transient(self.root)
        top.grab_set()

        # 3. 添加标题
        ttk.Label(top, text=f"当前共有 {len(all_brands)} 个品牌:", font=('微软雅黑', 10, 'bold')).pack(pady=10)

        # 4. 使用带滚动条的文本框展示品牌
        frame = ttk.Frame(top)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        # state='disabled' 是为了防止用户在里面乱打字，但要先 insert 再 disable
        text_area = tk.Text(frame, font=('微软雅黑', 10), yscrollcommand=scrollbar.set, width=30, height=15)
        text_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_area.yview)

        # 5. 逐行插入品牌名称
        for i, brand in enumerate(sorted(all_brands), 1):
            text_area.insert("end", f"{i}. {brand}\n")

        # 设置为只读
        text_area.config(state="disabled")

        # 6. 关闭按钮
        ttk.Button(top, text="关闭", command=top.destroy).pack(pady=10)