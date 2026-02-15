# main.py
import tkinter as tk
from gui import AssetToolGUI
import sys


def main():
    root = tk.Tk()

    # Windows 高 DPI 修复（防止界面模糊）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = AssetToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()