# save as install_yt_dlp_elevated.py and run with python on Windows
import ctypes
from ctypes import wintypes
import base64
import sys

# PowerShell command to run (as a plain string)
ps_command = (
    r'iwr -useb "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" '
    r'-OutFile "C:\Windows\yt-dlp.exe" ; '
    r'if ($LASTEXITCODE -eq 0) { Write-Output "Download finished." } else { Write-Output "Download failed (exit code $LASTEXITCODE)." }'
)

# Encode the PowerShell command in UTF-16LE then base64 (safe for passing to -EncodedCommand)
b64_command = base64.b64encode(ps_command.encode('utf-16-le')).decode('ascii')
ps_args = '-NoProfile -ExecutionPolicy Bypass -EncodedCommand ' + b64_command

# Constants and struct for ShellExecuteEx
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOW = 5
INFINITE = 0xFFFFFFFF

class SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", wintypes.LPVOID),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]

shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

def run_powershell_elevated_and_wait(ps_args: str):
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"                # triggers UAC elevation
    sei.lpFile = "powershell.exe"       # program to run
    sei.lpParameters = ps_args          # arguments to powershell
    sei.lpDirectory = None
    sei.nShow = SW_SHOW
    sei.hInstApp = None
    sei.lpIDList = None
    sei.lpClass = None
    sei.hkeyClass = None
    sei.dwHotKey = 0
    sei.hIcon = None
    sei.hProcess = None

    ok = shell32.ShellExecuteExW(ctypes.byref(sei))
    if not ok:
        raise ctypes.WinError()

    # Wait for the launched process to finish
    hProcess = sei.hProcess
    if not hProcess:
        raise RuntimeError("Could not obtain process handle to wait on.")

    # Wait until the PowerShell process exits
    WAIT_OBJECT_0 = 0x00000000
    res = kernel32.WaitForSingleObject(hProcess, INFINITE)
    if res != WAIT_OBJECT_0:
        # Still return gracefully, but let user know
        print("WaitForSingleObject returned:", res)

    # Optionally check exit code
    exit_code = wintypes.DWORD()
    if kernel32.GetExitCodeProcess(hProcess, ctypes.byref(exit_code)):
        print("Elevated process exit code:", exit_code.value)
    else:
        print("Failed to get exit code.")

    # Close the handle
    kernel32.CloseHandle(hProcess)

if __name__ == "__main__":
    try:
        print("Requesting elevation and running PowerShell...")
        run_powershell_elevated_and_wait(ps_args)
        print("Done.")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

