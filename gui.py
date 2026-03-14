# gui.py
from collector import HardwareCollector
from data_handler import DataHandler

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import os
from datetime import datetime





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
            "型号": tk.StringVar(value="-"),
            "品牌": tk.StringVar(value="-"),
            "CPU": tk.StringVar(value="-"),
            "内存": tk.StringVar(value="-"),
            "内存详情": tk.StringVar(value="-"),
            "硬盘": tk.StringVar(value="-"),
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
            "操作系统",
            "CPU",
            "内存",
            "内存详情",
            "硬盘",
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
            "CPU",
            "内存",
            "内存详情",
            "硬盘",
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
            "型号": 140,
            "CPU": 220,
            "内存": 80,
            "内存详情": 180,
            "硬盘": 220,
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
        self.info_vars["型号"].set(info.get('型号', '-'))
        self.info_vars["品牌"].set(info.get('品牌', '-'))
        self.info_vars["CPU"].set(info.get('CPU', '-'))
        self.info_vars["内存"].set(info.get('内存', '-'))
        self.info_vars["内存详情"].set(info.get('内存详情', '-'))
        self.info_vars["硬盘"].set(info.get('硬盘', '-'))
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