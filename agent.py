# agent.py
# 轻量级采集端：在任意一台 Windows 电脑上运行，采集本机硬件信息后上报到中心服务器，
# 或写入共享文件夹 / 本机。
# 本文件已设计为可编译成单个 agent.exe（自带 Python 解释器），目标机【无需安装任何环境】。
# 注意：本程序以“当前用户(asInvoker)”权限运行，普通标准用户即可采集与上报，无需管理员。
import argparse
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import datetime

# 让 agent 能 import 同目录下的 collector（源码模式下）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collector import HardwareCollector, set_step_log  # noqa: E402


def app_base_dir():
    """程序根目录：打包成 exe 后为 exe 所在目录，源码模式为脚本目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def config_path():
    """agent_config.json 与 exe 同目录，用于存放服务器地址等配置"""
    return os.path.join(app_base_dir(), "agent_config.json")


def log_path():
    """运行日志：与 exe 同目录，方便排查上报问题（标准用户也有写权限）"""
    return os.path.join(app_base_dir(), "agent_log.txt")


def write_log(msg):
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def load_config():
    p = config_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def collect(dept="", user=""):
    """采集本机硬件信息，附加来源、上报时间、部门/使用人（可选）"""
    data = HardwareCollector.get_hardware_info()
    data["来源"] = "批量上报"
    data["上报时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if dept:
        data["部门"] = dept
    if user:
        data["现使用人"] = user
    return data


def collect_with_watchdog(dept="", user="", timeout=180):
    """
    带总超时看门狗的采集：即使某个系统命令意外卡死（已通过 subprocess timeout 兜底），
    这里也能保证在 timeout 秒后强制中止，不会“永远卡在收集信息这一步”。
    返回 (data, error)；成功时 error 为 None。
    """
    box = {}

    def worker():
        try:
            box["data"] = collect(dept=dept, user=user)
        except Exception as e:  # noqa: BLE001
            box["err"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, (
            f"采集超时：超过 {timeout} 秒仍未完成，疑似某系统命令卡死。"
            f"请打开同目录“采集步骤.log”查看卡在哪一步，并临时关闭杀毒/安全软件后重试。"
        )
    if "err" in box:
        return None, f"采集失败：{box['err']}"
    return box.get("data"), None


def _safe_name(name):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name or "unknown"))


def upload(data, server_url):
    """通过 HTTP POST 上报到中心服务器（/api/report）"""
    import urllib.request

    url = server_url.rstrip("/") + "/api/report"
    req = urllib.request.Request(
        url,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_file(data, folder):
    """把上报数据写成 <计算机名称>.json 到指定目录（用于共享文件夹 / 本机兜底）"""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{_safe_name(data.get('计算机名称'))}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def resolve_servers(args, config):
    """解析上报目标（按优先级，去重）：命令行 --server > 配置 servers 列表 > 配置 server"""
    urls = []
    if args.server:
        urls.append(args.server.strip().rstrip("/"))
    for s in (config.get("servers") or []):
        s = (s or "").strip().rstrip("/")
        if s:
            urls.append(s)
    srv = (config.get("server") or "").strip().rstrip("/")
    if srv:
        urls.append(srv)
    seen = set()
    out = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def do_report(data, servers, args):
    """
    上报到服务器 + 写共享文件夹/本机兜底。
    返回 (ok, msg)：ok 表示至少有一种上报/落盘方式成功。
    """
    ok = False
    err = ""
    for su in servers:
        try:
            r = upload(data, su)
            write_log(f"已上报到 {su}：{r}")
            print(f"[agent] 已上报到 {su}：{r}")
            ok = True
            err = ""
            break
        except Exception as e:
            err = f"上报到 {su} 失败：{e}"
            write_log(err)
            print("[agent]", err)

    if args.share:
        p = write_file(data, args.share)
        write_log(f"已写入共享文件夹：{p}")
        print(f"[agent] 已写入共享文件夹：{p}")
        ok = True
    if args.save_local:
        p = write_file(data, args.save_local)
        write_log(f"已保存到本地：{p}")
        print(f"[agent] 已保存到本地：{p}")
        ok = True

    # 所有方式都没成功：最后兜底写本机 reports 目录
    if not ok:
        p = write_file(data, os.path.join(app_base_dir(), "reports"))
        write_log(f"未上报，已保存到本机：{p}")
        print(f"[agent] 未上报，已保存到：{p}")
        if err:
            err += f"\n数据已存到本机 reports 目录，详见 agent_log.txt。"
        else:
            err = f"未配置可用服务器，已存到本机 reports 目录，详见 agent_log.txt。"
    return ok, err


def ask_server_gui():
    """无参数且无配置时，弹出输入框让用户填写服务器地址"""
    root = tk.Tk()
    root.withdraw()
    url = simpledialog.askstring(
        "服务器地址",
        "未检测到服务器地址，请输入中心采集服务器地址：\n例如 http://192.168.1.10:8000",
    )
    root.destroy()
    return (url or "").strip()


def ask_meta_gui(config):
    """可选填写部门/使用人；点“跳过”返回空。非强制。"""
    root = tk.Tk()
    root.title("补充资产信息（可选）")
    root.geometry("320x170")
    root.resizable(False, False)
    dept_v = tk.StringVar(value=config.get("department", ""))
    user_v = tk.StringVar(value=config.get("user", ""))
    result = {"dept": "", "user": ""}

    tk.Label(root, text="部门 / 使用人（可选，留空则上报时为空）", font=("微软雅黑", 10)).pack(pady=(10, 4))
    f1 = tk.Frame(root)
    f1.pack(fill="x", padx=16)
    tk.Label(f1, text="部门：").pack(side="left")
    tk.Entry(f1, textvariable=dept_v, width=18).pack(side="left", padx=4)
    f2 = tk.Frame(root)
    f2.pack(fill="x", padx=16, pady=4)
    tk.Label(f2, text="使用人：").pack(side="left")
    tk.Entry(f2, textvariable=user_v, width=18).pack(side="left", padx=4)

    def ok():
        result["dept"] = dept_v.get().strip()
        result["user"] = user_v.get().strip()
        root.destroy()

    def skip():
        root.destroy()

    bf = tk.Frame(root)
    bf.pack(pady=10)
    tk.Button(bf, text="确定", width=10, command=ok).pack(side="left", padx=8)
    tk.Button(bf, text="跳过", width=10, command=skip).pack(side="left", padx=8)
    root.mainloop()
    return result["dept"], result["user"]


def notify(title, msg):
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, msg)
        root.destroy()
    except Exception:
        pass


def build_arg_parser():
    ap = argparse.ArgumentParser(description="硬件资产采集 agent（单机部署包版）")
    ap.add_argument("--server", help="中心服务器地址，如 http://192.168.1.10:8000")
    ap.add_argument("--share", help="共享文件夹路径，如 \\\\server\\share\\reports")
    ap.add_argument("--save-local", help="额外保存到本机某个目录")
    ap.add_argument("--dept", help="部门（可选）")
    ap.add_argument("--user", help="使用人（可选）")
    ap.add_argument("--no-gui", action="store_true", help="静默模式，不弹窗（适合计划任务）")
    ap.add_argument("--no-meta", action="store_true", help="不弹窗询问部门/使用人")
    return ap


def run_headless(args, config):
    """命令行 / 计划任务模式：不弹窗，直接采集、上报、写日志。"""
    dept = args.dept or config.get("department", "") or ""
    user = args.user or config.get("user", "") or ""

    set_step_log(os.path.join(app_base_dir(), "采集步骤.log"))
    write_log("开始采集本机硬件信息（分步日志见同目录 采集步骤.log）...")
    try:
        data, cerr = collect_with_watchdog(dept=dept, user=user, timeout=180)
        if data is None:
            raise RuntimeError(cerr or "采集失败")
    except Exception as e:
        msg = f"采集失败：{e}"
        write_log(msg)
        print("[agent]", msg)
        return

    summary = (f"{data.get('品牌')} {data.get('型号')} | 硬盘 {data.get('硬盘')} | "
               f"健康 {data.get('硬盘健康')} | 部门 {data.get('部门', '')} | 使用人 {data.get('现使用人', '')}")
    print(f"[agent] 采集完成：{summary}")
    write_log(f"采集完成：{summary}")

    servers = resolve_servers(args, config)
    # 命令行模式：若完全没有目标，直接落本机 reports（不弹窗）
    if not servers and not args.share and not args.save_local:
        servers = []
    ok, msg = do_report(data, servers, args)
    if ok:
        print("[agent] 上报/保存完成。")
    else:
        print("[agent]", msg)


def run_gui(args, config):
    """
    GUI 模式：单窗口 + mainloop 驱动，采集与上报放入后台线程，
    扫描一完成就立即上报，UI 轮询更新进度，完成后弹结果。
    彻底避免“窗口假死 / 关程序才上传”的问题。
    """
    dept = args.dept or config.get("department", "") or ""
    user = args.user or config.get("user", "") or ""

    # 1) 部门/使用人：命令行 > 配置文件 > 交互询问(可选，非强制，且配置 no_meta 可抑制)
    need_meta = (not dept and not user and not args.no_meta and not config.get("no_meta"))
    if need_meta:
        d, u = ask_meta_gui(config)
        dept, user = d, u

    # 2) 解析上报目标；交互模式下若完全没有目标，先问服务器地址（独立 Tk，用完即销）
    servers = resolve_servers(args, config)
    if not servers and not args.share and not args.save_local:
        url = ask_server_gui()
        if url:
            servers = [url]

    # 3) 单一主窗口（带 mainloop），后台线程负责采集+上报
    root = tk.Tk()
    root.title("资产采集")
    root.geometry("400x130")
    root.resizable(False, False)
    label = tk.Label(
        root,
        text="正在准备采集本机资产信息…",
        font=("微软雅黑", 11),
        padx=12,
        pady=22,
        justify="left",
    )
    label.pack(fill="x")
    root.update()

    set_step_log(os.path.join(app_base_dir(), "采集步骤.log"))
    write_log("开始采集本机硬件信息（分步日志见同目录 采集步骤.log）...")

    state = {}

    def work():
        try:
            data, cerr = collect_with_watchdog(dept=dept, user=user, timeout=180)
            if data is None:
                state["result"] = (False, f"采集失败：{cerr}", "")
                return
            summary = (f"{data.get('品牌')} {data.get('型号')} | 硬盘 {data.get('硬盘')} | "
                       f"健康 {data.get('硬盘健康')} | 部门 {data.get('部门', '')} | 使用人 {data.get('现使用人', '')}")
            write_log(f"采集完成：{summary}")
            ok, msg = do_report(data, servers, args)
            body = summary
            if msg:
                body += f"\n\n{msg}"
            if not ok:
                body += "\n（数据已存到本机 reports 目录，详见 agent_log.txt）"
            state["result"] = (ok, body, summary)
        except Exception as e:  # noqa: BLE001
            state["result"] = (False, f"发生异常：{e}\n详见 agent_log.txt。", "")

    threading.Thread(target=work, daemon=True).start()

    def poll():
        r = state.get("result")
        if r is not None:
            ok, msg, _summary = r
            messagebox.showinfo("采集完成" if ok else "采集完成（未完成上报）", msg)
            root.destroy()
            return
        label.config(
            text="正在采集并上报本机资产信息，请稍候…\n"
                 "（首次运行或少数机器上可能稍慢，属正常现象）"
        )
        root.after(300, poll)

    root.after(300, poll)
    root.mainloop()


def main():
    ap = build_arg_parser()
    args = ap.parse_args()
    config = load_config()

    if args.no_gui:
        run_headless(args, config)
    else:
        run_gui(args, config)


if __name__ == "__main__":
    main()
