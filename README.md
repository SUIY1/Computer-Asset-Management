# 💻 Computer-Asset-Management（计算机资产管理系统）

> **面向 IT 运维的 Windows 硬件资产自动采集与集中管理工具**
> 从「一台台手动登记」到「点一下自动盘点 + 网页端统一看板」，把单次资产盘点从 5 分钟压缩到 10 秒以内。

[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

---

## 📌 这个项目解决什么？

日常运维里，给员工电脑建档最头疼三件事：**慢、错、散**。

- **慢**：手动打开「此电脑 / 设备管理器 / 命令提示符」抄配置，一台 5 分钟起步；
- **错**：人抄难免手滑，内存第几代、硬盘是固态还是机械经常写错；
- **散**：数据记在 Excel、微信、脑子里的都有，中心服务器上看不到全貌。

本项目用一组底层 API 自动抓取硬件指纹，再配合 **智能品牌识别算法**，把"杂乱的 OEM 字符串"翻译成人能看懂的品牌型号，最后通过**采集代理 + 中心服务器**把零散数据汇总成一张可导出、可筛选的资产总表。

---

## ✨ 核心功能

### 1. 🖥️ 桌面端（本地工具 · `main.py`）
- **异步深度采集**：程序秒开，后台静默扫描 CPU / 内存（含代数与频率）/ 硬盘（类型 + 容量 + 品牌）/ 主板 / 显卡 / 网卡（IP + MAC）。
- **智能品牌引擎**：内置 43+ 品牌模糊匹配，能从 `TUF GAMING B550M` 这类 OEM 串里识别出「华硕」。
- **引导式录入**：采集完自动弹窗，补上部门、使用人即可入档，不打断思路。
- **可编辑资产表**：双击 / 右键即可改、删任意记录，工具栏按钮齐活。
- **JSON 持久化 + 一键 Excel 导出**：本地先存 JSON 防丢，随时导出标准资产报表。

### 2. 📡 采集代理（部署到员工机 · `agent.py` → `agent.exe`）
把上面那套采集能力打成**单个 exe**，发到每台员工电脑上跑：
- **自动上报**：采集完立刻推送到中心服务器 / 共享文件夹 / 本机指定目录（多目标回退）。
- **静默模式**：`--no-gui --no-meta` 不弹窗、不问部门，适合用**计划任务**定时跑。
- **命令行即配**：部门、使用人、服务器地址都能一条命令传进去，批量下发无压力。

### 3. 🌐 中心服务器（统一看板 · `server.py` / `web_server.py`）
- `server.py`：**零依赖**（纯标准库），`python server.py` 起一个局域网看板，收上报、展示、导出。
- `web_server.py`：**Flask 版**，适合上云，支持搜索筛选、网页端**一键导出 Excel / CSV**（导出内容跟随当前筛选条件）。
- **网页端导出**：不管用哪种服务端，仪表盘上都有「⬇ 导出 Excel / CSV」按钮，和桌面端导出的表完全一致。

### 4. 🛡️ 数据双保险
- 实时 JSON 持久化，断电 / 异常退出不丢数据；
- openpyxl 报表：表头蓝底白字、冻结首行、自动筛选、健康度红底高亮、附带统计工作表。

---

## 🚀 快速开始

### 环境要求
- Windows 10 / 11
- Python 3.8+

### 1. 获取代码
```bash
git clone https://github.com/SUIY1/Computer-Asset-Management.git
cd Computer-Asset-Management
pip install -r requirements.txt
```

### 2. 方案 A：本地桌面工具
```bash
python main.py
```
打开后点「深度采集」→ 自动弹窗填部门/使用人 → 点「导出 Excel」交差。

### 3. 方案 B：中心化部署（推荐多台电脑场景）
```bash
# 在一台"中心服务器"上启动看板（局域网用 server.py，上云用 web_server.py）
python server.py --host 0.0.0.0 --port 8000

# 在每台员工电脑上运行采集代理，把数据上报到上面的地址
agent.exe --server http://192.168.1.10:8000 --dept 财务部 --user 张三
```
浏览器打开 `http://中心服务器IP:8000`，即可看到所有上报设备的汇总表，随时导出 Excel / CSV。

### 4. 打包采集代理（可选 · 以 UPX 压缩为核心）
把 `agent.py` 打成**单个、体积小巧的 `agent.exe`**，发到员工机双击即用（目标机无需安装 Python / psutil 等任何环境）。

本项目采用 **PyInstaller 打包 + UPX 压缩** 的方式——UPX 是体积压缩的核心手段，`agent.spec` 里已写死 `upx=True`：

```bash
# 1) 安装打包器
pip install pyinstaller
# 2)（建议）安装 UPX 并放到 PATH，PyInstaller 会自动调用它做压缩
#    UPX 下载：https://github.com/upx/upx/releases
# 3) 用已配置好的 spec 打包（单文件 + 无控制台 + 启用 UPX 压缩）
pyinstaller agent.spec
# 产物在 dist/agent.exe，经 UPX 压缩通常可降到原体积的 30%~50%
```

> 之后在桌面端点「一键生成部署包」会自动走上面流程，并把 `agent.exe` + 配置 + 品牌库打包成 `agent_deploy/` 目录，可直接分发到各员工机。
>
> 备选：若想进一步压缩，也可走 Nuitka 单文件方式：
> `python -m nuitka --standalone --onefile --windows-disable-console --enable-plugin=tk-inter agent.py`

---

## 🗂 项目结构
```text
├── main.py              # 桌面端启动入口
├── gui.py               # 界面布局与交互逻辑
├── collector.py         # 硬件采集底层模块（WMI / psutil）
├── data_handler.py      # Excel 导出与 JSON 读写
├── brand_database.py    # 品牌匹配算法与数据库（43+ 品牌）
├── agent.py             # 采集代理（可打包为 agent.exe，部署到员工机）
├── server.py            # 中心服务器（纯标准库，零依赖）
├── web_server.py        # 中心服务器（Flask 版，适合上云）
├── agent.spec           # PyInstaller 打包配置
├── requirements.txt     # 依赖列表
├── 网站版部署说明.md      # 网页/云部署详细步骤
├── images/              # 界面截图
└── 数据存储/             # 自动生成：品牌库 + 资产记录 + 上报数据
```

---

## 🛠 技术栈
| 模块 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| 桌面 GUI | Tkinter（自定义样式美化） |
| 硬件采集 | WMI、pywin32、psutil |
| 中心服务端 | 标准库 `http.server`（server.py）/ Flask（web_server.py） |
| 数据处理 | openpyxl、JSON |
| 打包 | PyInstaller + **UPX 压缩**（单文件 `agent.exe`，`agent.spec` 已启用 `upx=True`；Nuitka 备选） |

---

## 🆕 本次更新（v2.0）
- ✅ 新增 **独立采集代理 `agent.py`**：可打包为单文件 exe，部署到员工机自动上报；
- ✅ 新增 **中心服务器**：`server.py`（零依赖）/ `web_server.py`（Flask），收上报 + 看板；
- ✅ 新增 **网页端一键导出 Excel / CSV**：导出内容跟随搜索筛选，与桌面端报表一致；
- ✅ 优化 **导出报表**：表头样式、冻结首行、自动筛选、健康度高亮、统计页；
- ✅ 智能品牌库扩充至 43+ 品牌，支持 GUI 增删。

---

## 📝 说明
本项目由 **SUI缘儿科技** 维护，面向基层 IT 运维工程师，目标是做一个真正好用、能放心交给同事去跑的开源工具。

## 🤝 贡献与支持
- 发现问题或有好点子？欢迎提交 **Issue** 或 **Pull Request**；
- 觉得有用，点个 **Star ⭐** 就是最大的鼓励。

© 2026 SUI缘儿科技

---

## 🌍 English Overview

A Python-based Windows hardware asset collection & centralized management tool. It auto-captures CPU, memory (DDR gen + freq), disks (type + size + brand), mainboard, GPU, IP/MAC, then identifies brands via a fuzzy-match engine.

**Highlights**
- **Desktop tool** (`main.py`): deep scan + editable asset table + one-click Excel export.
- **Collection agent** (`agent.py` → `agent.exe`): deploy to each PC, auto-report to a central server / SMB share / local dir; silent mode (`--no-gui --no-meta`) for scheduled tasks.
- **Central server**: `server.py` (stdlib-only, zero deps) or `web_server.py` (Flask for cloud), both with dashboard + **web Excel/CSV export** that follows the current filter.
- **Brand library**: 43+ brands, GUI-managed.
- **Data safety**: JSON persistence + styled openpyxl export (frozen header, auto-filter, health highlight, summary sheet).

**Quick start**
```bash
pip install -r requirements.txt
python main.py                      # desktop tool
python server.py --port 8000        # central server (LAN)
agent.exe --server http://IP:8000   # report from a client PC
```
