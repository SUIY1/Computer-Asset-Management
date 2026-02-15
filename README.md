    ComputerAssetTool /
    │
    ├── main.py  # 程序入口（负责启动逻辑）
    ├── gui.py  # UI 界面类（负责画窗口、表格）
    ├── collector.py  # 数据采集类（负责读取硬件信息）
    ├── data_handler.py  # 数据处理类（负责 JSON 保存和 Excel 导出）
    └── utils.py  # 工具函数（负责路径获取、品牌判断等）

打包：python -m nuitka --standalone --onefile --windows-disable-console --enable-plugin=tk-inter --upx-path="upx.exe" --output-dir=dist main.py

python -m nuitka --standalone --onefile --windows-disable-console --enable-plugin=tk-inter --nofollow-import-to=pydantic --output-dir=dist main.py
upx --best main.exe