import ctypes
from ctypes import wintypes
import base64
import sys

# PowerShell script:
# 1️⃣ Creates a temp folder
# 2️⃣ Downloads and extracts ffmpeg.zip from Gyan.dev (trusted mirror)
# 3️⃣ Moves ffmpeg.exe into C:\Windows\
# 4️⃣ Cleans up temporary files
# 5️⃣ Closes automatically
ps_command = r'''
$temp = "$env:TEMP\ffmpeg"
$zipPath = "$temp\ffmpeg.zip"
$binPath = "$temp\ffmpeg\bin\ffmpeg.exe"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

Write-Host "Downloading FFmpeg..."
New-Item -ItemType Directory -Force -Path $temp | Out-Null
Invoke-WebRequest -Uri $url -OutFile $zipPath

Write-Host "Extracting FFmpeg..."
Expand-Archive -Path $zipPath -DestinationPath $temp -Force

$ffmpegExe = Get-ChildItem -Path $temp -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if ($ffmpegExe) {
    Write-Host "Moving FFmpeg to C:\Windows..."
    Copy-Item $ffmpegExe.FullName "C:\Windows\ffmpeg.exe" -Force
    Write-Host "FFmpeg installed successfully at C:\Windows\ffmpeg.exe"
} else {
    Write-Host "ffmpeg.exe not found after extraction."
}

# Clean up
Remove-Item $temp -Recurse -Force
'''

# Encode PowerShell command (UTF-16LE → base64)
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

def run_powershell_admin_and_wait(ps_args: str):
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"                # Ask for admin permission
    sei.lpFile = "powershell.exe"       # Run PowerShell
    sei.lpParameters = ps_args          # Run encoded command
    sei.lpDirectory = None
    sei.nShow = SW_SHOW
    sei.hInstApp = None
    sei.lpIDList = None
    sei.lpClass = None
    sei.hkeyClass = None
    sei.dwHotKey = 0
    sei.hIcon = None
    sei.hProcess = None

    if not shell32.ShellExecuteExW(ctypes.byref(sei)):
        raise ctypes.WinError()

    # Wait for PowerShell to finish
    if sei.hProcess:
        kernel32.WaitForSingleObject(sei.hProcess, INFINITE)
        exit_code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
        print("PowerShell exited with code:", exit_code.value)
        kernel32.CloseHandle(sei.hProcess)
    else:
        print("Could not get PowerShell process handle.")

if __name__ == "__main__":
    print("Requesting admin privileges and installing FFmpeg...")
    run_powershell_admin_and_wait(ps_args)
    print("Done. FFmpeg should now be available at C:\\Windows\\ffmpeg.exe")

