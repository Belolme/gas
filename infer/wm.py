from typing import Optional

import cv2
import numpy as np
import win32api
import win32com.client
import win32con
import win32gui
import win32print
import win32ui


def switch_to_genshin() -> int:
    # # Make program aware of DPI scaling
    # from ctypes import windll
    # user32 = windll.user32
    # user32.SetProcessDPIAware()
    #
    # or use import pyautogui, it will auto to set DPI awareness.

    hwnd = win32gui.FindWindow(None, "原神")

    if hwnd == 0:
        return 0

    # Send an Alt key press, Magic!!
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys("%")

    win32gui.ShowWindow(hwnd, 9)
    win32gui.SetForegroundWindow(hwnd)

    return hwnd


def get_client_frame(hwnd):
    l, t, r, b = win32gui.GetWindowRect(hwnd)

    scale = get_scaling()
    title_bar_height = int(
        round(win32api.GetSystemMetrics(win32con.SM_CYCAPTION) * scale, 0)
    )
    framex = int(round(win32api.GetSystemMetrics(win32con.SM_CXEDGE) * scale, 0))
    framey = int(round(win32api.GetSystemMetrics(win32con.SM_CYEDGE) * scale, 0))

    return l + framex, t + title_bar_height + framey, r - framex, b - framey


def get_screen_resolution():
    hDC = win32gui.GetDC(0)
    width = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
    height = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
    return width, height


def get_screen_size():
    width = win32api.GetSystemMetrics(0)
    height = win32api.GetSystemMetrics(1)
    return width, height


def get_scaling():
    screen_resolution = get_screen_resolution()
    screen_size = get_screen_size()
    proportion = round(screen_resolution[0] / screen_size[0], 2)
    return proportion


class ScreenshootHandler(object):
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.scale = get_scaling()

        self.window_dc = win32gui.GetWindowDC(self.hwnd)
        self.dc = win32ui.CreateDCFromHandle(self.window_dc)
        self.compatible_dc = self.dc.CreateCompatibleDC()

        self.title_bar_height = int(
            round(win32api.GetSystemMetrics(win32con.SM_CYCAPTION) * self.scale, 0)
        )
        self.framex = int(
            round(win32api.GetSystemMetrics(win32con.SM_CXEDGE) * self.scale, 0)
        )
        self.framey = int(
            round(win32api.GetSystemMetrics(win32con.SM_CYEDGE) * self.scale, 0)
        )

        _, _, width, height = win32gui.GetClientRect(self.hwnd)
        self.width = int(round(width * self.scale, 0))
        self.height = int(round(height * self.scale, 0))

        self.bm = win32ui.CreateBitmap()
        self.bm.CreateCompatibleBitmap(self.dc, self.width, self.height)

    def take(self, path: Optional[str] = None):
        bm_info = self.bm.GetInfo()
        width = bm_info["bmWidth"]
        height = bm_info["bmHeight"]

        self.compatible_dc.SelectObject(self.bm)
        self.compatible_dc.BitBlt(
            (0, 0),
            (width, height),
            self.dc,
            (self.framex, self.title_bar_height + self.framey),
            win32con.SRCCOPY,
        )

        buffer = self.bm.GetBitmapBits(True)
        img = np.frombuffer(buffer, dtype=np.uint8)
        img.shape = (height, width, 4)
        # img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if path is not None:
            cv2.imwrite(
                path,
                img,
                # params= [int(cv2.IMWRITE_JPEG_QUALITY), 9],
            )

        return img

    def close(self):
        win32gui.DeleteObject(self.bm.GetHandle())

        self.compatible_dc.DeleteDC()
        self.dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, self.window_dc)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
