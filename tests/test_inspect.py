import signal
import sys
import atexit
import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# 定义控制台控制事件处理函数类型
PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

def cleanup():
    print("程序退出时清理资源...")

# 注册清理函数
atexit.register(cleanup)

def signal_handler(signum, frame):
    print("接收到退出信号，正在清理资源...")
    cleanup()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 处理控制台关闭和关机事件
def console_handler(event):
    if event in (0, 1, 2, 5):
        print("接收到控制台关闭或关机事件")
        cleanup()
        sys.exit(0)
    return True

if sys.platform == 'win32':
    # 设置控制台控制事件处理程序
    handler = PHANDLER_ROUTINE(console_handler)
    if not kernel32.SetConsoleCtrlHandler(handler, True):
        raise ctypes.WinError(ctypes.get_last_error())

if __name__ == "__main__":
    print("程序运行中，可以使用 Ctrl+C、Ctrl+Break 或 taskkill 命令关闭...")
    while True:
        pass
